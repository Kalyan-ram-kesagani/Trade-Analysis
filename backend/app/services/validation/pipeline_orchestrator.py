import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.services.backtesting.models import BacktestConfig, BacktestResult
from app.services.backtesting.engine import BacktestingEngine
from app.services.backtesting.data_loader import HistoricalDataLoader
from app.services.validation.oos_engine import OutOfSampleValidationEngine
from app.services.validation.walk_forward_engine import WalkForwardValidationEngine
from app.services.validation.monte_carlo_engine import MonteCarloValidationEngine
from app.services.validation.sensitivity_engine import SensitivityStressValidationEngine
from app.services.risk.validator import DeterministicRiskGateValidator

logger = logging.getLogger(__name__)

class ValidationPipelineOrchestrator:
    """
    Coordinates the full deterministic validation lifecycle of a Strategy Proposal.
    Enforces sequential progression:
    PROPOSED -> BACKTESTED -> OUT_OF_SAMPLE -> WALK_FORWARD -> MONTE_CARLO -> RISK_VALIDATED -> APPROVAL_REQUIRED.
    No stage can be skipped or spoofed. AI CANNOT approve.
    """
    @classmethod
    async def run_full_pipeline(
        cls,
        proposal_id: str,
        account_risk_rules: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        from app.database import AsyncSessionLocal
        from sqlalchemy import text

        async with AsyncSessionLocal() as session:
            # 1. Fetch Proposal
            result = await session.execute(
                text("""
                    SELECT p.*, s.name as strat_name, s.rules as strat_rules, s.risk_parameters as strat_risk
                    FROM strategy_proposals p
                    JOIN strategies s ON s.id = p.strategy_id
                    WHERE p.id = CAST(:proposal_id AS UUID)
                """),
                {"proposal_id": proposal_id}
            )
            row = result.mappings().first()

            if not row:
                raise ValueError(f"Proposal with ID '{proposal_id}' not found.")

            proposal = dict(row)
            strat_rules = proposal["strat_rules"]
            if isinstance(strat_rules, str):
                strat_rules = json.loads(strat_rules)
            strat_rules = strat_rules or []

            strat_risk = proposal["strat_risk"]
            if isinstance(strat_risk, str):
                strat_risk = json.loads(strat_risk)
            strat_risk = strat_risk or {}

            # Extract or synthesize parameters
            parameters = {}
            for r in strat_rules:
                if isinstance(r, dict) and "params" in r:
                    parameters.update(r["params"])

            config = BacktestConfig(
                strategy_id=str(proposal["strategy_id"]),
                proposal_id=str(proposal["id"]),
                account_id=str(proposal["account_id"]) if proposal["account_id"] else None,
                symbol="EURUSD",
                timeframe="H1",
                initial_balance=10000.0,
                risk_per_trade_pct=float(strat_risk.get("max_risk_per_trade_pct", 1.0)),
                parameters=parameters,
            )

            # Strategy Snapshot: Freeze the exact state of the strategy rules and risk at validation time
            strategy_snapshot = {
                "strategy_id": str(proposal["strategy_id"]),
                "name": proposal["strat_name"],
                "version": proposal["proposed_version"],
                "base_version": proposal["base_strategy_version"],
                "rules": strat_rules,
                "risk_parameters": strat_risk,
                "hypothesis": proposal.get("hypothesis", ""),
                "proposed_change": proposal.get("proposed_change", ""),
                "snapshot_time": datetime.now(timezone.utc).isoformat(),
            }

            # Pre-load shared candles
            # Allow fallback ONLY for test environments, but tag production eligibility strictly
            candles, provenance, integrity_report = HistoricalDataLoader.load_candles(
                symbol=config.symbol,
                timeframe=config.timeframe,
                bar_count=800,
                allow_synthetic=True,
                enforce_production_integrity=False # Allow loader to run, but pipeline will block non-eligible data below
            )

            # Stage 1: Deterministic Backtest
            logger.info(f"Pipeline Stage 1: Running Backtest for proposal {proposal_id} [Provenance: {provenance.value}]")
            backtest_res: BacktestResult = BacktestingEngine.run_backtest(config, custom_candles=candles)
            backtest_res.data_provenance = provenance
            backtest_res.production_eligible = integrity_report.production_eligible
            backtest_res.integrity_report = integrity_report
            backtest_json = backtest_res.to_dict()

            # Record run in backtest_runs table
            await session.execute(
                text("""
                    INSERT INTO backtest_runs (
                        proposal_id, strategy_id, account_id, symbol, timeframe,
                        start_time, end_time, initial_balance, parameters,
                        metrics, trades_summary, equity_curve, execution_assumptions, validation_stage,
                        data_provenance, production_eligible, integrity_check_passed, risk_policy_version
                    ) VALUES (
                        CAST(:proposal_id AS UUID), CAST(:strategy_id AS UUID), 
                        CASE WHEN :account_id IS NOT NULL THEN CAST(:account_id AS UUID) ELSE NULL END,
                        :symbol, :timeframe, :start_time, :end_time, :initial_balance,
                        CAST(:parameters AS JSONB), CAST(:metrics AS JSONB), CAST(:trades_summary AS JSONB),
                        CAST(:equity_curve AS JSONB), CAST(:execution_assumptions AS JSONB), 'BACKTEST',
                        :data_provenance, :production_eligible, :integrity_check_passed, 'v1.0'
                    )
                """),
                {
                    "proposal_id": str(proposal["id"]),
                    "strategy_id": str(proposal["strategy_id"]),
                    "account_id": str(proposal["account_id"]) if proposal["account_id"] else None,
                    "symbol": config.symbol,
                    "timeframe": config.timeframe,
                    "start_time": candles[0].time,
                    "end_time": candles[-1].time,
                    "initial_balance": config.initial_balance,
                    "parameters": json.dumps(backtest_json["parameters"]),
                    "metrics": json.dumps(backtest_json["metrics"]),
                    "trades_summary": json.dumps(backtest_json["trades_summary"]),
                    "equity_curve": json.dumps(backtest_json["equity_curve"]),
                    "execution_assumptions": json.dumps(backtest_json["execution_assumptions"]),
                    "data_provenance": provenance.value,
                    "production_eligible": integrity_report.production_eligible,
                    "integrity_check_passed": integrity_report.is_valid,
                }
            )

            # Stage 2: Out of Sample (OOS)
            logger.info(f"Pipeline Stage 2: Running Out of Sample for proposal {proposal_id}")
            oos_res = OutOfSampleValidationEngine.run_validation(config, custom_candles=candles)

            # Stage 3: Walk-Forward Analysis
            logger.info(f"Pipeline Stage 3: Running Walk Forward for proposal {proposal_id}")
            wf_res = WalkForwardValidationEngine.run_validation(config, custom_candles=candles)

            # Stage 4: Monte Carlo Resampling & Risk of Ruin
            logger.info(f"Pipeline Stage 4: Running Monte Carlo for proposal {proposal_id}")
            mc_res = MonteCarloValidationEngine.run_simulation(
                trades=backtest_res.trades,
                initial_balance=config.initial_balance,
                simulations_count=1000
            )

            # Stage 5: Sensitivity & Stress Testing
            logger.info(f"Pipeline Stage 5: Running Sensitivity Stress for proposal {proposal_id}")
            stress_res = SensitivityStressValidationEngine.run_validation(config, custom_candles=candles)

            # Stage 6: Deterministic Risk Gate Validation
            logger.info(f"Pipeline Stage 6: Running Risk Gate for proposal {proposal_id}")
            risk_res = DeterministicRiskGateValidator.validate(
                backtest_result=backtest_res,
                monte_carlo_result=mc_res,
                account_risk_rules=account_risk_rules or strat_risk
            )

            # Hard Production Rules:
            # 1. All quantitative mathematical stages must pass
            # 2. Data MUST be authentic (REAL_MT5 or IMPORTED_HISTORICAL) - Synthetic data can NEVER qualify for live deployment
            # 3. Data integrity checks must have passed
            math_stages_passed = (
                oos_res.get("passed", False) and
                wf_res.get("passed", False) and
                mc_res.get("passed", False) and
                stress_res.get("passed", False) and
                risk_res.get("passed", False)
            )

            is_synthetic = (provenance.value == "SYNTHETIC_TEST")
            production_eligible = math_stages_passed and not is_synthetic and integrity_report.production_eligible

            if not math_stages_passed:
                next_status = "REJECTED"
                rejection_reason = "Failed one or more quantitative validation stages (OOS/WF/MonteCarlo/RiskGate)."
            elif is_synthetic:
                # Synthetic data cannot qualify for live deployment
                next_status = "BACKTESTED" # Frozen at BACKTESTED; cannot advance to APPROVAL_REQUIRED
                rejection_reason = "Synthetic/test data detected. Validated for testing only — strictly prohibited from live production deployment."
            else:
                next_status = "APPROVAL_REQUIRED"
                rejection_reason = None

            # Update proposal in DB
            await session.execute(
                text("""
                    UPDATE strategy_proposals
                    SET status = :status,
                        data_provenance = :data_provenance,
                        production_eligible = :production_eligible,
                        live_deployment_eligible = :live_deployment_eligible,
                        strategy_snapshot = CAST(:strategy_snapshot AS JSONB),
                        backtest_result = CAST(:backtest_result AS JSONB),
                        oos_result = CAST(:oos_result AS JSONB),
                        walkforward_result = CAST(:walkforward_result AS JSONB),
                        montecarlo_result = CAST(:montecarlo_result AS JSONB),
                        risk_validation_result = CAST(:risk_validation_result AS JSONB),
                        rejected_reason = :rejected_reason,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = CAST(:proposal_id AS UUID)
                """),
                {
                    "status": next_status,
                    "data_provenance": provenance.value,
                    "production_eligible": production_eligible,
                    "live_deployment_eligible": production_eligible,
                    "strategy_snapshot": json.dumps(strategy_snapshot),
                    "backtest_result": json.dumps(backtest_json),
                    "oos_result": json.dumps(oos_res),
                    "walkforward_result": json.dumps(wf_res),
                    "montecarlo_result": json.dumps(mc_res),
                    "risk_validation_result": json.dumps(risk_res),
                    "rejected_reason": rejection_reason,
                    "proposal_id": str(proposal["id"]),
                }
            )

            await session.commit()

            return {
                "proposal_id": str(proposal["id"]),
                "status": next_status,
                "all_stages_passed": all_stages_passed,
                "backtest": backtest_json["metrics"],
                "out_of_sample": oos_res,
                "walk_forward": wf_res,
                "monte_carlo": mc_res,
                "sensitivity_stress": stress_res,
                "risk_validation": risk_res,
            }

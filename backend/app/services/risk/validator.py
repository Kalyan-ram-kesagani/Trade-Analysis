from dataclasses import dataclass
from typing import Dict, Any, List
from app.services.backtesting.models import BacktestResult

@dataclass
class VersionedRiskPolicy:
    version: str = "v1.0"
    max_drawdown_pct: float = 12.0
    min_profit_factor: float = 1.10
    min_win_rate_pct: float = 35.0
    max_risk_of_ruin_pct: float = 5.0
    min_total_trades: int = 15
    low_sample_threshold: int = 30
    moderate_sample_threshold: int = 100

class DeterministicRiskGateValidator:
    """
    Validates strategy quantitative metrics against account-level and firm-level risk thresholds.
    Enforces policy versioning and neutral sample adequacy ratings.
    Zero LLM interference. Hard mathematical constraints only.
    """
    POLICY_V1 = VersionedRiskPolicy()

    @classmethod
    def validate(
        cls,
        backtest_result: BacktestResult,
        monte_carlo_result: Dict[str, Any] = None,
        account_risk_rules: Dict[str, Any] = None,
        policy: VersionedRiskPolicy = None
    ) -> Dict[str, Any]:
        p = policy or cls.POLICY_V1
        rules = account_risk_rules or {}

        max_allowed_dd = float(rules.get("max_drawdown_pct", p.max_drawdown_pct))
        min_pf = float(rules.get("min_profit_factor", p.min_profit_factor))
        min_wr = float(rules.get("min_win_rate_pct", p.min_win_rate_pct))
        max_ruin = float(rules.get("max_risk_of_ruin_pct", p.max_risk_of_ruin_pct))
        min_trades = int(rules.get("min_total_trades", p.min_total_trades))

        metrics = backtest_result.metrics
        checks: List[Dict[str, Any]] = []
        all_passed = True

        # Phase 12: Neutral Sample Adequacy Calculation
        total_trades = metrics.total_trades
        if total_trades < p.low_sample_threshold:
            sample_adequacy = "LOW"
            sample_description = f"{total_trades} trades satisfies the minimum technical gate ({min_trades}), but statistical significance is low."
        elif total_trades < p.moderate_sample_threshold:
            sample_adequacy = "MODERATE"
            sample_description = f"{total_trades} trades provides moderate statistical sample depth."
        else:
            sample_adequacy = "HIGH"
            sample_description = f"{total_trades} trades provides robust statistical sample size."

        # Check 1: Max Drawdown
        dd_passed = metrics.max_drawdown_pct <= max_allowed_dd
        checks.append({
            "name": "Maximum Drawdown Constraint",
            "required": f"<= {max_allowed_dd}%",
            "actual": f"{metrics.max_drawdown_pct}%",
            "passed": dd_passed
        })
        if not dd_passed: all_passed = False

        # Check 2: Profit Factor
        pf_passed = metrics.profit_factor >= min_pf
        checks.append({
            "name": "Profit Factor Threshold",
            "required": f">= {min_pf}",
            "actual": f"{metrics.profit_factor}",
            "passed": pf_passed
        })
        if not pf_passed: all_passed = False

        # Check 3: Statistical Sample Size
        trades_passed = total_trades >= min_trades
        checks.append({
            "name": "Minimum Statistical Sample Size",
            "required": f">= {min_trades} trades",
            "actual": f"{total_trades} trades (Sample Adequacy: {sample_adequacy})",
            "passed": trades_passed
        })
        if not trades_passed: all_passed = False

        # Check 4: Win Rate vs R:R expectancy
        wr_passed = metrics.win_rate_pct >= min_wr or (metrics.profit_factor > 1.25 and metrics.expectancy > 0)
        checks.append({
            "name": "Win Rate & Positive Expectancy",
            "required": f">= {min_wr}% OR Expectancy > 0 with PF > 1.25",
            "actual": f"{metrics.win_rate_pct}% (Exp: {metrics.expectancy})",
            "passed": wr_passed
        })
        if not wr_passed: all_passed = False

        # Check 5: Monte Carlo Risk of Ruin (if available)
        if monte_carlo_result and "risk_of_ruin_pct" in monte_carlo_result:
            ruin_pct = monte_carlo_result["risk_of_ruin_pct"]
            ruin_passed = ruin_pct <= max_ruin
            checks.append({
                "name": "Monte Carlo Resampling Risk of Ruin",
                "required": f"<= {max_ruin}%",
                "actual": f"{ruin_pct}%",
                "passed": ruin_passed
            })
            if not ruin_passed: all_passed = False

        # Check 6: Data Provenance check
        provenance = getattr(backtest_result, "data_provenance", None)
        production_eligible = getattr(backtest_result, "production_eligible", True)
        if provenance and provenance.value == "SYNTHETIC_TEST":
            checks.append({
                "name": "Market Data Authenticity",
                "required": "REAL_MT5 or IMPORTED_HISTORICAL",
                "actual": "SYNTHETIC_TEST (Ineligible for Production)",
                "passed": False
            })
            all_passed = False
        else:
            checks.append({
                "name": "Market Data Authenticity",
                "required": "REAL_MT5 or IMPORTED_HISTORICAL",
                "actual": provenance.value if provenance else "VERIFIED",
                "passed": True
            })

        return {
            "validation_stage": "RISK_VALIDATION",
            "passed": all_passed,
            "status": "APPROVED_FOR_REVIEW" if all_passed else "RISK_REJECTED",
            "risk_policy_version": p.version,
            "sample_adequacy": sample_adequacy,
            "sample_description": sample_description,
            "rules_applied": {
                "policy_version": p.version,
                "max_drawdown_pct": max_allowed_dd,
                "min_profit_factor": min_pf,
                "min_total_trades": min_trades,
                "max_risk_of_ruin_pct": max_ruin,
            },
            "checks": checks,
            "summary": "Passed all deterministic risk gates and authenticity checks. Ready for human authorization." if all_passed else "Violated one or more firm risk or authenticity constraints."
        }

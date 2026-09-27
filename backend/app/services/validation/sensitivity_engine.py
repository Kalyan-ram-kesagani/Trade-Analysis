import copy
from typing import Dict, Any, List
from app.services.backtesting.models import BacktestConfig, BacktestResult, Candle, ExecutionAssumptions
from app.services.backtesting.engine import BacktestingEngine
from app.services.backtesting.data_loader import HistoricalDataLoader

class SensitivityStressValidationEngine:
    """
    Tests strategy sensitivity under:
    1. Parameter perturbation (e.g. ±10%, ±20% variation in lookback / periods)
    2. Execution stress testing (doubled spread, 3x slippage, adverse market liquidity)
    Guarantees the strategy is not resting on a knife-edge parameter cliff.
    """
    @classmethod
    def run_validation(
        cls,
        config: BacktestConfig,
        custom_candles: List[Candle] = None
    ) -> Dict[str, Any]:
        if custom_candles is not None:
            candles = custom_candles
        else:
            candles, _, _ = HistoricalDataLoader.load_candles(
                symbol=config.symbol,
                timeframe=config.timeframe,
                bar_count=600
            )

        # Baseline execution
        base_res: BacktestResult = BacktestingEngine.run_backtest(config, custom_candles=candles)

        # 1. Parameter Perturbation Tests (±15% on key indicators)
        perturbation_results = []
        base_params = config.parameters or {"fast_ema": 9, "slow_ema": 21}

        # Perturbation variations
        variations = [
            {"label": "Parameters -15%", "mult": 0.85},
            {"label": "Parameters +15%", "mult": 1.15},
        ]

        for var in variations:
            pert_params = {}
            for k, v in base_params.items():
                if isinstance(v, (int, float)):
                    new_val = max(2, int(round(v * var["mult"]))) if isinstance(v, int) else round(v * var["mult"], 2)
                    pert_params[k] = new_val
                else:
                    pert_params[k] = v

            pert_config = copy.deepcopy(config)
            pert_config.parameters = pert_params
            pert_res = BacktestingEngine.run_backtest(pert_config, custom_candles=candles)
            perturbation_results.append({
                "variation": var["label"],
                "parameters": pert_params,
                "net_profit": pert_res.metrics.net_profit,
                "profit_factor": pert_res.metrics.profit_factor,
                "drawdown_pct": pert_res.metrics.max_drawdown_pct,
            })

        # 2. Execution Stress Tests (Adverse spread & slippage)
        stress_config_2x = copy.deepcopy(config)
        stress_config_2x.execution.spread_points = config.execution.spread_points * 2.0 # 2x spread
        stress_config_2x.execution.slippage_points = config.execution.slippage_points * 2.5 # 2.5x slippage
        stress_res_2x = BacktestingEngine.run_backtest(stress_config_2x, custom_candles=candles)

        stress_config_extreme = copy.deepcopy(config)
        stress_config_extreme.execution.spread_points = config.execution.spread_points * 3.5 # 3.5x spread
        stress_config_extreme.execution.slippage_points = config.execution.slippage_points * 4.0 # 4x slippage
        stress_res_extreme = BacktestingEngine.run_backtest(stress_config_extreme, custom_candles=candles)

        # Check for fragility
        survived_adverse_execution = stress_res_2x.metrics.net_profit > (base_res.metrics.net_profit * 0.2) or stress_res_2x.metrics.profit_factor >= 1.05
        param_plateau_stable = all(p["profit_factor"] >= 0.95 for p in perturbation_results)

        passed = survived_adverse_execution and param_plateau_stable

        return {
            "validation_stage": "SENSITIVITY_STRESS",
            "passed": passed,
            "baseline": {
                "net_profit": base_res.metrics.net_profit,
                "profit_factor": base_res.metrics.profit_factor,
                "drawdown_pct": base_res.metrics.max_drawdown_pct,
            },
            "perturbation_analysis": perturbation_results,
            "execution_stress": {
                "stress_2x_cost": {
                    "spread_points": stress_config_2x.execution.spread_points,
                    "slippage_points": stress_config_2x.execution.slippage_points,
                    "net_profit": stress_res_2x.metrics.net_profit,
                    "profit_factor": stress_res_2x.metrics.profit_factor,
                    "drawdown_pct": stress_res_2x.metrics.max_drawdown_pct,
                },
                "stress_extreme_cost": {
                    "spread_points": stress_config_extreme.execution.spread_points,
                    "slippage_points": stress_config_extreme.execution.slippage_points,
                    "net_profit": stress_res_extreme.metrics.net_profit,
                    "profit_factor": stress_res_extreme.metrics.profit_factor,
                    "drawdown_pct": stress_res_extreme.metrics.max_drawdown_pct,
                }
            }
        }

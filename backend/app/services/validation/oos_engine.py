from typing import Dict, Any, List
from app.services.backtesting.models import BacktestConfig, BacktestResult, Candle
from app.services.backtesting.engine import BacktestingEngine
from app.services.backtesting.data_loader import HistoricalDataLoader

class OutOfSampleValidationEngine:
    """
    Splits historical candle data chronologically into In-Sample (IS) and Out-Of-Sample (OOS).
    Evaluates parameter stability and detects severe curve-fitting/overfitting.
    Strictly deterministic.
    """
    @classmethod
    def run_validation(
        cls,
        config: BacktestConfig,
        split_ratio: float = 0.70, # 70% In-Sample, 30% Out-Of-Sample
        custom_candles: List[Candle] = None
    ) -> Dict[str, Any]:
        if custom_candles is not None:
            candles = custom_candles
        else:
            candles, _, _ = HistoricalDataLoader.load_candles(
                symbol=config.symbol,
                timeframe=config.timeframe,
                bar_count=700
            )

        total_bars = len(candles)
        if total_bars < 100:
            raise ValueError(f"Insufficient bars ({total_bars}) for robust OOS validation (minimum 100 required)")

        split_idx = int(total_bars * split_ratio)
        is_candles = candles[:split_idx]
        oos_candles = candles[split_idx:]

        # Run In-Sample backtest
        is_result: BacktestResult = BacktestingEngine.run_backtest(config, custom_candles=is_candles)
        # Run Out-Of-Sample backtest with FROZEN parameters
        oos_result: BacktestResult = BacktestingEngine.run_backtest(config, custom_candles=oos_candles)

        # Performance Degradation & Efficiency Metrics
        is_pf = is_result.metrics.profit_factor
        oos_pf = oos_result.metrics.profit_factor
        is_sharpe = is_result.metrics.sharpe_ratio
        oos_sharpe = oos_result.metrics.sharpe_ratio

        # Walk-forward efficiency ratio (WFE) = OOS annual return / IS annual return
        # Here we approximate with Profit Factor & Sharpe degradation
        pf_retention_pct = round((oos_pf / is_pf) * 100.0, 2) if is_pf > 0 else 0.0
        sharpe_retention_pct = round((oos_sharpe / is_sharpe) * 100.0, 2) if is_sharpe > 0 else 0.0

        # Degradation checks
        is_overfit = False
        degradation_warnings: List[str] = []

        if oos_result.metrics.net_profit < 0 and is_result.metrics.net_profit > 0:
            is_overfit = True
            degradation_warnings.append("OOS Net Profit collapsed into negative territory.")

        if pf_retention_pct < 50.0:
            is_overfit = True
            degradation_warnings.append(f"Profit Factor degraded significantly ({pf_retention_pct}% of IS).")

        if oos_result.metrics.max_drawdown_pct > (is_result.metrics.max_drawdown_pct * 1.8):
            is_overfit = True
            degradation_warnings.append("OOS Drawdown exceeded 1.8x the In-Sample drawdown.")

        passed = not is_overfit and (oos_result.metrics.net_profit >= 0 or oos_result.metrics.profit_factor >= 1.05)

        return {
            "validation_stage": "OUT_OF_SAMPLE",
            "passed": passed,
            "split_ratio": split_ratio,
            "in_sample_bars": len(is_candles),
            "out_of_sample_bars": len(oos_candles),
            "in_sample": {
                "net_profit": is_result.metrics.net_profit,
                "profit_factor": is_result.metrics.profit_factor,
                "win_rate_pct": is_result.metrics.win_rate_pct,
                "sharpe_ratio": is_result.metrics.sharpe_ratio,
                "max_drawdown_pct": is_result.metrics.max_drawdown_pct,
                "total_trades": is_result.metrics.total_trades,
            },
            "out_of_sample": {
                "net_profit": oos_result.metrics.net_profit,
                "profit_factor": oos_result.metrics.profit_factor,
                "win_rate_pct": oos_result.metrics.win_rate_pct,
                "sharpe_ratio": oos_result.metrics.sharpe_ratio,
                "max_drawdown_pct": oos_result.metrics.max_drawdown_pct,
                "total_trades": oos_result.metrics.total_trades,
            },
            "retention": {
                "pf_retention_pct": pf_retention_pct,
                "sharpe_retention_pct": sharpe_retention_pct,
            },
            "warnings": degradation_warnings,
            "sample_oos_trades": [
                {
                    "ticket": t.ticket,
                    "direction": t.direction.value,
                    "net_pl": t.net_pl,
                    "exit_reason": t.exit_reason.value if t.exit_reason else None,
                }
                for t in oos_result.trades[-10:]
            ]
        }

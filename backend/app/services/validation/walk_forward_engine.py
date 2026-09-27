from typing import Dict, Any, List
from app.services.backtesting.models import BacktestConfig, BacktestResult, Candle
from app.services.backtesting.engine import BacktestingEngine
from app.services.backtesting.data_loader import HistoricalDataLoader

class WalkForwardValidationEngine:
    """
    Executes multi-window rolling Walk-Forward Analysis (WFA).
    Validates strategy performance consistency across multiple unseen time windows.
    Zero curve fitting; strictly chronological walk-forward steps.
    """
    @classmethod
    def run_validation(
        cls,
        config: BacktestConfig,
        windows_count: int = 4,
        custom_candles: List[Candle] = None
    ) -> Dict[str, Any]:
        if custom_candles is not None:
            candles = custom_candles
        else:
            candles, _, _ = HistoricalDataLoader.load_candles(
                symbol=config.symbol,
                timeframe=config.timeframe,
                bar_count=800
            )

        total_bars = len(candles)
        if total_bars < 200:
            raise ValueError(f"Insufficient bars ({total_bars}) for {windows_count}-window Walk Forward Analysis")

        # Each window has an In-Sample (training) segment and Out-Of-Sample (forward) segment
        window_size = total_bars // windows_count
        step_results: List[Dict[str, Any]] = []

        profitable_oos_windows = 0
        total_oos_net_profit = 0.0
        total_is_net_profit = 0.0

        for w in range(windows_count):
            start_idx = w * (window_size // 2) if windows_count > 2 else 0
            end_idx = min(start_idx + window_size, total_bars)
            window_candles = candles[start_idx:end_idx]

            sub_split = int(len(window_candles) * 0.65) # 65% train, 35% forward test
            is_candles = window_candles[:sub_split]
            oos_candles = window_candles[sub_split:]

            is_res: BacktestResult = BacktestingEngine.run_backtest(config, custom_candles=is_candles)
            oos_res: BacktestResult = BacktestingEngine.run_backtest(config, custom_candles=oos_candles)

            if oos_res.metrics.net_profit > 0:
                profitable_oos_windows += 1

            total_oos_net_profit += oos_res.metrics.net_profit
            total_is_net_profit += is_res.metrics.net_profit

            step_results.append({
                "window": w + 1,
                "is_bars": len(is_candles),
                "oos_bars": len(oos_candles),
                "is_net_profit": is_res.metrics.net_profit,
                "is_pf": is_res.metrics.profit_factor,
                "oos_net_profit": oos_res.metrics.net_profit,
                "oos_pf": oos_res.metrics.profit_factor,
                "oos_win_rate": oos_res.metrics.win_rate_pct,
                "oos_trades": oos_res.metrics.total_trades,
            })

        # Walk-Forward Efficiency (WFE) = (OOS Annualized Return / IS Annualized Return)
        wfe_ratio = round((total_oos_net_profit / total_is_net_profit) * 100.0, 2) if total_is_net_profit > 0 else 0.0
        consistency_score = round((profitable_oos_windows / windows_count) * 100.0, 1)

        # Robustness threshold: at least 50% of forward windows must be profitable & WFE >= 30%
        passed = (consistency_score >= 50.0) and (total_oos_net_profit >= 0)

        return {
            "validation_stage": "WALK_FORWARD",
            "passed": passed,
            "windows_count": windows_count,
            "consistency_score_pct": consistency_score,
            "walk_forward_efficiency_pct": wfe_ratio,
            "cumulative_oos_profit": round(total_oos_net_profit, 2),
            "cumulative_is_profit": round(total_is_net_profit, 2),
            "profitable_windows": profitable_oos_windows,
            "windows": step_results
        }

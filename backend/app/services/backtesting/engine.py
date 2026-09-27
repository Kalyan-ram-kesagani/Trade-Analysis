import logging
from typing import Optional, List
from .models import BacktestConfig, BacktestResult, Candle
from .data_loader import HistoricalDataLoader
from .simulator import BarByBarSimulator
from .metrics import FinancialMetricsCalculator

logger = logging.getLogger(__name__)

class BacktestingEngine:
    """
    Orchestrates the end-to-end execution of deterministic strategy backtests.
    Combines data loading, bar-by-bar simulation, and financial metrics calculation.
    """
    @classmethod
    def run_backtest(
        cls,
        config: BacktestConfig,
        custom_candles: Optional[List[Candle]] = None
    ) -> BacktestResult:
        logger.info(f"Initiating Backtest for Symbol={config.symbol}, TF={config.timeframe}")

        # 1. Load historical candles
        provenance = None
        report = None
        if custom_candles is not None:
            candles = custom_candles
            from .models import DataProvenance
            provenance = DataProvenance.IMPORTED_HISTORICAL
            report = HistoricalDataLoader.validate_data_integrity(candles, provenance)
        else:
            candles, provenance, report = HistoricalDataLoader.load_candles(
                symbol=config.symbol,
                timeframe=config.timeframe,
                start_time=config.start_time,
                end_time=config.end_time,
                bar_count=600
            )

        if not candles:
            raise ValueError(f"No candle data available for backtesting {config.symbol}")

        if report and not report.is_valid:
            raise ValueError(f"Data integrity validation failed: {report.errors}")

        # 2. Run deterministic bar simulation
        simulator = BarByBarSimulator(config, candles)
        trades, equity_curve = simulator.run()

        # 3. Calculate quantitative metrics
        metrics = FinancialMetricsCalculator.calculate(
            initial_balance=config.initial_balance,
            trades=trades,
            equity_curve=equity_curve,
            risk_free_rate=config.execution.risk_free_rate
        )

        return BacktestResult(
            config=config,
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve,
            validation_stage="BACKTEST",
            data_provenance=provenance,
            production_eligible=report.production_eligible if report else False,
            integrity_report=report
        )


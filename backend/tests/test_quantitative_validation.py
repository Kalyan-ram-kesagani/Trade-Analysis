"""
Comprehensive Quantitative Validation & Backtesting Test Suite
Tests pure mathematical calculation, data loading, backtest simulation,
OOS, Walk-Forward, Monte Carlo, and Risk Gate logic.
Zero LLM dependencies.
"""

import unittest
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.backtesting.models import (
    BacktestConfig, Candle, SimulatedTrade, TradeDirection, ExitReason, ExecutionAssumptions, EquityPoint, DataProvenance
)
from app.services.backtesting.execution_model import RealisticExecutionModel
from app.services.backtesting.metrics import FinancialMetricsCalculator
from app.services.backtesting.data_loader import HistoricalDataLoader
from app.services.backtesting.simulator import BarByBarSimulator
from app.services.backtesting.engine import BacktestingEngine
from app.services.validation.oos_engine import OutOfSampleValidationEngine
from app.services.validation.walk_forward_engine import WalkForwardValidationEngine
from app.services.validation.monte_carlo_engine import MonteCarloValidationEngine
from app.services.validation.sensitivity_engine import SensitivityStressValidationEngine
from app.services.risk.validator import DeterministicRiskGateValidator

class TestQuantitativeValidation(unittest.TestCase):

    def setUp(self):
        self.assumptions = ExecutionAssumptions(
            spread_points=15.0,
            point_size=0.0001,
            contract_size=100000.0,
            commission_per_lot=7.0,
            slippage_points=5.0,
            enable_slippage=True
        )
        self.execution = RealisticExecutionModel(self.assumptions)

    def test_execution_model_position_sizing(self):
        """Test position size calculation from risk % and stop loss distance."""
        balance = 10000.0
        risk_pct = 1.0 # $100 risk
        entry = 1.0850
        sl = 1.0800 # 50 pips distance = 0.0050 * 100000 = $500 per lot
        # Expected lot: 100 / 500 = 0.20 lots
        lot = self.execution.calculate_position_size(balance, risk_pct, entry, sl)
        self.assertEqual(lot, 0.20)

    def test_execution_model_fill_prices(self):
        """Ensure spreads and slippage penalize entries and exits deterministically."""
        entry_buy = self.execution.get_entry_fill_price(TradeDirection.BUY, 1.0850)
        # Expected: 1.0850 + half_spread (0.00075) + slippage (0.0005) = 1.08625
        self.assertAlmostEqual(entry_buy, 1.08625, places=5)

        entry_sell = self.execution.get_entry_fill_price(TradeDirection.SELL, 1.0850)
        # Expected: 1.0850 - half_spread (0.00075) - slippage (0.0005) = 1.08375
        self.assertAlmostEqual(entry_sell, 1.08375, places=5)

    def test_financial_metrics_calculation(self):
        """Test pure Python financial metrics calculation with known trades."""
        now = datetime.utcnow()
        t1 = SimulatedTrade(
            ticket=1, symbol="EURUSD", direction=TradeDirection.BUY, lot_size=1.0,
            entry_time=now, entry_price=1.0800, exit_time=now + timedelta(hours=1), exit_price=1.0850,
            gross_pl=500.0, commission=7.0, slippage_cost=10.0, net_pl=483.0, return_pct=4.83
        )
        t2 = SimulatedTrade(
            ticket=2, symbol="EURUSD", direction=TradeDirection.BUY, lot_size=1.0,
            entry_time=now, entry_price=1.0850, exit_time=now + timedelta(hours=1), exit_price=1.0820,
            gross_pl=-300.0, commission=7.0, slippage_cost=10.0, net_pl=-317.0, return_pct=-3.17
        )

        equity_curve = [
            EquityPoint(timestamp=now, equity=10000.0, drawdown_pct=0.0, open_positions=0),
            EquityPoint(timestamp=now + timedelta(hours=1), equity=10483.0, drawdown_pct=0.0, open_positions=0),
            EquityPoint(timestamp=now + timedelta(hours=2), equity=10166.0, drawdown_pct=3.02, open_positions=0),
        ]

        metrics = FinancialMetricsCalculator.calculate(10000.0, [t1, t2], equity_curve)

        self.assertEqual(metrics.total_trades, 2)
        self.assertEqual(metrics.winning_trades, 1)
        self.assertEqual(metrics.losing_trades, 1)
        self.assertEqual(metrics.win_rate_pct, 50.0)
        self.assertAlmostEqual(metrics.net_profit, 166.0, places=2)
        self.assertAlmostEqual(metrics.profit_factor, round(483.0 / 317.0, 2), places=2)

    def test_historical_data_loader(self):
        """Test data loader delivers deterministic sequence with consistent PRNG seed."""
        candles_a, prov_a, report_a = HistoricalDataLoader.load_candles("EURUSD", "H1", bar_count=100, random_seed=999)
        candles_b, prov_b, report_b = HistoricalDataLoader.load_candles("EURUSD", "H1", bar_count=100, random_seed=999)

        self.assertEqual(len(candles_a), 100)
        self.assertEqual(len(candles_b), 100)
        self.assertEqual(candles_a[0].close, candles_b[0].close)
        self.assertEqual(candles_a[-1].close, candles_b[-1].close)

    def test_backtest_engine_run(self):
        """Test full backtest engine execution and trade generation."""
        config = BacktestConfig(
            symbol="EURUSD",
            timeframe="H1",
            initial_balance=10000.0,
            risk_per_trade_pct=1.0,
            parameters={"fast_ema": 9, "slow_ema": 21, "atr_multiplier": 2.0}
        )
        res = BacktestingEngine.run_backtest(config)

        self.assertIsNotNone(res)
        self.assertGreater(len(res.equity_curve), 0)
        self.assertEqual(res.validation_stage, "BACKTEST")
        self.assertIsInstance(res.metrics.profit_factor, float)

    def test_oos_validation_engine(self):
        """Test 70/30 out-of-sample data splitting and evaluation."""
        config = BacktestConfig(symbol="EURUSD", timeframe="H1")
        oos_res = OutOfSampleValidationEngine.run_validation(config, split_ratio=0.70)

        self.assertEqual(oos_res["validation_stage"], "OUT_OF_SAMPLE")
        self.assertIn("passed", oos_res)
        self.assertIn("in_sample", oos_res)
        self.assertIn("out_of_sample", oos_res)
        self.assertIn("retention", oos_res)

    def test_walk_forward_validation_engine(self):
        """Test multi-window walk forward execution."""
        config = BacktestConfig(symbol="EURUSD", timeframe="H1")
        wf_res = WalkForwardValidationEngine.run_validation(config, windows_count=3)

        self.assertEqual(wf_res["validation_stage"], "WALK_FORWARD")
        self.assertEqual(wf_res["windows_count"], 3)
        self.assertEqual(len(wf_res["windows"]), 3)
        self.assertIn("consistency_score_pct", wf_res)

    def test_monte_carlo_resampling(self):
        """Test Monte Carlo trade resampling and risk of ruin confidence intervals."""
        now = datetime.utcnow()
        # Seed 10 sample trades (7 wins, 3 losses)
        trades = []
        for i in range(7):
            trades.append(SimulatedTrade(
                ticket=i, symbol="EURUSD", direction=TradeDirection.BUY, lot_size=0.1,
                entry_time=now, entry_price=1.08, exit_time=now, exit_price=1.09,
                gross_pl=100.0, commission=1.0, slippage_cost=1.0, net_pl=98.0, return_pct=1.0
            ))
        for i in range(7, 10):
            trades.append(SimulatedTrade(
                ticket=i, symbol="EURUSD", direction=TradeDirection.BUY, lot_size=0.1,
                entry_time=now, entry_price=1.08, exit_time=now, exit_price=1.075,
                gross_pl=-50.0, commission=1.0, slippage_cost=1.0, net_pl=-52.0, return_pct=-0.5
            ))

        mc_res = MonteCarloValidationEngine.run_simulation(trades, simulations_count=500)

        self.assertEqual(mc_res["validation_stage"], "MONTE_CARLO")
        self.assertEqual(mc_res["simulations_count"], 500)
        self.assertIn("drawdown_confidence_intervals", mc_res)
        self.assertIn("profit_confidence_intervals", mc_res)
        self.assertLessEqual(mc_res["risk_of_ruin_pct"], 10.0)

    def test_sensitivity_stress_engine(self):
        """Test parameter perturbation and adverse execution stress testing."""
        config = BacktestConfig(symbol="EURUSD", timeframe="H1")
        stress_res = SensitivityStressValidationEngine.run_validation(config)

        self.assertEqual(stress_res["validation_stage"], "SENSITIVITY_STRESS")
        self.assertIn("perturbation_analysis", stress_res)
        self.assertIn("execution_stress", stress_res)

    def test_deterministic_risk_gate_validator(self):
        """Test risk limits strictly pass or fail based on thresholds."""
        config = BacktestConfig()
        res = BacktestingEngine.run_backtest(config)

        # Force metric to breach max drawdown constraint
        res.metrics.max_drawdown_pct = 25.0
        risk_res = DeterministicRiskGateValidator.validate(
            res,
            account_risk_rules={"max_drawdown_pct": 10.0}
        )

        self.assertFalse(risk_res["passed"])
        self.assertEqual(risk_res["status"], "RISK_REJECTED")

        # Now set conservative drawdown within limits and tag real provenance
        res.data_provenance = DataProvenance.REAL_MT5
        res.production_eligible = True
        res.metrics.max_drawdown_pct = 4.5
        res.metrics.profit_factor = 1.65
        res.metrics.total_trades = 30
        res.metrics.win_rate_pct = 55.0
        risk_res_pass = DeterministicRiskGateValidator.validate(
            res,
            account_risk_rules={"max_drawdown_pct": 10.0, "min_profit_factor": 1.20, "min_total_trades": 10}
        )
        self.assertTrue(risk_res_pass["passed"])
        self.assertEqual(risk_res_pass["status"], "APPROVED_FOR_REVIEW")



if __name__ == '__main__':
    unittest.main()

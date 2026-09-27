from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from .models import (
    Candle, BacktestConfig, SimulatedTrade, EquityPoint,
    TradeDirection, ExitReason
)
from .execution_model import RealisticExecutionModel

class TechnicalIndicators:
    """Pure mathematical indicator calculations on candle sequences"""
    @staticmethod
    def sma(values: List[float], period: int) -> List[Optional[float]]:
        out: List[Optional[float]] = []
        for i in range(len(values)):
            if i + 1 < period:
                out.append(None)
            else:
                out.append(sum(values[i + 1 - period : i + 1]) / period)
        return out

    @staticmethod
    def ema(values: List[float], period: int) -> List[Optional[float]]:
        out: List[Optional[float]] = []
        multiplier = 2.0 / (period + 1)
        prev_ema: Optional[float] = None
        for i, val in enumerate(values):
            if i + 1 < period:
                out.append(None)
            elif prev_ema is None:
                sma_init = sum(values[:period]) / period
                prev_ema = sma_init
                out.append(prev_ema)
            else:
                curr_ema = (val - prev_ema) * multiplier + prev_ema
                prev_ema = curr_ema
                out.append(curr_ema)
        return out

    @staticmethod
    def rsi(closes: List[float], period: int = 14) -> List[Optional[float]]:
        out: List[Optional[float]] = [None] * len(closes)
        if len(closes) <= period:
            return out

        gains = []
        losses = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            gains.append(max(0.0, diff))
            losses.append(max(0.0, -diff))

        if len(gains) < period:
            return out

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        rs = avg_gain / avg_loss if avg_loss > 0 else 100.0
        out[period] = 100.0 - (100.0 / (1.0 + rs))

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            rs = avg_gain / avg_loss if avg_loss > 0 else 100.0
            out[i + 1] = 100.0 - (100.0 / (1.0 + rs))

        return out

    @staticmethod
    def bollinger_bands(closes: List[float], period: int = 20, std_dev_mult: float = 2.0) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
        sma = TechnicalIndicators.sma(closes, period)
        upper: List[Optional[float]] = []
        lower: List[Optional[float]] = []

        for i in range(len(closes)):
            mid = sma[i]
            if mid is None:
                upper.append(None)
                lower.append(None)
            else:
                window = closes[i + 1 - period : i + 1]
                variance = sum((x - mid) ** 2 for x in window) / period
                std = variance ** 0.5
                upper.append(mid + std * std_dev_mult)
                lower.append(mid - std * std_dev_mult)
        return upper, sma, lower

    @staticmethod
    def atr(candles: List[Candle], period: int = 14) -> List[Optional[float]]:
        trs: List[float] = []
        for i, c in enumerate(candles):
            if i == 0:
                trs.append(c.high - c.low)
            else:
                prev_c = candles[i - 1]
                tr = max(c.high - c.low, abs(c.high - prev_c.close), abs(c.low - prev_c.close))
                trs.append(tr)
        return TechnicalIndicators.sma(trs, period)


class BarByBarSimulator:
    """
    Simulates strategy execution candle by candle.
    Prevents lookahead bias by strictly acting on closed bar information or bar open.
    """
    def __init__(self, config: BacktestConfig, candles: List[Candle]):
        self.config = config
        self.candles = candles
        self.execution = RealisticExecutionModel(config.execution)

    def run(self) -> Tuple[List[SimulatedTrade], List[EquityPoint]]:
        if not self.candles:
            return [], []

        closes = [c.close for c in self.candles]
        params = self.config.parameters or {}

        # Indicators setup based on parameters
        fast_ema_period = int(params.get("fast_ema", params.get("lookback", 9)))
        slow_ema_period = int(params.get("slow_ema", 21))
        rsi_period = int(params.get("rsi_period", 14))
        atr_period = int(params.get("atr_period", 14))
        atr_mult = float(params.get("atr_multiplier", 2.0))

        fast_ema = TechnicalIndicators.ema(closes, fast_ema_period)
        slow_ema = TechnicalIndicators.ema(closes, slow_ema_period)
        rsi = TechnicalIndicators.rsi(closes, rsi_period)
        atr = TechnicalIndicators.atr(self.candles, atr_period)
        upper_bb, mid_bb, lower_bb = TechnicalIndicators.bollinger_bands(closes, 20, 2.0)

        open_trades: List[SimulatedTrade] = []
        completed_trades: List[SimulatedTrade] = []
        equity_curve: List[EquityPoint] = []

        current_equity = self.config.initial_balance
        ticket_counter = 1000

        # Start simulation once warm-up period passes
        warmup = max(slow_ema_period, rsi_period, 25)

        for i in range(warmup, len(self.candles)):
            candle = self.candles[i]
            prev_candle = self.candles[i - 1]

            # 1. Update & Manage Open Trades (Check Stop Loss, Take Profit, Break-Even)
            trades_to_keep: List[SimulatedTrade] = []
            for trade in open_trades:
                exited = False
                exit_price = 0.0
                reason: Optional[ExitReason] = None

                # Track MAE & MFE
                if trade.direction == TradeDirection.BUY:
                    adverse = trade.entry_price - candle.low
                    favorable = candle.high - trade.entry_price
                    if adverse > trade.mae_points: trade.mae_points = adverse
                    if favorable > trade.mfe_points: trade.mfe_points = favorable

                    hit_sl = trade.stop_loss is not None and candle.low <= trade.stop_loss
                    hit_tp = trade.take_profit is not None and candle.high >= trade.take_profit

                    # Phase 4: Explicit Same-Candle SL/TP Ambiguity Resolution
                    if hit_sl and hit_tp:
                        # Conservative Policy: Always penalize adverse execution first
                        exit_price = trade.stop_loss
                        reason = ExitReason.STOP_LOSS
                        exited = True
                    elif hit_sl:
                        exit_price = trade.stop_loss
                        reason = ExitReason.STOP_LOSS
                        exited = True
                    elif hit_tp:
                        exit_price = trade.take_profit
                        reason = ExitReason.TAKE_PROFIT
                        exited = True
                else: # SELL
                    adverse = candle.high - trade.entry_price
                    favorable = trade.entry_price - candle.low
                    if adverse > trade.mae_points: trade.mae_points = adverse
                    if favorable > trade.mfe_points: trade.mfe_points = favorable

                    hit_sl = trade.stop_loss is not None and candle.high >= trade.stop_loss
                    hit_tp = trade.take_profit is not None and candle.low <= trade.take_profit

                    # Phase 4: Explicit Same-Candle SL/TP Ambiguity Resolution
                    if hit_sl and hit_tp:
                        # Conservative Policy: Always penalize adverse execution first
                        exit_price = trade.stop_loss
                        reason = ExitReason.STOP_LOSS
                        exited = True
                    elif hit_sl:
                        exit_price = trade.stop_loss
                        reason = ExitReason.STOP_LOSS
                        exited = True
                    elif hit_tp:
                        exit_price = trade.take_profit
                        reason = ExitReason.TAKE_PROFIT
                        exited = True


                if exited:
                    self._close_trade(trade, candle.time, exit_price, reason)
                    current_equity += trade.net_pl
                    completed_trades.append(trade)
                else:
                    trades_to_keep.append(trade)

            open_trades = trades_to_keep

            # 2. Check Strategy Entry Rules if capacity allows
            if len(open_trades) < self.config.max_open_trades:
                curr_atr = atr[i - 1] or (candle.close * 0.005)
                sl_dist = curr_atr * atr_mult
                tp_dist = sl_dist * 2.0 # 1:2 R:R baseline

                signal_dir: Optional[TradeDirection] = None

                # Rule Set 1: EMA crossover + RSI confirmation
                if fast_ema[i - 1] is not None and slow_ema[i - 1] is not None:
                    # Bullish Cross
                    if (fast_ema[i - 2] is not None and
                        fast_ema[i - 2] <= slow_ema[i - 2] and
                        fast_ema[i - 1] > slow_ema[i - 1]):
                        if rsi[i - 1] is not None and rsi[i - 1] < 68:
                            signal_dir = TradeDirection.BUY
                    # Bearish Cross
                    elif (fast_ema[i - 2] is not None and
                          fast_ema[i - 2] >= slow_ema[i - 2] and
                          fast_ema[i - 1] < slow_ema[i - 1]):
                        if rsi[i - 1] is not None and rsi[i - 1] > 32:
                            signal_dir = TradeDirection.SELL

                # Rule Set 2: Mean Reversion Bollinger deviation
                if signal_dir is None and upper_bb[i - 1] is not None and lower_bb[i - 1] is not None:
                    if prev_candle.low <= lower_bb[i - 1] and candle.open > lower_bb[i - 1]:
                        if rsi[i - 1] is not None and rsi[i - 1] < 35:
                            signal_dir = TradeDirection.BUY
                    elif prev_candle.high >= upper_bb[i - 1] and candle.open < upper_bb[i - 1]:
                        if rsi[i - 1] is not None and rsi[i - 1] > 65:
                            signal_dir = TradeDirection.SELL

                if signal_dir:
                    entry_fill = self.execution.get_entry_fill_price(signal_dir, candle.open)
                    if signal_dir == TradeDirection.BUY:
                        sl = entry_fill - sl_dist
                        tp = entry_fill + tp_dist
                    else:
                        sl = entry_fill + sl_dist
                        tp = entry_fill - tp_dist

                    lot_size = self.execution.calculate_position_size(
                        current_equity, self.config.risk_per_trade_pct, entry_fill, sl, symbol=self.config.symbol
                    )

                    new_trade = SimulatedTrade(
                        ticket=ticket_counter,
                        symbol=self.config.symbol,
                        direction=signal_dir,
                        lot_size=lot_size,
                        entry_time=candle.time,
                        entry_price=entry_fill,
                        stop_loss=sl,
                        take_profit=tp,
                    )
                    ticket_counter += 1
                    open_trades.append(new_trade)

            # 3. Record Equity Point
            unrealized_pl = 0.0
            for ot in open_trades:
                unrealized_pl += self.execution.calculate_pnl(
                    ot.direction, ot.entry_price, candle.close, ot.lot_size
                )

            total_equity = current_equity + unrealized_pl
            equity_curve.append(EquityPoint(
                timestamp=candle.time,
                equity=round(total_equity, 2),
                drawdown_pct=0.0, # Updated by metrics calculator
                open_positions=len(open_trades)
            ))

        # Close any lingering open trades at final candle
        final_candle = self.candles[-1]
        for trade in open_trades:
            self._close_trade(trade, final_candle.time, final_candle.close, ExitReason.END_OF_DATA)
            completed_trades.append(trade)

        return completed_trades, equity_curve

    def _close_trade(
        self,
        trade: SimulatedTrade,
        exit_time: datetime,
        raw_exit_price: float,
        reason: ExitReason
    ):
        fill_exit = self.execution.get_exit_fill_price(trade.direction, raw_exit_price)
        trade.exit_time = exit_time
        trade.exit_price = fill_exit
        trade.exit_reason = reason

        gross_pl = self.execution.calculate_pnl(
            trade.direction, trade.entry_price, fill_exit, trade.lot_size
        )
        commission = self.execution.calculate_commission(trade.lot_size)
        slippage_cost = self.execution.calculate_slippage_cost(trade.lot_size)
        net_pl = gross_pl - commission - slippage_cost

        trade.gross_pl = gross_pl
        trade.commission = commission
        trade.slippage_cost = slippage_cost
        trade.net_pl = round(net_pl, 2)

        capital_committed = trade.lot_size * self.config.execution.contract_size * trade.entry_price
        trade.return_pct = round((net_pl / capital_committed) * 100.0, 3) if capital_committed > 0 else 0.0

        if trade.entry_time and exit_time:
            trade.duration_minutes = round((exit_time - trade.entry_time).total_seconds() / 60.0, 1)

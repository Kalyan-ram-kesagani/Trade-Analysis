import math
from typing import List
from .models import SimulatedTrade, EquityPoint, BacktestMetrics

class FinancialMetricsCalculator:
    """
    Pure Python deterministic calculation of financial and risk metrics.
    Zero LLM involvement. Adheres to professional quantitative standards.
    """
    @staticmethod
    def calculate(
        initial_balance: float,
        trades: List[SimulatedTrade],
        equity_curve: List[EquityPoint],
        risk_free_rate: float = 0.04
    ) -> BacktestMetrics:
        if not trades:
            return BacktestMetrics(
                initial_balance=initial_balance,
                final_equity=initial_balance,
                net_profit=0.0,
                net_profit_pct=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                breakeven_trades=0,
                win_rate_pct=0.0,
                loss_rate_pct=0.0,
                profit_factor=0.0,
                gross_profit=0.0,
                gross_loss=0.0,
                average_trade_net_pl=0.0,
                average_win=0.0,
                average_loss=0.0,
                win_loss_ratio=0.0,
                expectancy=0.0,
                max_drawdown_amount=0.0,
                max_drawdown_pct=0.0,
                max_consecutive_wins=0,
                max_consecutive_losses=0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                calmar_ratio=0.0,
                total_commission_paid=0.0,
                total_slippage_cost=0.0,
                average_trade_duration_minutes=0.0,
            )

        total_trades = len(trades)
        winning_trades = [t for t in trades if t.net_pl > 0]
        losing_trades = [t for t in trades if t.net_pl < 0]
        breakeven_trades = [t for t in trades if t.net_pl == 0]

        n_wins = len(winning_trades)
        n_losses = len(losing_trades)
        n_be = len(breakeven_trades)

        gross_profit = sum(t.net_pl for t in winning_trades)
        gross_loss = abs(sum(t.net_pl for t in losing_trades))
        net_profit = sum(t.net_pl for t in trades)

        final_equity = initial_balance + net_profit
        net_profit_pct = (net_profit / initial_balance) * 100.0 if initial_balance > 0 else 0.0

        win_rate_pct = (n_wins / total_trades) * 100.0 if total_trades > 0 else 0.0
        loss_rate_pct = (n_losses / total_trades) * 100.0 if total_trades > 0 else 0.0

        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)

        average_win = (gross_profit / n_wins) if n_wins > 0 else 0.0
        average_loss = (gross_loss / n_losses) if n_losses > 0 else 0.0
        win_loss_ratio = (average_win / average_loss) if average_loss > 0 else (999.0 if average_win > 0 else 0.0)

        # Expectancy = (Win% * AvgWin) - (Loss% * AvgLoss)
        win_prob = win_rate_pct / 100.0
        loss_prob = loss_rate_pct / 100.0
        expectancy = (win_prob * average_win) - (loss_prob * average_loss)

        average_trade_net_pl = net_profit / total_trades if total_trades > 0 else 0.0

        # Maximum Drawdown calculation from equity points
        peak_equity = initial_balance
        max_dd_amount = 0.0
        max_dd_pct = 0.0

        for ep in equity_curve:
            if ep.equity > peak_equity:
                peak_equity = ep.equity
            dd_amt = peak_equity - ep.equity
            dd_pct = (dd_amt / peak_equity) * 100.0 if peak_equity > 0 else 0.0

            if dd_amt > max_dd_amount:
                max_dd_amount = dd_amt
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

        # Consecutive streaks
        max_cons_wins = 0
        max_cons_losses = 0
        curr_cons_wins = 0
        curr_cons_losses = 0

        for t in trades:
            if t.net_pl > 0:
                curr_cons_wins += 1
                curr_cons_losses = 0
                if curr_cons_wins > max_cons_wins:
                    max_cons_wins = curr_cons_wins
            elif t.net_pl < 0:
                curr_cons_losses += 1
                curr_cons_wins = 0
                if curr_cons_losses > max_cons_losses:
                    max_cons_losses = curr_cons_losses
            else:
                curr_cons_wins = 0
                curr_cons_losses = 0

        # Trade returns list for Sharpe and Sortino
        returns = [t.return_pct for t in trades if t.return_pct is not None]
        sharpe_ratio = 0.0
        sortino_ratio = 0.0

        if len(returns) >= 2:
            mean_ret = sum(returns) / len(returns)
            variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
            std_dev = math.sqrt(variance) if variance > 0 else 0.0

            # Annualization factor assuming ~250 trading days or ~200 trades/yr
            annual_factor = math.sqrt(252)

            if std_dev > 0:
                daily_rf = (risk_free_rate / 252.0) * 100.0 # Rf in %
                sharpe_ratio = round(((mean_ret - daily_rf) / std_dev) * annual_factor, 2)

            # Downside deviation for Sortino
            downside_sq = [min(0.0, r) ** 2 for r in returns]
            downside_dev = math.sqrt(sum(downside_sq) / len(downside_sq)) if downside_sq else 0.0
            if downside_dev > 0:
                daily_rf = (risk_free_rate / 252.0) * 100.0
                sortino_ratio = round(((mean_ret - daily_rf) / downside_dev) * annual_factor, 2)

        # Calmar Ratio = Annualized Net Return % / Max Drawdown %
        calmar_ratio = 0.0
        if max_dd_pct > 0:
            calmar_ratio = round(net_profit_pct / max_dd_pct, 2)

        total_commission_paid = sum(t.commission for t in trades)
        total_slippage_cost = sum(t.slippage_cost for t in trades)
        avg_duration = sum(t.duration_minutes for t in trades) / total_trades if total_trades > 0 else 0.0

        return BacktestMetrics(
            initial_balance=round(initial_balance, 2),
            final_equity=round(final_equity, 2),
            net_profit=round(net_profit, 2),
            net_profit_pct=round(net_profit_pct, 2),
            total_trades=total_trades,
            winning_trades=n_wins,
            losing_trades=n_losses,
            breakeven_trades=n_be,
            win_rate_pct=round(win_rate_pct, 2),
            loss_rate_pct=round(loss_rate_pct, 2),
            profit_factor=round(profit_factor, 2),
            gross_profit=round(gross_profit, 2),
            gross_loss=round(gross_loss, 2),
            average_trade_net_pl=round(average_trade_net_pl, 2),
            average_win=round(average_win, 2),
            average_loss=round(average_loss, 2),
            win_loss_ratio=round(win_loss_ratio, 2),
            expectancy=round(expectancy, 2),
            max_drawdown_amount=round(max_dd_amount, 2),
            max_drawdown_pct=round(max_dd_pct, 2),
            max_consecutive_wins=max_cons_wins,
            max_consecutive_losses=max_cons_losses,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            total_commission_paid=round(total_commission_paid, 2),
            total_slippage_cost=round(total_slippage_cost, 2),
            average_trade_duration_minutes=round(avg_duration, 1),
        )

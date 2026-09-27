import random
import math
from typing import Dict, Any, List
from app.services.backtesting.models import SimulatedTrade

class MonteCarloValidationEngine:
    """
    Simulates thousands of alternative equity path permutations via trade-order bootstrapping.
    Calculates confidence intervals for Max Drawdown, Final Profit, and Risk of Ruin.
    Zero LLM hallucination; strictly statistical resampling.
    """
    @classmethod
    def run_simulation(
        cls,
        trades: List[SimulatedTrade],
        initial_balance: float = 10000.0,
        simulations_count: int = 1000,
        ruin_drawdown_pct: float = 20.0, # Account ruin considered if DD >= 20%
        random_seed: int = 42
    ) -> Dict[str, Any]:
        if not trades or len(trades) < 5:
            # Need minimum trades for bootstrapping
            return {
                "validation_stage": "MONTE_CARLO",
                "passed": False,
                "error": "Insufficient trades for statistical bootstrapping (minimum 5 trades required)",
                "simulations_count": 0,
            }

        pnl_sequence = [t.net_pl for t in trades]
        n_trades = len(pnl_sequence)
        rng = random.Random(random_seed)

        ending_equities: List[float] = []
        max_drawdowns: List[float] = []
        ruin_occurrences = 0

        # Resample with replacement (bootstrap)
        for _ in range(simulations_count):
            current_eq = initial_balance
            peak_eq = initial_balance
            sim_max_dd = 0.0
            ruined = False

            for _ in range(n_trades):
                # Pick random trade from observed historical trades
                trade_pl = rng.choice(pnl_sequence)
                current_eq += trade_pl

                if current_eq > peak_eq:
                    peak_eq = current_eq

                dd_pct = ((peak_eq - current_eq) / peak_eq) * 100.0 if peak_eq > 0 else 100.0
                if dd_pct > sim_max_dd:
                    sim_max_dd = dd_pct

                if sim_max_dd >= ruin_drawdown_pct:
                    ruined = True

            if ruined:
                ruin_occurrences += 1

            ending_equities.append(round(current_eq, 2))
            max_drawdowns.append(round(sim_max_dd, 2))

        # Calculate percentiles (5th, 25th, 50th/Median, 75th, 95th)
        ending_equities.sort()
        max_drawdowns.sort()

        def get_percentile(arr: List[float], p: float) -> float:
            idx = int(len(arr) * (p / 100.0))
            idx = min(max(0, idx), len(arr) - 1)
            return round(arr[idx], 2)

        risk_of_ruin_pct = round((ruin_occurrences / simulations_count) * 100.0, 2)
        median_equity = get_percentile(ending_equities, 50)
        median_dd = get_percentile(max_drawdowns, 50)
        p95_dd = get_percentile(max_drawdowns, 95) # Worst 5% of cases

        # Pass criteria: Risk of ruin <= 5.0% and 95th percentile drawdown <= 25.0%
        passed = (risk_of_ruin_pct <= 5.0) and (p95_dd <= 25.0)

        return {
            "validation_stage": "MONTE_CARLO",
            "passed": passed,
            "simulations_count": simulations_count,
            "trades_resampled": n_trades,
            "risk_of_ruin_pct": risk_of_ruin_pct,
            "drawdown_confidence_intervals": {
                "p05_best_case": get_percentile(max_drawdowns, 5),
                "p25": get_percentile(max_drawdowns, 25),
                "p50_median": median_dd,
                "p75": get_percentile(max_drawdowns, 75),
                "p95_worst_case": p95_dd,
            },
            "profit_confidence_intervals": {
                "p05_worst_profit": get_percentile(ending_equities, 5),
                "p25": get_percentile(ending_equities, 25),
                "p50_median_equity": median_equity,
                "p75": get_percentile(ending_equities, 75),
                "p95_best_equity": get_percentile(ending_equities, 95),
            }
        }

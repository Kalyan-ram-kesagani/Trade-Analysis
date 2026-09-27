from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

class TradeDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class ExitReason(str, Enum):
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"
    BREAK_EVEN = "BREAK_EVEN"
    SIGNAL = "SIGNAL"
    END_OF_DATA = "END_OF_DATA"

class DataProvenance(str, Enum):
    REAL_MT5 = "REAL_MT5"
    IMPORTED_HISTORICAL = "IMPORTED_HISTORICAL"
    SYNTHETIC_TEST = "SYNTHETIC_TEST"

class SameCandleResolutionPolicy(str, Enum):
    CONSERVATIVE_ADVERSE = "CONSERVATIVE_ADVERSE"  # Stop-loss assumed to hit before take-profit
    OPTIMISTIC = "OPTIMISTIC"                      # Prohibited in production validation
    INTRABAR_STRICT = "INTRABAR_STRICT"

@dataclass
class DataIntegrityReport:
    is_valid: bool
    data_provenance: DataProvenance
    production_eligible: bool
    total_candles: int
    duplicate_count: int
    disordered_count: int
    invalid_ohlc_count: int
    zero_volume_count: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

@dataclass
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: int = 0
    spread: float = 0.0

@dataclass
class ExecutionAssumptions:
    spread_points: float = 15.0         # 1.5 pips default for forex/gold
    point_size: float = 0.0001          # 0.01 for JPY/Gold, 0.0001 for EURUSD
    contract_size: float = 100000.0     # 100k standard lot
    commission_per_lot: float = 7.0     # $7 round-turn per lot
    slippage_points: float = 5.0        # 0.5 pip slippage assumption
    risk_free_rate: float = 0.04        # 4% annual risk-free rate for Sharpe
    enable_slippage: bool = True
    same_candle_policy: SameCandleResolutionPolicy = SameCandleResolutionPolicy.CONSERVATIVE_ADVERSE
    version: str = "v1.0"


@dataclass
class BacktestConfig:
    strategy_id: Optional[str] = None
    proposal_id: Optional[str] = None
    account_id: Optional[str] = None
    symbol: str = "EURUSD"
    timeframe: str = "H1"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    initial_balance: float = 10000.0
    risk_per_trade_pct: float = 1.0     # Risk 1% of account per trade
    max_open_trades: int = 1
    parameters: Dict[str, Any] = field(default_factory=dict)
    execution: ExecutionAssumptions = field(default_factory=ExecutionAssumptions)

@dataclass
class SimulatedTrade:
    ticket: int
    symbol: str
    direction: TradeDirection
    lot_size: float
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    break_even_price: Optional[float] = None
    exit_reason: Optional[ExitReason] = None
    gross_pl: float = 0.0
    commission: float = 0.0
    slippage_cost: float = 0.0
    net_pl: float = 0.0
    return_pct: float = 0.0
    mae_points: float = 0.0 # Maximum Adverse Excursion
    mfe_points: float = 0.0 # Maximum Favorable Excursion
    duration_minutes: float = 0.0

@dataclass
class EquityPoint:
    timestamp: datetime
    equity: float
    drawdown_pct: float
    open_positions: int

@dataclass
class BacktestMetrics:
    initial_balance: float
    final_equity: float
    net_profit: float
    net_profit_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    win_rate_pct: float
    loss_rate_pct: float
    profit_factor: float
    gross_profit: float
    gross_loss: float
    average_trade_net_pl: float
    average_win: float
    average_loss: float
    win_loss_ratio: float
    expectancy: float
    max_drawdown_amount: float
    max_drawdown_pct: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    total_commission_paid: float
    total_slippage_cost: float
    average_trade_duration_minutes: float

@dataclass
class BacktestResult:
    config: BacktestConfig
    metrics: BacktestMetrics
    trades: List[SimulatedTrade]
    equity_curve: List[EquityPoint]
    validation_stage: str = "BACKTEST"
    data_provenance: DataProvenance = DataProvenance.REAL_MT5
    production_eligible: bool = True
    integrity_report: Optional[DataIntegrityReport] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_stage": self.validation_stage,
            "data_provenance": self.data_provenance.value,
            "production_eligible": self.production_eligible,
            "integrity_passed": self.integrity_report.is_valid if self.integrity_report else True,

            "metrics": {
                "initial_balance": self.metrics.initial_balance,
                "final_equity": self.metrics.final_equity,
                "net_profit": self.metrics.net_profit,
                "net_profit_pct": self.metrics.net_profit_pct,
                "total_trades": self.metrics.total_trades,
                "winning_trades": self.metrics.winning_trades,
                "losing_trades": self.metrics.losing_trades,
                "breakeven_trades": self.metrics.breakeven_trades,
                "win_rate_pct": self.metrics.win_rate_pct,
                "profit_factor": self.metrics.profit_factor,
                "average_win": self.metrics.average_win,
                "average_loss": self.metrics.average_loss,
                "win_loss_ratio": self.metrics.win_loss_ratio,
                "expectancy": self.metrics.expectancy,
                "max_drawdown_amount": self.metrics.max_drawdown_amount,
                "max_drawdown_pct": self.metrics.max_drawdown_pct,
                "max_consecutive_wins": self.metrics.max_consecutive_wins,
                "max_consecutive_losses": self.metrics.max_consecutive_losses,
                "sharpe_ratio": self.metrics.sharpe_ratio,
                "sortino_ratio": self.metrics.sortino_ratio,
                "calmar_ratio": self.metrics.calmar_ratio,
                "total_commission_paid": self.metrics.total_commission_paid,
                "total_slippage_cost": self.metrics.total_slippage_cost,
                "average_trade_duration_minutes": self.metrics.average_trade_duration_minutes,
            },
            "parameters": self.config.parameters,
            "execution_assumptions": {
                "spread_points": self.config.execution.spread_points,
                "slippage_points": self.config.execution.slippage_points,
                "commission_per_lot": self.config.execution.commission_per_lot,
            },
            "trades_summary": {
                "total_trades": self.metrics.total_trades,
                "winning_trades": self.metrics.winning_trades,
                "losing_trades": self.metrics.losing_trades,
                "win_rate_pct": self.metrics.win_rate_pct,
            },
            "equity_curve": [
                {
                    "timestamp": ep.timestamp.isoformat(),
                    "equity": ep.equity,
                    "drawdown_pct": ep.drawdown_pct,
                }
                for ep in self.equity_curve
            ],
            "sample_trades": [
                {
                    "ticket": t.ticket,
                    "direction": t.direction.value,
                    "lot_size": t.lot_size,
                    "entry_time": t.entry_time.isoformat() if t.entry_time else None,
                    "entry_price": t.entry_price,
                    "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                    "exit_price": t.exit_price,
                    "net_pl": t.net_pl,
                    "exit_reason": t.exit_reason.value if t.exit_reason else None,
                }
                for t in self.trades[-20:] # Return last 20 trades
            ]
        }

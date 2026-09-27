from .models import TradeDirection, ExecutionAssumptions

class RealisticExecutionModel:
    """
    Deterministic execution simulation with realistic spread, slippage, and commissions.
    Zero LLM interference; mathematical precision only.
    """
    def __init__(self, assumptions: ExecutionAssumptions):
        self.assumptions = assumptions

    def calculate_position_size(
        self,
        account_balance: float,
        risk_pct: float,
        entry_price: float,
        stop_loss: float,
        symbol: str = "EURUSD"
    ) -> float:
        """
        Calculates position size in standard lots based on risk % and stop loss distance.
        Accounts for instrument specifications (Forex, Gold, JPY, Crypto).
        Formula: Lot = Risk_Capital / (SL_Distance_Points * Point_Value_Per_Lot)
        """
        if entry_price <= 0 or stop_loss <= 0 or account_balance <= 0:
            return 0.01

        sl_distance = abs(entry_price - stop_loss)
        if sl_distance <= 0:
            return 0.01

        # Instrument-specific contract and point adjustments
        sym = symbol.upper()
        if "XAU" in sym or "GOLD" in sym:
            contract_size = 100.0  # 100 oz per standard lot
        elif "BTC" in sym or "CRYPTO" in sym:
            contract_size = 1.0    # 1 BTC per contract
        elif "JPY" in sym:
            contract_size = 100000.0 # Standard lot, but 1 pip = 0.01
        else:
            contract_size = self.assumptions.contract_size

        risk_capital = account_balance * (risk_pct / 100.0)
        lot_size = risk_capital / (sl_distance * contract_size)

        # Clamp between 0.01 and 50.0 lots, rounded to 2 decimal places
        clamped_lot = max(0.01, min(50.0, round(lot_size, 2)))
        return clamped_lot


    def get_entry_fill_price(self, direction: TradeDirection, current_price: float) -> float:
        """
        Applies spread and execution slippage against the trader.
        For BUY: Entry fills at Ask = Price + Spread/2 + Slippage
        For SELL: Entry fills at Bid = Price - Spread/2 - Slippage
        """
        half_spread = (self.assumptions.spread_points * self.assumptions.point_size) / 2.0
        slippage = (self.assumptions.slippage_points * self.assumptions.point_size) if self.assumptions.enable_slippage else 0.0

        if direction == TradeDirection.BUY:
            return current_price + half_spread + slippage
        else:
            return current_price - half_spread - slippage

    def get_exit_fill_price(self, direction: TradeDirection, target_exit_price: float) -> float:
        """
        Applies spread and exit slippage against the trader.
        For closing BUY (selling): Exit fills at Bid = target - half_spread - slippage
        For closing SELL (buying): Exit fills at Ask = target + half_spread + slippage
        """
        half_spread = (self.assumptions.spread_points * self.assumptions.point_size) / 2.0
        slippage = (self.assumptions.slippage_points * self.assumptions.point_size) if self.assumptions.enable_slippage else 0.0

        if direction == TradeDirection.BUY:
            return target_exit_price - half_spread - slippage
        else:
            return target_exit_price + half_spread + slippage

    def calculate_commission(self, lot_size: float) -> float:
        """Standard round-turn commission per lot"""
        return round(lot_size * self.assumptions.commission_per_lot, 2)

    def calculate_slippage_cost(self, lot_size: float) -> float:
        """Total slippage monetary drag (entry + exit)"""
        if not self.assumptions.enable_slippage:
            return 0.0
        # 2 events (entry + exit) * slippage_points * point_size * contract_size * lots
        slip_per_event = self.assumptions.slippage_points * self.assumptions.point_size * self.assumptions.contract_size * lot_size
        return round(slip_per_event * 2.0, 2)

    def calculate_pnl(
        self,
        direction: TradeDirection,
        entry_price: float,
        exit_price: float,
        lot_size: float
    ) -> float:
        """
        Calculates raw gross P&L based on contract size.
        BUY: (exit - entry) * contract_size * lot_size
        SELL: (entry - exit) * contract_size * lot_size
        """
        if direction == TradeDirection.BUY:
            price_delta = exit_price - entry_price
        else:
            price_delta = entry_price - exit_price

        gross_pl = price_delta * self.assumptions.contract_size * lot_size
        return round(gross_pl, 2)

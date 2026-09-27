"""
AI Context Builder
Converts raw system data into structured context suitable for AI prompts.
Ensures account isolation and data relevance.
"""

import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from app.services.ai import tools

logger = logging.getLogger("ai_context")


def _safe_serialize(obj: Any) -> str:
    """JSON-serialize with fallback for non-serializable types."""
    def default_handler(o):
        if isinstance(o, datetime):
            return o.isoformat()
        if hasattr(o, "__str__"):
            return str(o)
        return repr(o)
    return json.dumps(obj, default=default_handler, indent=2)


async def build_analysis_context(account_id: str) -> Dict[str, Any]:
    """
    Build context for Analysis AI.
    Gathers account metrics, recent trades, open positions,
    risk config, and computed statistics.
    """
    account = await tools.get_account_metrics(account_id)
    trades = await tools.get_trade_history(account_id, limit=30)
    positions = await tools.get_open_positions(account_id)
    risk = await tools.get_risk_configuration(account_id) if account_id and account_id != "all" else None
    stats = await tools.compute_trade_statistics(account_id)
    activities = await tools.get_recent_activity(account_id, limit=15)

    context = {
        "account": _format_account(account),
        "trade_statistics": stats,
        "recent_trades": _format_trades(trades[:15]),
        "open_positions": _format_positions(positions),
        "risk_configuration": _format_risk(risk),
        "recent_activities": _format_activities(activities[:10]),
        "data_availability": {
            "has_account": bool(account),
            "trade_count": len(trades),
            "position_count": len(positions),
            "has_risk_config": risk is not None,
            "has_activities": len(activities) > 0,
        }
    }
    return context


async def build_journal_context(
    account_id: str, trade_id: str
) -> Dict[str, Any]:
    """
    Build context for Journal AI.
    Focuses on a specific trade with surrounding context.
    """
    trade = await tools.get_trade_by_id(trade_id)
    if not trade:
        return {"error": f"Trade {trade_id} not found"}

    # Verify account isolation
    if account_id != "all" and str(trade.get("account_id")) != account_id:
        return {"error": "Trade does not belong to the specified account"}

    account = await tools.get_account_metrics(str(trade["account_id"]))
    risk = await tools.get_risk_configuration(str(trade["account_id"]))

    # Get nearby trades for context
    all_trades = await tools.get_trade_history(str(trade["account_id"]), limit=10)

    # Get strategy if linked
    strategy = None
    if trade.get("strategy_id"):
        strategy = await tools.get_strategy_by_id(str(trade["strategy_id"]))

    # Check for existing journal entries for this trade
    journals = await tools.get_journal_history(str(trade["account_id"]), limit=50)
    existing_journal = None
    for j in journals:
        if str(j.get("trade_id")) == trade_id:
            existing_journal = j
            break

    context = {
        "trade": _format_single_trade(trade),
        "account": _format_account(account),
        "strategy": _format_strategy(strategy) if strategy else None,
        "risk_configuration": _format_risk(risk),
        "nearby_trades": _format_trades(all_trades[:5]),
        "existing_journal": _format_journal_entry(existing_journal) if existing_journal else None,
        "data_availability": {
            "has_trade": True,
            "has_account": bool(account),
            "has_strategy": strategy is not None,
            "has_risk_config": risk is not None,
            "has_existing_journal": existing_journal is not None,
        }
    }
    return context


async def build_strategy_context(
    strategy_id: str, account_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build context for Strategy AI.
    Gathers strategy definition, performance stats, and related trades.
    """
    strategy = await tools.get_strategy_by_id(strategy_id)
    if not strategy:
        return {"error": f"Strategy {strategy_id} not found"}

    # Get trade history (all accounts or specific)
    trades = await tools.get_trade_history(account_id or "all", limit=100)
    stats = await tools.compute_trade_statistics(account_id or "all")

    context = {
        "strategy": _format_strategy(strategy),
        "trade_statistics": stats,
        "recent_trades": _format_trades(trades[:20]),
        "data_availability": {
            "has_strategy": True,
            "trade_count": len(trades),
        }
    }
    return context


# ==========================================
# Formatting Helpers
# ==========================================

def _format_account(account: Dict[str, Any]) -> Dict[str, Any]:
    """Format account data for AI context (exclude sensitive fields)."""
    if not account:
        return {}
    return {
        "broker": account.get("broker", ""),
        "account_name": account.get("account_name", ""),
        "masked_number": account.get("masked_number", ""),
        "currency": account.get("currency", "USD"),
        "balance": float(account.get("balance", 0)),
        "equity": float(account.get("equity", 0)),
        "margin": float(account.get("margin", 0)),
        "free_margin": float(account.get("free_margin", 0)),
        "margin_level": float(account.get("margin_level", 0)),
        "floating_pl": float(account.get("floating_pl", 0)),
        "status": account.get("status", "unknown"),
        "account_type": account.get("account_type", "demo"),
        "leverage": int(account.get("leverage", 0)),
        "last_sync": str(account.get("last_sync", "")),
    }


def _format_trades(trades: list) -> list:
    """Format trades list for AI context."""
    return [_format_single_trade(t) for t in trades]


def _format_single_trade(trade: Dict[str, Any]) -> Dict[str, Any]:
    """Format a single trade for AI context with exact recorded data."""
    if not trade:
        return {}
    
    # Calculate duration if timestamps present
    duration_str = "Not available"
    if trade.get("entry_time") and trade.get("exit_time"):
        try:
            e_t = trade["entry_time"]
            x_t = trade["exit_time"]
            if hasattr(e_t, "timestamp") and hasattr(x_t, "timestamp"):
                seconds = int(x_t.timestamp() - e_t.timestamp())
                mins, secs = divmod(seconds, 60)
                hours, mins = divmod(mins, 60)
                duration_str = f"{hours}h {mins}m {secs}s" if hours else f"{mins}m {secs}s"
        except Exception:
            pass

    return {
        "account_id": str(trade.get("account_id", "Not available")),
        "trade_id": str(trade.get("id", "Not available")),
        "ticket": int(trade.get("ticket", 0)),
        "symbol": trade.get("symbol", "Not available"),
        "direction": trade.get("direction", "Not available"),
        "volume": float(trade.get("volume", 0)),
        "entry_price": float(trade.get("entry_price", 0)),
        "exit_price": float(trade.get("exit_price", 0)) if trade.get("exit_price") is not None else "Not available",
        "entry_time": str(trade.get("entry_time", "Not available")),
        "exit_time": str(trade.get("exit_time", "Not available")),
        "duration": duration_str,
        "stop_loss": float(trade.get("stop_loss")) if trade.get("stop_loss") else "Not available",
        "take_profit": float(trade.get("take_profit")) if trade.get("take_profit") else "Not available",
        "realized_pl": float(trade.get("profit_loss", 0)),
        "commission": float(trade.get("commission", 0)),
        "swap": float(trade.get("swap", 0)),
        "net_pl": float(trade.get("net_pl", 0)),
        "risk_percentage": float(trade.get("initial_risk_percent", 0)) if trade.get("initial_risk_percent") is not None else "Not available",
        "initial_risk_amount": float(trade.get("initial_risk_amount", 0)) if trade.get("initial_risk_amount") is not None else "Not available",
        "risk_free_status": trade.get("risk_free_status", "Not available"),
        "break_even_price": float(trade.get("break_even_price")) if trade.get("break_even_price") else "Not available",
        "risk_reward_ratio": float(trade.get("risk_reward_ratio")) if trade.get("risk_reward_ratio") else "Not available",
        "strategy_id": str(trade.get("strategy_id")) if trade.get("strategy_id") else "Not available",
        "strategy_name": trade.get("strategy_name", "Not available"),
        "strategy_version": trade.get("strategy_version", "Not available"),
        "entry_reason": trade.get("entry_reason", "Not available"),
        "exit_reason": trade.get("exit_reason", "Not available"),
        "market_session": trade.get("market_session", "Not available"),
        "spread_slippage": trade.get("spread_slippage", "Not available"),
        "indicator_values": trade.get("indicator_values", "Not available"),
        "trade_mode": trade.get("account_type", "demo"),
        "execution_result": trade.get("status", "Not available"),
        "notes": trade.get("notes", "Not available"),
    }


def _format_positions(positions: list) -> list:
    """Format open positions for AI context."""
    formatted = []
    for pos in positions:
        formatted.append({
            "ticket": int(pos.get("ticket", 0)),
            "symbol": pos.get("symbol", ""),
            "direction": pos.get("direction", ""),
            "volume": float(pos.get("volume", 0)),
            "entry_price": float(pos.get("entry_price", 0)),
            "current_price": float(pos.get("current_price", 0)),
            "stop_loss": float(pos.get("stop_loss", 0)) if pos.get("stop_loss") else None,
            "take_profit": float(pos.get("take_profit", 0)) if pos.get("take_profit") else None,
            "floating_pl": float(pos.get("floating_pl", 0)),
            "risk_free_status": pos.get("risk_free_status", "N/A"),
            "entry_time": str(pos.get("entry_time", "")),
            "strategy_name": pos.get("strategy_name", ""),
        })
    return formatted


def _format_risk(risk: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Format risk configuration for AI context."""
    if not risk:
        return None
    return {
        "daily_risk_limit_percent": float(risk.get("daily_risk_limit_percent", 0)),
        "max_drawdown_limit_percent": float(risk.get("max_drawdown_limit_percent", 0)),
        "max_risk_per_trade_percent": float(risk.get("max_risk_per_trade_percent", 0)),
        "max_open_positions": int(risk.get("max_open_positions", 0)),
        "breakeven_trigger_r": float(risk.get("breakeven_trigger_r", 0)),
        "breakeven_offset_pips": float(risk.get("breakeven_offset_pips", 0)),
        "trading_locked": bool(risk.get("trading_locked", False)),
    }


def _format_strategy(strategy: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Format strategy for AI context."""
    if not strategy:
        return None
    return {
        "id": str(strategy.get("id", "")),
        "name": strategy.get("name", ""),
        "version": strategy.get("version", ""),
        "description": strategy.get("description", ""),
        "status": strategy.get("status", ""),
        "rules": strategy.get("rules", []),
        "risk_parameters": strategy.get("risk_parameters", {}),
        "version_history": strategy.get("version_history", []),
    }


def _format_activities(activities: list) -> list:
    """Format activities for AI context."""
    return [
        {
            "type": a.get("type", ""),
            "title": a.get("title", ""),
            "description": a.get("description", ""),
            "symbol": a.get("symbol", ""),
            "pl": float(a.get("pl", 0)) if a.get("pl") else None,
            "level": a.get("level", "info"),
            "time": str(a.get("created_at", "")),
        }
        for a in activities
    ]


def _format_journal_entry(entry: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Format journal entry for AI context."""
    if not entry:
        return None
    return {
        "id": str(entry.get("id", "")),
        "symbol": entry.get("symbol", ""),
        "date": str(entry.get("date", "")),
        "result": entry.get("result", ""),
        "notes": entry.get("notes", ""),
        "reason": entry.get("reason", ""),
        "lessons": entry.get("lessons", ""),
        "tags": entry.get("tags", []),
    }


def context_to_prompt_text(context: Dict[str, Any]) -> str:
    """Convert a context dict to a readable text block for the AI prompt."""
    return _safe_serialize(context)

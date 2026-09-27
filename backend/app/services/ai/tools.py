"""
Controlled AI Tools — Data Access Layer
The AI NEVER gets raw SQL or unrestricted database access.
Each tool queries specific data with account isolation enforced.
"""

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from app.database import AsyncSessionLocal

logger = logging.getLogger("ai_tools")


async def get_account_metrics(account_id: str) -> Dict[str, Any]:
    """Fetch account balance, equity, margin, and status."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT
                    id, broker, account_name, account_number,
                    masked_number, server, currency,
                    balance, equity, margin, free_margin,
                    margin_level, floating_pl, status,
                    account_type, leverage, last_sync
                FROM trading_accounts
                WHERE id = CAST(:account_id AS UUID)
            """),
            {"account_id": account_id}
        )
        row = result.mappings().first()
        if not row:
            return {}
        return dict(row)


async def get_trade_history(
    account_id: str, limit: int = 50
) -> List[Dict[str, Any]]:
    """Fetch recent closed trades for a specific account."""
    async with AsyncSessionLocal() as session:
        if account_id and account_id != "all":
            result = await session.execute(
                text("""
                    SELECT
                        id, ticket, account_id, strategy_id,
                        symbol, direction, volume,
                        entry_price, exit_price,
                        stop_loss, take_profit,
                        entry_time, exit_time,
                        profit_loss, commission, swap, net_pl,
                        status, initial_risk_percent,
                        initial_risk_amount, risk_free_status,
                        break_even_price, risk_reward_ratio,
                        notes, created_at
                    FROM trades
                    WHERE account_id = CAST(:account_id AS UUID)
                    ORDER BY exit_time DESC
                    LIMIT :limit
                """),
                {"account_id": account_id, "limit": limit}
            )
        else:
            result = await session.execute(
                text("""
                    SELECT
                        id, ticket, account_id, strategy_id,
                        symbol, direction, volume,
                        entry_price, exit_price,
                        stop_loss, take_profit,
                        entry_time, exit_time,
                        profit_loss, commission, swap, net_pl,
                        status, initial_risk_percent,
                        initial_risk_amount, risk_free_status,
                        break_even_price, risk_reward_ratio,
                        notes, created_at
                    FROM trades
                    ORDER BY exit_time DESC
                    LIMIT :limit
                """),
                {"limit": limit}
            )
        return [dict(row) for row in result.mappings().all()]


async def get_trade_by_id(trade_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single trade by ID."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT
                    id, ticket, account_id, strategy_id,
                    symbol, direction, volume,
                    entry_price, exit_price,
                    stop_loss, take_profit,
                    entry_time, exit_time,
                    profit_loss, commission, swap, net_pl,
                    status, initial_risk_percent,
                    initial_risk_amount, risk_free_status,
                    break_even_price, risk_reward_ratio, notes
                FROM trades
                WHERE id = CAST(:trade_id AS UUID)
            """),
            {"trade_id": trade_id}
        )
        row = result.mappings().first()
        return dict(row) if row else None


async def get_open_positions(account_id: str) -> List[Dict[str, Any]]:
    """Fetch currently open positions for a specific account."""
    async with AsyncSessionLocal() as session:
        if account_id and account_id != "all":
            result = await session.execute(
                text("""
                    SELECT
                        id, ticket, account_id, symbol,
                        direction, volume, entry_price,
                        current_price, stop_loss, take_profit,
                        floating_pl, risk_free_status,
                        break_even_price, entry_time,
                        strategy_name, updated_at
                    FROM open_positions
                    WHERE account_id = CAST(:account_id AS UUID)
                    ORDER BY entry_time DESC
                """),
                {"account_id": account_id}
            )
        else:
            result = await session.execute(
                text("""
                    SELECT
                        id, ticket, account_id, symbol,
                        direction, volume, entry_price,
                        current_price, stop_loss, take_profit,
                        floating_pl, risk_free_status,
                        break_even_price, entry_time,
                        strategy_name, updated_at
                    FROM open_positions
                    ORDER BY entry_time DESC
                """)
            )
        return [dict(row) for row in result.mappings().all()]


async def get_strategies() -> List[Dict[str, Any]]:
    """Fetch all strategies."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT
                    id, name, version, description, status,
                    rules, risk_parameters, version_history,
                    created_at, updated_at
                FROM strategies
                ORDER BY created_at DESC
            """)
        )
        return [dict(row) for row in result.mappings().all()]


async def get_strategy_by_id(strategy_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single strategy by ID."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT
                    id, name, version, description, status,
                    rules, risk_parameters, version_history,
                    created_at, updated_at
                FROM strategies
                WHERE id = CAST(:strategy_id AS UUID)
            """),
            {"strategy_id": strategy_id}
        )
        row = result.mappings().first()
        return dict(row) if row else None


async def get_risk_configuration(account_id: str) -> Optional[Dict[str, Any]]:
    """Fetch risk configuration for an account."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT
                    id, account_id,
                    daily_risk_limit_percent,
                    max_drawdown_limit_percent,
                    max_risk_per_trade_percent,
                    max_open_positions,
                    breakeven_trigger_r,
                    breakeven_offset_pips,
                    trading_locked, updated_at
                FROM risk_configurations
                WHERE account_id = CAST(:account_id AS UUID)
            """),
            {"account_id": account_id}
        )
        row = result.mappings().first()
        return dict(row) if row else None


async def get_recent_activity(
    account_id: str, limit: int = 30
) -> List[Dict[str, Any]]:
    """Fetch recent system activities for an account."""
    async with AsyncSessionLocal() as session:
        if account_id and account_id != "all":
            result = await session.execute(
                text("""
                    SELECT
                        id, account_id, type, title,
                        description, symbol, pl, level, created_at
                    FROM system_activities
                    WHERE account_id = CAST(:account_id AS UUID)
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"account_id": account_id, "limit": limit}
            )
        else:
            result = await session.execute(
                text("""
                    SELECT
                        id, account_id, type, title,
                        description, symbol, pl, level, created_at
                    FROM system_activities
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"limit": limit}
            )
        return [dict(row) for row in result.mappings().all()]


async def get_journal_history(
    account_id: str, limit: int = 20
) -> List[Dict[str, Any]]:
    """Fetch journal entries for an account."""
    async with AsyncSessionLocal() as session:
        if account_id and account_id != "all":
            result = await session.execute(
                text("""
                    SELECT
                        id, trade_id, account_id, user_id,
                        symbol, date, result, notes,
                        reason, lessons, strategy_version,
                        tags, ai_detected_reason,
                        ai_recommendation, ai_modification,
                        created_at, updated_at,
                        journal_type, status, ai_provider,
                        ai_model, prompt_version, structured_ai_output,
                        ai_confidence, error_info, retry_count, generated_at
                    FROM journal_entries
                    WHERE account_id = CAST(:account_id AS UUID)
                    ORDER BY date DESC, created_at DESC
                    LIMIT :limit
                """),
                {"account_id": account_id, "limit": limit}
            )
        else:
            result = await session.execute(
                text("""
                    SELECT
                        id, trade_id, account_id, user_id,
                        symbol, date, result, notes,
                        reason, lessons, strategy_version,
                        tags, ai_detected_reason,
                        ai_recommendation, ai_modification,
                        created_at, updated_at,
                        journal_type, status, ai_provider,
                        ai_model, prompt_version, structured_ai_output,
                        ai_confidence, error_info, retry_count, generated_at
                    FROM journal_entries
                    ORDER BY date DESC, created_at DESC
                    LIMIT :limit
                """),
                {"limit": limit}
            )
        return [dict(row) for row in result.mappings().all()]


async def compute_trade_statistics(
    account_id: str
) -> Dict[str, Any]:
    """
    Compute deterministic trade statistics from the database.
    AI should interpret these — NOT re-calculate from raw trades.
    """
    trades = await get_trade_history(account_id, limit=500)
    if not trades:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "win_rate": 0.0,
            "total_pl": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
            "profit_factor": 0.0,
            "avg_rr": 0.0,
            "symbols_traded": [],
            "symbol_performance": {},
            "consecutive_losses_max": 0,
            "consecutive_wins_max": 0,
        }

    wins = [t for t in trades if t.get("status") == "WIN"]
    losses = [t for t in trades if t.get("status") == "LOSS"]
    be_trades = [t for t in trades if t.get("status") == "BREAKEVEN"]

    total_pl = sum(float(t.get("net_pl", 0)) for t in trades)
    gross_profit = sum(float(t.get("net_pl", 0)) for t in wins)
    gross_loss = abs(sum(float(t.get("net_pl", 0)) for t in losses))

    avg_win = gross_profit / len(wins) if wins else 0.0
    avg_loss = gross_loss / len(losses) if losses else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (9.99 if gross_profit > 0 else 0.0)

    win_pls = [float(t.get("net_pl", 0)) for t in wins]
    loss_pls = [float(t.get("net_pl", 0)) for t in losses]
    largest_win = max(win_pls) if win_pls else 0.0
    largest_loss = min(loss_pls) if loss_pls else 0.0

    # Symbol breakdown
    symbol_performance: Dict[str, Dict[str, Any]] = {}
    for t in trades:
        sym = t.get("symbol", "UNKNOWN")
        if sym not in symbol_performance:
            symbol_performance[sym] = {"count": 0, "wins": 0, "pl": 0.0}
        symbol_performance[sym]["count"] += 1
        if t.get("status") == "WIN":
            symbol_performance[sym]["wins"] += 1
        symbol_performance[sym]["pl"] += float(t.get("net_pl", 0))

    for sym in symbol_performance:
        sp = symbol_performance[sym]
        sp["win_rate"] = round(sp["wins"] / sp["count"] * 100, 1) if sp["count"] > 0 else 0.0
        sp["pl"] = round(sp["pl"], 2)

    # Consecutive wins/losses
    max_consec_wins = 0
    max_consec_losses = 0
    curr_wins = 0
    curr_losses = 0
    for t in reversed(trades):  # chronological order
        if t.get("status") == "WIN":
            curr_wins += 1
            curr_losses = 0
            max_consec_wins = max(max_consec_wins, curr_wins)
        elif t.get("status") == "LOSS":
            curr_losses += 1
            curr_wins = 0
            max_consec_losses = max(max_consec_losses, curr_losses)
        else:
            curr_wins = 0
            curr_losses = 0

    # Average risk-reward
    rr_values = [float(t.get("risk_reward_ratio", 0)) for t in trades if t.get("risk_reward_ratio")]
    avg_rr = sum(rr_values) / len(rr_values) if rr_values else 0.0

    return {
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(be_trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0.0,
        "total_pl": round(total_pl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "largest_win": round(largest_win, 2),
        "largest_loss": round(largest_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_rr": round(avg_rr, 2),
        "symbols_traded": list(symbol_performance.keys()),
        "symbol_performance": symbol_performance,
        "consecutive_losses_max": max_consec_losses,
        "consecutive_wins_max": max_consec_wins,
    }


async def log_ai_audit(
    account_id: str,
    agent_type: str,
    model: str,
    input_summary: str,
    output_summary: str,
    tools_used: List[str],
    duration_ms: int,
    error: Optional[str] = None,
    related_trade_id: Optional[str] = None,
    related_strategy_id: Optional[str] = None,
) -> None:
    """Write an AI audit log entry to the database."""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    text("""
                        INSERT INTO ai_audit_logs (
                            account_id, agent_type, model,
                            input_summary, output_summary,
                            tools_used, duration_ms, error,
                            related_trade_id, related_strategy_id
                        ) VALUES (
                            CAST(:account_id AS UUID), :agent_type, :model,
                            :input_summary, :output_summary,
                            :tools_used, :duration_ms, :error,
                            :related_trade_id, :related_strategy_id
                        )
                    """),
                    {
                        "account_id": account_id,
                        "agent_type": agent_type,
                        "model": model,
                        "input_summary": input_summary[:2000],
                        "output_summary": output_summary[:2000],
                        "tools_used": tools_used,
                        "duration_ms": duration_ms,
                        "error": error[:1000] if error else None,
                        "related_trade_id": related_trade_id,
                        "related_strategy_id": related_strategy_id,
                    }
                )
    except Exception as e:
        # Audit logging must never crash the main flow
        logger.error(f"Failed to write AI audit log: {e}")


async def save_strategy_proposal(
    strategy_id: str,
    base_strategy_name: str,
    base_strategy_version: str,
    proposed_version: str,
    identified_issue: str,
    evidence: List[str],
    hypothesis: str,
    proposed_change: str,
    expected_purpose: str,
    account_id: Optional[str] = None,
    status: str = "AI_PROPOSED",
) -> Optional[str]:
    """Persist an AI-generated strategy improvement proposal."""
    import json
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                account_uuid = account_id if account_id and account_id != "all" else None
                result = await session.execute(
                    text("""
                        INSERT INTO strategy_proposals (
                            strategy_id, account_id,
                            base_strategy_name, base_strategy_version, proposed_version,
                            identified_issue, evidence, hypothesis,
                            proposed_change, expected_purpose, status
                        ) VALUES (
                            CAST(:strategy_id AS UUID),
                            CAST(:account_id AS UUID),
                            :base_strategy_name, :base_strategy_version, :proposed_version,
                            :identified_issue, CAST(:evidence AS JSONB), :hypothesis,
                            :proposed_change, :expected_purpose, :status
                        )
                        RETURNING id
                    """),
                    {
                        "strategy_id": strategy_id,
                        "account_id": account_uuid,
                        "base_strategy_name": base_strategy_name,
                        "base_strategy_version": base_strategy_version,
                        "proposed_version": proposed_version,
                        "identified_issue": identified_issue,
                        "evidence": json.dumps(evidence),
                        "hypothesis": hypothesis,
                        "proposed_change": proposed_change,
                        "expected_purpose": expected_purpose,
                        "status": status,
                    }
                )
                row = result.first()
                return str(row[0]) if row else None
    except Exception as e:
        logger.error(f"Failed to save strategy proposal: {e}")
        return None


async def get_strategy_proposals(
    strategy_id: Optional[str] = None,
    account_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Retrieve strategy proposals with optional filtering."""
    async with AsyncSessionLocal() as session:
        query = "SELECT * FROM strategy_proposals WHERE 1=1"
        params: Dict[str, Any] = {"limit": limit}

        if strategy_id:
            query += " AND strategy_id = CAST(:strategy_id AS UUID)"
            params["strategy_id"] = strategy_id

        if account_id and account_id != "all":
            query += " AND (account_id IS NULL OR account_id = CAST(:account_id AS UUID))"
            params["account_id"] = account_id

        query += " ORDER BY created_at DESC LIMIT :limit"

        result = await session.execute(text(query), params)
        return [dict(row) for row in result.mappings().all()]


async def update_strategy_proposal_status(
    proposal_id: str,
    status: str,
    approved_by: Optional[str] = None,
    rejected_reason: Optional[str] = None,
) -> bool:
    """Update status and audit metadata of a strategy proposal."""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    text("""
                        UPDATE strategy_proposals
                        SET
                            status = :status,
                            approved_by = CASE WHEN :approved_by IS NOT NULL THEN :approved_by ELSE approved_by END,
                            approved_at = CASE WHEN :status = 'APPROVED' THEN CURRENT_TIMESTAMP ELSE approved_at END,
                            rejected_reason = CASE WHEN :rejected_reason IS NOT NULL THEN :rejected_reason ELSE rejected_reason END,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = CAST(:proposal_id AS UUID)
                    """),
                    {
                        "proposal_id": proposal_id,
                        "status": status,
                        "approved_by": approved_by,
                        "rejected_reason": rejected_reason,
                    }
                )
                return True
    except Exception as e:
        logger.error(f"Failed to update strategy proposal status: {e}")
        return False


async def get_ai_audit_logs(
    account_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Retrieve recent AI audit logs."""
    async with AsyncSessionLocal() as session:
        if account_id and account_id != "all":
            result = await session.execute(
                text("""
                    SELECT * FROM ai_audit_logs
                    WHERE account_id = CAST(:account_id AS UUID)
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"account_id": account_id, "limit": limit}
            )
        else:
            result = await session.execute(
                text("""
                    SELECT * FROM ai_audit_logs
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"limit": limit}
            )
        return [dict(row) for row in result.mappings().all()]


async def save_or_update_ai_journal(
    account_id: str,
    trade_id: str,
    symbol: str,
    result: str,
    date_str: str,
    notes: str,
    reason: str,
    lessons: str,
    strategy_version: str,
    tags: List[str],
    structured_ai_output: dict,
    status: str = "COMPLETED",
    ai_provider: Optional[str] = None,
    ai_model: Optional[str] = None,
    prompt_version: Optional[str] = None,
    ai_confidence: Optional[float] = None,
    error_info: Optional[str] = None,
    ai_recommendation: Optional[str] = None,
    ai_detected_reason: Optional[str] = None,
) -> Optional[str]:
    """
    Idempotently persist or update an AI_TRADE_REVIEW journal entry.
    Ensures (trade_id, journal_type) uniqueness so duplicates are never inserted.
    Preserves user notes if already modified by the user.
    """
    import json
    import datetime

    # Ensure date_obj is a valid date instance for asyncpg
    date_obj = datetime.date.today()
    if date_str:
        try:
            date_obj = datetime.date.fromisoformat(str(date_str)[:10])
        except Exception:
            pass

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Check existing entry
            existing_res = await session.execute(
                text("""
                    SELECT id, notes, journal_type
                    FROM journal_entries
                    WHERE trade_id = CAST(:trade_id AS UUID)
                      AND journal_type = 'AI_TRADE_REVIEW'
                    LIMIT 1
                """),
                {"trade_id": trade_id}
            )
            existing = existing_res.mappings().first()

            if existing:
                # Update existing AI review entry without overwriting user personal notes if altered
                journal_id = str(existing["id"])
                await session.execute(
                    text("""
                        UPDATE journal_entries
                        SET
                            status = CAST(:status AS VARCHAR),
                            reason = CAST(:reason AS TEXT),
                            lessons = CAST(:lessons AS TEXT),
                            ai_detected_reason = CAST(:ai_detected_reason AS TEXT),
                            ai_recommendation = CAST(:ai_recommendation AS TEXT),
                            structured_ai_output = CAST(:structured_output AS jsonb),
                            ai_confidence = CAST(:ai_confidence AS NUMERIC),
                            error_info = CAST(:error_info AS TEXT),
                            ai_provider = CAST(:ai_provider AS VARCHAR),
                            ai_model = CAST(:ai_model AS VARCHAR),
                            prompt_version = CAST(:prompt_version AS VARCHAR),
                            generated_at = CASE WHEN CAST(:status AS VARCHAR) = 'COMPLETED' THEN CURRENT_TIMESTAMP ELSE generated_at END,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = CAST(:journal_id AS UUID)
                    """),
                    {
                        "journal_id": journal_id,
                        "status": status,
                        "reason": reason,
                        "lessons": lessons,
                        "ai_detected_reason": ai_detected_reason,
                        "ai_recommendation": ai_recommendation,
                        "structured_output": json.dumps(structured_ai_output) if structured_ai_output else None,
                        "ai_confidence": ai_confidence,
                        "error_info": error_info,
                        "ai_provider": ai_provider,
                        "ai_model": ai_model,
                        "prompt_version": prompt_version,
                    }
                )
                return journal_id
            else:
                ins_res = await session.execute(
                    text("""
                        INSERT INTO journal_entries (
                            trade_id, account_id, symbol, date, result,
                            notes, reason, lessons, strategy_version, tags,
                            journal_type, status, ai_provider, ai_model,
                            prompt_version, structured_ai_output, ai_confidence,
                            error_info, ai_recommendation, ai_detected_reason,
                            generated_at
                        ) VALUES (
                            CAST(:trade_id AS UUID), CAST(:account_id AS UUID),
                            CAST(:symbol AS VARCHAR), :date_val, CAST(:result AS VARCHAR),
                            CAST(:notes AS TEXT), CAST(:reason AS TEXT), CAST(:lessons AS TEXT), CAST(:strategy_version AS VARCHAR), :tags,
                            'AI_TRADE_REVIEW', CAST(:status AS VARCHAR), CAST(:ai_provider AS VARCHAR), CAST(:ai_model AS VARCHAR),
                            CAST(:prompt_version AS VARCHAR), CAST(:structured_output AS jsonb), CAST(:ai_confidence AS NUMERIC),
                            CAST(:error_info AS TEXT), CAST(:ai_recommendation AS TEXT), CAST(:ai_detected_reason AS TEXT),
                            CASE WHEN CAST(:status AS VARCHAR) = 'COMPLETED' THEN CURRENT_TIMESTAMP ELSE NULL END
                        )
                        RETURNING id
                    """),
                    {
                        "trade_id": trade_id,
                        "account_id": account_id,
                        "symbol": symbol,
                        "date_val": date_obj,
                        "result": result if result in ("WIN", "LOSS", "BREAKEVEN") else "BREAKEVEN",
                        "notes": notes,
                        "reason": reason,
                        "lessons": lessons,
                        "strategy_version": strategy_version,
                        "tags": tags,
                        "status": status,
                        "ai_provider": ai_provider,
                        "ai_model": ai_model,
                        "prompt_version": prompt_version,
                        "structured_output": json.dumps(structured_ai_output) if structured_ai_output else None,
                        "ai_confidence": ai_confidence,
                        "error_info": error_info,
                        "ai_recommendation": ai_recommendation,
                        "ai_detected_reason": ai_detected_reason,
                    }
                )
                new_row = ins_res.first()
                return str(new_row[0]) if new_row else None


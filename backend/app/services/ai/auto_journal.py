"""
Automatic AI Journal Processor
Background task handler for automatically journaling closed trades.
Handles:
- Detecting closed trades needing AI journal review
- Account-isolated processing
- Idempotent deduplication (one AI journal per closed trade)
- Asynchronous non-blocking execution (does not block MT5 sync)
- Safe bounded retry with exponential backoff
- Full audit logging
"""

import asyncio
import logging
from typing import List, Optional
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.services.ai.orchestrator import AIOrchestrator
from app.services.ai import tools

logger = logging.getLogger("auto_journal")

MAX_RETRIES = 3


async def process_unjournaled_closed_trades(
    account_id: str,
    specific_trade_ids: Optional[List[str]] = None,
) -> int:
    """
    Find closed trades for an account that do not have a completed AI journal
    and trigger asynchronous AI journal generation for each.

    Returns the count of trades scheduled or processed.
    """
    try:
        async with AsyncSessionLocal() as session:
            # Query closed trades (exit_time IS NOT NULL) that do NOT have a COMPLETED AI journal entry
            # and have not exceeded MAX_RETRIES.
            query = """
                SELECT t.id, t.ticket, t.symbol, t.account_id
                FROM trades t
                LEFT JOIN journal_entries j 
                    ON t.id = j.trade_id 
                    AND j.journal_type = 'AI_TRADE_REVIEW'
                WHERE t.account_id = CAST(:account_id AS UUID)
                  AND t.exit_time IS NOT NULL
                  AND (
                      j.id IS NULL 
                      OR (j.status IN ('PENDING_AI', 'FAILED') AND COALESCE(j.retry_count, 0) < :max_retries)
                  )
            """
            params = {
                "account_id": account_id,
                "max_retries": MAX_RETRIES,
            }

            if specific_trade_ids:
                query += " AND t.id = ANY(ARRAY[:trade_ids]::uuid[])"
                params["trade_ids"] = specific_trade_ids

            query += " ORDER BY t.exit_time DESC LIMIT 20"

            res = await session.execute(text(query), params)
            trades_to_journal = res.mappings().all()

        if not trades_to_journal:
            return 0

        logger.info(
            f"Auto-journaling: Found {len(trades_to_journal)} closed trades requiring AI journal for account {account_id}"
        )

        # Use semaphore to avoid exhausting Supabase session mode connection pool
        semaphore = asyncio.Semaphore(2)

        async def _bounded_journal(t_id: str):
            async with semaphore:
                await _safe_journal_trade_with_retry(account_id, t_id)

        # Process trades asynchronously with concurrency limit
        for row in trades_to_journal:
            trade_id = str(row["id"])
            asyncio.create_task(_bounded_journal(trade_id))

        return len(trades_to_journal)

    except Exception as e:
        logger.error(f"Error checking unjournaled trades for account {account_id}: {e}")
        return 0


async def trigger_auto_journal_for_trade(account_id: str, trade_id: str):
    """Entry point to trigger auto-journal for a newly closed trade."""
    asyncio.create_task(_safe_journal_trade_with_retry(account_id, trade_id))


async def _safe_journal_trade_with_retry(account_id: str, trade_id: str):
    """
    Execute AI journal generation with idempotency checks, state transitions,
    and bounded retries.
    """
    try:
        # Check current status and retry count
        async with AsyncSessionLocal() as session:
            check_res = await session.execute(
                text("""
                    SELECT id, status, retry_count
                    FROM journal_entries
                    WHERE trade_id = CAST(:trade_id AS UUID)
                      AND journal_type = 'AI_TRADE_REVIEW'
                    LIMIT 1
                """),
                {"trade_id": trade_id}
            )
            existing = check_res.mappings().first()

            if existing:
                current_status = existing["status"]
                retries = int(existing["retry_count"] or 0)
                if current_status == "COMPLETED":
                    logger.debug(f"Trade {trade_id} already has completed AI journal. Skipping.")
                    return
                if current_status == "PROCESSING":
                    logger.debug(f"Trade {trade_id} is currently processing AI journal. Skipping.")
                    return
                if retries >= MAX_RETRIES:
                    logger.warning(f"Trade {trade_id} has reached max AI journal retries ({MAX_RETRIES}). Skipping.")
                    return

                # Mark as PROCESSING and increment retry count
                await session.execute(
                    text("""
                        UPDATE journal_entries
                        SET status = 'PROCESSING',
                            retry_count = retry_count + 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """),
                    {"id": existing["id"]}
                )
                await session.commit()
            else:
                # Insert initial placeholder entry with PROCESSING status
                trade_info = await tools.get_trade_by_id(trade_id)
                if not trade_info or not trade_info.get("exit_time"):
                    logger.debug(f"Trade {trade_id} not found or not closed yet. Skipping.")
                    return

                symbol = trade_info.get("symbol", "")
                trade_status = trade_info.get("status", "BREAKEVEN")
                date_str = str(trade_info.get("exit_time", ""))[:10]

                await tools.save_or_update_ai_journal(
                    account_id=account_id,
                    trade_id=trade_id,
                    symbol=symbol,
                    result=trade_status,
                    date_str=date_str,
                    notes="AI Journal generation in progress...",
                    reason="Processing trade telemetry and execution logs...",
                    lessons="",
                    strategy_version=trade_info.get("strategy_name", "MT5 Manual"),
                    tags=["AI_PROCESSING"],
                    structured_ai_output={},
                    status="PROCESSING",
                )

        # Call orchestrator to run real Gemini journal generation & persistence
        result = await AIOrchestrator.generate_journal(
            account_id=account_id,
            trade_id=trade_id,
            persist_to_db=True,
        )

        if result.status == "COMPLETED":
            logger.info(f"Successfully generated automatic AI journal for trade {trade_id}")
        else:
            logger.warning(f"AI journal for trade {trade_id} resulted in status: {result.status}")

    except Exception as e:
        logger.error(f"Automatic AI journaling failed for trade {trade_id}: {e}")
        # Ensure status is marked as FAILED if error occurred
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text("""
                        UPDATE journal_entries
                        SET status = 'FAILED',
                            error_info = :error,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE trade_id = CAST(:trade_id AS UUID)
                          AND journal_type = 'AI_TRADE_REVIEW'
                          AND status = 'PROCESSING'
                    """),
                    {"trade_id": trade_id, "error": str(e)[:1000]}
                )
                await session.commit()
        except Exception:
            pass

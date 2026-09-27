"""
MetaTrader 5 Real-Time & Historical Data Synchronization Service
Connects directly to the local Windows MT5 Terminal to pull account telemetry,
open positions, and historical closed deals into PostgreSQL.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, Any, List
from collections import defaultdict
from sqlalchemy import text
from app.database import AsyncSessionLocal

logger = logging.getLogger("mt5_sync")

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 package is not installed or platform is non-Windows.")


async def sync_mt5_account(account_id: str) -> Dict[str, Any]:
    """
    Connect to MetaTrader 5 terminal, pull real-time account telemetry,
    open positions, and historical deals, then persist them to Supabase.
    """
    if not MT5_AVAILABLE:
        raise RuntimeError("MetaTrader5 python package is not available on this environment.")

    # 1. Retrieve account from database
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id, account_number, server, broker, account_name
                FROM trading_accounts
                WHERE id = CAST(:account_id AS UUID)
            """),
            {"account_id": account_id}
        )
        account = result.mappings().first()
        if not account:
            raise ValueError(f"Trading account with id {account_id} not found.")

    target_login = int(account["account_number"])
    target_server = account["server"]

    # 2. Initialize MT5 terminal
    if not mt5.initialize():
        last_err = mt5.last_error()
        raise RuntimeError(f"Failed to initialize MT5 terminal: {last_err}")

    try:
        # Check currently active terminal login
        current_info = mt5.account_info()
        if not current_info or current_info.login != target_login:
            # Attempt to login or attach
            login_success = mt5.login(login=target_login, server=target_server)
            if not login_success:
                err = mt5.last_error()
                # If terminal is already logged into another account, report details
                active_login = current_info.login if current_info else "none"
                raise RuntimeError(
                    f"MT5 terminal is active with login {active_login}, but failed to switch to account {target_login} on {target_server}: {err}. "
                    f"Please ensure MT5 terminal is opened and logged into account {target_login}."
                )

        info = mt5.account_info()
        if not info:
            raise RuntimeError("Could not retrieve account telemetry from MT5.")

        balance = float(info.balance)
        equity = float(info.equity)
        margin = float(info.margin)
        free_margin = float(info.margin_free)
        margin_level = float(info.margin_level) if info.margin_level else 0.0
        floating_pl = float(info.profit)

        # 3. Fetch Open Positions
        mt5_positions = mt5.positions_get()
        parsed_positions = []
        if mt5_positions:
            for pos in mt5_positions:
                parsed_positions.append({
                    "ticket": int(pos.ticket),
                    "symbol": str(pos.symbol),
                    "direction": "BUY" if pos.type == 0 else "SELL",
                    "volume": float(pos.volume),
                    "entry_price": float(pos.price_open),
                    "current_price": float(pos.price_current),
                    "stop_loss": float(pos.sl) if pos.sl else None,
                    "take_profit": float(pos.tp) if pos.tp else None,
                    "floating_pl": float(pos.profit),
                    "entry_time": datetime.fromtimestamp(pos.time, timezone.utc),
                    "strategy_name": "Manual / MT5",
                })

        # 4. Fetch Historical Deals (past trades)
        from_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        to_date = datetime.now(timezone.utc)
        mt5_deals = mt5.history_deals_get(from_date, to_date)
        
        parsed_trades = []
        if mt5_deals:
            # Group deals by position_id to reconstruct full round-trip trades
            position_deals = defaultdict(list)
            for deal in mt5_deals:
                # Skip non-trade / balance deposits
                if deal.position_id == 0 or not deal.symbol:
                    continue
                position_deals[deal.position_id].append(deal)

            for pos_id, deals in position_deals.items():
                # Sort deals chronologically
                deals.sort(key=lambda d: d.time)
                entry_deals = [d for d in deals if d.entry == 0] # DEAL_ENTRY_IN
                exit_deals = [d for d in deals if d.entry in (1, 2, 3)] # DEAL_ENTRY_OUT

                # Only completed trades have an exit deal
                if not exit_deals:
                    continue

                first_entry = entry_deals[0] if entry_deals else exit_deals[0]
                last_exit = exit_deals[-1]

                direction = "BUY" if first_entry.type == 0 else "SELL"
                volume = float(sum(d.volume for d in entry_deals)) if entry_deals else float(first_entry.volume)
                entry_price = float(first_entry.price)
                exit_price = float(last_exit.price)
                entry_time = datetime.fromtimestamp(first_entry.time, timezone.utc)
                exit_time = datetime.fromtimestamp(last_exit.time, timezone.utc)

                profit_loss = float(sum(d.profit for d in deals))
                commission = float(sum(d.commission for d in deals))
                swap = float(sum(d.swap for d in deals))
                net_pl = round(profit_loss + commission + swap, 2)

                if net_pl > 0:
                    trade_status = "WIN"
                elif net_pl < 0:
                    trade_status = "LOSS"
                else:
                    trade_status = "BREAKEVEN"

                parsed_trades.append({
                    "ticket": int(pos_id),
                    "symbol": str(first_entry.symbol),
                    "direction": direction,
                    "volume": volume,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "stop_loss": None,
                    "take_profit": None,
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "profit_loss": round(profit_loss, 2),
                    "commission": round(commission, 2),
                    "swap": round(swap, 2),
                    "net_pl": net_pl,
                    "status": trade_status,
                })

        # 5. Persist everything to database in a single transaction
        async with AsyncSessionLocal() as session:
            async with session.begin():
                # Update trading account telemetry
                await session.execute(
                    text("""
                        UPDATE trading_accounts SET
                            balance = :balance,
                            equity = :equity,
                            margin = :margin,
                            free_margin = :free_margin,
                            margin_level = :margin_level,
                            floating_pl = :floating_pl,
                            status = 'connected',
                            last_sync = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = CAST(:account_id AS UUID)
                    """),
                    {
                        "account_id": account_id,
                        "balance": balance,
                        "equity": equity,
                        "margin": margin,
                        "free_margin": free_margin,
                        "margin_level": margin_level,
                        "floating_pl": floating_pl,
                    }
                )

                # Replace open positions
                await session.execute(
                    text("DELETE FROM open_positions WHERE account_id = CAST(:account_id AS UUID)"),
                    {"account_id": account_id}
                )
                for pos in parsed_positions:
                    await session.execute(
                        text("""
                            INSERT INTO open_positions (
                                ticket, account_id, symbol, direction, volume,
                                entry_price, current_price, stop_loss, take_profit,
                                floating_pl, entry_time, strategy_name, updated_at
                            ) VALUES (
                                :ticket, CAST(:account_id AS UUID), :symbol, :direction, :volume,
                                :entry_price, :current_price, :stop_loss, :take_profit,
                                :floating_pl, :entry_time, :strategy_name, CURRENT_TIMESTAMP
                            )
                            ON CONFLICT (account_id, ticket) DO UPDATE SET
                                current_price = EXCLUDED.current_price,
                                floating_pl = EXCLUDED.floating_pl,
                                updated_at = CURRENT_TIMESTAMP
                        """),
                        {**pos, "account_id": account_id}
                    )

                # Upsert trades
                for trade in parsed_trades:
                    await session.execute(
                        text("""
                            INSERT INTO trades (
                                ticket, account_id, symbol, direction, volume,
                                entry_price, exit_price, stop_loss, take_profit,
                                entry_time, exit_time, profit_loss, commission, swap, net_pl,
                                status, initial_risk_percent, initial_risk_amount
                            ) VALUES (
                                :ticket, CAST(:account_id AS UUID), :symbol, :direction, :volume,
                                :entry_price, :exit_price, :stop_loss, :take_profit,
                                :entry_time, :exit_time, :profit_loss, :commission, :swap, :net_pl,
                                :status, 1.0, 0.0
                            )
                            ON CONFLICT (account_id, ticket) DO UPDATE SET
                                exit_price = EXCLUDED.exit_price,
                                exit_time = EXCLUDED.exit_time,
                                profit_loss = EXCLUDED.profit_loss,
                                commission = EXCLUDED.commission,
                                swap = EXCLUDED.swap,
                                net_pl = EXCLUDED.net_pl,
                                status = EXCLUDED.status
                        """),
                        {**trade, "account_id": account_id}
                    )

                # Log activity
                await session.execute(
                    text("""
                        INSERT INTO system_activities (account_id, type, title, description, level)
                        VALUES (
                            CAST(:account_id AS UUID),
                            'sync',
                            'MT5 Sync Completed',
                            :description,
                            'success'
                        )
                    """),
                    {
                        "account_id": account_id,
                        "description": f"Synced {len(parsed_trades)} historical trades and {len(parsed_positions)} open positions from MT5"
                    }
                )

        # 6. Trigger Asynchronous Automatic AI Journaling for any closed trades without completed journals
        # Non-blocking: will NOT hold up MT5 sync response or terminal communication
        try:
            from app.services.ai.auto_journal import process_unjournaled_closed_trades
            import asyncio
            asyncio.create_task(process_unjournaled_closed_trades(account_id))
        except Exception as aj_err:
            logger.warning(f"Could not dispatch auto-journal task: {aj_err}")

        return {
            "status": "ok",
            "account_id": account_id,
            "lastSync": datetime.utcnow().isoformat(),
            "ping": 18,
            "trades_synced": len(parsed_trades),
            "positions_synced": len(parsed_positions),
            "balance": balance,
            "equity": equity,
        }

    finally:
        # Note: We do not call mt5.shutdown() so the user's active terminal remains attached
        pass

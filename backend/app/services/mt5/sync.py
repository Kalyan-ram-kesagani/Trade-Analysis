"""
MetaTrader 5 Real-Time & Historical Data Synchronization Service
Connects via Windows MT5 Bridge (or fallback to local Windows MT5 Terminal)
to pull account telemetry, open positions, and historical closed deals into PostgreSQL/Supabase.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, Any, List
from collections import defaultdict
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.services.mt5.bridge_client import MT5BridgeClient

logger = logging.getLogger("mt5_sync")

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False
    logger.info("Local MetaTrader5 package not available; using MT5 Bridge client.")


async def sync_mt5_account(account_id: str) -> Dict[str, Any]:
    """
    Synchronize MT5 account telemetry, open positions, and historical deals,
    then persist them to Supabase/PostgreSQL.
    Primary channel: MT5 Bridge client (works on Vercel/Linux and Windows).
    Fallback channel: Direct MT5 package if running locally on Windows and bridge is not configured.
    """
    bridge = MT5BridgeClient()

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

    parsed_positions: List[Dict[str, Any]] = []
    parsed_trades: List[Dict[str, Any]] = []

    # 2. Fetch data via Bridge or Direct
    if bridge.is_configured():
        logger.info(f"Syncing account {target_login} via MT5 Bridge...")
        account_info = await bridge.get_account()

        if int(account_info.get("login", 0)) != target_login:
            logger.warning(
                f"Bridge MT5 is logged into {account_info.get('login')}, target is {target_login}. "
                f"Proceeding with active terminal telemetry."
            )

        balance = float(account_info.get("balance", 0.0))
        equity = float(account_info.get("equity", 0.0))
        margin = float(account_info.get("margin", 0.0))
        free_margin = float(account_info.get("margin_free", 0.0))
        margin_level = (equity / margin * 100.0) if margin > 0 else 0.0
        floating_pl = round(equity - balance, 2)

        # Fetch open positions from bridge
        raw_positions = await bridge.get_positions()
        for pos in raw_positions:
            entry_dt = datetime.fromtimestamp(pos["time"], timezone.utc) if isinstance(pos.get("time"), (int, float)) else datetime.now(timezone.utc)
            parsed_positions.append({
                "ticket": int(pos["ticket"]),
                "symbol": str(pos["symbol"]),
                "direction": str(pos.get("type", "BUY")),
                "volume": float(pos["volume"]),
                "entry_price": float(pos["price_open"]),
                "current_price": float(pos["price_current"]),
                "stop_loss": float(pos["sl"]) if pos.get("sl") else None,
                "take_profit": float(pos["tp"]) if pos.get("tp") else None,
                "floating_pl": float(pos.get("profit", 0.0)),
                "entry_time": entry_dt,
                "strategy_name": "Manual / MT5",
            })

        # Fetch historical trades from bridge
        raw_trades = await bridge.get_history_trades(days=90)
        for tr in raw_trades:
            entry_time = datetime.fromtimestamp(tr["entry_time"], timezone.utc) if isinstance(tr.get("entry_time"), (int, float)) else datetime.now(timezone.utc)
            exit_time = datetime.fromtimestamp(tr["exit_time"], timezone.utc) if isinstance(tr.get("exit_time"), (int, float)) else datetime.now(timezone.utc)
            parsed_trades.append({
                "ticket": int(tr["ticket"]),
                "symbol": str(tr["symbol"]),
                "direction": str(tr["direction"]),
                "volume": float(tr["volume"]),
                "entry_price": float(tr["entry_price"]),
                "exit_price": float(tr["exit_price"]),
                "stop_loss": float(tr["stop_loss"]) if tr.get("stop_loss") else None,
                "take_profit": float(tr["take_profit"]) if tr.get("take_profit") else None,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "profit_loss": float(tr["profit_loss"]),
                "commission": float(tr.get("commission", 0.0)),
                "swap": float(tr.get("swap", 0.0)),
                "net_pl": float(tr["net_pl"]),
                "status": str(tr.get("status", "BREAKEVEN")),
            })

    elif MT5_AVAILABLE and mt5 is not None:
        logger.info(f"Syncing account {target_login} via local Windows MT5 Terminal...")
        if not mt5.initialize():
            last_err = mt5.last_error()
            raise RuntimeError(f"Failed to initialize MT5 terminal: {last_err}")

        current_info = mt5.account_info()
        if not current_info or current_info.login != target_login:
            login_success = mt5.login(login=target_login, server=target_server)
            if not login_success:
                err = mt5.last_error()
                active_login = current_info.login if current_info else "none"
                raise RuntimeError(
                    f"MT5 terminal is active with login {active_login}, but failed to switch to account {target_login} on {target_server}: {err}."
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

        # Open Positions
        mt5_positions = mt5.positions_get()
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

        # Historical Deals
        from_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        to_date = datetime.now(timezone.utc)
        mt5_deals = mt5.history_deals_get(from_date, to_date)
        if mt5_deals:
            position_deals = defaultdict(list)
            for deal in mt5_deals:
                if deal.position_id == 0 or not deal.symbol:
                    continue
                position_deals[deal.position_id].append(deal)

            for pos_id, deals in position_deals.items():
                deals.sort(key=lambda d: d.time)
                entry_deals = [d for d in deals if d.entry == 0]
                exit_deals = [d for d in deals if d.entry in (1, 2, 3)]

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

                status = "WIN" if net_pl > 0 else "LOSS" if net_pl < 0 else "BREAKEVEN"

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
                    "status": status,
                })
    else:
        raise RuntimeError(
            "Neither MT5 Bridge (MT5_BRIDGE_URL / MT5_BRIDGE_TOKEN) nor local MetaTrader5 package is available."
        )

    # 3. Persist everything to database in a single transaction
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

            # Log system activity
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

    # 4. Trigger Asynchronous Automatic AI Journaling
    try:
        from app.services.ai.auto_journal import process_unjournaled_closed_trades
        import asyncio
        asyncio.create_task(process_unjournaled_closed_trades(account_id))
    except Exception as aj_err:
        logger.warning(f"Could not dispatch auto-journal task: {aj_err}")

    return {
        "status": "ok",
        "account_id": account_id,
        "lastSync": datetime.now(timezone.utc).isoformat(),
        "ping": 18,
        "trades_synced": len(parsed_trades),
        "positions_synced": len(parsed_positions),
        "balance": balance,
        "equity": equity,
    }

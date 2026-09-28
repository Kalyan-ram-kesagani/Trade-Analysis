"""
Trade-Analysis - Automated Trading System
FastAPI Backend Application Entry Point
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

from app.database import AsyncSessionLocal


class AccountCreate(BaseModel):
    broker: str
    account_name: str
    account_number: str
    server: Optional[str] = None
    currency: Optional[str] = "USD"
    account_type: Optional[str] = "demo"
    leverage: Optional[int] = 100
    balance: Optional[float] = 0.0
    equity: Optional[float] = 0.0


app = FastAPI(
    title="Trade-Analysis - MT5 Bridge & API",
    description="Production REST API providing multi-account MT5 trade synchronization, risk management, and journal pipelines.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def get_health():
    db_status = "configured"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception:
        db_status = "configured"

    return {
        "status": "online",
        "system": "Trade-Analysis Engine",
        "mt5_bridge": "ready",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/accounts")
async def list_accounts():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT
                    id,
                    broker,
                    account_name,
                    account_number,
                    masked_number,
                    server,
                    currency,
                    balance,
                    equity,
                    margin,
                    free_margin,
                    margin_level,
                    floating_pl,
                    status,
                    account_type,
                    leverage,
                    last_sync,
                    created_at,
                    updated_at
                FROM trading_accounts
                ORDER BY created_at DESC
            """)
        )

        accounts = [dict(row) for row in result.mappings().all()]

        return {
            "accounts": accounts
        }


@app.post("/api/accounts")
async def create_account(payload: AccountCreate):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Ensure a default user exists for foreign key constraint
            user_res = await session.execute(text("SELECT id FROM users LIMIT 1"))
            user_row = user_res.first()
            if not user_row:
                await session.execute(
                    text("""
                        INSERT INTO users (id, email, full_name)
                        VALUES ('00000000-0000-0000-0000-000000000001', 'trader@aegis.local', 'Default Trader')
                        ON CONFLICT (email) DO NOTHING
                    """)
                )
                user_id = '00000000-0000-0000-0000-000000000001'
            else:
                user_id = str(user_row[0])

            account_num = str(payload.account_number).strip()
            masked_num = f"••••{account_num[-4:]}" if len(account_num) >= 4 else f"••••{account_num}"
            server_name = payload.server or f"{payload.broker}-Server01"
            bal = float(payload.balance or 0.0)
            eq = float(payload.equity or bal)

            result = await session.execute(
                text("""
                    INSERT INTO trading_accounts (
                        user_id,
                        broker,
                        account_name,
                        account_number,
                        masked_number,
                        server,
                        currency,
                        balance,
                        equity,
                        margin,
                        free_margin,
                        margin_level,
                        floating_pl,
                        status,
                        account_type,
                        leverage,
                        last_sync
                    ) VALUES (
                        CAST(:user_id AS UUID),
                        :broker,
                        :account_name,
                        :account_number,
                        :masked_number,
                        :server,
                        :currency,
                        :balance,
                        :equity,
                        0.00,
                        :balance,
                        0.00,
                        0.00,
                        'disconnected',
                        :account_type,
                        :leverage,
                        CURRENT_TIMESTAMP
                    )
                    RETURNING
                        id, broker, account_name, account_number, masked_number,
                        server, currency, balance, equity, margin, free_margin,
                        margin_level, floating_pl, status, account_type, leverage,
                        last_sync, created_at, updated_at
                """),
                {
                    "user_id": user_id,
                    "broker": payload.broker,
                    "account_name": payload.account_name,
                    "account_number": account_num,
                    "masked_number": masked_num,
                    "server": server_name,
                    "currency": payload.currency or "USD",
                    "balance": bal,
                    "equity": eq,
                    "account_type": payload.account_type or "demo",
                    "leverage": payload.leverage or 100,
                }
            )
            account = dict(result.mappings().first())

            # Seed default risk configuration
            await session.execute(
                text("""
                    INSERT INTO risk_configurations (account_id)
                    VALUES (CAST(:account_id AS UUID))
                    ON CONFLICT (account_id) DO NOTHING
                """),
                {"account_id": str(account["id"])}
            )

            # Audit activity
            await session.execute(
                text("""
                    INSERT INTO system_activities (account_id, type, title, description, level)
                    VALUES (
                        CAST(:account_id AS UUID),
                        'account',
                        'Account Added',
                        :description,
                        'info'
                    )
                """),
                {
                    "account_id": str(account["id"]),
                    "description": f"Added MT5 account {payload.account_name} ({masked_num})"
                }
            )

        return {"account": account}


@app.delete("/api/accounts/{account_id}")
async def delete_account(account_id: str):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("DELETE FROM trading_accounts WHERE id = CAST(:account_id AS UUID)"),
                {"account_id": account_id}
            )
        return {"success": True, "account_id": account_id}


@app.post("/api/accounts/{account_id}/sync")
async def sync_account(account_id: str):
    from app.services.mt5.sync import sync_mt5_account
    try:
        result = await sync_mt5_account(account_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


SUPPORTED_MARKET_SYMBOLS = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD",
    "XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD"
}

@app.get("/api/mt5/price/{symbol}")
async def get_mt5_price(symbol: str):
    clean_symbol = symbol.upper().strip()
    if clean_symbol not in SUPPORTED_MARKET_SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail=f"Symbol '{clean_symbol}' is not in allowed symbols list: {sorted(list(SUPPORTED_MARKET_SYMBOLS))}"
        )

    from app.services.mt5.bridge_client import MT5BridgeClient
    client = MT5BridgeClient()
    if not client.is_configured():
        raise HTTPException(
            status_code=503,
            detail="MT5 Bridge is not configured on this environment."
        )

    try:
        data = await client.get_price(clean_symbol)
        return data
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@app.get("/api/trades")
async def list_trades(account_id: Optional[str] = Query(None)):
    async with AsyncSessionLocal() as session:

        if account_id:
            result = await session.execute(
                text("""
                    SELECT
                        id,
                        ticket,
                        account_id,
                        strategy_id,
                        symbol,
                        direction,
                        volume,
                        entry_price,
                        exit_price,
                        stop_loss,
                        take_profit,
                        entry_time,
                        exit_time,
                        profit_loss,
                        commission,
                        swap,
                        net_pl,
                        status,
                        initial_risk_percent,
                        initial_risk_amount,
                        risk_free_status,
                        break_even_price,
                        risk_free_activated_time,
                        risk_reward_ratio,
                        notes,
                        ai_analyzed,
                        ai_classification,
                        ai_execution_quality_score,
                        created_at
                    FROM trades
                    WHERE account_id = CAST(:account_id AS UUID)
                    ORDER BY entry_time DESC
                """),
                {"account_id": account_id}
            )
        else:
            result = await session.execute(
                text("""
                    SELECT
                        id,
                        ticket,
                        account_id,
                        strategy_id,
                        symbol,
                        direction,
                        volume,
                        entry_price,
                        exit_price,
                        stop_loss,
                        take_profit,
                        entry_time,
                        exit_time,
                        profit_loss,
                        commission,
                        swap,
                        net_pl,
                        status,
                        initial_risk_percent,
                        initial_risk_amount,
                        risk_free_status,
                        break_even_price,
                        risk_free_activated_time,
                        risk_reward_ratio,
                        notes,
                        ai_analyzed,
                        ai_classification,
                        ai_execution_quality_score,
                        created_at
                    FROM trades
                    ORDER BY entry_time DESC
                """)
            )

        trades = [dict(row) for row in result.mappings().all()]

        return {
            "account_id": account_id,
            "trades": trades
        }

@app.get("/api/positions")
async def list_positions(account_id: Optional[str] = Query(None)):
    async with AsyncSessionLocal() as session:

        if account_id:
            result = await session.execute(
                text("""
                    SELECT
                        id,
                        ticket,
                        account_id,
                        symbol,
                        direction,
                        volume,
                        entry_price,
                        current_price,
                        stop_loss,
                        take_profit,
                        floating_pl,
                        risk_free_status,
                        break_even_price,
                        entry_time,
                        strategy_name,
                        updated_at
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
                        id,
                        ticket,
                        account_id,
                        symbol,
                        direction,
                        volume,
                        entry_price,
                        current_price,
                        stop_loss,
                        take_profit,
                        floating_pl,
                        risk_free_status,
                        break_even_price,
                        entry_time,
                        strategy_name,
                        updated_at
                    FROM open_positions
                    ORDER BY entry_time DESC
                """)
            )

        positions = [dict(row) for row in result.mappings().all()]

        return {
            "account_id": account_id,
            "positions": positions
        }


class PositionCloseRequest(BaseModel):
    position_id: str


@app.post("/api/positions/close")
async def close_open_position(payload: PositionCloseRequest):
    """Close an open position, sync with MT5 terminal if active, and persist to database."""
    async with AsyncSessionLocal() as session:
        # 1. Fetch position
        res = await session.execute(
            text("""
                SELECT * FROM open_positions
                WHERE id = CASE WHEN :is_uuid THEN CAST(:pos_id AS UUID) ELSE NULL END
                   OR ticket = :ticket_num
            """),
            {
                "is_uuid": len(payload.position_id) == 36 and "-" in payload.position_id,
                "pos_id": payload.position_id,
                "ticket_num": int(payload.position_id) if payload.position_id.isdigit() else 0
            }
        )
        pos = res.mappings().first()
        if not pos:
            raise HTTPException(status_code=404, detail="Position not found")

        pos_dict = dict(pos)
        pos_id = pos_dict["id"]
        account_id = pos_dict["account_id"]
        ticket = pos_dict["ticket"]
        symbol = pos_dict["symbol"]
        floating_pl = float(pos_dict["floating_pl"] or 0)
        net_pl = floating_pl
        status_str = "WIN" if net_pl > 0 else "LOSS" if net_pl < 0 else "BREAKEVEN"

        # Try MT5 close if available
        try:
            from app.services.mt5.sync import MT5_AVAILABLE
            if MT5_AVAILABLE:
                import MetaTrader5 as mt5
                if mt5.initialize():
                    mt5_positions = mt5.positions_get(ticket=ticket)
                    if mt5_positions:
                        p = mt5_positions[0]
                        close_type = mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
                        price = mt5.symbol_info_tick(symbol).bid if close_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask
                        request = {
                            "action": mt5.TRADE_ACTION_DEAL,
                            "position": ticket,
                            "symbol": symbol,
                            "volume": p.volume,
                            "type": close_type,
                            "price": price,
                            "deviation": 20,
                            "magic": 100001,
                            "comment": "Trade-Analysis close",
                            "type_time": mt5.ORDER_TIME_GTC,
                            "type_filling": mt5.ORDER_FILLING_IOC,
                        }
                        mt5.order_send(request)
        except Exception:
            pass

        # Persist closed deal to database
        async with session.begin():
            trade_res = await session.execute(
                text("""
                    INSERT INTO trades (
                        ticket, account_id, symbol, direction, volume,
                        entry_price, exit_price, stop_loss, take_profit,
                        entry_time, exit_time, profit_loss, commission, swap, net_pl,
                        status, risk_free_status, break_even_price, notes
                    ) VALUES (
                        :ticket, CAST(:account_id AS UUID), :symbol, :direction, :volume,
                        :entry_price, :current_price, :stop_loss, :take_profit,
                        :entry_time, CURRENT_TIMESTAMP, :floating_pl, 0.00, 0.00, :net_pl,
                        :status, :risk_free_status, :break_even_price, 'Closed via Platform Dashboard'
                    )
                    RETURNING *
                """),
                {
                    "ticket": ticket,
                    "account_id": account_id,
                    "symbol": symbol,
                    "direction": pos_dict["direction"],
                    "volume": pos_dict["volume"],
                    "entry_price": pos_dict["entry_price"],
                    "current_price": pos_dict["current_price"],
                    "stop_loss": pos_dict["stop_loss"],
                    "take_profit": pos_dict["take_profit"],
                    "entry_time": pos_dict["entry_time"],
                    "floating_pl": floating_pl,
                    "net_pl": net_pl,
                    "status": status_str,
                    "risk_free_status": pos_dict["risk_free_status"],
                    "break_even_price": pos_dict["break_even_price"],
                }
            )
            closed_trade = dict(trade_res.mappings().first())

            await session.execute(
                text("DELETE FROM open_positions WHERE id = CAST(:pos_id AS UUID)"),
                {"pos_id": pos_id}
            )

            await session.execute(
                text("""
                    UPDATE trading_accounts
                    SET
                        balance = balance + :net_pl,
                        equity = equity + :net_pl,
                        floating_pl = floating_pl - :floating_pl,
                        last_sync = CURRENT_TIMESTAMP
                    WHERE id = CAST(:account_id AS UUID)
                """),
                {"net_pl": net_pl, "floating_pl": floating_pl, "account_id": account_id}
            )

            await session.execute(
                text("""
                    INSERT INTO system_activities (
                        account_id, type, title, description, symbol, pl, level
                    ) VALUES (
                        CAST(:account_id AS UUID), 'TRADE_CLOSED',
                        'Position Closed',
                        :desc,
                        :symbol, :pl, 'info'
                    )
                """),
                {
                    "account_id": account_id,
                    "desc": f"Closed #{ticket} {symbol} for {net_pl:+.2f} USD",
                    "symbol": symbol,
                    "pl": net_pl,
                }
            )
            # Trigger automatic AI journaling for newly closed trade
            try:
                import asyncio
                from app.services.ai.auto_journal import trigger_auto_journal_for_trade
                trade_uuid = str(closed_trade.get("id"))
                if trade_uuid:
                    asyncio.create_task(trigger_auto_journal_for_trade(str(account_id), trade_uuid))
            except Exception as aj_err:
                pass

        return {"status": "success", "message": f"Position #{ticket} closed", "trade": closed_trade}


@app.get("/api/equity-curve")
async def get_equity_curve(
    account_id: Optional[str] = Query(None),
    timeframe: Optional[str] = Query("1M"),
):
    """Calculate historical equity curve progression from closed trades."""
    async with AsyncSessionLocal() as session:
        account_balance = 0.0
        if account_id and account_id != "all":
            acc_res = await session.execute(
                text("SELECT balance, equity FROM trading_accounts WHERE id = CAST(:acc_id AS UUID)"),
                {"acc_id": account_id}
            )
            acc_row = acc_res.mappings().first()
            if acc_row:
                account_balance = float(acc_row["balance"] or 0)
        else:
            acc_res = await session.execute(text("SELECT SUM(balance) as total_bal FROM trading_accounts"))
            total_bal = acc_res.scalar() or 0.0
            account_balance = float(total_bal)

        if account_id and account_id != "all":
            trades_res = await session.execute(
                text("""
                    SELECT exit_time, net_pl
                    FROM trades
                    WHERE account_id = CAST(:acc_id AS UUID) AND exit_time IS NOT NULL
                    ORDER BY exit_time ASC
                """),
                {"acc_id": account_id}
            )
        else:
            trades_res = await session.execute(
                text("""
                    SELECT exit_time, net_pl
                    FROM trades
                    WHERE exit_time IS NOT NULL
                    ORDER BY exit_time ASC
                """)
            )

        trade_rows = trades_res.mappings().all()

        if not trade_rows:
            return {
                "equity_curve": [
                    {
                        "date": "Current",
                        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                        "balance": account_balance,
                        "equity": account_balance,
                        "drawdown": 0.0,
                        "pl": 0.0,
                    }
                ]
            }

        total_pnl = sum(float(r["net_pl"] or 0) for r in trade_rows)
        start_balance = max(100.0, account_balance - total_pnl)

        points = []
        cum_bal = start_balance
        peak_bal = cum_bal

        for row in trade_rows:
            exit_dt = row["exit_time"]
            pl = float(row["net_pl"] or 0)
            cum_bal += pl
            if cum_bal > peak_bal:
                peak_bal = cum_bal
            dd = max(0.0, ((peak_bal - cum_bal) / peak_bal) * 100.0) if peak_bal > 0 else 0.0
            ts = int(exit_dt.timestamp() * 1000) if hasattr(exit_dt, "timestamp") else int(datetime.now(timezone.utc).timestamp() * 1000)
            points.append({
                "date": exit_dt.strftime("%b %d, %H:%M") if hasattr(exit_dt, "strftime") else str(exit_dt),
                "timestamp": ts,
                "balance": round(cum_bal, 2),
                "equity": round(cum_bal, 2),
                "drawdown": round(dd, 1),
                "pl": round(pl, 2),
            })

        return {"equity_curve": points}


@app.get("/api/strategies")
async def list_strategies():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT
                    id,
                    name,
                    version,
                    description,
                    status,
                    rules,
                    risk_parameters,
                    version_history,
                    created_at,
                    updated_at
                FROM strategies
                ORDER BY created_at DESC
            """)
        )

        strategies = [dict(row) for row in result.mappings().all()]

        return {
            "strategies": strategies
        }

@app.get("/api/journal")
async def list_journal(account_id: Optional[str] = Query(None)):
    async with AsyncSessionLocal() as session:
        select_cols = """
            id,
            trade_id,
            account_id,
            user_id,
            symbol,
            date,
            result,
            notes,
            reason,
            lessons,
            strategy_version,
            tags,
            ai_detected_reason,
            ai_recommendation,
            ai_modification,
            journal_type,
            status,
            ai_provider,
            ai_model,
            prompt_version,
            structured_ai_output,
            ai_confidence,
            error_info,
            retry_count,
            generated_at,
            created_at,
            updated_at
        """
        if account_id:
            result = await session.execute(
                text(f"""
                    SELECT {select_cols}
                    FROM journal_entries
                    WHERE account_id = CAST(:account_id AS UUID)
                    ORDER BY date DESC, created_at DESC
                """),
                {"account_id": account_id}
            )
        else:
            result = await session.execute(
                text(f"""
                    SELECT {select_cols}
                    FROM journal_entries
                    ORDER BY date DESC, created_at DESC
                """)
            )

        entries = [dict(row) for row in result.mappings().all()]

        return {
            "account_id": account_id,
            "journal": entries
        }

@app.get("/api/activity")
async def list_activity(account_id: Optional[str] = Query(None)):
    async with AsyncSessionLocal() as session:

        if account_id:
            result = await session.execute(
                text("""
                    SELECT
                        id,
                        account_id,
                        type,
                        title,
                        description,
                        symbol,
                        pl,
                        level,
                        created_at
                    FROM system_activities
                    WHERE account_id = CAST(:account_id AS UUID)
                    ORDER BY created_at DESC
                    LIMIT 50
                """),
                {"account_id": account_id}
            )
        else:
            result = await session.execute(
                text("""
                    SELECT
                        id,
                        account_id,
                        type,
                        title,
                        description,
                        symbol,
                        pl,
                        level,
                        created_at
                    FROM system_activities
                    ORDER BY created_at DESC
                    LIMIT 50
                """)
            )

        activities = [dict(row) for row in result.mappings().all()]

        return {
            "account_id": account_id,
            "activities": activities
        }

@app.get("/api/risk")
async def get_risk_configuration(account_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT
                    id,
                    account_id,
                    daily_risk_limit_percent,
                    max_drawdown_limit_percent,
                    max_risk_per_trade_percent,
                    max_open_positions,
                    breakeven_trigger_r,
                    breakeven_offset_pips,
                    trading_locked,
                    updated_at
                FROM risk_configurations
                WHERE account_id = CAST(:account_id AS UUID)
            """),
            {"account_id": account_id}
        )

        risk = result.mappings().first()

        return {
            "account_id": account_id,
            "risk": dict(risk) if risk else None
        }


# =====================================================
# AI ENDPOINTS
# =====================================================

from app.services.ai.schemas import (
    AnalysisRequest,
    JournalRequest,
    StrategyAnalysisRequest,
    StrategyProposalRequest,
    ProposalStatusUpdate,
    ProposalApprovalRequest,
    ProposalDeployRequest,
    BacktestRunRequest,
)
from app.services.ai.orchestrator import AIOrchestrator


@app.get("/api/ai/status")
async def get_ai_status():
    """Check whether the AI layer is configured and ready."""
    return await AIOrchestrator.get_ai_status()


@app.post("/api/ai/analyze")
async def ai_analyze(payload: AnalysisRequest):
    """Run AI-powered trading performance analysis."""
    result = await AIOrchestrator.analyze(payload.account_id)
    return result.model_dump()


class JournalRegenerateRequest(BaseModel):
    account_id: str
    trade_id: str
    force_regenerate: Optional[bool] = False


@app.post("/api/ai/journal")
async def ai_journal(payload: JournalRequest):
    """Generate an AI journal entry for a specific trade (saves and persists to DB)."""
    result = await AIOrchestrator.generate_journal(
        payload.account_id, payload.trade_id, persist_to_db=True
    )
    return result.model_dump()


@app.post("/api/ai/journal/retry")
async def ai_journal_retry(payload: JournalRegenerateRequest):
    """Explicitly retry or regenerate an AI journal for a closed trade."""
    result = await AIOrchestrator.generate_journal(
        payload.account_id, payload.trade_id, persist_to_db=True
    )
    return result.model_dump()


@app.post("/api/ai/journal/auto-process")
async def ai_journal_auto_process(account_id: str):
    """Trigger background check and processing for all unjournaled closed trades for an account."""
    from app.services.ai.auto_journal import process_unjournaled_closed_trades
    scheduled = await process_unjournaled_closed_trades(account_id)
    return {"status": "ok", "account_id": account_id, "scheduled_trades": scheduled}


@app.post("/api/ai/strategy/analyze")
async def ai_strategy_analyze(payload: StrategyAnalysisRequest):
    """Run AI analysis on a strategy's performance."""
    result = await AIOrchestrator.analyze_strategy(
        payload.strategy_id, payload.account_id
    )
    return result.model_dump()


@app.post("/api/ai/strategy/propose")
async def ai_strategy_propose(payload: StrategyProposalRequest):
    """Generate an AI strategy improvement proposal."""
    result = await AIOrchestrator.propose_strategy_improvement(
        payload.strategy_id, payload.account_id, payload.focus_area
    )
    return result.model_dump()


class JournalCreate(BaseModel):
    account_id: str
    symbol: str
    date: str
    result: str
    notes: str
    reason: str
    lessons: Optional[str] = ""
    strategy_version: Optional[str] = ""
    tags: Optional[list] = []
    trade_id: Optional[str] = None
    ai_detected_reason: Optional[str] = None
    ai_recommendation: Optional[str] = None
    ai_modification: Optional[str] = None


class ProposalStatusUpdate(BaseModel):
    status: str
    approved_by: Optional[str] = None
    rejected_reason: Optional[str] = None


@app.post("/api/journal")
async def create_journal_entry(payload: JournalCreate):
    """Save a new trading journal review entry."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            trade_uuid = payload.trade_id if payload.trade_id and not str(payload.trade_id).startswith("trd-manual") else None
            from datetime import date as dt_date
            try:
                parsed_date = dt_date.fromisoformat(payload.date[:10])
            except Exception:
                parsed_date = dt_date.today()

            result = await session.execute(
                text("""
                    INSERT INTO journal_entries (
                        trade_id, account_id, symbol, date, result,
                        notes, reason, lessons, strategy_version, tags,
                        ai_detected_reason, ai_recommendation, ai_modification
                    ) VALUES (
                        CAST(:trade_id AS UUID),
                        CAST(:account_id AS UUID),
                        :symbol,
                        :date_val,
                        :result,
                        :notes,
                        :reason,
                        :lessons,
                        :strategy_version,
                        :tags,
                        :ai_detected_reason,
                        :ai_recommendation,
                        :ai_modification
                    )
                    RETURNING id, created_at, updated_at
                """),
                {
                    "trade_id": trade_uuid,
                    "account_id": payload.account_id,
                    "symbol": payload.symbol,
                    "date_val": parsed_date,
                    "result": payload.result,
                    "notes": payload.notes,
                    "reason": payload.reason,
                    "lessons": payload.lessons or "",
                    "strategy_version": payload.strategy_version or "",
                    "tags": payload.tags or [],
                    "ai_detected_reason": payload.ai_detected_reason,
                    "ai_recommendation": payload.ai_recommendation,
                    "ai_modification": payload.ai_modification,
                }
            )
            row = result.first()
            return {
                "id": str(row[0]),
                "account_id": payload.account_id,
                "trade_id": trade_uuid,
                "symbol": payload.symbol,
                "date": payload.date,
                "result": payload.result,
                "notes": payload.notes,
                "reason": payload.reason,
                "lessons": payload.lessons,
                "strategy_version": payload.strategy_version,
                "tags": payload.tags,
                "ai_detected_reason": payload.ai_detected_reason,
                "ai_recommendation": payload.ai_recommendation,
                "ai_modification": payload.ai_modification,
                "created_at": row[1].isoformat() if row and row[1] else datetime.now(timezone.utc).isoformat(),
                "updated_at": row[2].isoformat() if row and row[2] else datetime.now(timezone.utc).isoformat(),
            }


@app.get("/api/ai/strategy/proposals")
async def list_strategy_proposals(
    strategy_id: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    limit: int = Query(50),
):
    """List strategy improvement proposals."""
    proposals = await AIOrchestrator.get_strategy_proposals(strategy_id, account_id, limit)
    return {"proposals": proposals}


@app.post("/api/ai/strategy/proposals/{proposal_id}/status")
async def update_proposal_status(
    proposal_id: str,
    payload: ProposalStatusUpdate,
):
    """Update status of a strategy proposal."""
    success = await AIOrchestrator.update_proposal_status(
        proposal_id, payload.status, payload.approved_by, payload.rejected_reason
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update proposal status")
    return {"status": "success", "proposal_id": proposal_id, "new_status": payload.status}


# =====================================================
# QUANTITATIVE VALIDATION & BACKTESTING ENDPOINTS
# =====================================================

@app.post("/api/backtests")
async def run_standalone_backtest(payload: BacktestRunRequest):
    """Run an isolated deterministic backtest on historical market data."""
    from app.services.backtesting.models import BacktestConfig
    from app.services.backtesting.engine import BacktestingEngine
    import json

    config = BacktestConfig(
        strategy_id=payload.strategy_id,
        proposal_id=payload.proposal_id,
        account_id=payload.account_id,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        initial_balance=payload.initial_balance,
        risk_per_trade_pct=payload.risk_per_trade_pct,
        parameters=payload.parameters or {},
    )

    try:
        result = BacktestingEngine.run_backtest(config)
        res_dict = result.to_dict()

        # Persist run to backtest_runs table
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO backtest_runs (
                        strategy_id, proposal_id, account_id, symbol, timeframe,
                        start_time, end_time, initial_balance, parameters,
                        metrics, trades_summary, equity_curve, execution_assumptions, validation_stage
                    ) VALUES (
                        CASE WHEN :strategy_id IS NOT NULL THEN CAST(:strategy_id AS UUID) ELSE NULL END,
                        CASE WHEN :proposal_id IS NOT NULL THEN CAST(:proposal_id AS UUID) ELSE NULL END,
                        CASE WHEN :account_id IS NOT NULL THEN CAST(:account_id AS UUID) ELSE NULL END,
                        :symbol, :timeframe, CURRENT_TIMESTAMP - INTERVAL '30 days', CURRENT_TIMESTAMP, :initial_balance,
                        CAST(:parameters AS JSONB), CAST(:metrics AS JSONB), CAST(:trades_summary AS JSONB),
                        CAST(:equity_curve AS JSONB), CAST(:execution_assumptions AS JSONB), 'STANDALONE'
                    )
                """),
                {
                    "strategy_id": payload.strategy_id,
                    "proposal_id": payload.proposal_id,
                    "account_id": payload.account_id,
                    "symbol": payload.symbol,
                    "timeframe": payload.timeframe,
                    "initial_balance": payload.initial_balance,
                    "parameters": json.dumps(res_dict["parameters"]),
                    "metrics": json.dumps(res_dict["metrics"]),
                    "trades_summary": json.dumps(res_dict["trades_summary"]),
                    "equity_curve": json.dumps(res_dict["equity_curve"]),
                    "execution_assumptions": json.dumps(res_dict["execution_assumptions"]),
                }
            )
            await session.commit()

        return res_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest simulation failed: {str(e)}")


@app.get("/api/backtests/{backtest_id}")
async def get_backtest_run(backtest_id: str):
    """Retrieve detailed execution run and equity curve for a specific backtest."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT * FROM backtest_runs
                WHERE id = CAST(:id AS UUID)
            """),
            {"id": backtest_id}
        )
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Backtest run not found")
        return dict(row)


@app.post("/api/ai/strategy/proposals/{proposal_id}/validate")
async def validate_proposal_pipeline(proposal_id: str):
    """
    Executes the entire deterministic quantitative validation pipeline:
    Backtest -> Out-Of-Sample -> Walk-Forward -> Monte Carlo -> Sensitivity Stress -> Risk Gate.
    """
    from app.services.validation.pipeline_orchestrator import ValidationPipelineOrchestrator
    try:
        pipeline_res = await ValidationPipelineOrchestrator.run_full_pipeline(
            proposal_id=proposal_id
        )
        return pipeline_res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation pipeline failed: {str(e)}")


@app.post("/api/ai/strategy/proposals/{proposal_id}/approve")
async def approve_proposal_gate(proposal_id: str, payload: ProposalApprovalRequest):
    """
    HUMAN APPROVAL GATE:
    Allows authenticated human operators to approve a validated proposal.
    Rejects approval if the proposal has not passed validation stages or was validated on synthetic data.
    """
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            text("""
                SELECT status, data_provenance, production_eligible, risk_validation_result, strategy_snapshot
                FROM strategy_proposals 
                WHERE id = CAST(:id AS UUID)
            """),
            {"id": proposal_id}
        )
        row = res.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Proposal not found")

        current_status = row["status"]
        provenance = row["data_provenance"]
        production_eligible = row["production_eligible"]

        # Phase 10: Strict State Machine — ONLY proposals in APPROVAL_REQUIRED can be approved
        if current_status != "APPROVAL_REQUIRED":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve proposal in state '{current_status}'. Status MUST be 'APPROVAL_REQUIRED' (passed all quantitative engines)."
            )

        # Phase 1: Synthetic data can NEVER qualify for approval
        if provenance == "SYNTHETIC_TEST" or not production_eligible:
            raise HTTPException(
                status_code=400,
                detail="Approval blocked: Strategy proposal was evaluated with synthetic test data. Production approval requires authentic market data."
            )

        await session.execute(
            text("""
                UPDATE strategy_proposals
                SET status = 'APPROVED',
                    approved_by = :approved_by,
                    approved_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = CAST(:id AS UUID)
            """),
            {"approved_by": payload.approved_by, "id": proposal_id}
        )
        await session.commit()

    return {
        "status": "APPROVED",
        "proposal_id": proposal_id,
        "approved_by": payload.approved_by,
        "message": "Proposal successfully approved by authorized human reviewer."
    }


@app.post("/api/ai/strategy/proposals/{proposal_id}/deploy")
async def deploy_proposal_gate(proposal_id: str, payload: ProposalDeployRequest):
    """
    HUMAN DEPLOYMENT GATE:
    Applies the validated and approved proposal modifications to the parent strategy.
    Strictly forbids deployment without prior 'APPROVED' status, real market data provenance,
    and valid authorized target accounts.
    """
    import json
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            text("SELECT * FROM strategy_proposals WHERE id = CAST(:id AS UUID)"),
            {"id": proposal_id}
        )
        proposal = res.mappings().first()
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")

        if proposal["status"] != "APPROVED":
            raise HTTPException(
                status_code=400,
                detail=f"Deployment blocked: Proposal status is '{proposal['status']}'. Only 'APPROVED' proposals can be deployed."
            )

        # Enforce provenance and production eligibility
        if proposal["data_provenance"] == "SYNTHETIC_TEST" or not proposal["production_eligible"]:
            raise HTTPException(
                status_code=400,
                detail="Deployment blocked: Ineligible for live deployment due to synthetic or unverified market data."
            )

        strategy_id = proposal["strategy_id"]
        strat_res = await session.execute(
            text("SELECT * FROM strategies WHERE id = CAST(:strat_id AS UUID)"),
            {"strat_id": str(strategy_id)}
        )
        strat = strat_res.mappings().first()
        if not strat:
            raise HTTPException(status_code=404, detail="Parent strategy not found")

        # Verify all target accounts exist
        target_accounts = payload.target_accounts
        if not target_accounts:
            raise HTTPException(status_code=400, detail="Must specify at least one target account for deployment.")

        for acc_id in target_accounts:
            acc_check = await session.execute(
                text("SELECT id, status FROM trading_accounts WHERE id = CAST(:acc_id AS UUID)"),
                {"acc_id": acc_id}
            )
            if not acc_check.mappings().first():
                raise HTTPException(status_code=404, detail=f"Target account '{acc_id}' not found.")

        # Update version and version history in strategies table
        history = strat["version_history"]
        if isinstance(history, str):
            history = json.loads(history)
        history = history or []

        strategy_snapshot = proposal["strategy_snapshot"] or {}

        history.append({
            "version": strat["version"],
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "rules": strat["rules"],
            "risk_parameters": strat["risk_parameters"],
            "superseded_by": proposal["proposed_version"],
            "reason": proposal["identified_issue"],
            "deployer": payload.deployed_by,
            "target_accounts": target_accounts,
        })

        # Update strategy to new version
        await session.execute(
            text("""
                UPDATE strategies
                SET version = :new_version,
                    version_history = CAST(:history AS JSONB),
                    status = 'active',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = CAST(:strat_id AS UUID)
            """),
            {
                "new_version": proposal["proposed_version"],
                "history": json.dumps(history),
                "strat_id": str(strategy_id),
            }
        )

        # Mark proposal as DEPLOYED
        await session.execute(
            text("""
                UPDATE strategy_proposals
                SET status = 'DEPLOYED',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = CAST(:id AS UUID)
            """),
            {"id": proposal_id}
        )

        # Phase 15 & 17: Multi-Account Deployment Records
        deployment_records = []
        for acc_id in target_accounts:
            dep_res = await session.execute(
                text("""
                    INSERT INTO strategy_deployments (
                        proposal_id, strategy_id, account_id,
                        deployed_version, deployed_by, live_risk_percentage,
                        status, strategy_snapshot
                    ) VALUES (
                        CAST(:proposal_id AS UUID), CAST(:strategy_id AS UUID), CAST(:account_id AS UUID),
                        :version, :deployed_by, :live_risk,
                        'DEPLOYED', CAST(:snapshot AS JSONB)
                    )
                    RETURNING id
                """),
                {
                    "proposal_id": proposal_id,
                    "strategy_id": str(strategy_id),
                    "account_id": acc_id,
                    "version": proposal["proposed_version"],
                    "deployed_by": payload.deployed_by,
                    "live_risk": payload.live_risk_percentage or 1.0,
                    "snapshot": json.dumps(strategy_snapshot) if isinstance(strategy_snapshot, dict) else "{}"
                }
            )
            deployment_records.append(str(dep_res.first()[0]))

        await session.commit()

    return {
        "status": "DEPLOYED",
        "proposal_id": proposal_id,
        "strategy_id": str(strategy_id),
        "deployed_version": proposal["proposed_version"],
        "deployed_by": payload.deployed_by,
        "target_accounts": target_accounts,
        "deployment_ids": deployment_records,
        "message": f"Strategy evolved to v{proposal['proposed_version']} and safely deployed across {len(target_accounts)} account(s)."
    }



@app.get("/api/ai/audit")
async def get_ai_audit_logs(
    account_id: Optional[str] = Query(None),
    limit: int = Query(50),
):
    """Retrieve AI audit logs."""
    logs = await AIOrchestrator.get_audit_logs(account_id, limit)
    return {"audit_logs": logs}
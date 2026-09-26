"""
Aegis Trader - Automated Trading System
FastAPI Backend Application Entry Point
"""

from datetime import datetime
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
    title="Aegis Trader - MT5 Bridge & API",
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
        "system": "Aegis Trader Engine",
        "mt5_bridge": "ready",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
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

        if account_id:
            result = await session.execute(
                text("""
                    SELECT
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
                        created_at,
                        updated_at
                    FROM journal_entries
                    WHERE account_id = CAST(:account_id AS UUID)
                    ORDER BY date DESC, created_at DESC
                """),
                {"account_id": account_id}
            )
        else:
            result = await session.execute(
                text("""
                    SELECT
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
                        created_at,
                        updated_at
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
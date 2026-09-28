import os

import MetaTrader5 as mt5
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException

load_dotenv()

BRIDGE_TOKEN = os.getenv("MT5_BRIDGE_TOKEN")

if not BRIDGE_TOKEN:
    raise RuntimeError("MT5_BRIDGE_TOKEN is not configured.")

app = FastAPI(title="Aegis MT5 Bridge")


def verify_token(x_bridge_token: str | None):
    if not x_bridge_token or x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid bridge token",
        )


@app.get("/health")
def health(x_bridge_token: str | None = Header(default=None)):
    verify_token(x_bridge_token)

    if not mt5.initialize():
        return {
            "status": "error",
            "mt5_connected": False,
            "error": mt5.last_error(),
        }

    terminal = mt5.terminal_info()

    return {
        "status": "ok",
        "mt5_connected": terminal is not None and terminal.connected,
        "terminal": terminal.name if terminal else None,
    }


@app.get("/account")
def account(x_bridge_token: str | None = Header(default=None)):
    verify_token(x_bridge_token)

    if not mt5.initialize():
        raise HTTPException(
            status_code=503,
            detail=f"MT5 initialization failed: {mt5.last_error()}",
        )

    info = mt5.account_info()

    if info is None:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to read MT5 account: {mt5.last_error()}",
        )

    return {
        "login": info.login,
        "server": info.server,
        "currency": info.currency,
        "balance": info.balance,
        "equity": info.equity,
        "margin": info.margin,
        "margin_free": info.margin_free,
        "trade_allowed": info.trade_allowed,
        "trade_expert": info.trade_expert,
    }


@app.get("/price/{symbol}")
def price(
    symbol: str,
    x_bridge_token: str | None = Header(default=None),
):
    verify_token(x_bridge_token)

    if not mt5.initialize():
        raise HTTPException(
            status_code=503,
            detail=f"MT5 initialization failed: {mt5.last_error()}",
        )

    tick = mt5.symbol_info_tick(symbol)

    if tick is None:
        raise HTTPException(
            status_code=404,
            detail=f"No tick data for {symbol}",
        )

    return {
        "symbol": symbol,
        "bid": tick.bid,
        "ask": tick.ask,
        "time": tick.time,
    }


@app.get("/positions")
def positions(x_bridge_token: str | None = Header(default=None)):
    verify_token(x_bridge_token)

    if not mt5.initialize():
        raise HTTPException(
            status_code=503,
            detail=f"MT5 initialization failed: {mt5.last_error()}",
        )

    raw_positions = mt5.positions_get()
    parsed = []
    if raw_positions:
        for pos in raw_positions:
            parsed.append({
                "ticket": int(pos.ticket),
                "symbol": str(pos.symbol),
                "type": "BUY" if pos.type == 0 else "SELL",
                "volume": float(pos.volume),
                "price_open": float(pos.price_open),
                "price_current": float(pos.price_current),
                "sl": float(pos.sl) if pos.sl else None,
                "tp": float(pos.tp) if pos.tp else None,
                "profit": float(pos.profit),
                "time": int(pos.time),
            })

    return parsed


@app.get("/history")
def history(
    days: int = 90,
    x_bridge_token: str | None = Header(default=None),
):
    from datetime import datetime, timedelta, timezone
    from collections import defaultdict

    verify_token(x_bridge_token)

    if not mt5.initialize():
        raise HTTPException(
            status_code=503,
            detail=f"MT5 initialization failed: {mt5.last_error()}",
        )

    to_date = datetime.now(timezone.utc)
    from_date = to_date - timedelta(days=max(1, min(days, 3650)))

    deals = mt5.history_deals_get(from_date, to_date)
    if not deals:
        return []

    position_deals = defaultdict(list)
    for deal in deals:
        if deal.position_id == 0 or not deal.symbol:
            continue
        position_deals[deal.position_id].append(deal)

    parsed_trades = []
    for pos_id, pdeals in position_deals.items():
        pdeals.sort(key=lambda d: d.time)
        entry_deals = [d for d in pdeals if d.entry == 0]
        exit_deals = [d for d in pdeals if d.entry in (1, 2, 3)]

        if not exit_deals:
            continue

        first_entry = entry_deals[0] if entry_deals else exit_deals[0]
        last_exit = exit_deals[-1]

        direction = "BUY" if first_entry.type == 0 else "SELL"
        volume = float(sum(d.volume for d in entry_deals)) if entry_deals else float(first_entry.volume)
        entry_price = float(first_entry.price)
        exit_price = float(last_exit.price)
        entry_time = int(first_entry.time)
        exit_time = int(last_exit.time)

        profit_loss = float(sum(d.profit for d in pdeals))
        commission = float(sum(d.commission for d in pdeals))
        swap = float(sum(d.swap for d in pdeals))
        net_pl = round(profit_loss + commission + swap, 2)

        if net_pl > 0:
            status = "WIN"
        elif net_pl < 0:
            status = "LOSS"
        else:
            status = "BREAKEVEN"

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

    return parsed_trades
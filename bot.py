"""
MarketMate Telegram Bot
Commands:
  /portfolio  — current P&L summary
  /sip        — all MF/SIP holdings with live NAV P&L
  /stocks     — top BUY signals from watchlist
  /ipo        — IPOs with positive GMP
  /alert add RELIANCE.NS below 2800  — set price alert
  /alert list — list all alerts
  /alert del 1 — delete alert by ID
  /help       — command list

Scheduled:
  3:45pm IST daily — P&L summary pushed automatically
  Every 15min      — price alert checks
"""

import asyncio
import logging
import os
import sqlite3
import threading
from datetime import datetime

import pandas as pd
import schedule
import time
import yfinance as yf
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import DB_PATH
from data.portfolio import get_all_holdings, compute_portfolio_value, init_db
from data.stocks import get_stock_fundamentals

BOT_TOKEN = "8766246491:AAERTPZ7Xzmm5BQ_7d2I8ZjlyJ5xSv_oNaw"
CHAT_ID   = 1334269123

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ── alert DB ──────────────────────────────────────────────────────────────────

def _alert_conn():
    return sqlite3.connect(DB_PATH)


def init_alerts_db():
    with _alert_conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker    TEXT NOT NULL,
                direction TEXT NOT NULL,  -- 'above' or 'below'
                target    REAL NOT NULL,
                triggered INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        con.commit()


def add_alert(ticker: str, direction: str, target: float):
    with _alert_conn() as con:
        con.execute(
            "INSERT INTO price_alerts (ticker, direction, target) VALUES (?,?,?)",
            (ticker.upper(), direction, target)
        )
        con.commit()


def get_alerts(triggered=False) -> list[dict]:
    with _alert_conn() as con:
        rows = con.execute(
            "SELECT id, ticker, direction, target FROM price_alerts WHERE triggered=?",
            (1 if triggered else 0,)
        ).fetchall()
    return [{"id": r[0], "ticker": r[1], "direction": r[2], "target": r[3]} for r in rows]


def delete_alert(alert_id: int):
    with _alert_conn() as con:
        con.execute("DELETE FROM price_alerts WHERE id=?", (alert_id,))
        con.commit()


def mark_alert_triggered(alert_id: int):
    with _alert_conn() as con:
        con.execute("UPDATE price_alerts SET triggered=1 WHERE id=?", (alert_id,))
        con.commit()


# ── helpers ───────────────────────────────────────────────────────────────────

def _fmt_inr(val) -> str:
    try:
        v = float(val)
        if abs(v) >= 1e7:
            return f"₹{v/1e7:.2f}Cr"
        if abs(v) >= 1e5:
            return f"₹{v/1e5:.2f}L"
        return f"₹{v:,.0f}"
    except Exception:
        return "—"


def _get_live_prices(tickers: list[str]) -> dict:
    prices = {}
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            prices[t] = info.get("currentPrice") or info.get("regularMarketPrice")
        except Exception:
            pass
    return prices


def _build_portfolio_summary() -> str:
    holdings = get_all_holdings()
    if holdings.empty:
        return "No holdings in portfolio yet."

    stock_h = holdings[holdings["asset_type"] == "STOCK"]
    mf_h    = holdings[holdings["asset_type"] == "MF"]

    lines = [f"📊 *Portfolio Summary* — {datetime.now().strftime('%d %b %Y %H:%M')}"]

    # stocks
    if not stock_h.empty:
        tickers = stock_h["ticker"].tolist()
        prices  = _get_live_prices(tickers)
        sp = compute_portfolio_value(stock_h, prices)
        total_inv = sp["invested_value"].sum()
        total_cur = sp["current_value"].dropna().sum()
        pnl       = total_cur - total_inv
        pnl_pct   = (pnl / total_inv * 100) if total_inv else 0
        sign      = "+" if pnl >= 0 else ""
        emoji     = "🟢" if pnl >= 0 else "🔴"
        lines.append(f"\n{emoji} *Stocks*")
        lines.append(f"  Invested : {_fmt_inr(total_inv)}")
        lines.append(f"  Current  : {_fmt_inr(total_cur)}")
        lines.append(f"  P&L      : {sign}{_fmt_inr(pnl)} ({sign}{pnl_pct:.1f}%)")

        lines.append("\n  *Holdings:*")
        for _, row in sp.iterrows():
            cur = row.get("current_value")
            inv = row.get("invested_value")
            p   = row.get("pnl_pct")
            if pd.notna(cur) and pd.notna(p):
                e = "🟢" if p >= 0 else "🔴"
                lines.append(f"  {e} {row['ticker']}  {_fmt_inr(cur)}  ({'+' if p>=0 else ''}{p:.1f}%)")
            else:
                lines.append(f"  ⚪ {row['ticker']}  price unavailable")

    # MF — show invested only (no live NAV fetch in bot to keep it fast)
    if not mf_h.empty:
        mf_inv = (mf_h["buy_price"] * mf_h["quantity"]).sum()
        lines.append(f"\n💰 *Mutual Funds*")
        lines.append(f"  Invested : {_fmt_inr(mf_inv)}")
        lines.append(f"  _(Live NAV P&L: open dashboard)_")

    return "\n".join(lines)


# ── command handlers ───────────────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📈 *MarketMate Bot Commands*\n\n"
        "/portfolio — stocks P&L summary\n"
        "/sip — MF/SIP holdings with live NAV P&L\n"
        "/stocks — BUY signals from watchlist\n"
        "/ipo — IPOs with positive GMP\n"
        "/alert add RELIANCE.NS below 2800\n"
        "/alert list — active alerts\n"
        "/alert del 1 — delete alert by ID\n"
        "/help — this message"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching portfolio...", parse_mode="Markdown")
    msg = _build_portfolio_summary()
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_sip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching MF NAV data...", parse_mode="Markdown")
    holdings = get_all_holdings()
    mf_h = holdings[holdings["asset_type"] == "MF"] if not holdings.empty else pd.DataFrame()

    if mf_h.empty:
        await update.message.reply_text("No MF/SIP holdings found. Add them via dashboard.")
        return

    # fetch live NAVs
    mf_codes = []
    for t in mf_h["ticker"].tolist():
        try:
            mf_codes.append(int(t))
        except (ValueError, TypeError):
            pass

    navs = {}
    if mf_codes:
        try:
            from utils.cache import cached_mf_nav_bulk
            navs = cached_mf_nav_bulk(tuple(mf_codes))
        except Exception:
            pass

    lines = [f"💰 *SIP / Mutual Fund Holdings* — {datetime.now().strftime('%d %b %Y')}\n"]
    total_inv = 0.0
    total_cur = 0.0

    for _, row in mf_h.iterrows():
        ticker   = str(row["ticker"])
        units    = float(row["quantity"])
        buy_nav  = float(row["buy_price"])
        invested = buy_nav * units
        total_inv += invested

        try:
            code = int(ticker)
            live_nav = navs.get(code)
        except (ValueError, TypeError):
            live_nav = None

        if live_nav:
            current  = live_nav * units
            pnl      = current - invested
            pnl_pct  = (pnl / invested * 100) if invested else 0
            total_cur += current
            emoji = "🟢" if pnl >= 0 else "🔴"
            sign  = "+" if pnl >= 0 else ""
            lines.append(
                f"{emoji} *Scheme {ticker}*\n"
                f"   Units: {units:.3f}  Buy NAV: ₹{buy_nav:.2f}  Live NAV: ₹{live_nav:.2f}\n"
                f"   Invested: {_fmt_inr(invested)}  Current: {_fmt_inr(current)}\n"
                f"   P&L: {sign}{_fmt_inr(pnl)} ({sign}{pnl_pct:.1f}%)\n"
            )
        else:
            total_cur += invested  # fallback
            lines.append(
                f"⚪ *Scheme {ticker}*\n"
                f"   Units: {units:.3f}  Buy NAV: ₹{buy_nav:.2f}  Live NAV: unavailable\n"
                f"   Invested: {_fmt_inr(invested)}\n"
            )

    overall_pnl = total_cur - total_inv
    overall_pct = (overall_pnl / total_inv * 100) if total_inv else 0
    sign  = "+" if overall_pnl >= 0 else ""
    emoji = "🟢" if overall_pnl >= 0 else "🔴"
    lines.append(
        f"\n{emoji} *Total MF*\n"
        f"   Invested : {_fmt_inr(total_inv)}\n"
        f"   Current  : {_fmt_inr(total_cur)}\n"
        f"   P&L      : {sign}{_fmt_inr(overall_pnl)} ({sign}{overall_pct:.1f}%)"
    )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_stocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Scanning stocks for BUY signals...", parse_mode="Markdown")
    from config import DEFAULT_WATCHLIST
    try:
        df = get_stock_fundamentals(tuple(DEFAULT_WATCHLIST[:10]))  # limit to keep fast
    except Exception as e:
        await update.message.reply_text(f"Error fetching stocks: {e}")
        return

    buys = []
    for _, row in df.iterrows():
        pe  = row.get("pe_ratio")
        roe = row.get("roe_pct")
        de  = row.get("debt_to_equity")
        rg  = row.get("revenue_growth_pct")
        green = red = 0
        if pe  is not None and not pd.isna(pe):
            green += (1 if pe < 20 else 0); red += (1 if pe >= 35 else 0)
        if roe is not None and not pd.isna(roe):
            green += (1 if roe > 15 else 0); red += (1 if roe < 8 else 0)
        if de  is not None and not pd.isna(de):
            green += (1 if de < 0.5 else 0); red += (1 if de >= 1.5 else 0)
        if rg  is not None and not pd.isna(rg):
            green += (1 if rg > 15 else 0); red += (1 if rg < 0 else 0)
        if green >= 2 and red == 0:
            buys.append(row)

    if not buys:
        await update.message.reply_text("No strong BUY signals right now.")
        return

    lines = ["📊 *BUY Signals Today*\n"]
    for row in buys:
        pe  = row.get("pe_ratio")
        roe = row.get("roe_pct")
        lines.append(
            f"✅ *{row['ticker']}* — {row.get('name','')}\n"
            f"   P/E: {pe:.1f}  ROE: {roe:.1f}%  Price: {_fmt_inr(row.get('price'))}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_ipo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching IPO GMP data (~15s)...", parse_mode="Markdown")
    try:
        from utils.cache import cached_ipo_data
        df, error = cached_ipo_data()
    except Exception as e:
        await update.message.reply_text(f"IPO fetch error: {e}")
        return

    if df is None or df.empty:
        await update.message.reply_text("No IPO data available right now.")
        return

    positive = df[df["gmp"].gt(0)] if "gmp" in df.columns else pd.DataFrame()
    if positive.empty:
        await update.message.reply_text("No IPOs with positive GMP right now.")
        return

    lines = ["🚀 *IPOs with Positive GMP*\n"]
    for _, row in positive.head(8).iterrows():
        gmp_pct = row.get("gmp_pct", 0)
        subs    = row.get("subscription", "—")
        lines.append(f"• *{row.get('name','—')}*  GMP: {gmp_pct:.1f}%  Sub: {subs}x")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage:\n/alert add RELIANCE.NS below 2800\n/alert list\n/alert del 1"
        )
        return

    sub = args[0].lower()

    if sub == "list":
        alerts = get_alerts()
        if not alerts:
            await update.message.reply_text("No active alerts.")
            return
        lines = ["🔔 *Active Alerts*\n"]
        for a in alerts:
            lines.append(f"  [{a['id']}] {a['ticker']} {a['direction']} ₹{a['target']:,.0f}")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    elif sub == "del":
        if len(args) < 2:
            await update.message.reply_text("Usage: /alert del <id>")
            return
        try:
            delete_alert(int(args[1]))
            await update.message.reply_text(f"Alert #{args[1]} deleted.")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    elif sub == "add":
        # /alert add RELIANCE.NS below 2800
        if len(args) < 4:
            await update.message.reply_text("Usage: /alert add TICKER above/below PRICE")
            return
        ticker    = args[1].upper()
        direction = args[2].lower()
        if direction not in ("above", "below"):
            await update.message.reply_text("Direction must be 'above' or 'below'.")
            return
        try:
            target = float(args[3])
        except ValueError:
            await update.message.reply_text("Price must be a number.")
            return
        if not ticker.endswith(".NS") and not ticker.endswith(".BO"):
            ticker += ".NS"
        add_alert(ticker, direction, target)
        await update.message.reply_text(
            f"🔔 Alert set: notify when *{ticker}* goes {direction} ₹{target:,.0f}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("Unknown subcommand. Use: add / list / del")


# ── scheduled jobs ─────────────────────────────────────────────────────────────

async def _send_daily_summary(app: Application):
    log.info("Sending daily portfolio summary")
    msg = _build_portfolio_summary()
    await app.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")


async def _check_price_alerts(app: Application):
    alerts = get_alerts()
    if not alerts:
        return
    tickers = list({a["ticker"] for a in alerts})
    prices  = _get_live_prices(tickers)
    for a in alerts:
        price = prices.get(a["ticker"])
        if price is None:
            continue
        triggered = (
            (a["direction"] == "below" and price <= a["target"]) or
            (a["direction"] == "above" and price >= a["target"])
        )
        if triggered:
            mark_alert_triggered(a["id"])
            msg = (
                f"🚨 *Price Alert Triggered!*\n"
                f"{a['ticker']} is now {_fmt_inr(price)}\n"
                f"Your target: {a['direction']} ₹{a['target']:,.0f}"
            )
            await app.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
            log.info(f"Alert triggered: {a}")


def _run_scheduler(app: Application):
    loop = asyncio.new_event_loop()

    def _daily():
        loop.run_until_complete(_send_daily_summary(app))

    def _alerts():
        loop.run_until_complete(_check_price_alerts(app))

    # 3:45pm IST = 10:15 UTC
    schedule.every().day.at("10:15").do(_daily)
    schedule.every(15).minutes.do(_alerts)

    while True:
        schedule.run_pending()
        time.sleep(30)


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    init_db()
    init_alerts_db()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("help",      cmd_help))
    app.add_handler(CommandHandler("start",     cmd_help))
    app.add_handler(CommandHandler("portfolio", cmd_portfolio))
    app.add_handler(CommandHandler("sip",       cmd_sip))
    app.add_handler(CommandHandler("stocks",    cmd_stocks))
    app.add_handler(CommandHandler("ipo",       cmd_ipo))
    app.add_handler(CommandHandler("alert",     cmd_alert))

    # scheduler in background thread
    t = threading.Thread(target=_run_scheduler, args=(app,), daemon=True)
    t.start()

    log.info("MarketMate bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

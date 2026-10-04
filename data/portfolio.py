import sqlite3
import pandas as pd
from config import DB_PATH
import os

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_holdings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker      TEXT NOT NULL,
                asset_type  TEXT NOT NULL DEFAULT 'STOCK',
                buy_price   REAL NOT NULL,
                quantity    REAL NOT NULL,
                buy_date    TEXT,
                notes       TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                ticker TEXT PRIMARY KEY
            )
        """)
        con.commit()


def get_watchlist() -> list[str]:
    with _conn() as con:
        rows = con.execute("SELECT ticker FROM watchlist ORDER BY ticker").fetchall()
    return [r[0] for r in rows]


def add_to_watchlist(ticker: str):
    with _conn() as con:
        con.execute("INSERT OR IGNORE INTO watchlist (ticker) VALUES (?)", (ticker.upper(),))
        con.commit()


def remove_from_watchlist(ticker: str):
    with _conn() as con:
        con.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))
        con.commit()


def add_holding(ticker: str, asset_type: str, buy_price: float, quantity: float,
                buy_date: str = None, notes: str = None) -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO portfolio_holdings (ticker, asset_type, buy_price, quantity, buy_date, notes) VALUES (?,?,?,?,?,?)",
            (ticker.upper(), asset_type, buy_price, quantity, buy_date, notes),
        )
        con.commit()
        return cur.lastrowid


def get_all_holdings() -> pd.DataFrame:
    with _conn() as con:
        df = pd.read_sql_query("SELECT * FROM portfolio_holdings ORDER BY created_at DESC", con)
    return df


def delete_holding(holding_id: int):
    with _conn() as con:
        con.execute("DELETE FROM portfolio_holdings WHERE id = ?", (holding_id,))
        con.commit()


def update_holding(holding_id: int, **kwargs):
    allowed = {"ticker", "asset_type", "buy_price", "quantity", "buy_date", "notes"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [holding_id]
    with _conn() as con:
        con.execute(f"UPDATE portfolio_holdings SET {set_clause} WHERE id = ?", values)
        con.commit()


def compute_portfolio_value(holdings_df: pd.DataFrame, current_prices: dict) -> pd.DataFrame:
    if holdings_df.empty:
        return holdings_df
    df = holdings_df.copy()
    df["current_price"] = df["ticker"].map(current_prices)
    df["invested_value"] = df["buy_price"] * df["quantity"]
    df["current_value"] = df["current_price"] * df["quantity"]
    df["pnl"] = df["current_value"] - df["invested_value"]
    df["pnl_pct"] = (df["pnl"] / df["invested_value"] * 100).round(2)
    return df

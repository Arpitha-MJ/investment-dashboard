import time
import yfinance as yf
import pandas as pd


def get_stock_fundamentals(tickers: list[str]) -> pd.DataFrame:
    records = []
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            records.append({
                "ticker": ticker,
                "name": info.get("shortName", ticker),
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "pe_ratio": info.get("trailingPE"),
                "roe_pct": round(info.get("returnOnEquity", 0) * 100, 2) if info.get("returnOnEquity") else None,
                "debt_to_equity": round(info.get("debtToEquity") / 100, 2) if info.get("debtToEquity") is not None else None,
                "revenue_growth_pct": round(info.get("revenueGrowth", 0) * 100, 2) if info.get("revenueGrowth") else None,
                "market_cap": info.get("marketCap"),
                "week52_high": info.get("fiftyTwoWeekHigh"),
                "week52_low": info.get("fiftyTwoWeekLow"),
                "dividend_yield": round((dy / 100 if dy > 1 else dy) * 100, 2) if (dy := info.get("dividendYield")) is not None else None,
                "beta": info.get("beta"),
            })
            time.sleep(0.3)
        except Exception:
            records.append({"ticker": ticker, "name": ticker})
    return pd.DataFrame(records)


def filter_stocks(
    df: pd.DataFrame,
    max_pe: float = 40,
    min_roe: float = 10,
    max_de: float = 2.0,
    min_rev_growth: float = 0,
) -> pd.DataFrame:
    mask = pd.Series([True] * len(df), index=df.index)
    if "pe_ratio" in df.columns:
        mask &= df["pe_ratio"].isna() | (df["pe_ratio"] <= max_pe)
    if "roe_pct" in df.columns:
        mask &= df["roe_pct"].isna() | (df["roe_pct"] >= min_roe)
    if "debt_to_equity" in df.columns:
        mask &= df["debt_to_equity"].isna() | (df["debt_to_equity"] <= max_de)
    if "revenue_growth_pct" in df.columns:
        mask &= df["revenue_growth_pct"].isna() | (df["revenue_growth_pct"] >= min_rev_growth)
    filtered = df[mask].copy()
    if "roe_pct" in filtered.columns and filtered["roe_pct"].notna().any():
        filtered = filtered.sort_values("roe_pct", ascending=False)
    elif "pe_ratio" in filtered.columns:
        filtered = filtered.sort_values("pe_ratio", ascending=True)
    return filtered.reset_index(drop=True)


def get_eod_prices(tickers: list[str]) -> dict[str, float]:
    if not tickers:
        return {}
    try:
        data = yf.download(
            tickers if len(tickers) > 1 else tickers[0],
            period="2d",
            auto_adjust=True,
            progress=False,
        )["Close"]
        if isinstance(data, pd.Series):
            return {tickers[0]: float(data.dropna().iloc[-1])}
        return {t: float(data[t].dropna().iloc[-1]) for t in tickers if t in data.columns}
    except Exception:
        return {}

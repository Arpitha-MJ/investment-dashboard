import requests
import pandas as pd
from config import MFAPI_ALL_FUNDS_URL, MFAPI_FUND_URL, CURATED_MF, RISK_FREE_RATE, MF_EXPENSE_RATIOS


def search_funds_by_name(query: str) -> list[dict]:
    """Return [{schemeCode, schemeName}] matching query string."""
    resp = requests.get(f"https://api.mfapi.in/mf/search?q={query}", timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_all_fund_list() -> list[dict]:
    resp = requests.get(MFAPI_ALL_FUNDS_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_fund_meta(scheme_code: int) -> dict:
    """Return {name, fund_house, scheme_type, scheme_category} from MFAPI."""
    url = MFAPI_FUND_URL.format(scheme_code)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    meta = payload.get("meta", {})
    return {
        "name": meta.get("scheme_name", f"Scheme {scheme_code}"),
        "fund_house": meta.get("fund_house", ""),
        "scheme_type": meta.get("scheme_type", ""),
        "scheme_category": meta.get("scheme_category", ""),
    }


def filter_direct_growth_funds(all_funds: list[dict]) -> list[dict]:
    results = []
    keywords = ["direct", "growth"]
    exclude = ["dividend", "idcw", "bonus", "fof"]
    for fund in all_funds:
        name_lower = fund.get("schemeName", "").lower()
        if all(k in name_lower for k in keywords) and not any(e in name_lower for e in exclude):
            results.append(fund)
    return results


def fetch_nav_history(scheme_code: int) -> pd.Series:
    url = MFAPI_FUND_URL.format(scheme_code)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    data = payload.get("data", [])
    if not data:
        return pd.Series(dtype=float)
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna().sort_values("date").set_index("date")
    return df["nav"]


def compute_cagr(nav_series: pd.Series, years: int) -> float | None:
    if nav_series.empty or len(nav_series) < 30:
        return None
    end_nav = nav_series.iloc[-1]
    start_date = nav_series.index[-1] - pd.DateOffset(years=years)
    try:
        start_nav = nav_series.asof(start_date)
    except Exception:
        return None
    if pd.isna(start_nav) or start_nav <= 0:
        return None
    return round(((end_nav / start_nav) ** (1 / years) - 1) * 100, 2)


def compute_sharpe(nav_series: pd.Series, risk_free_rate: float = RISK_FREE_RATE, years: int = 1) -> float | None:
    if nav_series.empty or len(nav_series) < 60:
        return None
    cutoff = nav_series.index[-1] - pd.DateOffset(years=years)
    series = nav_series[nav_series.index >= cutoff]
    if len(series) < 30:
        series = nav_series
    daily_returns = series.pct_change().dropna()
    annualized_return = daily_returns.mean() * 252
    annualized_std = daily_returns.std() * (252 ** 0.5)
    if annualized_std == 0:
        return None
    return round((annualized_return - risk_free_rate) / annualized_std, 2)


def get_top_mf_data(scheme_codes: list[int], category_map: dict[int, str]) -> pd.DataFrame:
    records = []
    for code in scheme_codes:
        try:
            nav = fetch_nav_history(code)
            meta = fetch_fund_meta(code)
            records.append({
                "scheme_code": code,
                "fund_name": meta.get("name", f"Scheme {code}"),
                "category": category_map.get(code, "Unknown"),
                "cagr_3yr": compute_cagr(nav, 3),
                "cagr_5yr": compute_cagr(nav, 5),
                "sharpe_1yr": compute_sharpe(nav),
                "latest_nav": round(float(nav.iloc[-1]), 2) if not nav.empty else None,
                "expense_ratio": MF_EXPENSE_RATIOS.get(code),
            })
        except Exception:
            records.append({"scheme_code": code, "fund_name": f"Scheme {code}", "category": category_map.get(code, "Unknown")})
    return pd.DataFrame(records)


def build_curated_category_map() -> dict[int, str]:
    mapping = {}
    for category, codes in CURATED_MF.items():
        for code in codes:
            mapping[code] = category
    return mapping


def get_all_curated_codes() -> list[int]:
    seen = set()
    result = []
    for codes in CURATED_MF.values():
        for c in codes:
            if c not in seen:
                seen.add(c)
                result.append(c)
    return result


def get_latest_nav_bulk(scheme_codes: list[int]) -> dict[int, float]:
    """Return {scheme_code: latest_nav} for each code. Skips failures silently."""
    result = {}
    for code in scheme_codes:
        try:
            nav = fetch_nav_history(code)
            if not nav.empty:
                result[code] = float(nav.iloc[-1])
        except Exception:
            pass
    return result

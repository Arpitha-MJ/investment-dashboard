import pandas as pd


def format_crore(val) -> str:
    if pd.isna(val) or val is None:
        return "N/A"
    return f"₹{val / 1e7:.1f}Cr"


def format_pct(val, decimals: int = 1) -> str:
    if pd.isna(val) or val is None:
        return "N/A"
    return f"{val:.{decimals}f}%"


def format_inr(val) -> str:
    if pd.isna(val) or val is None:
        return "N/A"
    return f"₹{val:,.2f}"


def badge_status(status: str) -> str:
    colors = {
        "open": "🟢",
        "upcoming": "🔵",
        "closing today": "🟠",
        "closed": "⚫",
        "listed": "🟣",
    }
    icon = colors.get(str(status).lower(), "⚪")
    return f"{icon} {status}"

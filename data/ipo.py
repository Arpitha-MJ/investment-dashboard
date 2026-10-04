import io
import re
import threading
import pandas as pd
from playwright.sync_api import sync_playwright

IPO_URL = "https://www.investorgain.com/report/live-ipo-gmp/331/"

EMPTY_SCHEMA = pd.DataFrame(columns=[
    "name", "gmp", "gmp_pct", "issue_price", "open_date",
    "close_date", "listing_date", "lot_size", "ipo_size_cr", "status",
])


def get_ipo_data() -> tuple[pd.DataFrame, str | None]:
    result = [EMPTY_SCHEMA.copy(), None]

    def _fetch():
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
                )
                page.goto(IPO_URL, wait_until="networkidle", timeout=30000)
                html = page.content()
                browser.close()
            result[0], result[1] = _parse(html)
        except Exception as e:
            result[1] = str(e)

    t = threading.Thread(target=_fetch)
    t.start()
    t.join(timeout=45)
    if t.is_alive():
        return EMPTY_SCHEMA.copy(), "IPO fetch timed out"
    return result[0], result[1]


def _parse(html: str) -> tuple[pd.DataFrame, str | None]:
    try:
        tables = pd.read_html(io.StringIO(html))
        if not tables:
            return EMPTY_SCHEMA.copy(), "No table found"

        df = max(tables, key=len).copy()

        # Strip sort arrows
        df.columns = [
            str(c).replace("▲▼", "").replace("▲", "").replace("▼", "").strip()
            for c in df.columns
        ]
        df = df.dropna(how="all").reset_index(drop=True)

        column_map = {
            "Name": "name",
            "GMP": "gmp",
            "Price (₹)": "issue_price",
            "Price": "issue_price",
            "Open": "open_date",
            "Close": "close_date",
            "Listing": "listing_date",
            "Lot": "lot_size",
            "IPO Size": "ipo_size_cr",
        }
        df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})

        # Parse GMP — format: "₹6 (8.57%) 6 ↓ / 7 ↑"
        if "gmp" in df.columns:
            def parse_gmp(val):
                m = re.search(r'₹([\d.]+)', str(val))
                return float(m.group(1)) if m else None

            def parse_gmp_pct(val):
                m = re.search(r'\(([-\d.]+)%\)', str(val))
                return float(m.group(1)) if m else None

            df["gmp_pct"] = df["gmp"].apply(parse_gmp_pct)
            df["gmp"] = df["gmp"].apply(parse_gmp)

        # Clean issue price
        if "issue_price" in df.columns:
            df["issue_price"] = pd.to_numeric(
                df["issue_price"].astype(str)
                .str.replace("₹", "").str.replace(",", "")
                .str.split().str[-1].str.strip(),
                errors="coerce",
            )

        # Clean dates — strip "GMP: N" bleed-in
        for date_col in ["open_date", "close_date", "listing_date"]:
            if date_col in df.columns:
                df[date_col] = (
                    df[date_col].astype(str)
                    .str.replace(r"\s*GMP:.*", "", regex=True)
                    .str.strip()
                    .replace("nan", None)
                )

        df["status"] = "Listed/Upcoming"

        for col in EMPTY_SCHEMA.columns:
            if col not in df.columns:
                df[col] = None

        return df[list(EMPTY_SCHEMA.columns)], None

    except Exception as e:
        return EMPTY_SCHEMA.copy(), str(e)

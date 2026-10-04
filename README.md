# Investment Dashboard

Personal investment dashboard for Indian markets. Tracks NSE/BSE stocks, mutual funds, IPOs, and your portfolio. Built with Streamlit + Python.

---

## Features

| Tab | What it does |
|-----|-------------|
| **Top Stocks** | Screen 20 NSE blue-chips by P/E, ROE, Debt/Equity, Revenue Growth. Add any custom ticker. |
| **Top SIP Funds** | Ranks curated mutual funds by 3yr/5yr CAGR and Sharpe ratio. One-click beginner pick. |
| **IPO Watch** | Live GMP (Grey Market Premium) tracker scraped from investorgain.com. |
| **My Portfolio** | Add/delete holdings (stocks or MF). Tracks P&L, current value, allocation pie chart. |

---

## Requirements

- Python 3.10+
- [Playwright](https://playwright.dev/python/) Chromium (for IPO scraping)

---

## Setup

```bash
# 1. Clone / download the project
cd investment-dashboard

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Playwright's Chromium browser (needed for IPO tab)
playwright install chromium

# 5. Run the app
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## Project Structure

```
investment-dashboard/
├── app.py               # Entry point — layout, global CSS, tab routing
├── config.py            # URLs, cache TTLs, watchlist, curated MF codes
├── requirements.txt
├── data/
│   ├── stocks.py        # yfinance fundamentals + EOD price fetch
│   ├── mutual_funds.py  # MFAPI.in NAV history, CAGR, Sharpe
│   ├── ipo.py           # Playwright scraper + HTML parser
│   └── portfolio.py     # SQLite CRUD — holdings, P&L compute
├── ui/
│   ├── tab_stocks.py    # Stocks tab render
│   ├── tab_mf.py        # Mutual funds tab render
│   ├── tab_ipo.py       # IPO tab render
│   └── tab_portfolio.py # Portfolio tab render
├── utils/
│   ├── cache.py         # st.cache_data wrappers (TTL per data type)
│   └── formatters.py    # ₹/%, crore formatters
└── db/
    └── portfolio.db     # Auto-created SQLite database
```

---

## How to Use Effectively

### Stock Screener (Tab 1)

- **Sidebar filters** apply in real time: P/E ≤ 150, ROE ≥ 0%, D/E ≤ 500 are the defaults (show everything). Tighten them to narrow results.
- Stocks sorted by ROE descending after filtering.
- Add any NSE ticker in the sidebar **"Add ticker"** field — append `.NS` for NSE or `.BO` for BSE (auto-appended if omitted).
- Data cached for **1 hour**. Hit **Refresh Stock Data** to force-update.
- D/E values come from yfinance in raw scale (can exceed 100). Compare relative, not absolute.

### Mutual Funds (Tab 2)

- Use the **Category** multiselect to focus on a fund category (Large Cap, Flexi Cap, Mid Cap, Small Cap, ELSS).
- Switch **Sort by** to rank on 3yr CAGR, 5yr CAGR, or Sharpe ratio.
- Click **"Pick Top 2 SIP Funds for Me"** for a beginner-friendly recommendation: scores Large Cap + Flexi Cap funds on 5yr CAGR (60%) + Sharpe (40%). Only funds with Sharpe ≥ 0.8 qualify.
- To start a SIP: note the **Scheme Code** shown, search it on Groww / Zerodha Coin / Kuvera.
- NAV data cached for **24 hours**. Fund list cached for **7 days**.

### IPO Watch (Tab 3)

- GMP (Grey Market Premium) indicates unofficial expected listing premium. Positive GMP = market expects above-issue listing.
- Table sorted by GMP% descending.
- Scrape uses a headless Chromium browser — first load takes **~15 seconds**.
- Data cached for **30 minutes**. Use **Refresh IPO Data** to force-update.
- GMP is sentiment data, not a guarantee.

### My Portfolio (Tab 4)

- Expand **"Add Holding"**, fill ticker/scheme code, buy price, quantity, and date, then submit.
- For stocks: use `TICKER.NS` (NSE) or `TICKER.BO` (BSE). `.NS` is auto-appended for stock assets.
- For mutual funds: enter the numeric **scheme code** (find it on MFAPI.in or the MF tab).
- P&L shows only for **STOCK** holdings — live prices fetched via yfinance. MF holdings show invested value only (NAV-based pricing not yet wired to portfolio).
- Delete a holding by entering its **ID** (shown in the table) and clicking Delete.
- Prices cached for **1 hour**. Use **Refresh Prices** to update.

---

## Data Sources

| Data | Source | Update Frequency |
|------|--------|-----------------|
| Stock fundamentals & prices | Yahoo Finance (yfinance) | 1 hr cache |
| Mutual fund NAV history | [MFAPI.in](https://mfapi.in) (free, public) | 24 hr cache |
| IPO GMP | [investorgain.com](https://investorgain.com) | 30 min cache |
| Portfolio holdings | Local SQLite (`db/portfolio.db`) | Real-time |

---

## Customisation

**Change the stock watchlist** — edit `DEFAULT_WATCHLIST` in `config.py`:
```python
DEFAULT_WATCHLIST = ["RELIANCE.NS", "TCS.NS", ...]
```

**Add/change curated mutual funds** — edit `CURATED_MF` in `config.py`. Keys are category names; values are lists of MFAPI scheme codes:
```python
CURATED_MF = {
    "Large Cap - Direct Growth": [119598, 120505, ...],
    ...
}
```

**Change cache durations** — edit `CACHE_TTL_*` constants in `config.py` (values in seconds).

**Risk-free rate for Sharpe** — edit `RISK_FREE_RATE` in `config.py` (default: 6.5% India 10yr G-Sec).

---

## Known Limitations

- **MF holdings P&L** — portfolio P&L currently works only for stocks. MF units show invested cost but no live NAV-based gain/loss.
- **IPO data** — depends on investorgain.com HTML structure. May break if the site changes layout.
- **yfinance rate limits** — fetching 20+ tickers sequentially adds a 0.3s sleep per ticker (~6s total). Large custom watchlists will be slower.
- **No authentication** — this is a local personal tool. Do not expose it publicly without adding auth.

---

## Improvements Made During Setup

- `playwright install chromium` step added to setup (not in original instructions — IPO tab fails silently without it).
- `.NS` suffix auto-appended for stocks added via the sidebar and portfolio form.
- Portfolio DB auto-created at first run (`db/` directory created by `data/portfolio.py`).

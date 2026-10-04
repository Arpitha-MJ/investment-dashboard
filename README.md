# Investment Dashboard

Personal investment dashboard for Indian markets. Tracks NSE/BSE stocks, mutual funds, IPOs, and portfolio. Built with Streamlit + Python.

Live demo: deployed on Coolify (self-hosted).

---

## Features

| Tab | What it does |
|-----|-------------|
| **My Portfolio** | Add/edit/delete holdings (stocks or MF). Tracks P&L, XIRR, held duration, allocation pie chart. CSV export. |
| **Top Stocks** | Screen 20+ NSE blue-chips by P/E, ROE, D/E, Revenue Growth. Persistent watchlist. Sector filter. Buy signal. "Should I Buy?" analyser. CSV export. |
| **Top SIP Funds** | Ranks curated MFs by 3yr/5yr CAGR and Sharpe. SIP calculator with step-up %. "Should I Invest?" verdict. Fund name search. |
| **IPO Watch** | Live GMP tracker scraped from investorgain.com. Apply/Maybe/Skip verdict per IPO. |

**UI:** Dark/Light mode toggle. Groww-inspired card layout.

---

## Requirements

- Python 3.10+
- [Playwright](https://playwright.dev/python/) Chromium (for IPO scraping)
- scipy (for XIRR calculation)

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
├── app.py               # Entry point — layout, global CSS, theme toggle, tab routing
├── config.py            # URLs, cache TTLs, watchlist, curated MF codes
├── requirements.txt
├── Dockerfile           # For Coolify / Docker deployment
├── Procfile             # Heroku-style process definition
├── data/
│   ├── stocks.py        # yfinance fundamentals + EOD price fetch
│   ├── mutual_funds.py  # MFAPI.in NAV history, CAGR, Sharpe, fund search
│   ├── ipo.py           # Playwright scraper + HTML parser
│   └── portfolio.py     # SQLite CRUD — holdings, watchlist, P&L compute
├── ui/
│   ├── tab_stocks.py    # Stocks tab — screener, watchlist, sector filter, buy analyser
│   ├── tab_mf.py        # MF tab — fund table, SIP calculator, step-up SIP, verdict
│   ├── tab_ipo.py       # IPO tab — GMP table, Apply/Maybe/Skip verdict
│   └── tab_portfolio.py # Portfolio tab — holdings, XIRR, edit, CSV export
├── utils/
│   ├── cache.py         # st.cache_data wrappers (TTL per data type)
│   └── formatters.py    # ₹/% formatters
└── db/
    └── portfolio.db     # Auto-created SQLite database
```

---

## How to Use

### My Portfolio (Tab 1)

- Expand **"Add Holding"** — enter ticker/scheme code, buy price, quantity, buy date.
- Stocks: use `TICKER.NS` (NSE) or `TICKER.BO` (BSE). `.NS` auto-appended.
- Mutual funds: enter numeric **scheme code** (find on MFAPI.in or MF tab fund search).
- **XIRR** — annualised return shown in KPI row, accounts for timing of each buy.
- **Held For** column shows duration since buy date (`1y 2m` / `8m 3d`).
- Edit holding: expand **"Edit Holding"**, enter ID and only the fields to change.
- Delete: enter holding ID and click Delete.
- **Export Portfolio CSV** button downloads current table.
- Prices cached 1 hr. Hit **Refresh Prices** to update.

### Stock Screener (Tab 2)

- Filters: P/E, ROE, D/E, Revenue Growth sliders + sector multiselect.
- **Persistent watchlist** — add/remove tickers saved to SQLite, survive restarts.
- Signal column: BUY / DECENT / WAIT / AVOID scored from 5 fundamentals.
- **"Should I Buy?"** section at bottom — enter any ticker for detailed verdict card.
- Add `.NS` for NSE or `.BO` for BSE (auto-appended if omitted).
- Data cached 1 hr. Hit **Refresh Stock Data** to force-update.
- **Export to CSV** button downloads screener results.

### Mutual Funds (Tab 3)

- Category multiselect, sort by 3yr CAGR / 5yr CAGR / Sharpe.
- **Fund name search** — type fund name to find scheme code without leaving app.
- **SIP Calculator** — monthly amount, tenure, expected return. Shows final corpus + chart.
- **Step-up SIP** — annual % increase slider (0–30%). Compounds monthly amount yearly.
- **"Should I Invest?"** — enter scheme code for NAV-based verdict card.
- **"Pick Top 2 SIP Funds for Me"** — beginner pick scored on 5yr CAGR (60%) + Sharpe (40%).
- NAV cached 24 hr. Fund list cached 7 days.

### IPO Watch (Tab 4)

- **Verdict** column first: ✅ APPLY (GMP≥20% + 10x subscribed), ⚠️ MAYBE, ❌ SKIP.
- Table sorted by GMP% descending.
- First load ~15s (headless Chromium). Cached 30 min.
- GMP is sentiment data, not a guarantee.

---

## Data Sources

| Data | Source | Cache |
|------|--------|-------|
| Stock fundamentals & prices | Yahoo Finance (yfinance) | 1 hr |
| Mutual fund NAV history | [MFAPI.in](https://mfapi.in) | 24 hr |
| Fund name search | [MFAPI.in](https://mfapi.in) | 5 min |
| IPO GMP | [investorgain.com](https://investorgain.com) | 30 min |
| Portfolio & watchlist | Local SQLite (`db/portfolio.db`) | Real-time |

---

## Customisation

**Change stock watchlist** — edit `DEFAULT_WATCHLIST` in `config.py`:
```python
DEFAULT_WATCHLIST = ["RELIANCE.NS", "TCS.NS", ...]
```

**Add curated MFs** — edit `CURATED_MF` in `config.py` (values are MFAPI scheme codes):
```python
CURATED_MF = {
    "Large Cap - Direct Growth": [119598, 120505, ...],
}
```

**Change cache durations** — edit `CACHE_TTL_*` in `config.py` (seconds).

**Risk-free rate for Sharpe** — edit `RISK_FREE_RATE` in `config.py` (default: 6.5% India 10yr G-Sec).

---

## Deployment (Coolify / Docker)

```bash
docker build -t investment-dashboard .
docker run -p 8501:8501 investment-dashboard
```

Or point Coolify at the GitHub repo. Set exposed port to **8501** in Coolify Networking settings.

---

## Known Limitations

- **IPO data** — depends on investorgain.com HTML structure. May break if site changes layout.
- **yfinance rate limits** — large custom watchlists will be slower (~0.3s sleep per ticker).
- **No authentication** — personal local tool. Do not expose publicly without adding auth.

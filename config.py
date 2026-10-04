import os

DB_PATH = os.path.join(os.path.dirname(__file__), "db", "portfolio.db")

MFAPI_ALL_FUNDS_URL = "https://api.mfapi.in/mf"
MFAPI_FUND_URL = "https://api.mfapi.in/mf/{}"

IPO_SCRAPE_URL = "https://www.investorgain.com/report/live-ipo-gmp/331/"
IPO_FALLBACK_URL = "https://www.chittorgarh.com/ipo/ipo_dashboard.asp"

CACHE_TTL_STOCKS = 3600       # 1 hour
CACHE_TTL_MF = 86400          # 24 hours
CACHE_TTL_IPO = 1800          # 30 minutes
CACHE_TTL_MF_LIST = 86400 * 7 # 7 days for the fund list

DEFAULT_WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "WIPRO.NS", "BAJFINANCE.NS", "MARUTI.NS", "TITAN.NS", "NESTLEIND.NS",
    "ASIANPAINT.NS", "LTIMINDTREE.NS", "SUNPHARMA.NS", "KOTAKBANK.NS", "AXISBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "ADANIENT.NS", "ULTRACEMCO.NS",
]

CURATED_MF = {
    "Large Cap - Direct Growth": [119598, 120505, 125354, 118989, 120843],
    "Flexi Cap - Direct Growth": [122639, 125497, 119062, 120503, 122658],
    "Mid Cap - Direct Growth":   [118778, 120841, 119285, 120816, 125354],
    "Small Cap - Direct Growth": [120828, 125497, 119598, 120505, 118989],
    "ELSS - Direct Growth":      [120503, 119598, 118778, 125354, 120505],
}

RISK_FREE_RATE = 0.065  # 6.5% (approximate India 10yr G-Sec yield)

MF_EXPENSE_RATIOS = {
    119598: 0.54,
    120505: 0.58,
    125354: 0.49,
    122639: 0.63,
    120503: 0.76,
    118989: 0.82,
    120843: 0.71,
    118778: 0.91,
}

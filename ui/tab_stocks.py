import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
from config import DEFAULT_WATCHLIST
from utils.cache import cached_stock_fundamentals
from data.stocks import filter_stocks
from data.portfolio import init_db, get_watchlist, add_to_watchlist, remove_from_watchlist
from utils.formatters import format_pct, format_inr

SECTOR_MAP = {
    "IT":       ["TCS.NS","INFY.NS","WIPRO.NS","LTIMINDTREE.NS"],
    "Banking":  ["HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","AXISBANK.NS","KOTAKBANK.NS"],
    "Auto":     ["MARUTI.NS","TATAMOTORS.NS","BAJAJ-AUTO.NS","HEROMOTOCO.NS"],
    "FMCG":     ["HINDUNILVR.NS","ITC.NS","NESTLEIND.NS","DABUR.NS"],
    "Finance":  ["BAJFINANCE.NS","HDFCLIFE.NS","SBILIFE.NS"],
    "Other":    ["RELIANCE.NS","TITAN.NS","ASIANPAINT.NS","SUNPHARMA.NS","ADANIENT.NS","ULTRACEMCO.NS"],
}


def render():
    init_db()
    st.markdown('<p class="section-title">Screener · NSE Stocks</p>', unsafe_allow_html=True)

    with st.expander("📖 What do these numbers mean?", expanded=False):
        st.markdown("""
| Term | Plain English | Good range |
|------|--------------|------------|
| **P/E Ratio** | Price ÷ Earnings. How much you pay for ₹1 of company profit. Lower = cheaper. | 10–30 for most sectors |
| **ROE %** | Return on Equity. How efficiently company uses shareholder money to make profit. Higher = better. | Above 15% is good |
| **D/E** | Debt ÷ Equity. How much debt the company carries vs its own money. Lower = safer. | Below 1.0 is safe |
| **Rev Growth** | Revenue Growth %. Is the company growing its sales? Positive = growing. | Above 10% is healthy |
| **Mkt Cap** | Total value of the company. Large cap = more stable. | — |
""")

    with st.expander("🔧 Filters & Watchlist", expanded=False):
        f1, f2 = st.columns(2)
        with f1:
            max_pe = st.slider("Max P/E Ratio", 5, 150, 150)
            min_roe = st.slider("Min ROE %", 0, 60, 0)
        with f2:
            max_de = st.slider("Max Debt/Equity", 0.0, 10.0, 10.0, step=0.5)
            min_rev_growth = st.slider("Min Revenue Growth %", -50, 50, -50)

        all_sectors = list(SECTOR_MAP.keys())
        selected_sectors = st.multiselect("Sector filter", all_sectors, default=all_sectors)

        add_col, rem_col = st.columns(2)
        with add_col:
            custom_input = st.text_input("➕ Add ticker to watchlist", placeholder="TATAMOTORS.NS")
            if st.button("Add", key="add_ticker"):
                if custom_input.strip():
                    t = custom_input.strip().upper()
                    if not t.endswith(".NS") and not t.endswith(".BO"):
                        t += ".NS"
                    add_to_watchlist(t)
                    cached_stock_fundamentals.clear()
                    st.rerun()
        with rem_col:
            remove_input = st.text_input("➖ Remove ticker from watchlist", placeholder="TATAMOTORS.NS")
            if st.button("Remove", key="remove_ticker"):
                if remove_input.strip():
                    remove_from_watchlist(remove_input.strip().upper())
                    cached_stock_fundamentals.clear()
                    st.rerun()

    saved_tickers = get_watchlist()
    watchlist = list(DEFAULT_WATCHLIST)
    for t in saved_tickers:
        if t not in watchlist:
            watchlist.append(t)

    if selected_sectors and selected_sectors != all_sectors:
        sector_tickers = []
        for s in selected_sectors:
            sector_tickers.extend(SECTOR_MAP.get(s, []))
        watchlist = [t for t in watchlist if t in sector_tickers] or watchlist

    with st.spinner("Fetching fundamentals from Yahoo Finance..."):
        df = cached_stock_fundamentals(tuple(watchlist))

    filtered = filter_stocks(df, max_pe=max_pe, min_roe=min_roe, max_de=max_de, min_rev_growth=min_rev_growth)

    total = len(df)
    matched = len(filtered)
    avg_roe = filtered["roe_pct"].mean() if not filtered.empty and "roe_pct" in filtered.columns else 0
    avg_pe = filtered["pe_ratio"].mean() if not filtered.empty and "pe_ratio" in filtered.columns else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Stocks Screened", total)
    k2.metric("Passed Filters", matched)
    k3.metric("Avg ROE %", f"{avg_roe:.1f}%" if avg_roe else "—")
    k4.metric("Avg P/E", f"{avg_pe:.1f}" if avg_pe else "—")

    st.markdown("---")

    if filtered.empty:
        st.warning("No stocks match current filters. Expand 'Filters' above to relax criteria.")
        return

    def _stock_signal(row) -> str:
        green = red = 0
        pe = row.get("pe_ratio")
        roe = row.get("roe_pct")
        de = row.get("debt_to_equity")
        rg = row.get("revenue_growth_pct")
        price_v = row.get("price")
        low52 = row.get("week52_low")
        high52 = row.get("week52_high")

        if pe is not None and not pd.isna(pe):
            if pe < 20: green += 1
            elif pe >= 35: red += 1
        if roe is not None and not pd.isna(roe):
            if roe > 15: green += 1
            elif roe < 8: red += 1
        if de is not None and not pd.isna(de):
            if de < 0.5: green += 1
            elif de >= 1.5: red += 1
        if rg is not None and not pd.isna(rg):
            if rg > 15: green += 1
            elif rg < 0: red += 1
        if price_v and low52 and high52 and high52 > low52:
            pct = (price_v - low52) / (high52 - low52) * 100
            if pct <= 20: green += 1
            elif pct >= 80: red += 1

        if green >= 3 and red == 0: return "✅ BUY"
        if green >= 2 and red == 0: return "✅ DECENT"
        if red >= 2: return "❌ AVOID"
        return "⚠️ WAIT"

    display = filtered.copy()
    display["signal"] = filtered.apply(_stock_signal, axis=1)
    display["price"] = display["price"].apply(format_inr)
    display["pe_ratio"] = display["pe_ratio"].apply(lambda v: f"{v:.1f}" if v and not pd.isna(v) else "N/A")
    display["roe_pct"] = display["roe_pct"].apply(format_pct)
    display["revenue_growth_pct"] = display["revenue_growth_pct"].apply(format_pct)

    rename = {
        "signal": "Signal", "name": "Company", "ticker": "Ticker",
        "price": "Price", "pe_ratio": "P/E", "roe_pct": "ROE %",
        "revenue_growth_pct": "Rev Growth",
    }
    cols_show = [c for c in ["signal", "name", "ticker", "price", "pe_ratio", "roe_pct", "revenue_growth_pct"] if c in display.columns]
    final_table = display[cols_show].rename(columns=rename).reset_index(drop=True)
    st.dataframe(final_table, use_container_width=True, height=400, hide_index=True)

    st.download_button(
        "⬇️ Export to CSV",
        data=final_table.to_csv(index=False).encode("utf-8"),
        file_name="stocks_screener.csv",
        mime="text/csv",
    )

    chart_df = filtered.dropna(subset=["roe_pct"]).head(10)
    if not chart_df.empty:
        fig = go.Figure(go.Bar(
            x=chart_df["ticker"], y=chart_df["roe_pct"],
            marker=dict(color=chart_df["roe_pct"],
                        colorscale=[[0, "#1A2235"], [0.5, "#D4900A"], [1, "#F5A623"]],
                        showscale=False),
            text=chart_df["roe_pct"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
        ))
        fig.update_layout(
            title="Top 10 Stocks by ROE%",
            paper_bgcolor="#0B0F1A", plot_bgcolor="#0B0F1A",
            font=dict(color="#FFFFFF"),
            xaxis=dict(gridcolor="#252D42"),
            yaxis=dict(gridcolor="#252D42", title="ROE %"),
            margin=dict(t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    if st.button("🔄 Refresh Stock Data"):
        cached_stock_fundamentals.clear()
        st.rerun()

    st.markdown("---")
    st.markdown('<p class="section-title">Should I Buy This Stock?</p>', unsafe_allow_html=True)

    with st.expander("📖 How this works", expanded=False):
        st.markdown("""
We score the stock on 5 factors and give a verdict:

| Factor | Green ✅ | Yellow ⚠️ | Red ❌ |
|--------|----------|-----------|--------|
| **P/E Ratio** | Below 20 (cheap) | 20–35 (fair) | Above 35 (expensive) |
| **ROE %** | Above 15% (efficient) | 8–15% (ok) | Below 8% (weak) |
| **Debt/Equity** | Below 0.5 (safe) | 0.5–1.5 (moderate) | Above 1.5 (risky) |
| **Revenue Growth** | Above 15% (growing fast) | 0–15% (slow growth) | Negative (shrinking) |
| **52W Position** | Near 52W low (good entry) | Mid range | Near 52W high (wait for dip) |

**Verdict:** 3+ greens and 0 reds → BUY · 2+ reds → AVOID · else → WAIT
""")

    buy_col1, buy_col2 = st.columns([3, 1])
    with buy_col1:
        buy_ticker_input = st.text_input("Enter stock ticker to analyse", placeholder="RELIANCE.NS", key="buy_ticker_input")
    with buy_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyse_clicked = st.button("🔍 Analyse Stock")

    if analyse_clicked and buy_ticker_input.strip():
        raw = buy_ticker_input.strip().upper()
        if not raw.endswith(".NS") and not raw.endswith(".BO"):
            raw += ".NS"

        with st.spinner(f"Fetching data for {raw}..."):
            try:
                info = yf.Ticker(raw).info
            except Exception as e:
                st.error(f"Could not fetch data for {raw}: {e}")
                info = {}

        if info:
            pe = info.get("trailingPE") or info.get("forwardPE")
            roe_raw = info.get("returnOnEquity")
            roe = roe_raw * 100 if roe_raw is not None else None
            de = info.get("debtToEquity")
            de_norm = round(de / 100, 2) if de is not None else None
            rev_growth_raw = info.get("revenueGrowth")
            rev_growth = rev_growth_raw * 100 if rev_growth_raw is not None else None
            week52_low = info.get("fiftyTwoWeekLow")
            week52_high = info.get("fiftyTwoWeekHigh")
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            name = info.get("longName") or info.get("shortName") or raw

            scores = []
            details = []

            # P/E
            if pe is not None and not pd.isna(pe):
                if pe < 20:
                    scores.append("green"); details.append(f"🟢 P/E {pe:.1f} — cheap valuation")
                elif pe < 35:
                    scores.append("yellow"); details.append(f"🟡 P/E {pe:.1f} — fair valuation")
                else:
                    scores.append("red"); details.append(f"🔴 P/E {pe:.1f} — expensive, pay high premium")
            else:
                details.append("⚪ P/E — not available")

            # ROE
            if roe is not None and not pd.isna(roe):
                if roe > 15:
                    scores.append("green"); details.append(f"🟢 ROE {roe:.1f}% — company uses money efficiently")
                elif roe > 8:
                    scores.append("yellow"); details.append(f"🟡 ROE {roe:.1f}% — decent but not great")
                else:
                    scores.append("red"); details.append(f"🔴 ROE {roe:.1f}% — weak returns on equity")
            else:
                details.append("⚪ ROE — not available")

            # D/E
            if de_norm is not None and not pd.isna(de_norm):
                if de_norm < 0.5:
                    scores.append("green"); details.append(f"🟢 Debt/Equity {de_norm:.2f} — low debt, financially safe")
                elif de_norm < 1.5:
                    scores.append("yellow"); details.append(f"🟡 Debt/Equity {de_norm:.2f} — moderate debt")
                else:
                    scores.append("red"); details.append(f"🔴 Debt/Equity {de_norm:.2f} — high debt, risky")
            else:
                details.append("⚪ Debt/Equity — not available")

            # Revenue Growth
            if rev_growth is not None and not pd.isna(rev_growth):
                if rev_growth > 15:
                    scores.append("green"); details.append(f"🟢 Revenue Growth {rev_growth:.1f}% — growing fast")
                elif rev_growth > 0:
                    scores.append("yellow"); details.append(f"🟡 Revenue Growth {rev_growth:.1f}% — growing slowly")
                else:
                    scores.append("red"); details.append(f"🔴 Revenue Growth {rev_growth:.1f}% — sales are shrinking")
            else:
                details.append("⚪ Revenue Growth — not available")

            # 52W Position
            if price and week52_low and week52_high and week52_high > week52_low:
                pct_from_low = (price - week52_low) / (week52_high - week52_low) * 100
                if pct_from_low <= 20:
                    scores.append("green"); details.append(f"🟢 Price near 52W low ({pct_from_low:.0f}% from bottom) — good entry point")
                elif pct_from_low >= 80:
                    scores.append("red"); details.append(f"🔴 Price near 52W high ({pct_from_low:.0f}% from bottom) — wait for a dip")
                else:
                    scores.append("yellow"); details.append(f"🟡 Price in mid range ({pct_from_low:.0f}% from 52W low)")
            else:
                details.append("⚪ 52W range — not available")

            green_count = scores.count("green")
            red_count = scores.count("red")

            if green_count >= 3 and red_count == 0:
                verdict = "✅ BUY"
                verdict_color = "#22C55E"
                verdict_bg = "#052e16"
                verdict_note = "Strong fundamentals. Good time to consider buying."
            elif red_count >= 2:
                verdict = "❌ AVOID"
                verdict_color = "#FF4466"
                verdict_bg = "#2d0a14"
                verdict_note = "Multiple red flags. High risk right now."
            elif green_count >= 2 and red_count == 0:
                verdict = "✅ BUY (Decent)"
                verdict_color = "#F5A623"
                verdict_bg = "#2a1a00"
                verdict_note = "Decent fundamentals. Reasonable to buy, monitor closely."
            else:
                verdict = "⚠️ WAIT"
                verdict_color = "#F5A623"
                verdict_bg = "#2a1a00"
                verdict_note = "Mixed signals. Wait for better conditions or more data."

            st.markdown(f"""
<div style="background:linear-gradient(135deg,#141927,#1A2140);border:2px solid {verdict_color}44;border-radius:14px;padding:1.4rem 1.8rem;margin:1rem 0;">
  <div style="color:#7B8699;font-size:0.72rem;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:0.5rem;">Stock Analysis · {name}</div>
  <div style="color:{verdict_color};font-size:2rem;font-weight:800;margin-bottom:0.3rem;">{verdict}</div>
  <div style="color:#C8D0DF;font-size:0.9rem;margin-bottom:1rem;">{verdict_note}</div>
  <div style="display:flex;flex-direction:column;gap:0.4rem;border-top:1px solid #252D42;padding-top:0.8rem;">
    {"".join(f'<div style="color:#C8D0DF;font-size:0.85rem;">{d}</div>' for d in details)}
  </div>
  <div style="color:#7B8699;font-size:0.72rem;margin-top:0.8rem;">Score: {green_count} green · {scores.count("yellow")} yellow · {red_count} red out of {len(scores)} factors rated</div>
</div>
""", unsafe_allow_html=True)
        else:
            st.warning(f"No data found for {raw}. Check the ticker symbol and try again.")

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from data.portfolio import init_db, add_holding, get_all_holdings, delete_holding, update_holding, compute_portfolio_value
from utils.cache import cached_eod_prices, cached_mf_nav_bulk
from utils.formatters import format_inr, format_pct
from datetime import datetime


def _compute_mf_value(holdings_df: pd.DataFrame, mf_navs: dict) -> pd.DataFrame:
    df = holdings_df.copy()
    def _nav(row):
        try:
            code = int(row["ticker"])
            return mf_navs.get(code)
        except (ValueError, TypeError):
            return None
    df["current_price"] = df.apply(_nav, axis=1)
    df["invested_value"] = df["buy_price"] * df["quantity"]
    df["current_value"] = df["current_price"] * df["quantity"]
    df["pnl"] = df["current_value"] - df["invested_value"]
    df["pnl_pct"] = (df["pnl"] / df["invested_value"] * 100).round(2)
    return df


def render():
    init_db()
    st.markdown('<p class="section-title">My Portfolio · Holdings Tracker</p>', unsafe_allow_html=True)

    with st.expander("📖 How to use this tab", expanded=False):
        st.markdown("""
**This is your main tab — open this every day.**

| What you see | What it means |
|---|---|
| **Total Invested** | Total money you have put in (stocks + SIP combined) |
| **Current Value** | What your investments are worth right now |
| **Total P&L** | Profit or Loss = Current Value − Invested. Green = profit, Red = loss |
| **P&L %** | Percentage gain or loss on your total investment |

**To add a holding:**
1. Click "➕ Add Holding" above
2. **Stocks** → enter ticker like `RELIANCE.NS`, select STOCK, enter price you bought at and how many shares
3. **SIP/MF** → enter scheme code (number), select MF, enter NAV when you bought and units

**Where to find scheme code for your SIP fund:**
- Open Groww / Zerodha → find your fund → Google `"fund name" MFAPI scheme code`
- Or go to [mfapi.in](https://mfapi.in) and search fund name

**Refresh Prices** button fetches latest prices from NSE/MFAPI. Do this once a day.
""")

    with st.expander("➕ Add Holding", expanded=False):
        with st.form("add_holding_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                ticker = st.text_input("Ticker / Scheme Code", placeholder="RELIANCE.NS or 119598")
                asset_type = st.selectbox("Asset Type", ["STOCK", "MF"])
            with c2:
                buy_price = st.number_input("Buy Price / NAV (₹)", min_value=0.01, value=100.0, step=0.01)
                quantity = st.number_input("Quantity / Units", min_value=0.001, value=1.0, step=0.001)
            with c3:
                buy_date = st.date_input("Buy Date")
                notes = st.text_input("Notes (optional)")
            submitted = st.form_submit_button("Add Holding")
            if submitted and ticker.strip():
                t = ticker.strip().upper()
                if asset_type == "STOCK" and not t.endswith(".NS") and not t.endswith(".BO") and not t.isdigit():
                    t += ".NS"
                if asset_type == "MF":
                    t = ticker.strip()  # keep numeric scheme code as-is
                add_holding(t, asset_type, buy_price, quantity, str(buy_date), notes)
                st.success(f"✅ Added {t}")
                cached_eod_prices.clear()
                cached_mf_nav_bulk.clear()
                st.rerun()

    holdings = get_all_holdings()

    if holdings.empty:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#7B8699;border:1px dashed #252D42;border-radius:12px;margin-top:1rem;">
            <div style="font-size:2.5rem">💼</div>
            <div style="font-size:1.1rem;margin-top:0.5rem">No holdings yet</div>
            <div style="font-size:0.85rem;margin-top:0.3rem">Add your first holding using the form above</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── fetch live prices ──────────────────────────────────────────────────
    stock_holdings = holdings[holdings["asset_type"] == "STOCK"]
    mf_holdings = holdings[holdings["asset_type"] == "MF"]

    stock_tickers = stock_holdings["ticker"].tolist()
    prices = cached_eod_prices(tuple(stock_tickers)) if stock_tickers else {}

    mf_codes = []
    for t in mf_holdings["ticker"].tolist():
        try:
            mf_codes.append(int(t))
        except (ValueError, TypeError):
            pass
    mf_navs = cached_mf_nav_bulk(tuple(mf_codes)) if mf_codes else {}

    # ── compute P&L per asset type ─────────────────────────────────────────
    stock_portfolio = pd.DataFrame()
    if not stock_holdings.empty:
        stock_portfolio = compute_portfolio_value(stock_holdings, prices)

    mf_portfolio = pd.DataFrame()
    if not mf_holdings.empty:
        mf_portfolio = _compute_mf_value(mf_holdings, mf_navs)

    portfolio = pd.concat([stock_portfolio, mf_portfolio], ignore_index=True) if not stock_portfolio.empty or not mf_portfolio.empty else holdings.copy()

    # ── XIRR ──────────────────────────────────────────────────────────────────
    def _compute_xirr(pf: pd.DataFrame) -> float | None:
        try:
            from scipy.optimize import brentq
            cashflows = []
            for _, row in pf.iterrows():
                try:
                    d = datetime.strptime(str(row.get("buy_date", "")), "%Y-%m-%d")
                    cashflows.append((d, -float(row["invested_value"])))
                except Exception:
                    pass
            if not cashflows:
                return None
            today = datetime.now()
            total_current_val = pf["current_value"].dropna().sum()
            cashflows.append((today, total_current_val))
            dates = [c[0] for c in cashflows]
            amounts = [c[1] for c in cashflows]
            t0 = dates[0]
            years = [(d - t0).days / 365.0 for d in dates]

            def npv(rate):
                return sum(a / (1 + rate) ** t for a, t in zip(amounts, years))

            return round(brentq(npv, -0.999, 100.0) * 100, 2)
        except Exception:
            return None

    xirr_val = _compute_xirr(portfolio) if "invested_value" in portfolio.columns and "current_value" in portfolio.columns else None

    # ── SUMMARY CARD ───────────────────────────────────────────────────────
    total_invested = portfolio["invested_value"].sum() if "invested_value" in portfolio.columns else 0
    total_current = portfolio["current_value"].dropna().sum() if "current_value" in portfolio.columns else 0
    total_pnl = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    stock_invested = stock_portfolio["invested_value"].sum() if not stock_portfolio.empty and "invested_value" in stock_portfolio.columns else 0
    stock_current = stock_portfolio["current_value"].dropna().sum() if not stock_portfolio.empty and "current_value" in stock_portfolio.columns else 0
    mf_invested = mf_portfolio["invested_value"].sum() if not mf_portfolio.empty and "invested_value" in mf_portfolio.columns else 0
    mf_current = mf_portfolio["current_value"].dropna().sum() if not mf_portfolio.empty and "current_value" in mf_portfolio.columns else 0

    pnl_color = "#F5A623" if total_pnl >= 0 else "#FF4466"
    pnl_sign = "+" if total_pnl >= 0 else ""

    st.markdown(f"""
<div style="background:linear-gradient(135deg,#141927,#0D1525);border:1px solid #252D42;border-radius:14px;padding:1.4rem 1.8rem;margin-bottom:1.2rem;">
  <div style="color:#7B8699;font-size:0.72rem;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:0.8rem;">Portfolio Summary</div>
  <div style="display:flex;gap:2.5rem;flex-wrap:wrap;align-items:flex-end;">
    <div>
      <div style="color:#7B8699;font-size:0.72rem;">Total Invested</div>
      <div style="color:#FFFFFF;font-size:1.5rem;font-weight:700;">{format_inr(total_invested)}</div>
    </div>
    <div>
      <div style="color:#7B8699;font-size:0.72rem;">Current Value</div>
      <div style="color:#FFFFFF;font-size:1.5rem;font-weight:700;">{format_inr(total_current)}</div>
    </div>
    <div>
      <div style="color:#7B8699;font-size:0.72rem;">Overall P&amp;L</div>
      <div style="color:{pnl_color};font-size:1.5rem;font-weight:700;">{pnl_sign}{format_inr(total_pnl)} <span style="font-size:1rem;">({pnl_sign}{total_pnl_pct:.1f}%)</span></div>
    </div>
  </div>
  <div style="display:flex;gap:2rem;flex-wrap:wrap;margin-top:1rem;padding-top:0.8rem;border-top:1px solid #252D42;">
    <div style="color:#7B8699;font-size:0.8rem;">📊 Stocks: <b style="color:#FFFFFF;">{format_inr(stock_current)}</b> <span style="color:{'#F5A623' if stock_current >= stock_invested else '#FF4466'}">({'+' if stock_current >= stock_invested else ''}{((stock_current-stock_invested)/stock_invested*100) if stock_invested else 0:.1f}%)</span></div>
    <div style="color:#7B8699;font-size:0.8rem;">💰 Mutual Funds: <b style="color:#FFFFFF;">{format_inr(mf_current)}</b> <span style="color:{'#F5A623' if mf_current >= mf_invested else '#FF4466'}">({'+' if mf_current >= mf_invested else ''}{((mf_current-mf_invested)/mf_invested*100) if mf_invested else 0:.1f}%)</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── KPI row ────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Invested", format_inr(total_invested))
    k2.metric("Current Value", format_inr(total_current))
    k3.metric("Total P&L", format_inr(total_pnl), delta=f"{pnl_sign}{total_pnl_pct:.1f}%")
    k4.metric("XIRR", f"{xirr_val:.1f}%" if xirr_val is not None else "—", help="Annualised return accounting for timing of each investment")

    valid_pnl = portfolio.dropna(subset=["pnl_pct"]) if "pnl_pct" in portfolio.columns else pd.DataFrame()
    if not valid_pnl.empty:
        best = valid_pnl.loc[valid_pnl["pnl_pct"].idxmax()]
        k5.metric("Best Performer", best["ticker"], delta=format_pct(best["pnl_pct"]))

    st.markdown("---")

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("**Holdings**")
        display_cols = ["id", "ticker", "asset_type", "quantity", "buy_price",
                        "current_price", "invested_value", "current_value", "pnl", "pnl_pct", "buy_date", "notes"]
        display = portfolio[[c for c in display_cols if c in portfolio.columns]].copy()

        if "buy_date" in display.columns:
            def _duration(d):
                try:
                    delta = (datetime.now() - datetime.strptime(str(d), "%Y-%m-%d")).days
                    if delta >= 365:
                        return f"{delta // 365}y {(delta % 365) // 30}m"
                    return f"{delta // 30}m {delta % 30}d"
                except Exception:
                    return "—"
            display["held_for"] = display["buy_date"].apply(_duration)

        if "buy_price" in display.columns:
            display["buy_price"] = display["buy_price"].apply(format_inr)
        if "current_price" in display.columns:
            display["current_price"] = display["current_price"].apply(format_inr)
        if "invested_value" in display.columns:
            display["invested_value"] = display["invested_value"].apply(format_inr)
        if "current_value" in display.columns:
            display["current_value"] = display["current_value"].apply(format_inr)
        if "pnl" in display.columns:
            display["pnl"] = display["pnl"].apply(format_inr)
        if "pnl_pct" in display.columns:
            display["pnl_pct"] = display["pnl_pct"].apply(lambda v: format_pct(v) if pd.notna(v) else "N/A")

        rename = {
            "id": "ID", "ticker": "Ticker", "asset_type": "Type",
            "quantity": "Qty", "buy_price": "Buy ₹",
            "current_price": "Current ₹", "invested_value": "Invested",
            "current_value": "Value", "pnl": "P&L", "pnl_pct": "P&L%",
            "buy_date": "Date", "held_for": "Held For", "notes": "Notes",
        }
        final_portfolio_table = display.rename(columns={k: v for k, v in rename.items() if k in display.columns})
        st.dataframe(final_portfolio_table, use_container_width=True)

        st.download_button(
            "⬇️ Export Portfolio CSV",
            data=final_portfolio_table.to_csv(index=False).encode("utf-8"),
            file_name="my_portfolio.csv",
            mime="text/csv",
        )

        delete_id = st.number_input("Delete holding by ID", min_value=0, value=0, step=1)
        if st.button("🗑 Delete"):
            if delete_id > 0:
                delete_holding(int(delete_id))
                cached_eod_prices.clear()
                cached_mf_nav_bulk.clear()
                st.rerun()
            else:
                st.warning("Enter a valid holding ID.")

        with st.expander("✏️ Edit Holding", expanded=False):
            with st.form("edit_holding_form"):
                e1, e2, e3 = st.columns(3)
                with e1:
                    edit_id = st.number_input("Holding ID to edit", min_value=1, value=1, step=1)
                    edit_ticker = st.text_input("New Ticker / Code (leave blank to keep)")
                with e2:
                    edit_price = st.number_input("New Buy Price (0 = keep)", min_value=0.0, value=0.0, step=0.01)
                    edit_qty = st.number_input("New Quantity (0 = keep)", min_value=0.0, value=0.0, step=0.001)
                with e3:
                    edit_date = st.text_input("New Buy Date (YYYY-MM-DD, blank = keep)")
                    edit_notes = st.text_input("New Notes (blank = keep)")
                edit_submitted = st.form_submit_button("✏️ Update Holding")
                if edit_submitted:
                    updates = {}
                    if edit_ticker.strip():
                        updates["ticker"] = edit_ticker.strip().upper()
                    if edit_price > 0:
                        updates["buy_price"] = edit_price
                    if edit_qty > 0:
                        updates["quantity"] = edit_qty
                    if edit_date.strip():
                        updates["buy_date"] = edit_date.strip()
                    if edit_notes.strip():
                        updates["notes"] = edit_notes.strip()
                    if updates:
                        update_holding(int(edit_id), **updates)
                        cached_eod_prices.clear()
                        cached_mf_nav_bulk.clear()
                        st.success(f"Updated holding #{edit_id}")
                        st.rerun()
                    else:
                        st.warning("No changes entered.")

    with col_right:
        valid_current = portfolio.dropna(subset=["current_value"]) if "current_value" in portfolio.columns else pd.DataFrame()
        if not valid_current.empty:
            fig = go.Figure(go.Pie(
                labels=valid_current["ticker"],
                values=valid_current["current_value"],
                hole=0.5,
                marker=dict(colors=[
                    "#F5A623", "#4B9EFF", "#FF8C00", "#FF4466",
                    "#AA88FF", "#44DDAA", "#FFD700", "#FF6644",
                ]),
                textinfo="label+percent",
                textfont=dict(color="#FFFFFF"),
            ))
            fig.update_layout(
                title="Allocation",
                paper_bgcolor="#0B0F1A",
                font=dict(color="#FFFFFF"),
                showlegend=False,
                margin=dict(t=40, b=10, l=10, r=10),
                height=320,
            )
            st.plotly_chart(fig, use_container_width=True)

        if not valid_pnl.empty and len(valid_pnl) > 1:
            worst = valid_pnl.loc[valid_pnl["pnl_pct"].idxmin()]
            st.metric("Worst Performer", worst["ticker"], delta=format_pct(worst["pnl_pct"]))

    if st.button("🔄 Refresh Prices"):
        cached_eod_prices.clear()
        cached_mf_nav_bulk.clear()
        st.rerun()
    st.caption(f"Prices last fetched: {datetime.now().strftime('%d %b %Y %H:%M')} · Stocks: NSE via Yahoo Finance · MF: MFAPI.in")

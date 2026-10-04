import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from config import CURATED_MF
from utils.cache import cached_mf_data, cached_fund_meta
from utils.formatters import format_pct, format_inr
from data.mutual_funds import fetch_nav_history


def _nav_buttons(active: str):
    sections = [
        ("📊", "Compare Funds", "Browse & compare all funds"),
        ("🎯", "Get Recommendation", "Best 2 funds picked for you"),
        ("📈", "SIP Calculator", "Simulate your SIP growth"),
        ("🔍", "Should I Invest?", "Get YES/NO verdict on any fund"),
    ]
    cols = st.columns(4)
    for col, (icon, label, desc) in zip(cols, sections):
        key = f"{icon} {label}"
        is_active = active == key
        border = "2px solid #F5A623" if is_active else "1px solid #252D42"
        bg = "#F5A62322" if is_active else "#141927"
        color = "#F5A623" if is_active else "#FFFFFF"
        desc_color = "#F5A623" if is_active else "#7B8699"
        clicked = col.button(
            f"{icon}  {label}",
            key=f"mf_nav_{label}",
            use_container_width=True,
        )
        col.markdown(f'<div style="text-align:center;color:{desc_color};font-size:0.75rem;margin-top:-0.6rem;margin-bottom:0.4rem;">{desc}</div>', unsafe_allow_html=True)
        if clicked:
            st.session_state["mf_section"] = key


def render():
    st.markdown('<p class="section-title">Mutual Funds · SIP Recommendations</p>', unsafe_allow_html=True)

    if "mf_section" not in st.session_state:
        st.session_state["mf_section"] = "📊 Compare Funds"

    active = st.session_state["mf_section"]
    _nav_buttons(active)
    st.markdown("---")

    # ── load data once ────────────────────────────────────────────────────
    with st.spinner("Loading fund data..."):
        df_all = cached_mf_data()

    # ══ SECTION 1: Compare Funds ══════════════════════════════════════════
    if active == "📊 Compare Funds":
        if df_all is None or df_all.empty:
            st.error("Could not load mutual fund data.")
            return

        categories = list(CURATED_MF.keys())
        col_a, col_b = st.columns([2, 1])
        with col_a:
            selected_cats = st.multiselect("Category", categories, default=categories)
        with col_b:
            sort_by = st.radio("Sort by", ["3yr CAGR", "5yr CAGR", "Sharpe"], horizontal=True)

        sort_col_map = {"3yr CAGR": "cagr_3yr", "5yr CAGR": "cagr_5yr", "Sharpe": "sharpe_1yr"}
        sort_col = sort_col_map[sort_by]

        df = df_all.copy()
        if selected_cats:
            df = df[df["category"].isin(selected_cats)]
        df = df.dropna(subset=[sort_col]).sort_values(sort_col, ascending=False).reset_index(drop=True)

        k1, k2, k3 = st.columns(3)
        k1.metric("Funds Analysed", len(df))
        k2.metric("Best 3yr CAGR", format_pct(df["cagr_3yr"].max() if "cagr_3yr" in df.columns else None))
        k3.metric("Best 5yr CAGR", format_pct(df["cagr_5yr"].max() if "cagr_5yr" in df.columns else None))

        display = df.copy()
        display["cagr_3yr"] = display["cagr_3yr"].apply(format_pct)
        display["cagr_5yr"] = display["cagr_5yr"].apply(format_pct)
        display["sharpe_1yr"] = display["sharpe_1yr"].apply(lambda v: f"{v:.2f}" if v else "N/A")
        display["expense_ratio"] = display["expense_ratio"].apply(lambda v: format_pct(v) if v else "N/A")
        display["latest_nav"] = display["latest_nav"].apply(lambda v: f"₹{v:.2f}" if v else "N/A")
        rename = {
            "fund_name": "Fund Name", "category": "Category",
            "cagr_3yr": "3yr CAGR", "cagr_5yr": "5yr CAGR",
            "sharpe_1yr": "Sharpe", "latest_nav": "NAV",
            "expense_ratio": "Exp Ratio", "scheme_code": "Code",
        }
        # reorder columns: Fund Name first, Code last
        col_order = [c for c in ["fund_name", "category", "cagr_3yr", "cagr_5yr", "sharpe_1yr", "latest_nav", "expense_ratio", "scheme_code"] if c in display.columns]
        st.dataframe(display[col_order].rename(columns=rename), use_container_width=True, height=420)
        st.caption("NAV data: MFAPI.in · Expense ratios approximate · Past performance ≠ future returns")

        col_r1, col_r2 = st.columns([1, 4])
        with col_r1:
            if st.button("🔄 Refresh"):
                cached_mf_data.clear()
                st.rerun()

        chart_df = df.dropna(subset=[sort_col]).head(10)
        if not chart_df.empty:
            if "fund_name" in chart_df.columns:
                labels = chart_df["fund_name"].str.slice(0, 35) + " (" + chart_df["scheme_code"].astype(str) + ")"
            else:
                labels = chart_df["scheme_code"].astype(str) + " · " + chart_df["category"].str.split(" - ").str[0]
            fig = go.Figure(go.Bar(
                x=chart_df[sort_col], y=labels, orientation="h",
                marker=dict(color=chart_df[sort_col],
                            colorscale=[[0, "#141D2E"], [0.5, "#2266AA"], [1, "#4B9EFF"]],
                            showscale=False),
                text=chart_df[sort_col].apply(lambda v: f"{v:.1f}%" if sort_col != "sharpe_1yr" else f"{v:.2f}"),
                textposition="outside",
            ))
            fig.update_layout(
                title=f"Top 10 Funds by {sort_by}",
                paper_bgcolor="#0B0F1A", plot_bgcolor="#0B0F1A",
                font=dict(color="#FFFFFF"),
                xaxis=dict(gridcolor="#252D42"),
                yaxis=dict(gridcolor="#252D42"),
                margin=dict(t=40, b=20, l=220), height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

    # ══ SECTION 2: Get Recommendation ═════════════════════════════════════
    elif active == "🎯 Get Recommendation":
        st.markdown("#### Best SIP funds for beginners")
        st.caption("Scores Large Cap + Flexi Cap funds on 5yr returns and risk. Safer categories for new investors.")

        if st.button("🎯 Pick Top 2 SIP Funds for Me"):
            if df_all is not None and not df_all.empty:
                beginner_cats = [c for c in df_all["category"].unique()
                                 if "Large Cap" in c or "Flexi Cap" in c]
                filtered = df_all[df_all["category"].isin(beginner_cats)].copy()
                filtered = filtered.dropna(subset=["cagr_5yr", "sharpe_1yr"])
                filtered = filtered[filtered["sharpe_1yr"] >= 0.0]
                if not filtered.empty:
                    filtered["score"] = filtered["cagr_5yr"] * 0.6 + filtered["sharpe_1yr"] * 10 * 0.4
                    top2 = filtered.nlargest(2, "score")
                    st.success("Best 2 SIP funds based on 5yr CAGR + Sharpe ratio:")
                    for i, row in top2.iterrows():
                        exp = f"{row['expense_ratio']}%" if row.get("expense_ratio") else "N/A"
                        fname = row.get("fund_name", f"Scheme {row['scheme_code']}")
                        st.markdown(f"""
<div style="background:#141927;border:1px solid #F5A62355;border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.8rem;">
  <div style="color:#F5A623;font-size:1rem;font-weight:700;">#{list(top2.index).index(i)+1} — {row['category']}</div>
  <div style="color:#FFFFFF;font-size:0.95rem;font-weight:600;margin:0.2rem 0 0.1rem;">{fname}</div>
  <div style="color:#7B8699;font-size:0.8rem;margin-bottom:0.6rem;">Scheme Code: <b style="color:#FFFFFF">{row['scheme_code']}</b> · Search on Groww/Zerodha to start SIP</div>
  <div style="display:flex;gap:2rem;flex-wrap:wrap;">
    <span>📈 <b>5yr CAGR:</b> <span style="color:#F5A623">{format_pct(row['cagr_5yr'])}</span></span>
    <span>📈 <b>3yr CAGR:</b> <span style="color:#F5A623">{format_pct(row['cagr_3yr'])}</span></span>
    <span>⚖️ <b>Sharpe:</b> {row['sharpe_1yr']:.2f}</span>
    <span>💰 <b>NAV:</b> ₹{row['latest_nav']:.2f}</span>
    <span>🏷️ <b>Exp Ratio:</b> {exp}</span>
  </div>
</div>
""", unsafe_allow_html=True)
                    st.info("💡 Invest equal amounts in both. Start ₹500–₹1000/month each. Increase every year.")
                else:
                    st.warning("Not enough data. Try refreshing fund data.")
            else:
                st.error("Fund data not loaded.")

        with st.expander("📖 What do these terms mean?"):
            st.markdown("""
| Term | Meaning |
|---|---|
| **5yr CAGR** | Average yearly return over 5 years. 15% = money grew 15%/year on average |
| **Sharpe** | Return vs risk. Above 1.0 = excellent. Above 0.5 = acceptable |
| **Exp Ratio** | Annual fee. Lower = better. Below 1% is good |
| **Large Cap** | Invests in big stable companies. Lower risk, steady growth |
| **Flexi Cap** | Can invest anywhere. More flexible, slightly more risk |
""")

    # ══ SECTION 3: SIP Calculator ══════════════════════════════════════════
    elif active == "📈 SIP Calculator":
        st.markdown("#### How much would your SIP be worth today?")
        st.caption("Simulates actual unit purchases using real historical NAV each month.")

        sip_c1, sip_c2, sip_c3 = st.columns(3)
        with sip_c1:
            sip_scheme = st.number_input("Scheme Code", min_value=1, value=119598, step=1,
                                         help="Find scheme code in Compare Funds section")
        with sip_c2:
            sip_amount = st.number_input("Monthly SIP Amount (₹)", min_value=100, value=1000, step=100)
        with sip_c3:
            sip_start = st.date_input("SIP Start Date", value=pd.Timestamp.now() - pd.DateOffset(years=3))

        if st.button("📊 Calculate SIP Returns"):
            with st.spinner("Fetching NAV history..."):
                try:
                    nav = fetch_nav_history(int(sip_scheme))
                    sip_meta = cached_fund_meta(int(sip_scheme))
                    sip_fund_name = sip_meta.get("name", f"Scheme {sip_scheme}")
                except Exception as e:
                    st.error(f"Could not fetch NAV: {e}")
                    nav = pd.Series(dtype=float)
                    sip_fund_name = f"Scheme {sip_scheme}"

            if nav.empty:
                st.warning("No NAV data for this scheme code.")
            else:
                nav_range = nav[nav.index >= pd.Timestamp(sip_start)]
                if nav_range.empty:
                    st.warning("No NAV data from that start date. Try an earlier date.")
                else:
                    monthly = nav_range.resample("MS").first().dropna()
                    if monthly.empty:
                        monthly = nav_range.resample("ME").first().dropna()
                    records = []
                    total_units = 0.0
                    total_invested = 0.0
                    latest_nav_val = float(nav.iloc[-1])
                    for date, nav_val in monthly.items():
                        units = sip_amount / nav_val
                        total_units += units
                        total_invested += sip_amount
                        records.append({
                            "date": date,
                            "total_invested": round(total_invested, 2),
                            "current_value": round(total_units * latest_nav_val, 2),
                        })
                    sim_df = pd.DataFrame(records)
                    if sim_df.empty:
                        st.warning("Not enough data to simulate.")
                    else:
                        st.markdown(f"**{sip_fund_name}** · Scheme `{sip_scheme}`")
                        final_value = sim_df["current_value"].iloc[-1]
                        final_invested = sim_df["total_invested"].iloc[-1]
                        final_pnl = final_value - final_invested
                        final_pnl_pct = (final_pnl / final_invested * 100) if final_invested > 0 else 0
                        pnl_sign = "+" if final_pnl >= 0 else ""

                        r1, r2, r3, r4 = st.columns(4)
                        r1.metric("Total Invested", format_inr(final_invested))
                        r2.metric("Current Value", format_inr(final_value))
                        r3.metric("Total Gain", format_inr(final_pnl),
                                  delta=f"{pnl_sign}{final_pnl_pct:.1f}%")
                        r4.metric("SIP Months", len(sim_df))

                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=sim_df["date"], y=sim_df["total_invested"],
                            name="Total Invested", line=dict(color="#7B8699", dash="dash"),
                        ))
                        fig.add_trace(go.Scatter(
                            x=sim_df["date"], y=sim_df["current_value"],
                            name="Current Value", line=dict(color="#F5A623"),
                            fill="tonexty", fillcolor="rgba(0,212,170,0.08)",
                        ))
                        fig.update_layout(
                            title=f"SIP Growth — {sip_fund_name} ({sip_scheme})",
                            paper_bgcolor="#0B0F1A", plot_bgcolor="#0B0F1A",
                            font=dict(color="#FFFFFF"),
                            xaxis=dict(gridcolor="#252D42"),
                            yaxis=dict(gridcolor="#252D42", title="₹ Value"),
                            legend=dict(orientation="h", y=1.1),
                            margin=dict(t=50, b=20), height=380,
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        st.caption("Units purchased on first available NAV each month. Current value uses latest NAV.")

    # ══ SECTION 4: Should I Invest? ════════════════════════════════════════
    elif active == "🔍 Should I Invest?":
        st.markdown("#### Get a plain-English verdict on any fund")
        st.caption("Enter scheme code → app scores returns, risk, and fees → gives YES / NO / MAYBE.")

        v_c1, v_c2 = st.columns(2)
        with v_c1:
            verdict_code = st.number_input("Scheme Code", min_value=1, value=119598, step=1,
                                           key="verdict_scheme")
        with v_c2:
            verdict_monthly = st.number_input("Monthly SIP you plan (₹)", min_value=100, value=1000, step=100,
                                              key="verdict_amount")

        if st.button("🔍 Analyse This Fund"):
            with st.spinner("Fetching fund data..."):
                try:
                    nav = fetch_nav_history(int(verdict_code))
                    meta = cached_fund_meta(int(verdict_code))
                except Exception as e:
                    st.error(f"Could not fetch NAV: {e}")
                    nav = pd.Series(dtype=float)
                    meta = {"name": f"Scheme {verdict_code}", "fund_house": "", "scheme_category": ""}

            if nav.empty:
                st.warning("No data found. Check scheme code is correct.")
            else:
                from data.mutual_funds import compute_cagr, compute_sharpe
                from config import MF_EXPENSE_RATIOS
                cagr_3 = compute_cagr(nav, 3)
                cagr_5 = compute_cagr(nav, 5)
                sharpe = compute_sharpe(nav, years=3)
                latest_nav_val = float(nav.iloc[-1])
                expense = MF_EXPENSE_RATIOS.get(int(verdict_code))
                years_of_data = (nav.index[-1] - nav.index[0]).days / 365
                fund_name = meta.get("name", f"Scheme {verdict_code}")
                fund_house = meta.get("fund_house", "")
                fund_category = meta.get("scheme_category", "")

                scores = {}
                if cagr_5 is not None:
                    if cagr_5 >= 15:
                        scores["5yr Returns"] = ("🟢 Excellent", f"{cagr_5:.1f}%/yr — very strong growth")
                    elif cagr_5 >= 10:
                        scores["5yr Returns"] = ("🟡 Good", f"{cagr_5:.1f}%/yr — beats most FDs")
                    else:
                        scores["5yr Returns"] = ("🔴 Weak", f"{cagr_5:.1f}%/yr — below average")
                elif cagr_3 is not None:
                    scores["5yr Returns"] = ("⚪ No 5yr data", "Fund under 5 years old")

                if cagr_3 is not None:
                    if cagr_3 >= 15:
                        scores["3yr Returns"] = ("🟢 Excellent", f"{cagr_3:.1f}%/yr recently")
                    elif cagr_3 >= 10:
                        scores["3yr Returns"] = ("🟡 Good", f"{cagr_3:.1f}%/yr recently")
                    else:
                        scores["3yr Returns"] = ("🔴 Weak", f"{cagr_3:.1f}%/yr — recent performance poor")

                if sharpe is not None:
                    if sharpe >= 1.0:
                        scores["Risk vs Return"] = ("🟢 Excellent", f"Sharpe {sharpe:.2f} — great returns for risk taken")
                    elif sharpe >= 0.5:
                        scores["Risk vs Return"] = ("🟡 Acceptable", f"Sharpe {sharpe:.2f} — reasonable")
                    else:
                        scores["Risk vs Return"] = ("🔴 Poor", f"Sharpe {sharpe:.2f} — too risky for returns given")

                if expense is not None:
                    if expense < 0.5:
                        scores["Annual Fee"] = ("🟢 Very Low", f"{expense}% — more money stays with you")
                    elif expense < 1.0:
                        scores["Annual Fee"] = ("🟡 Acceptable", f"{expense}% — reasonable")
                    else:
                        scores["Annual Fee"] = ("🔴 High", f"{expense}% — check if returns justify fee")
                else:
                    scores["Annual Fee"] = ("⚪ Unknown", "Check on Groww/Zerodha")

                green = sum(1 for v in scores.values() if v[0].startswith("🟢"))
                red = sum(1 for v in scores.values() if v[0].startswith("🔴"))

                if green >= 2 and red == 0:
                    overall = ("✅ YES — Good fund to invest in", "#F5A623")
                    advice = f"Strong performer. ₹{verdict_monthly:,}/month SIP here is a solid choice."
                elif green >= 1 and red == 0:
                    overall = ("✅ YES — Decent fund, worth investing", "#F5A623")
                    advice = f"No red flags. ₹{verdict_monthly:,}/month SIP here is reasonable."
                elif red >= 2:
                    overall = ("❌ NO — Avoid this fund", "#FF4466")
                    advice = "Multiple weak signals. Use Get Recommendation section for better options."
                else:
                    overall = ("⚠️ MAYBE — Mixed signals", "#FFB700")
                    advice = "Some concerns. Compare with top-rated funds before committing."

                st.markdown(f"""
<div style="background:linear-gradient(135deg,#141927,#0D1525);border:2px solid {overall[1]}55;border-radius:14px;padding:1.4rem 1.8rem;margin-bottom:1rem;">
  <div style="color:#7B8699;font-size:0.75rem;text-transform:uppercase;letter-spacing:1px;margin-bottom:0.2rem;">{fund_house}</div>
  <div style="color:#FFFFFF;font-size:1.05rem;font-weight:700;margin-bottom:0.5rem;">{fund_name}</div>
  <div style="color:{overall[1]};font-size:1.4rem;font-weight:700;margin-bottom:0.3rem;">{overall[0]}</div>
  <div style="color:#FFFFFF;font-size:0.9rem;margin-bottom:1rem;">{advice}</div>
  <div style="color:#7B8699;font-size:0.75rem;">Scheme {verdict_code} · {fund_category} · NAV ₹{latest_nav_val:.2f} · {years_of_data:.1f} yrs data</div>
</div>
""", unsafe_allow_html=True)

                for dimension, (rating, explanation) in scores.items():
                    st.markdown(f"""
<div style="background:#141927;border:1px solid #252D42;border-radius:8px;padding:0.7rem 1rem;margin-bottom:0.5rem;display:flex;gap:1rem;align-items:flex-start;">
  <div style="min-width:160px;font-weight:600;color:#FFFFFF;">{dimension}</div>
  <div><span style="font-weight:600;">{rating}</span>
  <span style="color:#7B8699;margin-left:0.5rem;font-size:0.85rem;">{explanation}</span></div>
</div>
""", unsafe_allow_html=True)

                if cagr_5 is not None:
                    r = cagr_5 / 100
                    fv = verdict_monthly * (((1 + r/12)**120 - 1) / (r/12)) * (1 + r/12)
                    invested = verdict_monthly * 120
                    st.info(f"📈 **10-year projection:** ₹{verdict_monthly:,}/month → invested ₹{invested:,.0f} → estimated **₹{fv:,.0f}** (at {cagr_5:.1f}% CAGR)\n\n*Past CAGR assumed to continue. Actual returns may vary.*")

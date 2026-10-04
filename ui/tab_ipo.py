import streamlit as st
import pandas as pd
from datetime import datetime
from utils.cache import cached_ipo_data


def render():
    st.markdown('<p class="section-title">IPO Watch · GMP Tracker</p>', unsafe_allow_html=True)

    with st.spinner("Fetching IPO data (using headless browser — may take ~15s)..."):
        df, error = cached_ipo_data()

    if error:
        st.warning(f"IPO fetch issue: {error}")

    st.caption(f"Source: investorgain.com · Last updated: {datetime.now().strftime('%d %b %Y %H:%M IST')}")

    if df is None or df.empty:
        st.info("No IPO data available.")
        if st.button("🔄 Retry"):
            cached_ipo_data.clear()
            st.rerun()
        return

    # KPI row
    total = len(df.dropna(subset=["name"]))
    positive_gmp = int(df["gmp"].gt(0).sum()) if "gmp" in df.columns else 0
    avg_gmp_pct = df["gmp_pct"].mean() if "gmp_pct" in df.columns else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("Total IPOs", total)
    k2.metric("Positive GMP", positive_gmp)
    k3.metric("Avg GMP%", f"{avg_gmp_pct:.1f}%" if pd.notna(avg_gmp_pct) else "—")

    st.markdown("---")

    # Sort by GMP% descending
    display = df.copy()
    if "gmp_pct" in display.columns:
        display = display.sort_values("gmp_pct", ascending=False, na_position="last")

    display = display.reset_index(drop=True)

    st.dataframe(display, use_container_width=True, height=480)

    st.caption("GMP is indicative only. Not investment advice.")
    if st.button("🔄 Refresh IPO Data"):
        cached_ipo_data.clear()
        st.rerun()

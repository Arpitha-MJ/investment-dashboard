import streamlit as st
from config import CACHE_TTL_STOCKS, CACHE_TTL_MF, CACHE_TTL_IPO
from data.stocks import get_stock_fundamentals, get_eod_prices
from data.mutual_funds import get_top_mf_data, build_curated_category_map, get_all_curated_codes, get_latest_nav_bulk, fetch_fund_meta
from data.ipo import get_ipo_data


@st.cache_data(ttl=CACHE_TTL_STOCKS)
def cached_stock_fundamentals(tickers_tuple: tuple) -> object:
    return get_stock_fundamentals(list(tickers_tuple))


@st.cache_data(ttl=CACHE_TTL_STOCKS)
def cached_eod_prices(tickers_tuple: tuple) -> dict:
    return get_eod_prices(list(tickers_tuple))


@st.cache_data(ttl=CACHE_TTL_MF)
def cached_mf_data() -> object:
    codes = get_all_curated_codes()
    cat_map = build_curated_category_map()
    return get_top_mf_data(codes, cat_map)


@st.cache_data(ttl=CACHE_TTL_IPO)
def cached_ipo_data() -> tuple:
    return get_ipo_data()


@st.cache_data(ttl=CACHE_TTL_MF)
def cached_mf_nav_bulk(scheme_codes_tuple: tuple) -> dict:
    return get_latest_nav_bulk(list(scheme_codes_tuple))


@st.cache_data(ttl=CACHE_TTL_MF)
def cached_fund_meta(scheme_code: int) -> dict:
    return fetch_fund_meta(scheme_code)

import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(
    page_title="Vigilanz-Cockpit",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== MOBILE CSS ====================
st.markdown("""
<style>
    .main { background: #0a0e27; color: #e8eef7; }
    h1 { font-size: 1.75rem; margin-bottom: 0.4rem; }
    .stTabs [data-baseweb="tab"] { font-size: 0.93rem; padding: 10px 12px; }
    .metric-box { background: rgba(255,255,255,0.06); padding: 1rem; border-radius: 12px; margin: 0.5rem 0; }
    .big-number { font-size: 2rem; font-weight: 700; }
    
    @media (max-width: 640px) {
        h1 { font-size: 1.55rem; }
        .big-number { font-size: 1.8rem; }
    }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Vigilanz-Cockpit")
st.caption("Operative Exzellenz • Faire Bewertung")

# ==================== SIDEBAR ====================
with st.sidebar:
    st.header("🔎 Ticker")
    ticker = st.text_input("Aktien-Ticker", value="AVGO", placeholder="z.B. MSFT, NVDA").upper().strip()
    
    st.divider()
    st.markdown("**Schnellzugriff**")
    popular = ["MSFT", "AAPL", "NVDA", "GOOGL", "AMZN", "META"]
    cols = st.columns(3)
    for i, t in enumerate(popular):
        with cols[i % 3]:
            if st.button(t, use_container_width=True):
                ticker = t
                st.rerun()

# ==================== DATA LOADING ====================
if ticker:
    with st.spinner(f"Lade {ticker}..."):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="5y")
            
            if hist.empty:
                st.error("Keine Daten gefunden.")
                st.stop()

            current_price = hist['Close'].iloc[-1]
            company_name = info.get('longName', ticker)
            sector = info.get('sector', 'Technology')

            fcf_yield = (info.get('freeCashflow', 0) / info.get('marketCap', 1) * 100) if info.get('marketCap', 1) > 0 else 0
            rev_growth = info.get('revenueGrowth', 0) * 100
            rule_of_40 = rev_growth + fcf_yield
            gross_margin = info.get('grossMargins', 0) * 100
            trailing_pe = info.get('trailingPE', 0)
            forward_pe = info.get('forwardPE', trailing_pe)
            pe_to_use = forward_pe if forward_pe > 0 else trailing_pe
            debt_to_equity = (info.get('debtToEquity', 0) / 100) if info.get('debtToEquity', 0) > 10 else info.get('debtToEquity', 0)
            beta = info.get('beta', 1.0)
            shares_outstanding = info.get('sharesOutstanding', 0) / 1_000_000

        except Exception as e:
            st.error(f"Fehler: {e}")
            st.stop()

    # ==================== SCORE ====================
    score = 0
    score += 18 if rule_of_40 >
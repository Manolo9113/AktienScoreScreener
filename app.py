import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

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
st.caption("Operative Exzellenz • Faire Bewertung • Langfristige Qualität")

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

        except Exception as e:
            st.error(f"Fehler: {e}")
            st.stop()

    # ==================== SCORE ====================
    score = 0
    score += 18 if rule_of_40 > 40 else 6
    score += 12 if fcf_yield > 3 else 4
    score += 10 if gross_margin > 55 else 5
    score += 5 if rule_of_40 > 50 else 0

    if pe_to_use > 65: score -= 16
    elif pe_to_use > 45: score -= 9

    score -= 8 if debt_to_equity > 2.0 else 0
    score -= 7 if beta > 1.6 else 0
    score = max(0, min(score, 45))

    status = "🚀 ELITE-QUALITÄT" if score >= 36 else "✅ Gute Qualität" if score >= 28 else "🟡 Vorsicht" if score >= 18 else "🔴 Erhebliche Bedenken"
    color = "green" if score >= 28 else "orange" if score >= 18 else "red"

    # ==================== TABS ====================
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Überblick", 
        "📈 Growth Chart", 
        "💰 Finanzentwicklung", 
        "📋 Bilanz & Struktur", 
        "⚖️ Bewertung & Risiko"
    ])

    # ==================== TAB 1: ÜBERBLICK ====================
    with tab1:
        st.subheader(f"{company_name} ({ticker})")
        st.caption(f"Sektor: {sector}")

        st.markdown(f"""
        <div style="background:#1a2338; padding:1.4rem; border-radius:14px; text-align:center; border:2px solid {'#22c55e' if color=='green' else '#f97316' if color=='orange' else '#ef4444'}">
            <h2 style="margin:0; color:{'#22c55e' if color=='green' else '#f97316' if color=='orange' else '#ef4444'}">{score}/45</h2>
            <p style="margin:0.4rem 0 0 0; font-size:1.1rem;">{status}</p>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Rule of 40", f"{round(rule_of_40, 1)}%")
        with c2: st.metric("FCF Yield", f"{round(fcf_yield, 1)}%")
        with c3: st.metric("Forward P/E", f"{round(pe_to_use, 1)}" if pe_to_use > 0 else "N/A")

    # ==================== TAB 2: GROWTH CHART ====================
    with tab2:
        st.subheader("📈 5-Jahres-Growth Chart")
        hist['EMA200'] = hist['Close'].rolling(window=200).mean()
        last_ema = hist['EMA200'].iloc[-1] if not pd.isna(hist['EMA200'].iloc[-1]) else current_price

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='Kurs', line=dict(color='#60a5fa', width=2.5)))
        fig.add_trace(go.Scatter(x=hist.index, y=hist['
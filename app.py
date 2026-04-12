import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Vigilanz-Cockpit",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"   # Für Handy besser
)

# ====================== MOBILE-FRIENDLY CSS ======================
st.markdown("""
<style>
    .main { background: #0a0e27; color: #e8eef7; }
    .stTabs [data-baseweb="tab"] { font-size: 0.95rem; padding: 10px 16px; }
    h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
    .metric-label { font-size: 0.95rem; }
    .big-number { font-size: 2.2rem; font-weight: 700; }
    
    @media (max-width: 640px) {
        h1 { font-size: 1.6rem; }
        .big-number { font-size: 1.9rem; }
        .stTabs [data-baseweb="tab"] { padding: 8px 12px; font-size: 0.9rem; }
    }
</style>
""", unsafe_allow_html=True)

# ====================== TITLE ======================
st.title("🛡️ Vigilanz-Cockpit")
st.caption("Qualitäts-Check für langfristige Investments")

# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("🔎 Ticker")
    ticker = st.text_input("Aktien-Ticker", value="AVGO", placeholder="z.B. MSFT, AAPL, NVDA").upper().strip()
    
    st.divider()
    st.markdown("**Schnellzugriff**")
    popular = ["MSFT", "AAPL", "NVDA", "GOOGL", "AMZN", "META", "V", "MA"]
    cols = st.columns(4)
    for i, t in enumerate(popular):
        with cols[i % 4]:
            if st.button(t, use_container_width=True):
                ticker = t
                st.rerun()

# ====================== DATA LOADING ======================
if ticker:
    with st.spinner(f"Lade {ticker}..."):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="5y")
            
            if hist.empty:
                st.error("Keine Daten gefunden. Bitte anderen Ticker probieren.")
                st.stop()
                
            current_price = hist['Close'].iloc[-1]
            company_name = info.get('longName', ticker)
            sector = info.get('sector', 'Technology')
            
            # Wichtige Kennzahlen
            fcf = info.get('freeCashflow', 0)
            market_cap = info.get('marketCap', 1)
            fcf_yield = (fcf / market_cap * 100) if market_cap > 0 else 0
            rev_growth = info.get('revenueGrowth', 0) * 100
            rule_of_40 = rev_growth + fcf_yield
            gross_margin = info.get('grossMargins', 0) * 100
            trailing_pe = info.get('trailingPE', 0)
            forward_pe = info.get('forwardPE', trailing_pe)
            pe_to_use = forward_pe if forward_pe > 0 else trailing_pe
            debt_to_equity = info.get('debtToEquity', 0) / 100 if info.get('debtToEquity', 0) > 10 else info.get('debtToEquity', 0)
            beta = info.get('beta', 1.0)
            
        except Exception as e:
            st.error(f"Fehler beim Laden von {ticker}: {e}")
            st.stop()

    # ====================== SCORE ======================
    score = 0
    score += 18 if rule_of_40 > 40 else 6
    score += 12 if fcf_yield > 3 else 3
    score += 10 if gross_margin > 55 else 5
    score += 5 if rule_of_40 > 50 else 0
    
    if pe_to_use > 65:
        score -= 18
    elif pe_to_use > 45:
        score -= 10
    # keine Strafe unter 45
    
    score -= 8 if debt_to_equity > 2.0 else 0
    score -= 7 if beta > 1.6 else 0
    score = max(0, min(score, 45))

    # Interpretation
    if score >= 36:
        interpretation = "🚀 ELITE-QUALITÄT"
        color = "green"
    elif score >= 28:
        interpretation = "✅ Gute Qualität"
        color = "green"
    elif score >= 18:
        interpretation = "🟡 Vorsicht"
        color = "orange"
    else:
        interpretation = "🔴 Erhebliche Bedenken"
        color = "red"

    # ====================== DISPLAY ======================
    st.subheader(f"{company_name} ({ticker})")
    st.caption(f"Sektor: {sector}")

    # Score Box
    st.markdown(f"""
    <div style="background:#1a2338; padding:1.2rem; border-radius:12px; text-align:center; border:2px solid {'#22c55e' if color=='green' else '#f97316' if color=='orange' else '#ef4444'}">
        <h2 style="margin:0; color:{'#22c55e' if color=='green' else '#f97316' if color=='orange' else '#ef4444'}">
            {score}/45
        </h2>
        <p style="margin:0.3rem 0 0 0; font-size:1.1rem;">{interpretation}</p>
    </div>
    """, unsafe_allow_html=True)

    # Schnell-Metriken
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Rule of 40", f"{round(rule_of_40, 1)}%", "stark" if rule_of_40 > 40 else "schwach")
    with col2:
        st.metric("FCF Yield", f"{round(fcf_yield, 1)}%")
    with col3:
        st.metric("Forward P/E", f"{round(forward_pe, 1)}" if forward_pe > 0 else "N/A")

    # ====================== CHART (Growth Style) ======================
    st.subheader("📈 5-Jahres-Chart mit Zonen")
    
    hist['EMA200'] = hist['Close'].rolling(window=200).mean()
    last_ema = hist['EMA200'].iloc[-1] if not pd.isna(hist['EMA200'].iloc[-1]) else current_price

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='Kurs', line=dict(color='#60a5fa', width=2.5)))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA200'], name='EMA 200', line=dict(color='#fbbf24', dash='dot')))

    # Zonen
    fig.add_hrect(y0=0, y1=last_ema, fillcolor="rgba(34,197,94,0.15)", line_width=0, annotation_text="🟢 Kaufzone")
    fig.add_hrect(y0=last_ema, y1=hist['Close'].max()*1.3, fillcolor="rgba(239,68,68,0.15)", line_width=0, annotation_text="🔴 Zu teuer")

    fig.update_layout(
        height=420,
        template="plotly_dark",
        yaxis_type="log",
        hovermode="x unified",
        margin=dict(t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption("🟢 Unter EMA 200 = potenzielle Einstiegszone | 🔴 Über EMA 200 = teuer")

    # ====================== FOOTER ======================
    st.caption("Daten von Yahoo Finance • Keine Anlageberatung • Nur zu Informationszwecken")
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(
    page_title="Aktien-Tool Bäumer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== MOBILE CSS ====================
st.markdown("""
<style>
    .main { background: #0a0e27; color: #e8eef7; }
    h1 { font-size: 1.8rem; margin-bottom: 0.3rem; }
    .stTabs [data-baseweb="tab"] { font-size: 0.95rem; padding: 10px 14px; }
    .metric-box { background: rgba(255,255,255,0.06); padding: 1rem; border-radius: 12px; margin: 0.5rem 0; }
    .big-number { font-size: 2.1rem; font-weight: 700; }
    
    @media (max-width: 640px) {
        h1 { font-size: 1.6rem; }
        .big-number { font-size: 1.85rem; }
    }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Aktien-Tool Bäumer")
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
                st.error("Keine Kursdaten gefunden. Bitte anderen Ticker probieren.")
                st.stop()

            current_price = float(hist['Close'].iloc[-1])
            company_name = info.get('longName', ticker)
            sector = info.get('sector', 'Technology')

            fcf_yield = (info.get('freeCashflow', 0) / info.get('marketCap', 1) * 100) if info.get('marketCap', 1) > 0 else 0
            rev_growth = info.get('revenueGrowth', 0) * 100
            rule_of_40 = rev_growth + fcf_yield
            gross_margin = info.get('grossMargins', 0) * 100
            trailing_pe = info.get('trailingPE', 0) or 0
            forward_pe = info.get('forwardPE', trailing_pe) or 0
            pe_to_use = forward_pe if forward_pe > 0 else trailing_pe
            debt_to_equity = (info.get('debtToEquity', 0) / 100) if info.get('debtToEquity', 0) > 10 else info.get('debtToEquity', 0) or 0
            beta = info.get('beta', 1.0) or 1.0
            shares_outstanding = (info.get('sharesOutstanding', 0) or 0) / 1_000_000

        except Exception as e:
            st.error(f"Fehler beim Laden von {ticker}: {str(e)[:100]}")
            st.stop()

    # ==================== SCORE ====================
    score = 0
    if rule_of_40 > 40:
        score += 18
    else:
        score += 6

    if fcf_yield > 3:
        score += 12
    else:
        score += 4

    if gross_margin > 55:
        score += 10
    else:
        score += 5

    if rule_of_40 > 50:
        score += 5

    if pe_to_use > 65:
        score -= 16
    elif pe_to_use > 45:
        score -= 9

    if debt_to_equity > 2.0:
        score -= 8
    if beta > 1.6:
        score -= 7

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

    with tab1:
        st.subheader(f"{company_name} ({ticker})")
        st.caption(f"Sektor: {sector}")

        st.markdown(f"""
        <div style="background:#1a2338; padding:1.5rem; border-radius:14px; text-align:center; border:2px solid {'#22c55e' if color=='green' else '#f97316' if color=='orange' else '#ef4444'}">
            <h2 style="margin:0; color:{'#22c55e' if color=='green' else '#f97316' if color=='orange' else '#ef4444'}">{score}/45</h2>
            <p style="margin:0.4rem 0 0 0; font-size:1.15rem;">{status}</p>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Rule of 40", f"{round(rule_of_40, 1)}%")
        with c2: st.metric("FCF Yield", f"{round(fcf_yield, 1)}%")
        with c3: st.metric("Forward P/E", f"{round(pe_to_use, 1)}" if pe_to_use > 0 else "N/A")

    with tab2:
        st.subheader("📈 5-Jahres-Growth Chart")
        hist['EMA200'] = hist['Close'].rolling(window=200).mean()
        last_ema = hist['EMA200'].iloc[-1] if not pd.isna(hist['EMA200'].iloc[-1]) else current_price

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='Kurs', line=dict(color='#60a5fa', width=2.5)))
        fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA200'], name='EMA 200', line=dict(color='#fbbf24', dash='dot')))

        fig.add_hrect(y0=0, y1=last_ema, fillcolor="rgba(34,197,94,0.18)", line_width=0, annotation_text="🟢 Kaufzone")
        fig.add_hrect(y0=last_ema, y1=hist['Close'].max()*1.35, fillcolor="rgba(239,68,68,0.18)", line_width=0, annotation_text="🔴 Zu teuer")

        fig.update_layout(height=460, template="plotly_dark", yaxis_type="log", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        st.caption("🟢 Unter EMA 200 = Kaufzone | 🔴 Über EMA 200 = Zu teuer")

    with tab3:
        st.subheader("💰 Finanzentwicklung")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Oper. Cashflow", f"${info.get('operatingCashflow', 0)/1e9:.1f} Mrd")
            st.metric("Free Cash Flow", f"${info.get('freeCashflow', 0)/1e9:.1f} Mrd")
        with c2:
            st.metric("Gewinn je Aktie", f"${info.get('trailingEps', 0):.2f}")
            st.metric("Umsatz je Aktie", "N/A")

    with tab4:
        st.subheader("📋 Bilanz & Struktur")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Bruttomarge", f"{round(gross_margin, 1)}%")
            st.metric("Debt/Equity", f"{round(debt_to_equity, 2)}×")
        with c2:
            st.metric("Beta", f"{round(beta, 2)}")
            st.metric("Aktienanzahl", f"{shares_outstanding:.1f} Mio" if shares_outstanding > 0 else "N/A")

        st.markdown(f"**[Zur originalen Bilanz auf Yahoo Finance](https://finance.yahoo.com/quote/{ticker}/balance-sheet)**", unsafe_allow_html=True)

    with tab5:
        st.subheader("⚖️ Bewertung & Risiko")
        st.metric("Trailing P/E", f"{round(trailing_pe, 1)}" if trailing_pe > 0 else "N/A")
        st.metric("Forward P/E", f"{round(forward_pe, 1)}" if forward_pe > 0 else "N/A")
        st.metric("Branchen-typisch", "25–35" if "Technology" in sector else "15–25")

        if pe_to_use > 50:
            st.warning("Hohes KGV → Das Narrativ muss perfekt bleiben")
        else:
            st.success("Bewertung im vernünftigen Bereich")

    st.caption("Daten von Yahoo Finance • Keine Anlageberatung")
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Vigilanz-Cockpit", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
.main { background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 100%); }
.header-title {
    background: linear-gradient(90deg, #00ff9d 0%, #00d4ff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 2.5em;
    font-weight: 800;
}
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Vigilanz-Cockpit")

# Sidebar
with st.sidebar:
    st.header("Ticker eingeben")
    ticker = st.text_input("Ticker (z.B. MSFT, AAPL):", "MSFT").upper().strip()

if not ticker:
    st.error("Bitte einen Ticker eingeben")
    st.stop()

# Laden
with st.spinner(f"Lade {ticker}..."):
    try:
        # Download direkt
        data = yf.download(ticker, start="2020-01-01", progress=False)
        
        if data.empty:
            st.error(f"❌ Keine Daten für {ticker}")
            st.stop()
        
        # Ticker Info
        stock = yf.Ticker(ticker)
        info = stock.info
        
    except Exception as e:
        st.error(f"❌ Fehler: {str(e)[:100]}")
        st.stop()

# Basis-Daten
current_price = data['Close'].iloc[-1]
company_name = info.get('longName', ticker)
sector = info.get('sector', 'N/A')

st.markdown(f"### {company_name} ({ticker}) - {sector}")
st.metric("Aktueller Kurs", f"${round(current_price, 2)}")

# Metriken
st.subheader("📊 Kennzahlen")

col1, col2, col3, col4 = st.columns(4)

with col1:
    pe = info.get('trailingPE', 0)
    st.metric("KGV", f"{round(pe, 1)}" if pe > 0 else "N/A")

with col2:
    fcf = info.get('freeCashflow', 0)
    market_cap = info.get('marketCap', 1)
    fcf_yield = (fcf / market_cap * 100) if market_cap > 0 else 0
    st.metric("FCF Yield %", f"{round(fcf_yield, 1)}%")

with col3:
    debt_eq = info.get('debtToEquity', 0)
    st.metric("Debt/Equity", f"{round(debt_eq, 2)}")

with col4:
    beta = info.get('beta', 1.0)
    st.metric("Beta", f"{round(beta, 2)}")

# Chart
st.subheader("📈 Chart")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=data.index,
    y=data['Close'],
    name='Kurs',
    line=dict(color='#00ff9d', width=2)
))

# EMA
ema_200 = data['Close'].rolling(200).mean()
fig.add_trace(go.Scatter(
    x=data.index,
    y=ema_200,
    name='EMA 200',
    line=dict(color='#ff9500', dash='dot')
))

fig.update_layout(
    template="plotly_dark",
    height=400,
    plot_bgcolor='#0f1419',
    paper_bgcolor='#0f1419'
)

st.plotly_chart(fig, use_container_width=True)

# Info
st.markdown(f"""
**Stand:** {datetime.now().strftime('%d.%m.%Y %H:%M')}

⚠️ Keine Anlageberatung
""")

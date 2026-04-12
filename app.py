import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import time

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

# --- AGGRESSIVE CACHING ---
@st.cache_data(ttl=86400)
def get_stock_data(ticker):
    """Hole Daten mit Ratelimit-Handling"""
    ticker = ticker.strip().upper()
    
    try:
        st.info(f"⏳ Lade {ticker}... (kann 10 Sekunden dauern)")
        
        for attempt in range(3):
            try:
                data = yf.download(
                    ticker, 
                    start="2020-01-01",
                    progress=False,
                    threads=False
                )
                
                if not data.empty:
                    break
                    
            except Exception as e:
                if "429" in str(e) or "Too Many" in str(e):
                    wait = 5 * (attempt + 1)
                    st.warning(f"⏳ Ratelimit - warte {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        
        if data.empty:
            return None, None
        
        time.sleep(2)
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return data, info
        
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Too Many" in error_msg:
            st.error("""
            ❌ **Zu viele Anfragen an Yahoo Finance**
            
            → Warte 5 Minuten und versuche es erneut
            → Oder probiere einen anderen Ticker
            """)
        else:
            st.error(f"❌ Fehler: {error_msg[:100]}")
        
        return None, None

# Sidebar
with st.sidebar:
    st.header("🔎 Ticker")
    
    popular = {
        "MSFT – Microsoft": "MSFT",
        "AAPL – Apple": "AAPL",
        "GOOGL – Google": "GOOGL",
        "AMZN – Amazon": "AMZN",
        "TSLA – Tesla": "TSLA",
        "NVDA – NVIDIA": "NVDA",
        "META – Meta": "META",
        "Eigener Ticker": ""
    }
    
    choice = st.selectbox("Wähle einen Ticker:", list(popular.keys()))
    
    if choice == "Eigener Ticker":
        ticker = st.text_input("Gib Ticker ein:", "MSFT").upper().strip()
    else:
        ticker = popular[choice]

if not ticker:
    st.error("Bitte einen Ticker eingeben")
    st.stop()

# --- DATEN LADEN ---
data, info = get_stock_data(ticker)

if data is None or info is None:
    st.stop()

# --- BASIS-METRIKEN ---
current_price = data['Close'].iloc[-1]
company_name = info.get('longName', ticker)
sector = info.get('sector', 'N/A')

st.markdown(f"### {company_name} ({ticker})")
st.caption(f"Sektor: {sector}")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("💰 Kurs", f"${round(current_price, 2)}")
with col2:
    market_cap = info.get('marketCap', 0)
    st.metric("📊 Marktcap", f"${round(market_cap / 1e9, 1)}B")
with col3:
    pe = info.get('trailingPE', 0)
    st.metric("📈 KGV", f"{round(pe, 1)}" if pe > 0 else "N/A")

# --- KENNZAHLEN ---
st.subheader("📊 Metriken")

m1, m2, m3, m4 = st.columns(4)

with m1:
    pe = info.get('trailingPE', 0)
    st.metric("Trailing P/E", f"{round(pe, 1)}" if pe > 0 else "N/A")

with m2:
    fcf = info.get('freeCashflow', 0)
    market_cap = info.get('marketCap', 1)
    fcf_yield = (fcf / market_cap * 100) if market_cap > 0 else 0
    st.metric("FCF Yield", f"{round(fcf_yield, 1)}%")

with m3:
    debt_eq = info.get('debtToEquity', 0)
    st.metric("Debt/Equity", f"{round(debt_eq, 2)}")

with m4:
    beta = info.get('beta', 1.0)
    st.metric("Beta", f"{round(beta, 2)}")

# Erweiterte Metriken
e1, e2, e3, e4 = st.columns(4)

with e1:
    gm = info.get('grossMargins', 0)
    st.metric("Gross Margin", f"{round(gm * 100, 1)}%" if gm > 0 else "N/A")

with e2:
    rg = info.get('revenueGrowth', 0)
    st.metric("Revenue Growth", f"{round(rg * 100, 1)}%" if rg > 0 else "N/A")

with e3:
    eps = info.get('trailingEps', 0)
    st.metric("EPS", f"${round(eps, 2)}" if eps > 0 else "N/A")

with e4:
    div = info.get('dividendRate', 0)
    st.metric("Dividend", f"{round(div, 2)}%" if div > 0 else "N/A")

# --- CHART ---
st.subheader("📈 Chart (5 Jahre)")

try:
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['Close'],
        name='Kurs',
        line=dict(color='#00ff9d', width=2)
    ))
    
    ema_200 = data['Close'].rolling(200).mean()
    fig.add_trace(go.Scatter(
        x=data.index,
        y=ema_200,
        name='EMA 200',
        line=dict(color='#ff9500', dash='dot', width=1.5),
        opacity=0.7
    ))
    
    ema_50 = data['Close'].rolling(50).mean()
    fig.add_trace(go.Scatter(
        x=data.index,
        y=ema_50,
        name='EMA 50',
        line=dict(color='#00d4ff', dash='dash', width=1),
        opacity=0.7
    ))
    
    fig.update_layout(
        template="plotly_dark",
        height=400,
        hovermode='x unified',
        plot_bgcolor='#0f1419',
        paper_bgcolor='#0f1419',
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
except Exception as e:
    st.warning(f"Chart konnte nicht geladen werden: {str(e)[:50]}")

# --- ANALYSE ---
st.subheader("⚖️ Analyse")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("**Bewertung:**")
    pe = info.get('trailingPE', 0)
    if pe > 50:
        st.error("🔴 Teuer (P/E > 50)")
    elif pe > 30:
        st.warning("🟡 Moderat teuer")
    else:
        st.success("🟢 Fair bewertet")

with col_b:
    st.markdown("**Schulden:**")
    de = info.get('debtToEquity', 0)
    if de > 2.0:
        st.error("🔴 Hohe Schulden")
    elif de > 1.0:
        st.warning("🟡 Moderate Schulden")
    else:
        st.success("🟢 Niedrige Schulden")

st.divider()
st.caption(f"📊 Daten: Yahoo Finance | {datetime.now().strftime('%d.%m.%Y %H:%M')}")
st.caption("⚠️ Keine Anlageberatung")

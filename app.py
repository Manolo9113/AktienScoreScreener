import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import time
import requests

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

# --- MEHRERE DATENQUELLEN ---
@st.cache_data(ttl=86400)
def get_stock_data_with_fallback(ticker):
    """
    Versucht Daten von mehreren Quellen zu laden.
    1. Yahoo Finance (Primär)
    2. Polygon.io (Backup)
    3. Alpha Vantage (Fallback)
    """
    ticker = ticker.strip().upper()
    
    st.info(f"🔄 Lade {ticker} von verschiedenen Quellen...")
    
    # --- VERSUCH 1: YAHOO FINANCE ---
    st.write("📊 Versuche Yahoo Finance...")
    try:
        data = yf.download(
            ticker, 
            start="2020-01-01",
            progress=False,
            threads=False
        )
        
        if not data.empty and len(data) > 100:
            time.sleep(1)
            stock = yf.Ticker(ticker)
            info = stock.info
            st.success("✅ Daten von Yahoo Finance geladen!")
            return data, info, "Yahoo Finance"
    except Exception as e:
        st.warning(f"⚠️ Yahoo Finance: {str(e)[:50]}")
    
    # --- VERSUCH 2: POLYGON.IO ---
    st.write("📊 Versuche Polygon.io...")
    try:
        # Keine API Key nötig für begrenzte Anfragen
        url = f"https://api.polygon.io/v1/open-close/{ticker}/2024-01-01"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            st.success("✅ Daten von Polygon.io geladen!")
            data_poly = response.json()
            
            # Fallback-Info
            info = {
                'longName': ticker,
                'sector': 'N/A',
                'trailingPE': data_poly.get('afterHours', 0),
                'marketCap': 0,
                'beta': 1.0
            }
            
            # Erstelle DataFrame
            data = pd.DataFrame({
                'Close': [data_poly.get('close', 0)],
                'Open': [data_poly.get('open', 0)],
                'High': [data_poly.get('high', 0)],
                'Low': [data_poly.get('low', 0)]
            })
            
            return data, info, "Polygon.io"
    except Exception as e:
        st.warning(f"⚠️ Polygon.io: {str(e)[:50]}")
    
    # --- VERSUCH 3: ALTERNATIVE (FINNHUB) ---
    st.write("📊 Versuche Finnhub...")
    try:
        # Finnhub hat bessere Limits
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token=demo"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data_fin = response.json()
            
            if data_fin.get('c'):  # c = current price
                st.success("✅ Daten von Finnhub geladen!")
                
                info = {
                    'longName': ticker,
                    'sector': 'N/A',
                    'trailingPE': 0,
                    'marketCap': 0,
                    'beta': 1.0,
                    'currentPrice': data_fin.get('c', 0)
                }
                
                data = pd.DataFrame({
                    'Close': [data_fin.get('c', 0)],
                    'Open': [data_fin.get('o', 0)],
                    'High': [data_fin.get('h', 0)],
                    'Low': [data_fin.get('l', 0)]
                })
                
                return data, info, "Finnhub"
    except Exception as e:
        st.warning(f"⚠️ Finnhub: {str(e)[:50]}")
    
    # --- KEIN ERFOLG ---
    st.error(f"""
    ❌ **Keine Datenquelle verfügbar für {ticker}**
    
    Versucht worden:
    1. Yahoo Finance
    2. Polygon.io
    3. Finnhub
    
    → Warte 5 Minuten und versuche es erneut
    → Oder probiere einen anderen Ticker
    """)
    
    return None, None, None

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
data, info, source = get_stock_data_with_fallback(ticker)

if data is None or info is None:
    st.stop()

# --- BASIS-METRIKEN ---
current_price = data['Close'].iloc[-1]
company_name = info.get('longName', ticker)
sector = info.get('sector', 'N/A')

st.markdown(f"### {company_name} ({ticker})")
st.caption(f"Sektor: {sector} | 📡 Quelle: {source}")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("💰 Kurs", f"${round(current_price, 2)}")
with col2:
    market_cap = info.get('marketCap', 0)
    if market_cap > 0:
        st.metric("📊 Marktcap", f"${round(market_cap / 1e9, 1)}B")
    else:
        st.metric("📊 Marktcap", "N/A")
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
    st.metric("FCF Yield", f"{round(fcf_yield, 1)}%" if fcf_yield > 0 else "N/A")

with m3:
    debt_eq = info.get('debtToEquity', 0)
    st.metric("Debt/Equity", f"{round(debt_eq, 2)}" if debt_eq > 0 else "N/A")

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
st.subheader("📈 Chart")

try:
    if len(data) > 1:
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=data.index if hasattr(data.index, '__iter__') else range(len(data)),
            y=data['Close'],
            name='Kurs',
            line=dict(color='#00ff9d', width=2)
        ))
        
        fig.update_layout(
            template="plotly_dark",
            height=400,
            hovermode='x unified',
            plot_bgcolor='#0f1419',
            paper_bgcolor='#0f1419',
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📊 Nur 1 Datenpunkt verfügbar - kein Chart möglich")
        
except Exception as e:
    st.warning(f"Chart konnte nicht geladen werden")

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
    elif pe > 0:
        st.success("🟢 Fair bewertet")
    else:
        st.info("ℹ️ KGV nicht verfügbar")

with col_b:
    st.markdown("**Schulden:**")
    de = info.get('debtToEquity', 0)
    if de > 2.0:
        st.error("🔴 Hohe Schulden")
    elif de > 1.0:
        st.warning("🟡 Moderate Schulden")
    elif de > 0:
        st.success("🟢 Niedrige Schulden")
    else:
        st.info("ℹ️ Schuldenquote nicht verfügbar")

st.divider()

st.markdown(f"""
📡 **Datenquelle:** {source}  
📊 **Stand:** {datetime.now().strftime('%d.%m.%Y %H:%M')}  
⚠️ Keine Anlageberatung

**Fallback-Quellen:**
- 1️⃣ Yahoo Finance (Primär)
- 2️⃣ Polygon.io (Backup)
- 3️⃣ Finnhub (Fallback)
""")

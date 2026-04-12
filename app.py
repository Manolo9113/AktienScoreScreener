import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging

# ===== DEBUG MODE =====
DEBUG = True

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Vigilanz-Cockpit 🛡️", page_icon="🛡️", layout="wide")

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

# --- BRANCHEN-SPEZIFISCHE BENCHMARKS ---
SECTOR_BENCHMARKS = {
    "Technology": {
        "pe_range": (20, 35, 50, 80),
        "margin_min": 15,
        "growth_min": 8,
        "debt_max": 1.0,
        "roe_min": 12,
        "fcf_yield_min": 2,
        "emojis": "💻"
    },
    "Software": {
        "pe_range": (25, 40, 60, 100),
        "margin_min": 20,
        "growth_min": 10,
        "debt_max": 0.8,
        "roe_min": 15,
        "fcf_yield_min": 3,
        "emojis": "⚙️"
    },
    "Internet": {
        "pe_range": (20, 35, 50, 80),
        "margin_min": 10,
        "growth_min": 15,
        "debt_max": 1.2,
        "roe_min": 10,
        "fcf_yield_min": 1,
        "emojis": "🌐"
    },
    "Financial Services": {
        "pe_range": (10, 15, 20, 30),
        "margin_min": 15,
        "growth_min": 3,
        "debt_max": 8.0,
        "roe_min": 10,
        "fcf_yield_min": 2,
        "emojis": "🏦"
    },
    "Healthcare": {
        "pe_range": (18, 28, 40, 60),
        "margin_min": 12,
        "growth_min": 5,
        "debt_max": 1.5,
        "roe_min": 12,
        "fcf_yield_min": 2,
        "emojis": "⚕️"
    },
    "Pharmaceuticals": {
        "pe_range": (15, 25, 35, 50),
        "margin_min": 20,
        "growth_min": 3,
        "debt_max": 1.0,
        "roe_min": 15,
        "fcf_yield_min": 2,
        "emojis": "💊"
    },
    "Consumer Cyclical": {
        "pe_range": (12, 18, 25, 40),
        "margin_min": 5,
        "growth_min": 3,
        "debt_max": 2.0,
        "roe_min": 8,
        "fcf_yield_min": 3,
        "emojis": "🛍️"
    },
    "Consumer Defensive": {
        "pe_range": (18, 25, 35, 50),
        "margin_min": 8,
        "growth_min": 2,
        "debt_max": 2.0,
        "roe_min": 10,
        "fcf_yield_min": 3,
        "emojis": "🥬"
    },
    "Industrials": {
        "pe_range": (12, 18, 25, 35),
        "margin_min": 6,
        "growth_min": 3,
        "debt_max": 2.5,
        "roe_min": 10,
        "fcf_yield_min": 2,
        "emojis": "🏭"
    },
    "Energy": {
        "pe_range": (10, 15, 20, 30),
        "margin_min": 10,
        "growth_min": 2,
        "debt_max": 3.0,
        "roe_min": 8,
        "fcf_yield_min": 4,
        "emojis": "⚡"
    },
    "Utilities": {
        "pe_range": (15, 20, 28, 40),
        "margin_min": 8,
        "growth_min": 1,
        "debt_max": 3.0,
        "roe_min": 8,
        "fcf_yield_min": 3,
        "emojis": "💡"
    },
    "Real Estate": {
        "pe_range": (12, 18, 25, 35),
        "margin_min": 5,
        "growth_min": 2,
        "debt_max": 4.0,
        "roe_min": 6,
        "fcf_yield_min": 3,
        "emojis": "🏠"
    },
    "Communication Services": {
        "pe_range": (15, 22, 30, 45),
        "margin_min": 15,
        "growth_min": 3,
        "debt_max": 2.0,
        "roe_min": 10,
        "fcf_yield_min": 2,
        "emojis": "📱"
    },
    "Materials": {
        "pe_range": (10, 15, 20, 30),
        "margin_min": 5,
        "growth_min": 2,
        "debt_max": 2.5,
        "roe_min": 8,
        "fcf_yield_min": 2,
        "emojis": "⛏️"
    }
}

# --- BEWERTUNGS-FUNKTIONEN ---
def get_sector_benchmark(sector):
    """Hole Benchmark für Sektor"""
    if sector in SECTOR_BENCHMARKS:
        return SECTOR_BENCHMARKS[sector]
    return SECTOR_BENCHMARKS["Technology"]

def get_color_for_metric_with_sector(value, metric_type, sector):
    """Intelligente Farbgebung basierend auf Sektor"""
    if value is None or (isinstance(value, (int, float)) and (value <= 0 or np.isnan(value) or np.isinf(value))):
        return "gray", "N/A"
    
    benchmark = get_sector_benchmark(sector)
    
    if metric_type == "pe":
        green, yellow, orange, red = benchmark["pe_range"]
        if value < green:
            return "green", f"Exzellent (unter {green})"
        elif value < yellow:
            return "green", f"Gut ({green}-{yellow})"
        elif value < orange:
            return "yellow", f"Mittel ({yellow}-{orange})"
        elif value < red:
            return "orange", f"Teuer ({orange}-{red})"
        else:
            return "red", f"Überbewertet (über {red})"
    
    elif metric_type == "fcf_yield":
        min_yield = benchmark["fcf_yield_min"]
        if value < min_yield * 0.3:
            return "red", f"Sehr niedrig"
        elif value < min_yield * 0.7:
            return "orange", f"Niedrig (unter {min_yield}%)"
        elif value < min_yield:
            return "yellow", f"Mittel ({min_yield}%)"
        else:
            return "green", f"Gut (über {min_yield}%)"
    
    elif metric_type == "div_yield":
        if value < 1:
            return "yellow", f"Niedrig"
        elif value < 3:
            return "green", f"Attraktiv"
        elif value < 5:
            return "yellow", f"Erhöht"
        else:
            return "orange", f"Sehr hoch"
    
    elif metric_type == "margin":
        min_margin = benchmark["margin_min"]
        if value < min_margin * 0.5:
            return "red", f"Sehr niedrig"
        elif value < min_margin:
            return "orange", f"Niedrig"
        elif value < min_margin * 1.5:
            return "yellow", f"Normal"
        else:
            return "green", f"Überdurchschnittlich"
    
    elif metric_type == "growth":
        min_growth = benchmark["growth_min"]
        if value < 0:
            return "red", "Negativ"
        elif value < min_growth * 0.5:
            return "orange", f"Unter Schnitt"
        elif value < min_growth:
            return "yellow", f"Unter Erwartung"
        elif value < min_growth * 2:
            return "green", f"Gut"
        else:
            return "green", f"Außergewöhnlich"
    
    elif metric_type == "debt":
        max_debt = benchmark["debt_max"]
        if value < max_debt * 0.5:
            return "green", f"Sehr niedrig"
        elif value < max_debt:
            return "green", f"Gesund"
        elif value < max_debt * 1.5:
            return "yellow", f"Erhöht"
        else:
            return "red", f"Hoch"
    
    elif metric_type == "roe":
        min_roe = benchmark["roe_min"]
        if value < min_roe * 0.5:
            return "red", f"Schwach"
        elif value < min_roe:
            return "orange", f"Unter Branche"
        elif value < min_roe * 1.5:
            return "green", f"Gut"
        else:
            return "green", f"Hervorragend"
    
    return "gray", "N/A"

def color_box(value, color, description=""):
    """Erstelle einen farbigen Box für Metriken"""
    colors = {
        "green": "#22c55e",
        "yellow": "#eab308",
        "orange": "#f97316",
        "red": "#ef4444",
        "gray": "#6b7280"
    }
    
    bg_colors = {
        "green": "rgba(34, 197, 94, 0.15)",
        "yellow": "rgba(234, 179, 8, 0.15)",
        "orange": "rgba(249, 115, 22, 0.15)",
        "red": "rgba(239, 68, 68, 0.15)",
        "gray": "rgba(107, 114, 128, 0.1)"
    }
    
    emojis = {
        "green": "🟢",
        "yellow": "🟡",
        "orange": "🟠",
        "red": "🔴",
        "gray": "⚪"
    }
    
    desc_text = f"<br><small style='color: #999; font-size: 0.85em;'>{description}</small>" if description else ""
    
    return f'<div style="background: {bg_colors[color]}; border-left: 4px solid {colors[color]}; padding: 12px; border-radius: 6px; margin: 8px 0;"><span style="color: {colors[color]}; font-weight: bold;">{emojis[color]} {value}</span>{desc_text}</div>'

def safe_get_float(dictionary, key, default=0):
    """Sichere Abfrage von Floats"""
    try:
        value = dictionary.get(key, default)
        if value is None:
            return default
        value = float(value)
        if np.isnan(value) or np.isinf(value):
            return default
        return value
    except:
        return default

# --- DATENLADUNG MIT DEBUG ---
@st.cache_data(ttl=3600)
def get_stock_data_extended(ticker):
    """Hole Daten mit Preis + FCF + Dividenden + Bewertung"""
    ticker = ticker.strip().upper()
    
    try:
        st.info(f"⏳ Lade {ticker}... (Preis, FCF, Dividenden, Bewertung)")
        
        # Preis-Daten (10 Jahre)
        for attempt in range(3):
            try:
                data = yf.download(
                    ticker, 
                    start="2014-01-01",
                    progress=False,
                    threads=False
                )
                
                if not data.empty:
                    if DEBUG:
                        st.success(f"✅ Preis-Daten geladen: {len(data)} Zeilen")
                    break
                    
            except Exception as e:
                if "429" in str(e) or "Too Many" in str(e):
                    wait = 5 * (attempt + 1)
                    st.warning(f"⏳ Ratelimit - warte {wait}s...")
                    time.sleep(wait)
                else:
                    if DEBUG:
                        st.error(f"❌ Fehler Versuch {attempt + 1}: {str(e)[:100]}")
                    raise
        
        if data is None or data.empty:
            st.error("❌ Keine Preis-Daten!")
            if DEBUG:
                st.write("data ist:", data)
            return None, None, None, None
        
        time.sleep(1)
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if DEBUG:
            st.info(f"✅ Info geladen: {len(info)} Keys")
            st.write(f"Sector: {info.get('sector', 'N/A')}")
            st.write(f"Market Cap: ${info.get('marketCap', 'N/A')}")
            st.write(f"Trailing PE: {info.get('trailingPE', 'N/A')}")
        
        # Cash Flow
        cashflow = None
        try:
            cashflow = stock.cashflow
            if cashflow is not None and not cashflow.empty:
                if DEBUG:
                    st.info(f"✅ Cashflow geladen: {cashflow.shape}")
        except Exception as e:
            if DEBUG:
                st.warning(f"⚠️ Cashflow nicht verfügbar: {str(e)[:50]}")
        
        # Dividenden
        dividends = None
        try:
            dividends = stock.dividends
            if dividends is not None and not dividends.empty:
                if DEBUG:
                    st.info(f"✅ Dividenden geladen: {len(dividends)} Einträge")
        except Exception as e:
            if DEBUG:
                st.warning(f"⚠️ Dividenden nicht verfügbar: {str(e)[:50]}")
        
        return data, info, cashflow, dividends
        
    except Exception as e:
        st.error(f"❌ Kritischer Fehler: {str(e)}")
        if DEBUG:
            st.write(f"Full error: {e}")
        return None, None, None, None

# Sidebar
with st.sidebar:
    st.header("🔎 Ticker")
    
    popular = {
        "MSFT – Microsoft (Software)": "MSFT",
        "AAPL – Apple (Tech)": "AAPL",
        "GOOGL – Alphabet (Internet)": "GOOGL",
        "AMZN – Amazon (Internet)": "AMZN",
        "JNJ – Johnson&Johnson (Healthcare)": "JNJ",
        "PG – Procter&Gamble (Consumer)": "PG",
        "XOM – ExxonMobil (Energy)": "XOM",
        "NVDA – NVIDIA (Tech)": "NVDA",
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
data, info, cashflow, dividends = get_stock_data_extended(ticker)

if data is None or info is None:
    st.error("Daten konnten nicht geladen werden")
    st.stop()

# --- BASIS-METRIKEN ---
current_price = data['Close'].iloc[-1] if not data.empty else 0
company_name = info.get('longName', ticker)
sector = info.get('sector', 'Technology')

st.markdown(f"### {company_name} ({ticker})")

col_header1, col_header2, col_header3 = st.columns(3)
with col_header1:
    st.caption(f"🏭 Sektor: {sector}")
with col_header2:
    benchmark = get_sector_benchmark(sector)
    st.caption(f"📊 Benchmark: {benchmark['emojis']}")
with col_header3:
    st.caption(f"📍 Branchengerecht bewertet!")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("💰 Kurs", f"${round(current_price, 2)}")
with col2:
    market_cap = safe_get_float(info, 'marketCap')
    st.metric("📊 Marktcap", f"${round(market_cap / 1e9, 1)}B" if market_cap > 0 else "N/A")
with col3:
    pe = safe_get_float(info, 'trailingPE')
    st.metric("📈 KGV", f"{round(pe, 1)}" if pe > 0 else "N/A")

st.divider()

# --- TABS ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Kennzahlen",
    "📈 Chart",
    "💰 FCF & Dividenden",
    "💎 Bewertung Historisch",
    "💼 Bilanzdaten",
    "⚖️ Risikoanalyse",
    "💵 Cashflow",
    "📋 Details"
])

# TAB 1: KENNZAHLEN
with tab1:
    st.subheader("🎯 Kern-Kennzahlen (Branchenangepasst)")
    
    benchmark = get_sector_benchmark(sector)
    
    st.info(f"""
    📌 **Branche:** {sector}
    
    **Benchmarks:**
    - KGV: {benchmark['pe_range'][1]}-{benchmark['pe_range'][2]} (normal)
    - FCF Yield: {benchmark['fcf_yield_min']}%+ | Bruttomarge: {benchmark['margin_min']}%+
    """)
    
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        pe = safe_get_float(info, 'trailingPE')
        color, desc = get_color_for_metric_with_sector(pe, "pe", sector)
        st.markdown(color_box(f"KGV: {round(pe, 1) if pe > 0 else 'N/A'}", color, desc), unsafe_allow_html=True)
    
    with m2:
        fcf = safe_get_float(info, 'freeCashflow')
        market_cap = safe_get_float(info, 'marketCap', 1)
        fcf_yield = (fcf / market_cap * 100) if market_cap > 0 and fcf > 0 else 0
        color, desc = get_color_for_metric_with_sector(fcf_yield, "fcf_yield", sector)
        st.markdown(color_box(f"FCF Yield: {round(fcf_yield, 1) if fcf_yield > 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    with m3:
        debt_eq = safe_get_float(info, 'debtToEquity')
        color, desc = get_color_for_metric_with_sector(debt_eq, "debt", sector)
        st.markdown(color_box(f"Debt/Equity: {round(debt_eq, 2) if debt_eq > 0 else 'N/A'}", color, desc), unsafe_allow_html=True)
    
    with m4:
        div_yield = safe_get_float(info, 'dividendYield') * 100 if info.get('dividendYield') else 0
        color, desc = get_color_for_metric_with_sector(div_yield, "div_yield", sector)
        st.markdown(color_box(f"Div Yield: {round(div_yield, 2) if div_yield > 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    st.divider()
    st.subheader("📈 Rentabilitäts-Metriken")
    
    r1, r2, r3, r4 = st.columns(4)
    
    with r1:
        gm = safe_get_float(info, 'grossMargins') * 100 if info.get('grossMargins') else 0
        color, desc = get_color_for_metric_with_sector(gm, "margin", sector)
        st.markdown(color_box(f"Gross Margin: {round(gm, 1) if gm > 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    with r2:
        om = safe_get_float(info, 'operatingMargins') * 100 if info.get('operatingMargins') else 0
        color, desc = get_color_for_metric_with_sector(om, "margin", sector)
        st.markdown(color_box(f"Operating Margin: {round(om, 1) if om > 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    with r3:
        pm = safe_get_float(info, 'profitMargins') * 100 if info.get('profitMargins') else 0
        color, desc = get_color_for_metric_with_sector(pm, "margin", sector)
        st.markdown(color_box(f"Profit Margin: {round(pm, 1) if pm > 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    with r4:
        roe = safe_get_float(info, 'returnOnEquity') * 100 if info.get('returnOnEquity') else 0
        color, desc = get_color_for_metric_with_sector(roe, "roe", sector)
        st.markdown(color_box(f"ROE: {round(roe, 1) if roe > 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    st.divider()
    st.subheader("📊 Wachstums-Metriken")
    
    g1, g2, g3, g4 = st.columns(4)
    
    with g1:
        rg = safe_get_float(info, 'revenueGrowth') * 100 if info.get('revenueGrowth') else 0
        color, desc = get_color_for_metric_with_sector(rg, "growth", sector)
        st.markdown(color_box(f"Revenue Growth: {round(rg, 1) if rg != 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    with g2:
        eg = safe_get_float(info, 'earningsGrowth') * 100 if info.get('earningsGrowth') else 0
        color, desc = get_color_for_metric_with_sector(eg, "growth", sector)
        st.markdown(color_box(f"Earnings Growth: {round(eg, 1) if eg != 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    with g3:
        eps = safe_get_float(info, 'trailingEps')
        st.metric("EPS", f"${round(eps, 2)}" if eps > 0 else "N/A")
    
    with g4:
        peg = safe_get_float(info, 'pegRatio')
        peg_color = "green" if 0.5 < peg < 1.5 else "yellow" if peg < 3 else "red"
        st.markdown(color_box(f"PEG Ratio: {round(peg, 2) if peg > 0 else 'N/A'}", peg_color), unsafe_allow_html=True)

# TAB 2: CHART MIT DEBUG
with tab2:
    st.subheader("📈 Preis-Chart (10 Jahre)")
    
    if DEBUG:
        col_debug1, col_debug2, col_debug3 = st.columns(3)
        with col_debug1:
            st.write(f"📊 Data Shape: {data.shape if data is not None else 'None'}")
        with col_debug2:
            st.write(f"📊 Data Empty: {data.empty if data is not None else 'N/A'}")
        with col_debug3:
            st.write(f"📊 Data Dtypes:\n{data.dtypes if data is not None else 'None'}")
    
    try:
        if data is None or data.empty:
            st.error("❌ Keine Daten für Chart vorhanden")
        elif len(data) < 10:
            st.error(f"❌ Zu wenig Daten: {len(data)} Zeilen (brauche 10+)")
        else:
            # Clean data
            data_clean = data[['Close']].copy().dropna()
            
            if DEBUG:
                st.write(f"🧹 Clean data shape: {data_clean.shape}")
                st.write(f"🧹 Last 5 rows:\n{data_clean.tail()}")
            
            if len(data_clean) > 10 and not data_clean['Close'].empty:
                fig = go.Figure()
                
                # Hauptlinie
                fig.add_trace(go.Scatter(
                    x=data_clean.index,
                    y=data_clean['Close'],
                    name='Schlusskurs',
                    line=dict(color='#00ff9d', width=2.5),
                    hovertemplate='<b>Schlusskurs</b><br>%{x|%d.%m.%Y}<br>%{y:.2f} USD<extra></extra>'
                ))
                
                # EMA 200
                ema_200 = data_clean['Close'].rolling(window=200).mean()
                if not ema_200.empty:
                    fig.add_trace(go.Scatter(
                        x=data_clean.index,
                        y=ema_200,
                        name='EMA 200',
                        line=dict(color='#ff9500', dash='dot', width=1.5),
                        opacity=0.8,
                        hovertemplate='<b>EMA 200</b><br>%{x|%d.%m.%Y}<br>%{y:.2f} USD<extra></extra>'
                    ))
                
                # EMA 50
                ema_50 = data_clean['Close'].rolling(window=50).mean()
                if not ema_50.empty:
                    fig.add_trace(go.Scatter(
                        x=data_clean.index,
                        y=ema_50,
                        name='EMA 50',
                        line=dict(color='#00d4ff', dash='dash', width=1.5),
                        opacity=0.8,
                        hovertemplate='<b>EMA 50</b><br>%{x|%d.%m.%Y}<br>%{y:.2f} USD<extra></extra>'
                    ))
                
                fig.update_layout(
                    title=f"📈 {ticker} - 10 Jahre Preisverlauf",
                    xaxis_title="Datum",
                    yaxis_title="Preis (USD)",
                    template="plotly_dark",
                    height=500,
                    hovermode='x unified',
                    plot_bgcolor='#0f1419',
                    paper_bgcolor='#0f1419',
                    font=dict(color='#ccc'),
                    margin=dict(l=50, r=50, t=80, b=50),
                    xaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)'),
                    yaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Info
                last_ema200 = ema_200.iloc[-1] if not pd.isna(ema_200.iloc[-1]) else None
                if last_ema200:
                    if current_price < last_ema200:
                        st.success(f"🟢 KAUFZONE - Preis (${round(current_price, 2)}) unter EMA 200 (${round(last_ema200, 2)})")
                    else:
                        st.warning(f"🔴 TEUER - Preis (${round(current_price, 2)}) über EMA 200 (${round(last_ema200, 2)})")
            else:
                st.error(f"❌ Zu wenig Clean-Daten: {len(data_clean)}")
                if DEBUG:
                    st.write(f"Close Series: {data_clean['Close'].describe()}")
    
    except Exception as e:
        st.error(f"❌ Chart-Fehler: {str(e)}")
        if DEBUG:
            st.write(f"Full error: {e}")
            import traceback
            st.write(traceback.format_exc())

# TAB 3: FCF & DIVIDENDEN
with tab3:
    st.subheader("💰 Free Cashflow & Dividenden Analyse")
    
    col_fcf1, col_fcf2, col_fcf3 = st.columns(3)
    
    with col_fcf1:
        fcf = safe_get_float(info, 'freeCashflow')
        st.metric("Aktueller FCF", f"${round(fcf / 1e9, 2)}B" if fcf > 0 else "N/A")
    
    with col_fcf2:
        market_cap = safe_get_float(info, 'marketCap', 1)
        fcf_yield = (fcf / market_cap * 100) if market_cap > 0 and fcf > 0 else 0
        color, desc = get_color_for_metric_with_sector(fcf_yield, "fcf_yield", sector)
        st.markdown(color_box(f"FCF Yield: {round(fcf_yield, 2) if fcf_yield > 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    with col_fcf3:
        div_yield = safe_get_float(info, 'dividendYield') * 100 if info.get('dividendYield') else 0
        color, desc = get_color_for_metric_with_sector(div_yield, "div_yield", sector)
        st.markdown(color_box(f"Div Yield: {round(div_yield, 2) if div_yield > 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    st.divider()
    
    # FCF HISTORISCH
    if cashflow is not None and not cashflow.empty:
        st.subheader("📊 FCF Trend (10 Jahre)")
        
        try:
            ocf_data = cashflow.loc['Operating Cash Flow'] if 'Operating Cash Flow' in cashflow.index else cashflow.iloc[0]
            capex_data = cashflow.loc['Capital Expenditure'] if 'Capital Expenditure' in cashflow.index else pd.Series()
            
            fcf_hist = ocf_data - capex_data.abs()
            fcf_hist = fcf_hist.sort_index(ascending=True)
            fcf_hist_10y = fcf_hist.tail(10)
            
            if DEBUG:
                st.write(f"FCF Historic data points: {len(fcf_hist_10y)}")
            
            if not fcf_hist_10y.empty and len(fcf_hist_10y) > 0:
                fig_fcf = go.Figure()
                
                years = [d.year for d in fcf_hist_10y.index]
                values = fcf_hist_10y.values / 1e9
                
                fig_fcf.add_trace(go.Bar(
                    x=years,
                    y=values,
                    name='Free Cashflow',
                    marker=dict(
                        color=['#22c55e' if v > 0 else '#ef4444' for v in values]
                    )
                ))
                
                avg_fcf = fcf_hist_10y.mean()
                fig_fcf.add_hline(
                    y=avg_fcf / 1e9,
                    line_dash="dash",
                    line_color="#eab308",
                    annotation_text=f"Ø: ${round(avg_fcf / 1e9, 2)}B",
                    annotation_position="right"
                )
                
                fig_fcf.update_layout(
                    title=f"📊 {ticker} - Free Cashflow (10 Jahre)",
                    xaxis_title="Jahr",
                    yaxis_title="FCF (Milliarden USD)",
                    template="plotly_dark",
                    height=400,
                    plot_bgcolor='#0f1419',
                    paper_bgcolor='#0f1419'
                )
                
                st.plotly_chart(fig_fcf, use_container_width=True)
                
                stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                with stat_col1:
                    st.metric("Letztes Jahr", f"${round(fcf_hist_10y.iloc[-1] / 1e9, 2)}B")
                with stat_col2:
                    st.metric("Durchschnitt", f"${round(avg_fcf / 1e9, 2)}B")
                with stat_col3:
                    st.metric("Minimum", f"${round(fcf_hist_10y.min() / 1e9, 2)}B")
                with stat_col4:
                    st.metric("Maximum", f"${round(fcf_hist_10y.max() / 1e9, 2)}B")
            else:
                st.info("ℹ️ Nicht genug FCF-Historisch verfügbar")
        except Exception as e:
            st.warning(f"⚠️ FCF-Historisch nicht verfügbar: {str(e)[:50]}")
    
    st.divider()
    
    # DIVIDENDEN HISTORISCH
    if dividends is not None and not dividends.empty:
        st.subheader("💵 Dividenden Historisch (10 Jahre)")
        
        dividends_sorted = dividends.sort_index(ascending=True)
        div_10y = dividends_sorted.tail(10)
        
        if DEBUG:
            st.write(f"Dividenden data points: {len(div_10y)}")
        
        if not div_10y.empty:
            fig_div = go.Figure()
            
            years_div = [d.year for d in div_10y.index]
            
            fig_div.add_trace(go.Bar(
                x=years_div,
                y=div_10y.values,
                name='Dividende pro Aktie',
                marker=dict(color='#22c55e')
            ))
            
            avg_div = div_10y.mean()
            fig_div.add_hline(
                y=avg_div,
                line_dash="dash",
                line_color="#eab308",
                annotation_text=f"Ø: ${round(avg_div, 2)}",
                annotation_position="right"
            )
            
            fig_div.update_layout(
                title=f"💵 {ticker} - Dividenden (10 Jahre)",
                xaxis_title="Jahr",
                yaxis_title="Dividende pro Aktie (USD)",
                template="plotly_dark",
                height=400,
                plot_bgcolor='#0f1419',
                paper_bgcolor='#0f1419'
            )
            
            st.plotly_chart(fig_div, use_container_width=True)
            
            div_stat_col1, div_stat_col2, div_stat_col3, div_stat_col4 = st.columns(4)
            
            with div_stat_col1:
                st.metric("Letzte Div", f"${round(div_10y.iloc[-1], 2)}")
            
            with div_stat_col2:
                st.metric("Ø 10 Jahre", f"${round(avg_div, 2)}")
            
            with div_stat_col3:
                if len(div_10y) > 1 and div_10y.iloc[0] > 0:
                    cagr_div = ((div_10y.iloc[-1] / div_10y.iloc[0]) ** (1 / (len(div_10y) - 1)) - 1) * 100
                else:
                    cagr_div = 0
                st.metric("Div CAGR", f"{round(cagr_div, 1)}%")
            
            with div_stat_col4:
                st.metric("Jahre gezahlt", f"{len(div_10y)}")
    else:
        st.info("ℹ️ Keine Dividenden verfügbar")

# TAB 4: BEWERTUNG HISTORISCH
with tab4:
    st.subheader("💎 Bewertung Historisch - KGV & Preis")
    
    st.info(f"""
    📊 **Historische Bewertungs-Analyse:**
    
    Diese Tab zeigt wie die Bewertung (KGV) der Aktie über 10 Jahre variiert hat.
    Hilft zu sehen ob die aktuelle Bewertung günstig oder teuer ist.
    """)
    
    try:
        stock = yf.Ticker(ticker)
        quarterly_financials = stock.quarterly_financials
        
        if DEBUG:
            st.write(f"Quarterly Financials Shape: {quarterly_financials.shape if quarterly_financials is not None else 'None'}")
        
        if quarterly_financials is not None and not quarterly_financials.empty:
            pe_history = []
            
            for i in range(min(32, len(quarterly_financials.columns))):
                try:
                    date = quarterly_financials.columns[i]
                    year = date.year
                    
                    if i + 3 < len(quarterly_financials.columns):
                        net_income_col = quarterly_financials.columns[i:i+4]
                        if 'Net Income' in quarterly_financials.index:
                            ttm = quarterly_financials.loc['Net Income', net_income_col].sum()
                        else:
                            ttm = quarterly_financials.iloc[0, i:i+4].sum()
                        
                        shares = safe_get_float(info, 'sharesOutstanding', 1)
                        if shares > 0 and ttm > 0:
                            eps = ttm / shares
                            
                            price_data = data[data.index.year == year]
                            if not price_data.empty:
                                price = price_data['Close'].iloc[0]
                                pe = price / eps if eps > 0 else 0
                                
                                if pe > 0 and pe < 500:
                                    pe_history.append({
                                        'year': year,
                                        'pe': pe,
                                        'eps': eps,
                                        'price': price
                                    })
                except:
                    continue
            
            if pe_history:
                pe_df = pd.DataFrame(pe_history).drop_duplicates(subset=['year']).sort_values('year')
                
                if DEBUG:
                    st.write(f"PE History records: {len(pe_df)}")
                    st.write(pe_df)
                
                fig_pe = go.Figure()
                
                fig_pe.add_trace(go.Scatter(
                    x=pe_df['year'],
                    y=pe_df['pe'],
                    name='KGV',
                    mode='lines+markers',
                    line=dict(color='#00ff9d', width=2.5),
                    marker=dict(size=8)
                ))
                
                avg_pe = pe_df['pe'].mean()
                fig_pe.add_hline(
                    y=avg_pe,
                    line_dash="dash",
                    line_color="#eab308",
                    annotation_text=f"Ø: {round(avg_pe, 1)}",
                    annotation_position="right"
                )
                
                benchmark_yellow = benchmark["pe_range"][1]
                benchmark_red = benchmark["pe_range"][2]
                
                fig_pe.add_hspan(
                    y0=0, y1=benchmark_yellow,
                    fillcolor="green", opacity=0.1
                )
                fig_pe.add_hspan(
                    y0=benchmark_yellow, y1=benchmark_red,
                    fillcolor="yellow", opacity=0.1
                )
                fig_pe.add_hspan(
                    y0=benchmark_red, y1=max(pe_df['pe'].max() * 1.1, 100),
                    fillcolor="red", opacity=0.1
                )
                
                fig_pe.update_layout(
                    title=f"💎 {ticker} - KGV Historisch",
                    xaxis_title="Jahr",
                    yaxis_title="KGV",
                    template="plotly_dark",
                    height=450,
                    plot_bgcolor='#0f1419',
                    paper_bgcolor='#0f1419',
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_pe, use_container_width=True)
                
                st.markdown("### 📊 KGV Statistiken")
                
                pe_stat_col1, pe_stat_col2, pe_stat_col3, pe_stat_col4 = st.columns(4)
                
                with pe_stat_col1:
                    current_pe = pe_df['pe'].iloc[-1]
                    st.metric("Aktuelles KGV", f"{round(current_pe, 1)}")
                
                with pe_stat_col2:
                    st.metric("Ø Historisch", f"{round(avg_pe, 1)}")
                
                with pe_stat_col3:
                    min_pe = pe_df['pe'].min()
                    st.metric("Minimum", f"{round(min_pe, 1)}")
                
                with pe_stat_col4:
                    max_pe = pe_df['pe'].max()
                    st.metric("Maximum", f"{round(max_pe, 1)}")
                
                st.divider()
                
                if current_pe < avg_pe * 0.8:
                    st.success(f"🟢 GÜNSTIG - KGV {round(current_pe, 1)} unter Schnitt ({round(avg_pe, 1)})")
                elif current_pe < avg_pe:
                    st.info(f"🟡 FAIR - KGV {round(current_pe, 1)} Nähe Schnitt ({round(avg_pe, 1)})")
                elif current_pe < avg_pe * 1.3:
                    st.warning(f"🟠 TEUER - KGV {round(current_pe, 1)} über Schnitt ({round(avg_pe, 1)})")
                else:
                    st.error(f"🔴 SEHR TEUER - KGV {round(current_pe, 1)} deutlich über Schnitt ({round(avg_pe, 1)})")
                
                st.divider()
                st.markdown(f"""
                ### 🏭 Branche: {sector}
                
                - **Günstig:** KGV < {benchmark_yellow}
                - **Fair:** KGV {benchmark_yellow}-{benchmark_red}
                - **Teuer:** KGV > {benchmark_red}
                """)
            else:
                st.info("ℹ️ Nicht genug Daten für KGV-Historie")
        else:
            st.info("ℹ️ Finanzdaten nicht verfügbar")
    
    except Exception as e:
        st.warning(f"⚠️ KGV-Historie nicht berechenbar: {str(e)[:50]}")
        if DEBUG:
            st.write(f"Full error: {e}")

# TAB 5: BILANZDATEN
with tab5:
    st.subheader("💼 Bilanz & Finanzielle Leistung")
    
    b1, b2, b3, b4 = st.columns(4)
    
    with b1:
        assets = safe_get_float(info, 'totalAssets')
        st.metric("Gesamtvermögen", f"${round(assets / 1e9, 1)}B" if assets > 0 else "N/A")
    
    with b2:
        debt = safe_get_float(info, 'totalDebt')
        st.metric("Gesamtschulden", f"${round(debt / 1e9, 1)}B" if debt > 0 else "N/A")
    
    with b3:
        equity = safe_get_float(info, 'totalEquity')
        st.metric("Eigenkapital", f"${round(equity / 1e9, 1)}B" if equity > 0 else "N/A")
    
    with b4:
        quick_ratio = safe_get_float(info, 'quickRatio')
        qr_color = "green" if quick_ratio > 1 else "yellow" if quick_ratio > 0.5 else "red"
        st.markdown(color_box(f"Quick Ratio: {round(quick_ratio, 2) if quick_ratio > 0 else 'N/A'}", qr_color), unsafe_allow_html=True)

# TAB 6: RISIKOANALYSE
with tab6:
    st.subheader("⚖️ Risiko-Bewertung")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("### 💪 Stärke-Faktoren")
        
        gm = safe_get_float(info, 'grossMargins') * 100 if info.get('grossMargins') else 0
        color, desc = get_color_for_metric_with_sector(gm, "margin", sector)
        st.markdown(color_box(f"Burggraben: {round(gm, 1) if gm > 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
        
        rg = safe_get_float(info, 'revenueGrowth') * 100 if info.get('revenueGrowth') else 0
        color, desc = get_color_for_metric_with_sector(rg, "growth", sector)
        st.markdown(color_box(f"Wachstum: {round(rg, 1) if rg != 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    with col_b:
        st.markdown("### ⛔ Risiko-Faktoren")
        
        de = safe_get_float(info, 'debtToEquity')
        color, desc = get_color_for_metric_with_sector(de, "debt", sector)
        st.markdown(color_box(f"Schulden: {round(de, 2) if de > 0 else 'N/A'}x", color, desc), unsafe_allow_html=True)
        
        pe = safe_get_float(info, 'trailingPE')
        color, desc = get_color_for_metric_with_sector(pe, "pe", sector)
        st.markdown(color_box(f"Bewertung: {round(pe, 1) if pe > 0 else 'N/A'}", color, desc), unsafe_allow_html=True)

# TAB 7: CASHFLOW
with tab7:
    st.subheader("💵 Cashflow-Analyse")
    
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        ocf = safe_get_float(info, 'operatingCashflow')
        st.metric("Operating CF", f"${round(ocf / 1e9, 1)}B" if ocf > 0 else "N/A")
    
    with c2:
        fcf = safe_get_float(info, 'freeCashflow')
        st.metric("Free Cashflow", f"${round(fcf / 1e9, 1)}B" if fcf > 0 else "N/A")
    
    with c3:
        capex = safe_get_float(info, 'capitalExpenditures')
        st.metric("CapEx", f"${round(capex / 1e9, 1)}B" if capex > 0 else "N/A")
    
    with c4:
        market_cap = safe_get_float(info, 'marketCap', 1)
        fcf_yield = (fcf / market_cap * 100) if market_cap > 0 and fcf > 0 else 0
        fcf_color = "green" if fcf_yield > 4 else "yellow" if fcf_yield > 2 else "orange"
        st.markdown(color_box(f"FCF Yield: {round(fcf_yield, 1) if fcf_yield > 0 else 'N/A'}%", fcf_color), unsafe_allow_html=True)

# TAB 8: DETAILS
with tab8:
    st.subheader("📋 Alle Metriken - Tabelle")
    
    metrics_dict = {
        "Metrik": [
            "Kurs",
            "Marktcap",
            "Trailing P/E",
            "Forward P/E",
            "Book Value",
            "FCF Yield",
            "Dividend Yield",
            "Beta",
            "52W High",
            "52W Low",
            "Debt/Equity",
            "Current Ratio",
            "Quick Ratio",
            "ROE",
            "ROA",
            "ROIC",
            "Gross Margin",
            "Op. Margin",
            "Profit Margin",
            "Revenue Growth",
            "EPS",
            "Div/Share"
        ],
        "Wert": [
            f"${round(current_price, 2)}",
            f"${round(safe_get_float(info, 'marketCap') / 1e9, 1)}B",
            f"{round(safe_get_float(info, 'trailingPE'), 2)}",
            f"{round(safe_get_float(info, 'forwardPE'), 2)}",
            f"${round(safe_get_float(info, 'bookValue'), 2)}",
            f"{round((safe_get_float(info, 'freeCashflow') / safe_get_float(info, 'marketCap', 1)) * 100, 2)}%",
            f"{round(safe_get_float(info, 'dividendYield') * 100 if info.get('dividendYield') else 0, 2)}%",
            f"{round(safe_get_float(info, 'beta'), 2)}",
            f"${round(safe_get_float(info, 'fiftyTwoWeekHigh'), 2)}",
            f"${round(safe_get_float(info, 'fiftyTwoWeekLow'), 2)}",
            f"{round(safe_get_float(info, 'debtToEquity'), 2)}",
            f"{round(safe_get_float(info, 'currentRatio'), 2)}",
            f"{round(safe_get_float(info, 'quickRatio'), 2)}",
            f"{round(safe_get_float(info, 'returnOnEquity') * 100 if info.get('returnOnEquity') else 0, 2)}%",
            f"{round(safe_get_float(info, 'returnOnAssets') * 100 if info.get('returnOnAssets') else 0, 2)}%",
            f"{round(safe_get_float(info, 'returnOnCapital') * 100 if info.get('returnOnCapital') else 0, 2)}%",
            f"{round(safe_get_float(info, 'grossMargins') * 100 if info.get('grossMargins') else 0, 2)}%",
            f"{round(safe_get_float(info, 'operatingMargins') * 100 if info.get('operatingMargins') else 0, 2)}%",
            f"{round(safe_get_float(info, 'profitMargins') * 100 if info.get('profitMargins') else 0, 2)}%",
            f"{round(safe_get_float(info, 'revenueGrowth') * 100 if info.get('revenueGrowth') else 0, 2)}%",
            f"${round(safe_get_float(info, 'trailingEps'), 2)}",
            f"${round(safe_get_float(info, 'dividendRate'), 2)}" if info.get('dividendRate') else "N/A"
        ]
    }
    
    df = pd.DataFrame(metrics_dict)
    st.dataframe(df, use_container_width=True, hide_index=True)

# Footer
st.divider()
st.markdown(f"""
📊 **Datenquelle:** Yahoo Finance  
🏭 **Sektor:** {sector}  
📅 **Stand:** {datetime.now().strftime('%d.%m.%Y %H:%M')}  
⚠️ **Disclaimer:** Keine Anlageberatung
""")

if DEBUG:
    st.divider()
    st.markdown("### 🔧 DEBUG INFO")
    with st.expander("Debug Informationen"):
        st.write("**Keys in info dict:**")
        st.write(list(info.keys())[:20])
        st.write("\n**Data Summary:**")
        st.write(data.describe() if data is not None else "None")

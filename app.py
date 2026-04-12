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

# --- BRANCHEN-SPEZIFISCHE BENCHMARKS ---
SECTOR_BENCHMARKS = {
    "Technology": {
        "pe_range": (20, 35, 50, 80),  # green, yellow, orange, red
        "margin_min": 15,
        "growth_min": 8,
        "debt_max": 1.0,
        "roe_min": 12,
        "emojis": "💻"
    },
    "Software": {
        "pe_range": (25, 40, 60, 100),
        "margin_min": 20,
        "growth_min": 10,
        "debt_max": 0.8,
        "roe_min": 15,
        "emojis": "⚙️"
    },
    "Internet": {
        "pe_range": (20, 35, 50, 80),
        "margin_min": 10,
        "growth_min": 15,
        "debt_max": 1.2,
        "roe_min": 10,
        "emojis": "🌐"
    },
    "Financial Services": {
        "pe_range": (10, 15, 20, 30),
        "margin_min": 15,
        "growth_min": 3,
        "debt_max": 8.0,
        "roe_min": 10,
        "emojis": "🏦"
    },
    "Healthcare": {
        "pe_range": (18, 28, 40, 60),
        "margin_min": 12,
        "growth_min": 5,
        "debt_max": 1.5,
        "roe_min": 12,
        "emojis": "⚕️"
    },
    "Pharmaceuticals": {
        "pe_range": (15, 25, 35, 50),
        "margin_min": 20,
        "growth_min": 3,
        "debt_max": 1.0,
        "roe_min": 15,
        "emojis": "💊"
    },
    "Consumer Cyclical": {
        "pe_range": (12, 18, 25, 40),
        "margin_min": 5,
        "growth_min": 3,
        "debt_max": 2.0,
        "roe_min": 8,
        "emojis": "🛍️"
    },
    "Consumer Defensive": {
        "pe_range": (18, 25, 35, 50),
        "margin_min": 8,
        "growth_min": 2,
        "debt_max": 2.0,
        "roe_min": 10,
        "emojis": "🥬"
    },
    "Industrials": {
        "pe_range": (12, 18, 25, 35),
        "margin_min": 6,
        "growth_min": 3,
        "debt_max": 2.5,
        "roe_min": 10,
        "emojis": "🏭"
    },
    "Energy": {
        "pe_range": (10, 15, 20, 30),
        "margin_min": 10,
        "growth_min": 2,
        "debt_max": 3.0,
        "roe_min": 8,
        "emojis": "⚡"
    },
    "Utilities": {
        "pe_range": (15, 20, 28, 40),
        "margin_min": 8,
        "growth_min": 1,
        "debt_max": 3.0,
        "roe_min": 8,
        "emojis": "💡"
    },
    "Real Estate": {
        "pe_range": (12, 18, 25, 35),
        "margin_min": 5,
        "growth_min": 2,
        "debt_max": 4.0,
        "roe_min": 6,
        "emojis": "🏠"
    },
    "Communication Services": {
        "pe_range": (15, 22, 30, 45),
        "margin_min": 15,
        "growth_min": 3,
        "debt_max": 2.0,
        "roe_min": 10,
        "emojis": "📱"
    },
    "Materials": {
        "pe_range": (10, 15, 20, 30),
        "margin_min": 5,
        "growth_min": 2,
        "debt_max": 2.5,
        "roe_min": 8,
        "emojis": "⛏️"
    }
}

# --- BEWERTUNGS-FUNKTIONEN MIT BRANCHE ---
def get_sector_benchmark(sector):
    """Hole Benchmark für Sektor, mit Fallback"""
    if sector in SECTOR_BENCHMARKS:
        return SECTOR_BENCHMARKS[sector]
    
    # Standard Fallback für unbekannte Sektoren
    return SECTOR_BENCHMARKS["Technology"]

def get_color_for_metric_with_sector(value, metric_type, sector):
    """
    Intelligente Farbgebung basierend auf Sektor
    """
    if value <= 0 or value is None:
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
    
    elif metric_type == "margin":
        min_margin = benchmark["margin_min"]
        if value < min_margin * 0.5:
            return "red", f"Sehr niedrig (unter {min_margin*0.5:.0f}%)"
        elif value < min_margin:
            return "orange", f"Niedrig für Branche (unter {min_margin}%)"
        elif value < min_margin * 1.5:
            return "yellow", f"Normal für Branche ({min_margin}-{min_margin*1.5:.0f}%)"
        else:
            return "green", f"Überdurchschnittlich (über {min_margin*1.5:.0f}%)"
    
    elif metric_type == "growth":
        min_growth = benchmark["growth_min"]
        if value < 0:
            return "red", "Negatives Wachstum"
        elif value < min_growth * 0.5:
            return "orange", f"Unter Branchenschnitt"
        elif value < min_growth:
            return "yellow", f"Unter Erwartung (unter {min_growth}%)"
        elif value < min_growth * 2:
            return "green", f"Gut für Branche ({min_growth}-{min_growth*2:.0f}%)"
        else:
            return "green", f"Außergewöhnlich (über {min_growth*2:.0f}%)"
    
    elif metric_type == "debt":
        max_debt = benchmark["debt_max"]
        if value < max_debt * 0.5:
            return "green", f"Sehr niedrig für Branche"
        elif value < max_debt:
            return "green", f"Gesund für Branche (unter {max_debt}x)"
        elif value < max_debt * 1.5:
            return "yellow", f"Erhöht für Branche ({max_debt}-{max_debt*1.5:.1f}x)"
        else:
            return "red", f"Hoch für Branche (über {max_debt*1.5:.1f}x)"
    
    elif metric_type == "roe":
        min_roe = benchmark["roe_min"]
        if value < min_roe * 0.5:
            return "red", f"Schwach (unter {min_roe*0.5:.0f}%)"
        elif value < min_roe:
            return "orange", f"Unter Branche (unter {min_roe}%)"
        elif value < min_roe * 1.5:
            return "green", f"Gut für Branche ({min_roe}-{min_roe*1.5:.0f}%)"
        else:
            return "green", f"Hervorragend (über {min_roe*1.5:.0f}%)"
    
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
            """)
        else:
            st.error(f"❌ Fehler: {error_msg[:100]}")
        
        return None, None

# Sidebar
with st.sidebar:
    st.header("🔎 Ticker")
    
    popular = {
        "MSFT – Microsoft (Software)": "MSFT",
        "AAPL – Apple (Technology)": "AAPL",
        "GOOGL – Alphabet (Internet)": "GOOGL",
        "AMZN – Amazon (Internet)": "AMZN",
        "TSLA – Tesla (Automotive)": "TSLA",
        "NVDA – NVIDIA (Technology)": "NVDA",
        "META – Meta (Communication)": "META",
        "JNJ – Johnson&Johnson (Healthcare)": "JNJ",
        "PG – Procter&Gamble (Consumer)": "PG",
        "XOM – ExxonMobil (Energy)": "XOM",
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
sector = info.get('sector', 'Technology')

st.markdown(f"### {company_name} ({ticker})")

col_header1, col_header2, col_header3 = st.columns(3)
with col_header1:
    st.caption(f"🏭 Sektor: {sector}")
with col_header2:
    benchmark = get_sector_benchmark(sector)
    st.caption(f"📊 Benchmark: {benchmark['emojis']}")
with col_header3:
    st.caption(f"📍 Diese Bewertung ist an die Branche angepasst!")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("💰 Kurs", f"${round(current_price, 2)}")
with col2:
    market_cap = info.get('marketCap', 0)
    st.metric("📊 Marktcap", f"${round(market_cap / 1e9, 1)}B" if market_cap > 0 else "N/A")
with col3:
    pe = info.get('trailingPE', 0)
    st.metric("📈 KGV", f"{round(pe, 1)}" if pe > 0 else "N/A")

st.divider()

# --- TABS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Kennzahlen",
    "📈 Chart",
    "💼 Bilanzdaten",
    "⚖️ Risikoanalyse",
    "💰 Cashflow",
    "📋 Details"
])

# TAB 1: KENNZAHLEN MIT BRANCHENVERGLEICH
with tab1:
    st.subheader("🎯 Kern-Kennzahlen (Branchenangepasst)")
    
    benchmark = get_sector_benchmark(sector)
    
    # Info-Box
    st.info(f"""
    📌 **Branche:** {sector}
    
    **Benchmarks für {sector}:**
    - KGV: {benchmark['pe_range'][1]}-{benchmark['pe_range'][2]} (normal)
    - Bruttomarge: mindestens {benchmark['margin_min']}%
    - Wachstum: mindestens {benchmark['growth_min']}%
    - Schuldenquote: max {benchmark['debt_max']}x
    """)
    
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        pe = info.get('trailingPE', 0)
        color, desc = get_color_for_metric_with_sector(pe, "pe", sector)
        st.markdown(color_box(f"KGV: {round(pe, 1) if pe > 0 else 'N/A'}", color, desc), unsafe_allow_html=True)
    
    with m2:
        fcf = info.get('freeCashflow', 0)
        market_cap = info.get('marketCap', 1)
        fcf_yield = (fcf / market_cap * 100) if market_cap > 0 else 0
        if fcf_yield > 0:
            color = "green" if fcf_yield > 3 else "yellow" if fcf_yield > 1 else "orange"
        else:
            color = "gray"
        st.markdown(color_box(f"FCF Yield: {round(fcf_yield, 1) if fcf_yield > 0 else 'N/A'}%", color, "Cashflow Rendite"), unsafe_allow_html=True)
    
    with m3:
        debt_eq = info.get('debtToEquity', 0)
        color, desc = get_color_for_metric_with_sector(debt_eq, "debt", sector)
        st.markdown(color_box(f"Debt/Equity: {round(debt_eq, 2) if debt_eq > 0 else 'N/A'}", color, desc), unsafe_allow_html=True)
    
    with m4:
        beta = info.get('beta', 1.0)
        beta_color = "green" if 0.8 <= beta <= 1.2 else "yellow" if 0.6 <= beta <= 1.5 else "orange"
        st.markdown(color_box(f"Beta: {round(beta, 2)}", beta_color, "Volatilität"), unsafe_allow_html=True)
    
    st.divider()
    st.subheader("📈 Rentabilitäts-Metriken")
    
    r1, r2, r3, r4 = st.columns(4)
    
    with r1:
        gm = info.get('grossMargins', 0) * 100 if info.get('grossMargins') else 0
        color, desc = get_color_for_metric_with_sector(gm, "margin", sector)
        st.markdown(color_box(f"Gross Margin: {round(gm, 1) if gm > 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    with r2:
        om = info.get('operatingMargins', 0) * 100 if info.get('operatingMargins') else 0
        color, desc = get_color_for_metric_with_sector(om, "margin", sector)
        st.markdown(color_box(f"Operating Margin: {round(om, 1) if om > 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    with r3:
        pm = info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0
        color, desc = get_color_for_metric_with_sector(pm, "margin", sector)
        st.markdown(color_box(f"Profit Margin: {round(pm, 1) if pm > 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    with r4:
        roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0
        color, desc = get_color_for_metric_with_sector(roe, "roe", sector)
        st.markdown(color_box(f"ROE: {round(roe, 1) if roe > 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    st.divider()
    st.subheader("📊 Wachstums-Metriken")
    
    g1, g2, g3, g4 = st.columns(4)
    
    with g1:
        rg = info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0
        color, desc = get_color_for_metric_with_sector(rg, "growth", sector)
        st.markdown(color_box(f"Revenue Growth: {round(rg, 1) if rg != 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    with g2:
        eg = info.get('earningsGrowth', 0) * 100 if info.get('earningsGrowth') else 0
        color, desc = get_color_for_metric_with_sector(eg, "growth", sector)
        st.markdown(color_box(f"Earnings Growth: {round(eg, 1) if eg != 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    with g3:
        eps = info.get('trailingEps', 0)
        st.metric("EPS", f"${round(eps, 2)}" if eps > 0 else "N/A")
    
    with g4:
        peg = info.get('pegRatio', 0)
        peg_color = "green" if 0.5 < peg < 1.5 else "yellow" if peg < 3 else "red"
        st.markdown(color_box(f"PEG Ratio: {round(peg, 2) if peg > 0 else 'N/A'}", peg_color, "Wachstum vs Bewertung"), unsafe_allow_html=True)

# TAB 2: CHART
with tab2:
    st.subheader("📈 Preis-Chart (5 Jahre)")
    
    try:
        if not data.empty and len(data) > 10:
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['Close'],
                name='Schlusskurs',
                line=dict(color='#00ff9d', width=2.5),
                hovertemplate='<b>Schlusskurs</b><br>%{x|%d.%m.%Y}<br>%{y:.2f} USD<extra></extra>'
            ))
            
            ema_200 = data['Close'].rolling(window=200).mean()
            fig.add_trace(go.Scatter(
                x=data.index,
                y=ema_200,
                name='EMA 200 (Trend)',
                line=dict(color='#ff9500', dash='dot', width=1.5),
                opacity=0.8,
                hovertemplate='<b>EMA 200</b><br>%{x|%d.%m.%Y}<br>%{y:.2f} USD<extra></extra>'
            ))
            
            ema_50 = data['Close'].rolling(window=50).mean()
            fig.add_trace(go.Scatter(
                x=data.index,
                y=ema_50,
                name='EMA 50 (Schnell)',
                line=dict(color='#00d4ff', dash='dash', width=1.5),
                opacity=0.8,
                hovertemplate='<b>EMA 50</b><br>%{x|%d.%m.%Y}<br>%{y:.2f} USD<extra></extra>'
            ))
            
            fig.update_layout(
                title=f"📈 {ticker} - 5 Jahre Preisverlauf",
                xaxis_title="Datum",
                yaxis_title="Preis (USD)",
                template="plotly_dark",
                height=500,
                hovermode='x unified',
                plot_bgcolor='#0f1419',
                paper_bgcolor='#0f1419',
                font=dict(color='#ccc', size=11),
                margin=dict(l=50, r=50, t=80, b=50),
                xaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)'),
                yaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            last_ema200 = ema_200.iloc[-1]
            if pd.notna(last_ema200):
                if current_price < last_ema200:
                    st.success(f"🟢 KAUFZONE - Preis unter EMA 200 (${round(last_ema200, 2)})")
                else:
                    st.warning(f"🔴 TEUER - Preis über EMA 200 (${round(last_ema200, 2)})")
        else:
            st.warning("⚠️ Nicht genug Daten für Chart")
            
    except Exception as e:
        st.error(f"❌ Chart-Fehler: {str(e)[:100]}")

# TAB 3: BILANZDATEN
with tab3:
    st.subheader("💼 Bilanz & Finanzielle Leistung")
    
    b1, b2, b3, b4 = st.columns(4)
    
    with b1:
        assets = info.get('totalAssets', 0)
        st.metric("Gesamtvermögen", f"${round(assets / 1e9, 1)}B" if assets > 0 else "N/A")
    
    with b2:
        debt = info.get('totalDebt', 0)
        st.metric("Gesamtschulden", f"${round(debt / 1e9, 1)}B" if debt > 0 else "N/A")
    
    with b3:
        equity = info.get('totalEquity', 0)
        st.metric("Eigenkapital", f"${round(equity / 1e9, 1)}B" if equity > 0 else "N/A")
    
    with b4:
        quick_ratio = info.get('quickRatio', 0)
        qr_color = "green" if quick_ratio > 1 else "yellow" if quick_ratio > 0.5 else "red"
        st.markdown(color_box(f"Quick Ratio: {round(quick_ratio, 2) if quick_ratio > 0 else 'N/A'}", qr_color, "Liquidität"), unsafe_allow_html=True)
    
    st.divider()
    
    b5, b6, b7, b8 = st.columns(4)
    
    with b5:
        current_ratio = info.get('currentRatio', 0)
        cr_color = "green" if current_ratio > 1.5 else "yellow" if current_ratio > 1 else "red"
        st.markdown(color_box(f"Liquiditätsquote: {round(current_ratio, 2) if current_ratio > 0 else 'N/A'}", cr_color), unsafe_allow_html=True)
    
    with b6:
        roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0
        color, desc = get_color_for_metric_with_sector(roe, "roe", sector)
        st.markdown(color_box(f"ROE: {round(roe, 1) if roe > 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    with b7:
        roc = info.get('returnOnCapital', 0) * 100 if info.get('returnOnCapital') else 0
        color, desc = get_color_for_metric_with_sector(roc, "roe", sector)
        st.markdown(color_box(f"ROIC: {round(roc, 1) if roc > 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    with b8:
        bvps = info.get('bookValue', 0)
        st.metric("Book Value/Share", f"${round(bvps, 2)}" if bvps > 0 else "N/A")

# TAB 4: RISIKOANALYSE
with tab4:
    st.subheader("⚠️ Risiko-Bewertung (Branchenangepasst)")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("### 💪 Stärke-Faktoren")
        
        gm = info.get('grossMargins', 0) * 100 if info.get('grossMargins') else 0
        color, desc = get_color_for_metric_with_sector(gm, "margin", sector)
        st.markdown(color_box(f"Burggraben: {round(gm, 1) if gm > 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
        
        rg = info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0
        color, desc = get_color_for_metric_with_sector(rg, "growth", sector)
        st.markdown(color_box(f"Wachstum: {round(rg, 1) if rg != 0 else 'N/A'}%", color, desc), unsafe_allow_html=True)
    
    with col_b:
        st.markdown("### ⛔ Risiko-Faktoren")
        
        de = info.get('debtToEquity', 0)
        color, desc = get_color_for_metric_with_sector(de, "debt", sector)
        st.markdown(color_box(f"Schulden: {round(de, 2) if de > 0 else 'N/A'}x", color, desc), unsafe_allow_html=True)
        
        pe = info.get('trailingPE', 0)
        color, desc = get_color_for_metric_with_sector(pe, "pe", sector)
        st.markdown(color_box(f"Bewertung (KGV): {round(pe, 1) if pe > 0 else 'N/A'}", color, desc), unsafe_allow_html=True)

# TAB 5: CASHFLOW
with tab5:
    st.subheader("💰 Cashflow-Analyse")
    
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        ocf = info.get('operatingCashflow', 0)
        st.metric("Operating Cashflow", f"${round(ocf / 1e9, 1)}B" if ocf > 0 else "N/A")
    
    with c2:
        fcf = info.get('freeCashflow', 0)
        st.metric("Free Cashflow", f"${round(fcf / 1e9, 1)}B" if fcf > 0 else "N/A")
    
    with c3:
        capex = info.get('capitalExpenditures', 0)
        st.metric("CapEx", f"${round(capex / 1e9, 1)}B" if capex > 0 else "N/A")
    
    with c4:
        fcf_yield = (fcf / (info.get('marketCap', 1)) * 100) if info.get('marketCap', 0) > 0 else 0
        fcf_color = "green" if fcf_yield > 4 else "yellow" if fcf_yield > 2 else "orange" if fcf_yield > 0 else "gray"
        st.markdown(color_box(f"FCF Yield: {round(fcf_yield, 1) if fcf_yield > 0 else 'N/A'}%", fcf_color), unsafe_allow_html=True)

# TAB 6: DETAILS
with tab6:
    st.subheader("📋 Alle Metriken - Tabelle")
    
    metrics_dict = {
        "Metrik": [
            "Kurs",
            "Marktcap",
            "Trailing P/E",
            "Forward P/E",
            "PEG Ratio",
            "Book Value",
            "FCF Yield",
            "Dividend Yield",
            "Beta",
            "52-Wochen-Hoch",
            "52-Wochen-Tief",
            "Debt/Equity",
            "Current Ratio",
            "Quick Ratio",
            "ROE",
            "ROA",
            "ROIC",
            "Gross Margin",
            "Operating Margin",
            "Profit Margin",
            "Revenue Growth",
            "EPS",
            "Dividende/Aktie"
        ],
        "Wert": [
            f"${round(current_price, 2)}",
            f"${round(info.get('marketCap', 0) / 1e9, 1)}B",
            f"{round(info.get('trailingPE', 0), 2)}",
            f"{round(info.get('forwardPE', 0), 2)}",
            f"{round(info.get('pegRatio', 0), 2)}",
            f"${round(info.get('bookValue', 0), 2)}",
            f"{round((info.get('freeCashflow', 0) / info.get('marketCap', 1)) * 100, 2)}%",
            f"{round(info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0, 2)}%",
            f"{round(info.get('beta', 0), 2)}",
            f"${round(info.get('fiftyTwoWeekHigh', 0), 2)}",
            f"${round(info.get('fiftyTwoWeekLow', 0), 2)}",
            f"{round(info.get('debtToEquity', 0), 2)}",
            f"{round(info.get('currentRatio', 0), 2)}",
            f"{round(info.get('quickRatio', 0), 2)}",
            f"{round(info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0, 2)}%",
            f"{round(info.get('returnOnAssets', 0) * 100 if info.get('returnOnAssets') else 0, 2)}%",
            f"{round(info.get('returnOnCapital', 0) * 100 if info.get('returnOnCapital') else 0, 2)}%",
            f"{round(info.get('grossMargins', 0) * 100 if info.get('grossMargins') else 0, 2)}%",
            f"{round(info.get('operatingMargins', 0) * 100 if info.get('operatingMargins') else 0, 2)}%",
            f"{round(info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0, 2)}%",
            f"{round(info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0, 2)}%",
            f"${round(info.get('trailingEps', 0), 2)}",
            f"${round(info.get('dividendRate', 0), 2)}" if info.get('dividendRate') else "N/A"
        ]
    }
    
    df = pd.DataFrame(metrics_dict)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.divider()
    st.markdown(f"""
    ### 📊 Sektor-Benchmarks für {sector}
    
    **KGV-Range:** {benchmark['pe_range'][0]}-{benchmark['pe_range'][1]} (normal) bis {benchmark['pe_range'][2]}-{benchmark['pe_range'][3]} (teuer)
    
    **Margin-Erwartung:** Mindestens {benchmark['margin_min']}%
    
    **Wachstums-Erwartung:** Mindestens {benchmark['growth_min']}% pro Jahr
    
    **Max Schuldenquote:** {benchmark['debt_max']}x
    
    **ROE-Erwartung:** Mindestens {benchmark['roe_min']}%
    
    ⚠️ Diese Werte wurden speziell für den Sektor **{sector}** optimiert!
    """)

# Footer
st.divider()
st.markdown(f"""
📊 **Datenquelle:** Yahoo Finance  
🏭 **Sektor:** {sector}  
📅 **Stand:** {datetime.now().strftime('%d.%m.%Y %H:%M')}  
⚠️ **Disclaimer:** Keine Anlageberatung | Nur zu Informationszwecken

### 🎨 Intelligente Farbcodierung:
✅ Diese App bewertet Metriken **relativ zur Branche**, nicht absolut!

Beispiele:
- **Software (MSFT):** KGV 25 = 🟢 Normal (Benchmark: 25-40)
- **Basiskonsumgüter (PG):** KGV 25 = 🔴 Teuer (Benchmark: 18-25)
- **Energy (XOM):** KGV 10 = 🟢 Gut (Benchmark: 10-15)
- **Tech (NVDA):** Margin 50% = 🟢 Normal (Benchmark: 15%+)
- **Utility:** Margin 25% = 🟢 Gut (Benchmark: 8%+)
""")

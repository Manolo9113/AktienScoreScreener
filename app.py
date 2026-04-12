import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from functools import lru_cache
import logging

# ===== STREAMLIT CONFIG =====
st.set_page_config(
    page_title="Vigilanz-Cockpit",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"  # Hamburger-Menü auf Mobile!
)

# ===== RESPONSIVE CUSTOM CSS =====
st.markdown("""
<style>
/* Dark Theme */
:root {
    --bg-dark: #0a0e27;
    --bg-card: #141b2f;
    --text-primary: #e8eef7;
    --text-secondary: #a8b2c1;
    --accent-green: #22c55e;
    --accent-red: #ef4444;
    --accent-yellow: #eab308;
    --accent-blue: #3b82f6;
}

.main {
    background: linear-gradient(135deg, #0a0e27 0%, #141b2f 100%);
    color: var(--text-primary);
    max-width: 100%;
    padding: 0;
}

/* Mobile-First: Kleine Screens zuerst */
@media (max-width: 640px) {
    .main {
        padding: 0.5rem !important;
    }
    
    h1, h2, h3 {
        font-size: 1.3rem !important;
        margin: 0.5rem 0 !important;
    }
    
    .metric-box {
        padding: 0.8rem !important;
        margin: 0.3rem 0 !important;
        border-radius: 8px !important;
    }
    
    .stMetric {
        background: transparent !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 0.5rem 0.8rem !important;
        font-size: 0.85rem !important;
    }
}

/* Tablets & Desktop */
@media (min-width: 641px) {
    .main {
        padding: 2rem 1rem;
    }
}

/* Allgemeine Styles */
.metric-box {
    background: rgba(255, 255, 255, 0.05);
    border-left: 4px solid var(--accent-blue);
    padding: 1rem;
    border-radius: 12px;
    margin: 0.5rem 0;
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
}

.metric-box:hover {
    background: rgba(255, 255, 255, 0.08);
    transform: translateX(4px);
}

.metric-box.green {
    border-left-color: var(--accent-green);
}

.metric-box.yellow {
    border-left-color: var(--accent-yellow);
}

.metric-box.red {
    border-left-color: var(--accent-red);
}

.score-box {
    background: linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(52, 211, 153, 0.1) 100%);
    border: 2px solid var(--accent-green);
    padding: 1.5rem;
    border-radius: 16px;
    text-align: center;
    margin: 1rem 0;
}

.score-box-warning {
    background: linear-gradient(135deg, rgba(249, 115, 22, 0.15) 0%, rgba(251, 146, 60, 0.1) 100%);
    border: 2px solid var(--accent-yellow);
}

.score-box-danger {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(252, 165, 165, 0.1) 100%);
    border: 2px solid var(--accent-red);
}

.score-number {
    font-size: 3rem;
    font-weight: 800;
    background: linear-gradient(90deg, #22c55e 0%, #3b82f6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
}

.score-label {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0.5rem 0 0 0;
}

.header-title {
    background: linear-gradient(90deg, #22c55e 0%, #3b82f6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 2.5rem;
    font-weight: 800;
    margin-bottom: 1rem;
}

/* Tabs responsive */
.stTabs {
    gap: 0.5rem;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0;
    background: rgba(255, 255, 255, 0.05);
    padding: 0.8rem 1rem;
    font-weight: 600;
    transition: all 0.2s;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: var(--accent-blue);
    color: white;
}

/* Charts responsive */
.plotly-chart {
    width: 100% !important;
}

/* Info/Warning/Error Boxen */
.stAlert {
    border-radius: 12px;
    padding: 1rem;
    margin: 0.5rem 0;
}

/* Buttons großer auf Mobile */
.stButton > button {
    width: 100%;
    padding: 0.8rem 1.5rem;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
}

/* Divider */
hr {
    border: 1px solid rgba(255, 255, 255, 0.1);
    margin: 1.5rem 0;
}

/* Tooltip Styling */
.tooltip-text {
    font-size: 0.85rem;
    color: var(--text-secondary);
    font-style: italic;
    margin-top: 0.25rem;
}

</style>
""", unsafe_allow_html=True)

# ===== LOGGING SETUP =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== SEKTOR-BENCHMARKS (Rule of 40 fokussiert) =====
SECTOR_BENCHMARKS = {
    "Technology": {
        "pe_forward": (18, 25, 35),
        "rule_of_40": 35,
        "gross_margin": 70,
        "fcf_yield": 1.5,
        "roe": 12,
        "emoji": "💻"
    },
    "Software": {
        "pe_forward": (20, 28, 40),
        "rule_of_40": 40,
        "gross_margin": 75,
        "fcf_yield": 2,
        "roe": 15,
        "emoji": "⚙️"
    },
    "Internet": {
        "pe_forward": (18, 28, 45),
        "rule_of_40": 40,
        "gross_margin": 65,
        "fcf_yield": 1,
        "roe": 10,
        "emoji": "🌐"
    },
    "Semiconductors": {
        "pe_forward": (15, 22, 32),
        "rule_of_40": 30,
        "gross_margin": 50,
        "fcf_yield": 2,
        "roe": 20,
        "emoji": "🔌"
    },
    "Healthcare": {
        "pe_forward": (15, 22, 30),
        "rule_of_40": 25,
        "gross_margin": 60,
        "fcf_yield": 2,
        "roe": 12,
        "emoji": "⚕️"
    },
    "Industrials": {
        "pe_forward": (12, 16, 22),
        "rule_of_40": 15,
        "gross_margin": 35,
        "fcf_yield": 3,
        "roe": 12,
        "emoji": "🏭"
    },
    "Consumer": {
        "pe_forward": (15, 20, 28),
        "rule_of_40": 18,
        "gross_margin": 40,
        "fcf_yield": 3,
        "roe": 10,
        "emoji": "🛍️"
    },
    "Energy": {
        "pe_forward": (10, 14, 20),
        "rule_of_40": 8,
        "gross_margin": 40,
        "fcf_yield": 5,
        "roe": 12,
        "emoji": "⚡"
    },
}

# ===== UTILITY FUNCTIONS =====

@lru_cache(maxsize=128)
def get_sector_from_ticker(ticker):
    """Cache-basierte Sektor-Abfrage"""
    try:
        stock = yf.Ticker(ticker)
        sector = stock.info.get('sector', 'Technology')
        return sector if sector in SECTOR_BENCHMARKS else 'Technology'
    except:
        return 'Technology'

def safe_get_float(dictionary, key, default=0):
    """Sichere Float-Abfrage ohne Crashes"""
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

def get_sector_benchmark(sector):
    """Benchmark für Sektor laden"""
    return SECTOR_BENCHMARKS.get(sector, SECTOR_BENCHMARKS['Technology'])

def calculate_rule_of_40(growth_rate, fcf_yield):
    """Rule of 40: Growth % + FCF Yield % sollte >= 40 sein"""
    if growth_rate is None or fcf_yield is None:
        return None
    return growth_rate + fcf_yield

def calculate_quality_score(info, sector):
    """
    Verbesserte Score-Logik (0-45):
    - Mildere KGV-Bestrafung
    - Rule of 40 wichtiger
    - Bruttomarge stark gewichtet
    - FCF-Yield bei Wachstum milder
    """
    score = 0
    max_score = 45
    
    # 1. Forward PE (10 Punkte) - milder
    pe_fwd = safe_get_float(info, 'forwardPE')
    benchmark = get_sector_benchmark(sector)
    pe_range = benchmark['pe_forward']
    
    if pe_fwd > 0:
        if pe_fwd < pe_range[0]:
            score += 10  # Sehr günstig
        elif pe_fwd < pe_range[1]:
            score += 8   # Günstig
        elif pe_fwd < pe_range[2]:
            score += 5   # Fair
        else:
            score += 2   # Teuer
    
    # 2. Rule of 40 (12 Punkte) - wichtigste Metrik!
    revenue_growth = safe_get_float(info, 'revenueGrowth') * 100
    fcf_yield = (safe_get_float(info, 'freeCashflow') / safe_get_float(info, 'marketCap', 1)) * 100 if safe_get_float(info, 'marketCap', 1) > 0 else 0
    rule_40 = calculate_rule_of_40(revenue_growth, fcf_yield)
    
    if rule_40 is not None:
        rule_40_benchmark = benchmark['rule_of_40']
        if rule_40 >= rule_40_benchmark:
            score += 12
        elif rule_40 >= rule_40_benchmark * 0.8:
            score += 9
        elif rule_40 >= rule_40_benchmark * 0.6:
            score += 6
        else:
            score += 2
    
    # 3. Bruttomarge (10 Punkte) - stark gewichtet
    gross_margin = safe_get_float(info, 'grossMargins') * 100
    margin_benchmark = benchmark['gross_margin']
    
    if gross_margin > 0:
        if gross_margin >= margin_benchmark:
            score += 10
        elif gross_margin >= margin_benchmark * 0.85:
            score += 8
        elif gross_margin >= margin_benchmark * 0.7:
            score += 5
        else:
            score += 2
    
    # 4. ROE (8 Punkte)
    roe = safe_get_float(info, 'returnOnEquity') * 100
    roe_benchmark = benchmark['roe']
    
    if roe > 0:
        if roe >= roe_benchmark * 1.5:
            score += 8
        elif roe >= roe_benchmark:
            score += 6
        elif roe >= roe_benchmark * 0.7:
            score += 3
        else:
            score += 1
    
    # 5. Verschuldung (5 Punkte)
    debt_to_equity = safe_get_float(info, 'debtToEquity')
    
    if debt_to_equity > 0:
        if debt_to_equity < 1:
            score += 5
        elif debt_to_equity < 2:
            score += 3
        elif debt_to_equity < 3:
            score += 1
    
    return min(score, max_score)

def score_to_interpretation(score):
    """Score 0-45 in Interpretation umwandeln"""
    if score >= 38:
        return "🟢 ELITE - Exzellentes Unternehmen", "green"
    elif score >= 30:
        return "🟢 GUT - Solides Qualitäts-Investment", "green"
    elif score >= 20:
        return "🟡 VORSICHT - Einige Warnsignale", "yellow"
    else:
        return "🔴 VERMEIDEN - Zu viele Schwächen", "red"

def color_box(label, value, color, description=""):
    """Formatierte Metrik-Box"""
    colors = {
        "green": "#22c55e",
        "yellow": "#eab308",
        "orange": "#f97316",
        "red": "#ef4444",
        "blue": "#3b82f6",
        "gray": "#6b7280"
    }
    
    bg_colors = {
        "green": "rgba(34, 197, 94, 0.15)",
        "yellow": "rgba(234, 179, 8, 0.15)",
        "orange": "rgba(249, 115, 22, 0.15)",
        "red": "rgba(239, 68, 68, 0.15)",
        "blue": "rgba(59, 130, 246, 0.15)",
        "gray": "rgba(107, 114, 128, 0.1)"
    }
    
    emojis = {
        "green": "🟢", "yellow": "🟡", "orange": "🟠", "red": "🔴", "blue": "🔵", "gray": "⚪"
    }
    
    desc_html = f"<br><small style='color: #999; font-size: 0.8rem;'>{description}</small>" if description else ""
    
    return f"""
    <div class="metric-box {color}" style="background: {bg_colors.get(color, bg_colors['blue'])}; 
         border-left: 4px solid {colors.get(color, colors['blue'])};
         padding: 0.8rem; border-radius: 8px; margin: 0.5rem 0;">
        <span style="color: {colors.get(color, colors['blue'])}; font-weight: bold;">
            {emojis.get(color, "•")} <strong>{label}:</strong> {value}
        </span>{desc_html}
    </div>
    """

@st.cache_data(ttl=3600)
def load_stock_data(ticker):
    """Optimierte Datenladung mit Caching"""
    ticker = ticker.strip().upper()
    
    try:
        # Preis-Daten
        with st.spinner(f"⏳ Lade {ticker}..."):
            data = yf.download(
                ticker,
                start=datetime.now() - timedelta(days=5*365),
                progress=False,
                threads=False
            )
        
        if data.empty:
            return None, None
        
        # Info + Finanzdaten
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return data, info
        
    except Exception as e:
        st.error(f"❌ Fehler beim Laden: {str(e)[:80]}")
        logger.error(f"Load error for {ticker}: {str(e)}")
        return None, None

# ===== APP HEADER =====
col_main = st.columns([1])[0]

with col_main:
    st.markdown('<h1 class="header-title">🛡️ Vigilanz-Cockpit</h1>', unsafe_allow_html=True)
    st.caption("Qualitäts-Investment Tool basierend auf Rule of 40 & Operative Exzellenz")

# ===== SIDEBAR - MOBILE FRIENDLY =====
with st.sidebar:
    st.header("⚙️ Einstellungen")
    
    col_input1, col_input2 = st.columns([3, 1])
    
    with col_input1:
        ticker_input = st.text_input(
            "🔎 Ticket eingeben:",
            value="MSFT",
            placeholder="z.B. MSFT, AAPL, GOOGL"
        )
    
    with col_input2:
        if st.button("🔍", help="Suchen"):
            st.rerun()
    
    st.divider()
    
    st.markdown("### 📊 Schnellzugriff")
    popular = ["MSFT", "AAPL", "GOOGL", "NVDA", "META", "TSLA", "AMZN"]
    
    # 2x4 Grid auf Mobile, 3x3 auf Desktop
    cols = st.columns(3)
    for idx, stock in enumerate(popular):
        with cols[idx % 3]:
            if st.button(stock, use_container_width=True):
                st.session_state.ticker = stock
                st.rerun()
    
    st.divider()
    st.markdown("""
    ### 📚 Über das Tool
    
    **Vigilanz-Cockpit** bewertet Qualitäts-Aktien nach:
    - **Rule of 40:** Growth + FCF Yield
    - **Bruttomarge:** Wettbewerbsvorteil
    - **Forward PE:** Realistic Bewertung
    - **ROE + Verschuldung:** Eigenkapital-Qualität
    
    📖 [Growth-Investing Philosophie](https://www.notion.so)
    """)

# ===== MAIN APP =====
ticker = ticker_input.strip().upper() if ticker_input else "MSFT"

if not ticker or len(ticker) > 5:
    st.error("❌ Bitte einen gültigen Ticker eingeben (z.B. MSFT, AAPL)")
    st.stop()

# Daten laden
data, info = load_stock_data(ticker)

if data is None or info is None:
    st.error(f"❌ '{ticker}' nicht gefunden. Bitte versuchen Sie es erneut.")
    st.stop()

# ===== BASELINE METRICS =====
current_price = data['Close'].iloc[-1] if not data.empty else 0
company_name = info.get('longName', ticker)
sector = info.get('sector', 'Technology')
market_cap = safe_get_float(info, 'marketCap')

# Quality Score berechnen
quality_score = calculate_quality_score(info, sector)
score_text, score_color = score_to_interpretation(quality_score)

# ===== HEADER SECTION =====
st.markdown(f"""
### 📈 {company_name} ({ticker})
**Sektor:** {SECTOR_BENCHMARKS.get(sector, SECTOR_BENCHMARKS['Technology'])['emoji']} {sector}
""")

# Schnellmetriken im 2x2 Grid (mobile responsive)
metric_cols = st.columns(2)

with metric_cols[0]:
    st.metric(
        label="💰 Aktueller Kurs",
        value=f"${round(current_price, 2)}",
        delta=None
    )

with metric_cols[1]:
    st.metric(
        label="📊 Marktcap",
        value=f"${round(market_cap / 1e9, 1)}B" if market_cap > 0 else "N/A",
        delta=None
    )

# ===== QUALITY SCORE BOX =====
score_class = "score-box"
if score_color == "yellow":
    score_class += " score-box-warning"
elif score_color == "red":
    score_class += " score-box-danger"

st.markdown(f"""
<div class="{score_class}">
    <p class="score-number">{round(quality_score, 1)}/45</p>
    <p class="score-label">{score_text}</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ===== TABS - MOBILE OPTIMIERT =====
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Score-Details",
    "📈 5J-Chart",
    "💎 Kennzahlen",
    "💰 Cashflow",
    "⚖️ Risiko"
])

# ===== TAB 1: SCORE DETAILS =====
with tab1:
    st.subheader("🎯 Quality Score Analyse")
    
    col_s1, col_s2 = st.columns(2)
    
    with col_s1:
        st.markdown(color_box(
            "Rule of 40",
            f"{round(calculate_rule_of_40(safe_get_float(info, 'revenueGrowth') * 100, (safe_get_float(info, 'freeCashflow') / safe_get_float(info, 'marketCap', 1)) * 100), 1) if calculate_rule_of_40(safe_get_float(info, 'revenueGrowth') * 100, (safe_get_float(info, 'freeCashflow') / safe_get_float(info, 'marketCap', 1)) * 100) else 'N/A'}",
            "blue",
            "Growth + FCF Yield sollte ≥ 40 sein"
        ), unsafe_allow_html=True)
    
    with col_s2:
        benchmark = get_sector_benchmark(sector)
        gm = safe_get_float(info, 'grossMargins') * 100
        gm_color = "green" if gm >= benchmark['gross_margin'] else "yellow" if gm >= benchmark['gross_margin'] * 0.85 else "red"
        st.markdown(color_box(
            "Bruttomarge",
            f"{round(gm, 1)}%" if gm > 0 else "N/A",
            gm_color,
            f"Benchmark: {benchmark['gross_margin']}%"
        ), unsafe_allow_html=True)
    
    st.divider()
    
    col_s3, col_s4 = st.columns(2)
    
    with col_s3:
        pe_fwd = safe_get_float(info, 'forwardPE')
        pe_range = benchmark['pe_forward']
        pe_color = "green" if pe_fwd < pe_range[0] else "green" if pe_fwd < pe_range[1] else "yellow" if pe_fwd < pe_range[2] else "red"
        st.markdown(color_box(
            "Forward P/E",
            f"{round(pe_fwd, 1)}" if pe_fwd > 0 else "N/A",
            pe_color,
            f"Fair: {pe_range[0]}-{pe_range[1]}, Benchmark: {pe_range[2]}"
        ), unsafe_allow_html=True)
    
    with col_s4:
        roe = safe_get_float(info, 'returnOnEquity') * 100
        roe_color = "green" if roe >= benchmark['roe'] * 1.5 else "green" if roe >= benchmark['roe'] else "yellow" if roe > 0 else "red"
        st.markdown(color_box(
            "ROE",
            f"{round(roe, 1)}%" if roe > 0 else "N/A",
            roe_color,
            f"Benchmark: {benchmark['roe']}%"
        ), unsafe_allow_html=True)
    
    st.divider()
    
    col_s5, col_s6 = st.columns(2)
    
    with col_s5:
        rg = safe_get_float(info, 'revenueGrowth') * 100
        rg_color = "green" if rg >= 15 else "green" if rg >= 10 else "yellow" if rg > 0 else "red"
        st.markdown(color_box(
            "Revenue Growth",
            f"{round(rg, 1)}%" if rg > 0 else "N/A",
            rg_color,
            "Wachstum Jahr-über-Jahr"
        ), unsafe_allow_html=True)
    
    with col_s6:
        de = safe_get_float(info, 'debtToEquity')
        de_color = "green" if de < 1 else "yellow" if de < 2 else "red"
        st.markdown(color_box(
            "Debt/Equity",
            f"{round(de, 2)}" if de > 0 else "N/A",
            de_color,
            "Finanzielle Stabilität"
        ), unsafe_allow_html=True)

# ===== TAB 2: 5-JAHRES-CHART MIT BUY/EXPENSIVE ZONEN =====
with tab2:
    st.subheader("📈 5-Jahres-Growth Chart (Logarithmisch)")
    
    try:
        # Letzten 5 Jahre
        data_5y = data[data.index >= datetime.now() - timedelta(days=5*365)].copy()
        
        if not data_5y.empty and len(data_5y) > 50:
            # EMA 200
            ema_200 = data_5y['Close'].rolling(window=200).mean()
            
            fig = go.Figure()
            
            # Schlusskurs
            fig.add_trace(go.Scatter(
                x=data_5y.index,
                y=data_5y['Close'],
                name='Schlusskurs',
                line=dict(color='#3b82f6', width=3),
                hovertemplate='<b>Preis</b><br>%{x|%d.%m.%Y}<br>%{y:.2f} USD<extra></extra>'
            ))
            
            # EMA 200 als Referenzlinie
            fig.add_trace(go.Scatter(
                x=ema_200.index,
                y=ema_200,
                name='EMA 200 (Trend)',
                line=dict(color='#eab308', dash='dash', width=2),
                hovertemplate='<b>EMA 200</b><br>%{x|%d.%m.%Y}<br>%{y:.2f} USD<extra></extra>'
            ))
            
            # Green Zone: Unten EMA 200 (Buy Zone)
            if not ema_200.empty:
                last_ema = ema_200.iloc[-1]
                min_price = ema_200.min() * 0.8
                
                fig.add_hspan(
                    y0=min_price,
                    y1=last_ema,
                    fillcolor="rgba(34, 197, 94, 0.15)",
                    line_width=0,
                    name="🟢 Kaufzone"
                )
                
                # Red Zone: Über EMA 200 (Expensive)
                max_price = ema_200.max() * 1.3
                fig.add_hspan(
                    y0=last_ema,
                    y1=max_price,
                    fillcolor="rgba(239, 68, 68, 0.15)",
                    line_width=0,
                    name="🔴 Teuer"
                )
            
            fig.update_yaxes(type="log", title_text="Preis (USD, log-Skala)")
            fig.update_xaxes(title_text="Datum")
            
            fig.update_layout(
                title=f"📈 {ticker} - 5 Jahre mit Buy/Expensive Zonen",
                height=500,
                template="plotly_dark",
                plot_bgcolor='rgba(20, 27, 47, 0.8)',
                paper_bgcolor='rgba(10, 14, 39, 1)',
                font=dict(color='#a8b2c1', size=12),
                margin=dict(l=50, r=50, t=80, b=50),
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Status: Buy oder Expensive
            if current_price < last_ema:
                st.success(f"✅ KAUFZONE - Unter EMA 200: ${round(current_price, 2)} vs ${round(last_ema, 2)}")
            else:
                st.warning(f"⚠️ TEUER - Über EMA 200: ${round(current_price, 2)} vs ${round(last_ema, 2)}")
        
        else:
            st.warning("⚠️ Nicht genug historische Daten")
    
    except Exception as e:
        st.error(f"❌ Chart-Fehler: {str(e)[:60]}")

# ===== TAB 3: KENNZAHLEN =====
with tab3:
    st.subheader("💎 Vollständige Kennzahlen")
    
    # Row 1
    col_k1, col_k2 = st.columns(2)
    
    with col_k1:
        pe_trail = safe_get_float(info, 'trailingPE')
        st.metric("Trailing P/E", f"{round(pe_trail, 1)}" if pe_trail > 0 else "N/A")
    with col_k2:
        fcf = safe_get_float(info, 'freeCashflow')
        st.metric("Free Cashflow", f"${round(fcf / 1e9, 2)}B" if fcf > 0 else "N/A")
    
    # Row 2
    col_k3, col_k4 = st.columns(2)
    
    with col_k3:
        div_yield = safe_get_float(info, 'dividendYield') * 100 if info.get('dividendYield') else 0
        st.metric("Dividend Yield", f"{round(div_yield, 2)}%" if div_yield > 0 else "N/A")
    
    with col_k4:
        eps = safe_get_float(info, 'trailingEps')
        st.metric("EPS", f"${round(eps, 2)}" if eps > 0 else "N/A")
    
    # Row 3
    col_k5, col_k6 = st.columns(2)
    
    with col_k5:
        beta = safe_get_float(info, 'beta')
        st.metric("Beta", f"{round(beta, 2)}" if beta > 0 else "N/A")
    
    with col_k6:
        assets = safe_get_float(info, 'totalAssets')
        st.metric("Gesamtvermögen", f"${round(assets / 1e9, 1)}B" if assets > 0 else "N/A")

# ===== TAB 4: CASHFLOW =====
with tab4:
    st.subheader("💰 Cashflow Analyse")
    
    col_cf1, col_cf2, col_cf3 = st.columns(3)
    
    with col_cf1:
        ocf = safe_get_float(info, 'operatingCashflow')
        st.metric("Operating CF", f"${round(ocf / 1e9, 2)}B" if ocf > 0 else "N/A")
    
    with col_cf2:
        fcf = safe_get_float(info, 'freeCashflow')
        st.metric("Free Cashflow", f"${round(fcf / 1e9, 2)}B" if fcf > 0 else "N/A")
    
    with col_cf3:
        capex = safe_get_float(info, 'capitalExpenditures')
        st.metric("CapEx", f"${round(capex / 1e9, 2)}B" if capex > 0 else "N/A")
    
    st.divider()
    
    # FCF Yield
    market_cap = safe_get_float(info, 'marketCap', 1)
    fcf_yield = (fcf / market_cap * 100) if market_cap > 0 and fcf > 0 else 0
    
    fcf_color = "green" if fcf_yield > 5 else "blue" if fcf_yield > 2.5 else "yellow" if fcf_yield > 1 else "red"
    
    st.markdown(color_box(
        "FCF Yield",
        f"{round(fcf_yield, 2)}%" if fcf_yield > 0 else "N/A",
        fcf_color,
        "Free Cashflow / Marktcap"
    ), unsafe_allow_html=True)

# ===== TAB 5: RISIKO =====
with tab5:
    st.subheader("⚖️ Risiko-Faktoren")
    
    col_r1, col_r2 = st.columns(2)
    
    with col_r1:
        st.markdown("#### 💪 Stärken")
        
        # Gross Margin
        gm = safe_get_float(info, 'grossMargins') * 100
        st.markdown(color_box(
            "Bruttomarge",
            f"{round(gm, 1)}%" if gm > 0 else "N/A",
            "green"
        ), unsafe_allow_html=True)
        
        # Revenue Growth
        rg = safe_get_float(info, 'revenueGrowth') * 100
        st.markdown(color_box(
            "Umsatzwachstum",
            f"{round(rg, 1)}%" if rg > 0 else "N/A",
            "green"
        ), unsafe_allow_html=True)
    
    with col_r2:
        st.markdown("#### ⛔ Schwächen")
        
        # Debt/Equity
        de = safe_get_float(info, 'debtToEquity')
        de_color = "green" if de < 1 else "yellow" if de < 2 else "red"
        st.markdown(color_box(
            "Verschuldung",
            f"{round(de, 2)}" if de > 0 else "N/A",
            de_color
        ), unsafe_allow_html=True)
        
        # Forward PE
        pe_fwd = safe_get_float(info, 'forwardPE')
        pe_color = "green" if pe_fwd < 20 else "yellow" if pe_fwd < 30 else "red"
        st.markdown(color_box(
            "Forward P/E",
            f"{round(pe_fwd, 1)}" if pe_fwd > 0 else "N/A",
            pe_color
        ), unsafe_allow_html=True)

# ===== FOOTER =====
st.divider()

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption(f"📊 Daten: Yahoo Finance")

with footer_col2:
    st.caption(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}")

with footer_col3:
    st.caption("⚠️ Keine Anlageberatung")

st.markdown("""
---
**🔐 Disclaimer:** Vigilanz-Cockpit ist ein Analyse-Tool für Informationszwecke. 
Keine Anlageberatung oder Handelsempfehlung. Investieren Sie nur, wenn Sie die Risiken verstehen.
""")

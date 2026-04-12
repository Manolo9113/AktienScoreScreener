import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import time

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Vigilanz-Cockpit Pro",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM STYLING ---
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
        margin-bottom: 0.5em;
        text-align: center;
    }
    .score-card {
        background: linear-gradient(135deg, #1f1f2e 0%, #2a2a3e 100%);
        border: 2px solid #00ff9d;
        border-radius: 15px;
        padding: 25px;
        box-shadow: 0 10px 40px rgba(0, 255, 157, 0.1);
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] button {
        background-color: #1f1f2e;
        border-radius: 10px 10px 0 0;
        color: #999;
        padding: 12px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #242a3a;
        border-bottom: 2px solid #00ff9d;
        color: #00ff9d;
    }
    .footer {
        text-align: center;
        padding: 20px;
        color: #666;
        font-size: 0.9em;
        border-top: 1px solid #2a2a3e;
        margin-top: 40px;
    }
</style>
""", unsafe_allow_html=True)

# --- VERBESSERTE HELPERS ---
@st.cache_data(ttl=3600)
def get_ticker_data(ticker: str):
    """Hole Ticker-Daten mit mehreren Fallback-Strategien."""
    ticker = ticker.strip().upper()
    
    if not ticker or len(ticker) > 5:
        return None, None
    
    try:
        # Strategie 1: Direkt mit yfinance.Ticker
        stock = yf.Ticker(ticker)
        
        # Versuche Info zu laden
        info = stock.info
        
        # Versuche History zu laden
        hist = stock.history(period="5y")
        
        # Prüfe ob Daten vorhanden sind
        if hist is not None and not hist.empty and len(hist) > 100:
            return info, hist
        
        # Strategie 2: yf.download als Fallback
        hist = yf.download(ticker, period="5y", progress=False)
        
        if hist is not None and not hist.empty:
            return info, hist
        
        return None, None
        
    except Exception as e:
        print(f"Fehler beim Laden von {ticker}: {str(e)}")
        return None, None

def safe_get(obj, key, default=0):
    """Sicherer Zugriff auf Dictionary."""
    try:
        val = obj.get(key, default)
        return float(val) if val else default
    except:
        return default

def calculate_metrics(info: dict, hist: pd.DataFrame) -> dict:
    """Berechne alle Metriken."""
    if hist is None or hist.empty:
        return {}
    
    metrics = {}
    
    # Basis-Info
    metrics['company_name'] = info.get('longName') or info.get('shortName') or "Unknown"
    metrics['sector'] = info.get('sector') or "N/A"
    
    # Preis
    try:
        metrics['current_price'] = float(hist['Close'].iloc[-1])
    except:
        metrics['current_price'] = safe_get(info, 'currentPrice', 0)
    
    # Wenn kein Preis: Fehler
    if metrics['current_price'] == 0:
        return {}
    
    # Fundamentale Daten
    fcf = safe_get(info, 'freeCashflow')
    market_cap = safe_get(info, 'marketCap', 1)
    revenue = safe_get(info, 'totalRevenue', 1)
    
    # FCF Metriken
    if market_cap > 0:
        metrics['fcf_yield'] = (fcf / market_cap) * 100 if fcf > 0 else 0
    else:
        metrics['fcf_yield'] = 0
    
    if revenue > 0:
        metrics['fcf_margin'] = (fcf / revenue) * 100 if fcf > 0 else 0
    else:
        metrics['fcf_margin'] = 0
    
    # Wachstum
    metrics['rev_growth'] = safe_get(info, 'revenueGrowth', 0) * 100
    metrics['rule_of_40'] = metrics['rev_growth'] + metrics['fcf_margin']
    
    # Schulden
    de_raw = safe_get(info, 'debtToEquity', 0)
    metrics['debt_to_equity'] = de_raw / 100 if de_raw > 10 else de_raw
    
    # Margen
    metrics['gross_margin'] = safe_get(info, 'grossMargins', 0) * 100
    
    # KGV
    metrics['trailing_pe'] = safe_get(info, 'trailingPE', 0)
    metrics['forward_pe'] = safe_get(info, 'forwardPE', 0)
    metrics['pe_to_use'] = metrics['forward_pe'] if metrics['forward_pe'] > 0 else metrics['trailing_pe']
    
    # Risiko
    metrics['beta'] = safe_get(info, 'beta', 1.0)
    metrics['market_cap'] = market_cap
    metrics['52w_high'] = safe_get(info, 'fiftyTwoWeekHigh', metrics['current_price'])
    metrics['52w_low'] = safe_get(info, 'fiftyTwoWeekLow', metrics['current_price'])
    
    return metrics

def calculate_score(metrics: dict) -> tuple:
    """Berechne Quality Score."""
    score = 0
    
    conditions = {
        'rule_of_40_strong': metrics.get('rule_of_40', 0) > 40,
        'fcf_yield_good': metrics.get('fcf_yield', 0) > 3,
        'gross_margin_strong': metrics.get('gross_margin', 0) > 50,
        'pe_reasonable': metrics.get('pe_to_use', 0) < 50,
        'debt_low': metrics.get('debt_to_equity', 0) < 1.5,
        'beta_stable': metrics.get('beta', 1) < 1.5
    }
    
    # Positive Faktoren
    score += 20 if conditions['rule_of_40_strong'] else 5
    score += 15 if conditions['fcf_yield_good'] else 0
    score += 8 if conditions['gross_margin_strong'] else 0
    score += 5 if metrics.get('rule_of_40', 0) > 50 else 0
    
    # Negative Faktoren
    pe = metrics.get('pe_to_use', 0)
    if pe > 60:
        score -= 20
    elif pe > 40:
        score -= 10
    
    score -= 10 if metrics.get('debt_to_equity', 0) > 2.0 else 0
    score -= 8 if metrics.get('beta', 1) > 1.5 else 0
    
    score = max(0, min(score, 45))
    
    return score, conditions

def get_score_label(score: int) -> tuple:
    if score >= 35:
        return "🚀", "ELITE-QUALITÄT", "success"
    elif score >= 25:
        return "✅", "Gute Qualität", "info"
    elif score >= 15:
        return "⚠️", "Vorsicht", "warning"
    else:
        return "❌", "Kritisch", "error"

# --- MAIN APP ---
st.markdown('<div class="header-title">🛡️ Vigilanz-Cockpit Pro</div>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #999;">Investment Quality Analysis Engine</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 🔎 Ticker-Eingabe")
    
    popular = {
        "MSFT – Microsoft": "MSFT",
        "AAPL – Apple": "AAPL",
        "GOOGL – Alphabet": "GOOGL",
        "AMZN – Amazon": "AMZN",
        "NVDA – NVIDIA": "NVDA",
        "TSLA – Tesla": "TSLA",
        "META – Meta": "META",
        "AVGO – Broadcom": "AVGO",
        "V – Visa": "V",
        "MA – Mastercard": "MA",
        "Eigener Ticker": ""
    }
    
    choice = st.selectbox("Wähle oder gib Ticker ein:", list(popular.keys()), index=0)
    
    if choice == "Eigener Ticker":
        user_input = st.text_input("Gib Ticker ein (z.B. MSFT, AAPL):", "MSFT")
    else:
        user_input = popular[choice]
    
    st.divider()
    st.info("💡 Gib einen US Stock Ticker ein z.B. MSFT, AAPL, GOOGL")

# --- DATEN LADEN ---
ticker_input = user_input.strip().upper()

if not ticker_input:
    st.error("❌ Bitte einen Ticker eingeben")
    st.stop()

with st.spinner(f'🔬 Lade Daten für {ticker_input}...'):
    info, hist = get_ticker_data(ticker_input)

# --- ERROR HANDLING ---
if info is None or hist is None or hist.empty:
    st.error(f"""
    ❌ **Fehler: Keine Daten für '{ticker_input}' gefunden**
    
    **Mögliche Gründe:**
    - Ticker ist nicht korrekt (verwende Großbuchstaben: MSFT, nicht msft)
    - Unternehmen existiert nicht auf Yahoo Finance
    - Netzwerkfehler - versuche in 30 Sekunden erneut
    
    **Funktioniert sicher:**
    ✅ MSFT (Microsoft)
    ✅ AAPL (Apple)
    ✅ GOOGL (Alphabet)
    ✅ AMZN (Amazon)
    ✅ NVDA (NVIDIA)
    """)
    st.stop()

# --- METRIKEN BERECHNEN ---
metrics = calculate_metrics(info, hist)

if not metrics or metrics.get('current_price', 0) == 0:
    st.error("❌ Fehler bei der Datenverarbeitung. Versuche einen anderen Ticker.")
    st.stop()

score, conditions = calculate_score(metrics)
score_emoji, score_label, alert_type = get_score_label(score)

# --- HEADER ---
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown(f"### {metrics['company_name']} ({ticker_input})")
    st.caption(f"Sektor: {metrics['sector']}")
with col2:
    st.metric("💰 Preis", f"${round(metrics['current_price'], 2)}")
with col3:
    st.metric("📊 Marktcap", f"${round(metrics['market_cap'] / 1e9, 1)}B")

# --- SCORE CARD ---
score_color = "#00ff9d" if alert_type == "success" else "#ffc107" if alert_type == "warning" else "#ff4757"
st.markdown(f"""
<div class="score-card" style="border-color: {score_color};">
    <h2 style="color: {score_color}; margin: 0;">{score_emoji} Vigilanz-Score</h2>
    <h1 style="color: {score_color}; font-size: 2.5em; margin: 10px 0;">{score}/45</h1>
    <p style="color: #999; margin: 0;">{score_label}</p>
</div>
""", unsafe_allow_html=True)

st.progress(score / 45)

if alert_type == "success":
    st.success(f"🚀 {score_label} – Operative Souveränität pur!")
elif alert_type == "info":
    st.info(f"✅ {score_label} – Solides Investment")
elif alert_type == "warning":
    st.warning(f"⚠️ {score_label} – Weitere Prüfung empfohlen")
else:
    st.error(f"❌ {score_label} – Erhebliche Bedenken")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Metriken", "📈 Chart", "⚖️ Analyse"])

# TAB 1: METRIKEN
with tab1:
    st.subheader("🎯 Kern-Metriken")
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        st.metric(
            "Rule of 40",
            f"{round(metrics['rule_of_40'], 1)}%",
            delta="✅" if conditions['rule_of_40_strong'] else "⚠️",
            help="Wachstum + FCF-Marge"
        )
    with m2:
        st.metric(
            "FCF Yield",
            f"{round(metrics['fcf_yield'], 1)}%",
            delta="✅" if conditions['fcf_yield_good'] else "⚠️",
            help="Cashflow Rendite"
        )
    with m3:
        pe = metrics['trailing_pe']
        pe_text = f"{round(pe, 1)}" if pe > 0 else "N/A"
        st.metric(
            "KGV",
            pe_text,
            delta="✅" if conditions['pe_reasonable'] else "⚠️",
            help="Kurs-Gewinn-Verhältnis"
        )
    with m4:
        st.metric(
            "Bruttomarge",
            f"{round(metrics['gross_margin'], 1)}%",
            delta="✅" if conditions['gross_margin_strong'] else "⚠️",
            help="Burggraben-Stärke"
        )
    
    st.divider()
    st.subheader("📈 Weitere Kennzahlen")
    
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("Schulden/EK", f"{round(metrics['debt_to_equity'], 2)}×")
    with s2:
        st.metric("Beta", f"{round(metrics['beta'], 2)}")
    with s3:
        st.metric("Revenue Growth", f"{round(metrics['rev_growth'], 1)}%")
    with s4:
        st.metric("FCF Margin", f"{round(metrics['fcf_margin'], 1)}%")

# TAB 2: CHART
with tab2:
    try:
        hist_copy = hist.copy()
        hist_copy['EMA200'] = hist_copy['Close'].rolling(window=200).mean()
        hist_copy['EMA50'] = hist_copy['Close'].rolling(window=50).mean()
        
        last_ema200 = hist_copy['EMA200'].iloc[-1]
        
        if pd.isna(last_ema200):
            last_ema200 = metrics['current_price']
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=hist_copy.index,
            y=hist_copy['Close'],
            name='Kurs',
            line=dict(color='#00ff9d', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=hist_copy.index,
            y=hist_copy['EMA200'],
            name='EMA 200',
            line=dict(color='#ff9500', dash='dot', width=1.5)
        ))
        
        fig.add_trace(go.Scatter(
            x=hist_copy.index,
            y=hist_copy['EMA50'],
            name='EMA 50',
            line=dict(color='#00d4ff', dash='dash', width=1)
        ))
        
        is_buy_zone = metrics['current_price'] < last_ema200
        fig.add_vrect(
            x0=hist_copy.index[0],
            x1=hist_copy.index[-1],
            fillcolor="rgba(0, 255, 157, 0.08)" if is_buy_zone else "rgba(255, 71, 87, 0.08)",
            layer="below",
            line_width=0
        )
        
        fig.update_layout(
            title="📊 5-Jahres-Chart",
            template="plotly_dark",
            height=450,
            hovermode='x unified',
            plot_bgcolor='#0f1419',
            paper_bgcolor='#0f1419',
            font=dict(size=10)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if is_buy_zone:
                st.success(f"🟢 KAUFZONE – Unter Trend (${round(last_ema200, 2)})")
            else:
                st.warning(f"🔴 TEUER – Über Trend (${round(last_ema200, 2)})")
        with c2:
            st.info(f"📌 52W: ${round(metrics['52w_low'], 2)} - ${round(metrics['52w_high'], 2)}")
    
    except Exception as e:
        st.warning("⚠️ Chart konnte nicht geladen werden")

# TAB 3: ANALYSE
with tab3:
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("⚠️ Risiko-Analyse")
        
        de = metrics['debt_to_equity']
        if de > 1.5:
            st.error(f"🚨 Hohe Schulden ({round(de, 2)}×)")
        else:
            st.success(f"✅ Schuldenquote OK ({round(de, 2)}×)")
        
        pe = metrics['pe_to_use']
        if pe > 50:
            st.error(f"💸 Überbewertet (KGV: {round(pe, 1)})")
        elif pe > 30:
            st.warning(f"⚠️ Moderat teuer (KGV: {round(pe, 1)})")
        else:
            st.success(f"✅ Fair bewertet (KGV: {round(pe, 1)})")
        
        beta = metrics['beta']
        if beta > 1.4:
            st.warning(f"🌊 Volatil (Beta: {round(beta, 2)})")
        else:
            st.success(f"✅ Stabil (Beta: {round(beta, 2)})")
    
    with col_b:
        st.subheader("💪 Stärke-Signale")
        
        gm = metrics['gross_margin']
        if gm > 50:
            st.success(f"🏰 Starker Burggraben ({round(gm, 1)}%)")
        else:
            st.warning(f"⚠️ Schwacher Burggraben ({round(gm, 1)}%)")
        
        r40 = metrics['rule_of_40']
        if r40 > 40:
            st.success(f"🎯 Weltklasse ({round(r40, 1)}%)")
        else:
            st.warning(f"⚠️ Verbesserung nötig ({round(r40, 1)}%)")
        
        fcf = metrics['fcf_yield']
        if fcf > 5:
            st.success(f"💰 Viel Cashflow ({round(fcf, 1)}%)")
        else:
            st.info(f"ℹ️ FCF Yield: {round(fcf, 1)}%")

# FOOTER
st.divider()
st.markdown("""
<div class="footer">
📊 Datenquelle: Yahoo Finance | """ + datetime.now().strftime('%d.%m.%Y %H:%M') + """<br>
⚠️ Keine Anlageberatung | Nur zu Informationszwecken<br>
© 2024 Vigilanz-Cockpit Pro
</div>
""", unsafe_allow_html=True)

import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import os

# --- SETUP ---
st.set_page_config(
    page_title="Vigilanz-Cockpit 3.4",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Investment Analyse Tool"}
)

# Custom CSS für besseres Design
st.markdown("""
    <style>
    .metric-card {
        background-color: #1f1f2e;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #00ff9d;
    }
    .advice-box { padding: 10px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Souveränes Qualitäts-Investment Tool")
st.markdown("**Name, Ticker oder ISIN → sofortige Souveränitäts-Analyse**")

# --- SIDEBAR SETUP ---
st.sidebar.header("🔎 Schnell-Suche")
popular = {
    "AVGO – Broadcom": "AVGO",
    "MSFT – Microsoft": "MSFT",
    "AAPL – Apple": "AAPL",
    "NVDA – NVIDIA": "NVDA",
    "AMZN – Amazon": "AMZN",
    "META – Meta": "META",
    "GOOGL – Alphabet": "GOOGL",
    "V – Visa": "V",
    "MA – Mastercard": "MA",
    "Anderer Ticker / Name / ISIN": ""
}

choice = st.sidebar.selectbox("Fokus-Aktien:", options=list(popular.keys()))
user_input = popular[choice] if choice != "Anderer Ticker / Name / ISIN" else st.sidebar.text_input(
    "Name/ISIN/Ticker:",
    "AVGO"
)

# --- HELPER FUNCTIONS ---
@st.cache_data(ttl=3600)
def get_ticker_symbol(query: str) -> str:
    """Resolve ticker symbol from name/ISIN/ticker input."""
    if not query:
        return ""
    try:
        search = yf.Search(query, max_results=1)
        if search.quotes:
            return search.quotes[0]['symbol']
        return query.upper()
    except Exception as e:
        return query.upper()

@st.cache_data(ttl=3600)
def fetch_stock_data(ticker: str) -> tuple:
    """Fetch stock info and history data with error handling."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="5y")
        return info, hist
    except Exception as e:
        return None, None

def safe_divide(numerator: float, denominator: float, default: float = 0) -> float:
    """Safely divide with fallback value."""
    try:
        return numerator / denominator if denominator != 0 else default
    except:
        return default

def calculate_all_metrics(info: dict, hist: pd.DataFrame) -> dict:
    """Calculate all financial metrics robustly."""
    metrics = {}
    
    # Basic info
    metrics['company_name'] = info.get('longName') or info.get('shortName') or "N/A"
    metrics['sector'] = info.get('sector') or "—"
    metrics['current_price'] = float(hist['Close'].iloc[-1]) if not hist.empty else 0
    
    # Financial metrics
    fcf = info.get('freeCashflow') or 0
    market_cap = info.get('marketCap') or 1
    rev = info.get('totalRevenue') or 1
    
    metrics['fcf_yield'] = safe_divide(fcf * 100, market_cap)
    metrics['fcf_margin'] = safe_divide(fcf * 100, rev)
    metrics['rev_growth'] = (info.get('revenueGrowth') or 0) * 100
    metrics['rule_of_40'] = metrics['rev_growth'] + metrics['fcf_margin']
    
    # Debt metrics
    de_raw = info.get('debtToEquity') or 0
    metrics['debt_to_equity'] = de_raw / 100 if de_raw > 10 else de_raw
    
    # Margins & Valuation
    metrics['gross_margin'] = (info.get('grossMargins') or 0) * 100
    metrics['trailing_pe'] = info.get('trailingPE') or 0
    metrics['forward_pe'] = info.get('forwardPE') or metrics['trailing_pe']
    metrics['pe_to_use'] = metrics['forward_pe'] if metrics['forward_pe'] > 0 else metrics['trailing_pe']
    
    # Risk metrics
    metrics['beta'] = info.get('beta') or 1.0
    metrics['market_cap'] = market_cap
    metrics['52w_high'] = info.get('fiftyTwoWeekHigh', metrics['current_price'])
    metrics['52w_low'] = info.get('fiftyTwoWeekLow', metrics['current_price'])
    
    return metrics

def calculate_score(metrics: dict) -> tuple:
    """Calculate Vigilanz-Score and return (score, conditions_met)."""
    score = 0
    conditions = {
        'rule_of_40_strong': metrics['rule_of_40'] > 40,
        'fcf_yield_good': metrics['fcf_yield'] > 3,
        'gross_margin_strong': metrics['gross_margin'] > 50,
        'pe_reasonable': metrics['pe_to_use'] < 50,
        'debt_low': metrics['debt_to_equity'] < 1.5,
        'beta_stable': metrics['beta'] < 1.5
    }
    
    # Positive factors
    score += 20 if conditions['rule_of_40_strong'] else 5
    score += 15 if conditions['fcf_yield_good'] else 0
    score += 8 if conditions['gross_margin_strong'] else 0
    score += 5 if metrics['rule_of_40'] > 50 else 0
    
    # Negative factors
    if metrics['pe_to_use'] > 60:
        score -= 20
    elif metrics['pe_to_use'] > 40:
        score -= 10
    
    score -= 10 if metrics['debt_to_equity'] > 2.0 else 0
    score -= 8 if metrics['beta'] > 1.5 else 0
    
    score = max(0, min(score, 45))
    
    return score, conditions

def get_score_label(score: int) -> tuple:
    """Return (emoji, label, alert_type)."""
    if score >= 35:
        return "🚀", "ELITE-QUALITÄT", "success"
    elif score >= 25:
        return "✅", "Gute Qualität", "info"
    elif score >= 15:
        return "⚠️", "Vorsicht", "warning"
    else:
        return "❌", "Kritisch", "error"

# --- MAIN APP LOGIC ---
ticker = get_ticker_symbol(user_input)

if not ticker:
    st.error("❌ Bitte einen gültigen Ticker eingeben.")
    st.stop()

# Loading spinner
with st.spinner(f'🔬 Seziere {ticker}...'):
    info, hist = fetch_stock_data(ticker)

if info is None or hist is None or hist.empty:
    st.error(f"❌ Keine Daten für '{ticker}' gefunden.")
    st.info("💡 Tipp: Stelle sicher, dass der Ticker auf Yahoo Finance verfügbar ist.")
    st.stop()

# Calculate metrics
metrics = calculate_all_metrics(info, hist)
score, conditions = calculate_score(metrics)
score_emoji, score_label, alert_type = get_score_label(score)

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Kennzahlen", "📈 Chart-Vigilanz", "⚖️ Analyse", "📋 Details"])

# ============= TAB 1: KENNZAHLEN =============
with tab1:
    st.subheader(f"{metrics['company_name']} ({ticker}) – {metrics['sector']}")
    
    # Score Display
    col_score_left, col_score_right = st.columns([2, 1])
    with col_score_left:
        st.markdown(f"### Vigilanz-Score: {score_emoji} **{score}/45**")
        st.progress(score / 45)
    
    with col_score_right:
        st.metric("Aktueller Kurs", f"${round(metrics['current_price'], 2)}")
    
    # Alert based on score
    if alert_type == "success":
        st.success(f"🚀 {score_label} – Operative Souveränität pur!")
    elif alert_type == "info":
        st.info(f"✅ {score_label} – Solides Investment")
    elif alert_type == "warning":
        st.warning(f"⚠️ {score_label} – Weitere Prüfung empfohlen")
    else:
        st.error(f"❌ {score_label} – Erhebliche Bedenken")
    
    # Key metrics in columns
    st.subheader("🎯 Kern-Metriken")
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        col_val = "✅" if conditions['rule_of_40_strong'] else "⚠️"
        st.metric(
            "Rule of 40",
            f"{round(metrics['rule_of_40'], 1)}%",
            delta=col_val,
            help="Wachstum + FCF-Marge. >40 = Weltklasse"
        )
    
    with c2:
        col_val = "✅" if conditions['fcf_yield_good'] else "⚠️"
        st.metric(
            "FCF Yield",
            f"{round(metrics['fcf_yield'], 1)}%",
            delta=col_val,
            help="Freier Cashflow vs. Marktwert"
        )
    
    with c3:
        col_val = "✅" if conditions['pe_reasonable'] else "⚠️"
        pe_display = f"{round(metrics['trailing_pe'], 1)}" if metrics['trailing_pe'] > 0 else "N/A"
        st.metric(
            "KGV (Trailing)",
            pe_display,
            delta=col_val,
            help="Kurs-Gewinn-Verhältnis"
        )
    
    with c4:
        col_val = "✅" if conditions['gross_margin_strong'] else "⚠️"
        st.metric(
            "Bruttomarge",
            f"{round(metrics['gross_margin'], 1)}%",
            delta=col_val,
            help="Indikator für Burggraben"
        )
    
    # Secondary metrics
    st.subheader("📈 Weitere Kennzahlen")
    s1, s2, s3, s4 = st.columns(4)
    
    with s1:
        col_val = "✅" if conditions['debt_low'] else "⚠️"
        st.metric("Schulden/EK", f"{round(metrics['debt_to_equity'], 2)}×", delta=col_val)
    
    with s2:
        col_val = "✅" if conditions['beta_stable'] else "⚠️"
        st.metric("Beta", f"{round(metrics['beta'], 2)}", delta=col_val)
    
    with s3:
        st.metric("Revenue Wachstum", f"{round(metrics['rev_growth'], 1)}%")
    
    with s4:
        st.metric("FCF Marge", f"{round(metrics['fcf_margin'], 1)}%")

# ============= TAB 2: CHART-VIGILANZ =============
with tab2:
    hist_copy = hist.copy()
    hist_copy['EMA200'] = hist_copy['Close'].rolling(window=200).mean()
    hist_copy['EMA50'] = hist_copy['Close'].rolling(window=50).mean()
    
    last_ema200 = hist_copy['EMA200'].iloc[-1] if not pd.isna(hist_copy['EMA200'].iloc[-1]) else metrics['current_price']
    last_ema50 = hist_copy['EMA50'].iloc[-1] if not pd.isna(hist_copy['EMA50'].iloc[-1]) else metrics['current_price']
    
    # Create figure
    fig = go.Figure()
    
    # Add traces
    fig.add_trace(go.Scatter(
        x=hist_copy.index,
        y=hist_copy['Close'],
        name='Kurs',
        line=dict(color='#00ff9d', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=hist_copy.index,
        y=hist_copy['EMA200'],
        name='EMA 200 (Langtrend)',
        line=dict(color='orange', dash='dot', width=1.5)
    ))
    
    fig.add_trace(go.Scatter(
        x=hist_copy.index,
        y=hist_copy['EMA50'],
        name='EMA 50 (Kurstrend)',
        line=dict(color='#FFD700', dash='dash', width=1)
    ))
    
    # Color zones
    is_buy_zone = metrics['current_price'] < last_ema200
    fig.add_vrect(
        x0=hist_copy.index[0],
        x1=hist_copy.index[-1],
        fillcolor="rgba(0, 255, 157, 0.12)" if is_buy_zone else "rgba(255, 80, 80, 0.12)",
        layer="below",
        line_width=0
    )
    
    fig.update_layout(
        title="📊 5-Jahres-Chart mit Trend-Analyse",
        template="plotly_dark",
        height=600,
        yaxis_type="log",
        xaxis_title="Zeit",
        yaxis_title="Kurs (logarithmisch)",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Zone explanation
    col_zone1, col_zone2 = st.columns(2)
    with col_zone1:
        if is_buy_zone:
            st.success("🟢 **KAUFZONE** – Preis unter langfristigem Trend")
        else:
            st.warning("🔴 **TEUER** – Preis über langfristigem Trend")
    
    with col_zone2:
        st.info(f"📌 EMA200: ${round(last_ema200, 2)} | EMA50: ${round(last_ema50, 2)}")

# ============= TAB 3: ANALYSE =============
with tab3:
    st.markdown("### 🔍 Qualitäts-Analyse")
    
    col_risks, col_strengths = st.columns(2)
    
    with col_risks:
        st.subheader("⚠️ Risikoeinschätzung")
        
        if metrics['debt_to_equity'] > 1.5:
            st.error(f"🚨 **Hohe Schuldenquote** ({round(metrics['debt_to_equity'], 2)}×)")
            st.caption("Gläubiger-Zwang: Eingeschränkte finanzielle Flexibilität")
        else:
            st.success(f"✅ Schuldenquote OK ({round(metrics['debt_to_equity'], 2)}×)")
        
        if metrics['pe_to_use'] > 50:
            st.error(f"💸 **Überbewertet** (KGV: {round(metrics['pe_to_use'], 1)})")
            st.caption("Hohe Wette auf zukünftiges Wachstum")
        elif metrics['pe_to_use'] > 30:
            st.warning(f"⚠️ **Moderat teuer** (KGV: {round(metrics['pe_to_use'], 1)})")
        else:
            st.success(f"✅ **Faire Bewertung** (KGV: {round(metrics['pe_to_use'], 1)})")
        
        if metrics['beta'] > 1.4:
            st.warning(f"🌊 **Volatil** (Beta: {round(metrics['beta'], 2)})")
            st.caption("Starke Schwankungen zu erwarten")
        else:
            st.success(f"✅ **Stabil** (Beta: {round(metrics['beta'], 2)})")
    
    with col_strengths:
        st.subheader("💪 Stärke-Signale")
        
        if metrics['gross_margin'] > 50:
            st.success(f"🏰 **Starker Burggraben** ({round(metrics['gross_margin'], 1)}%)")
            st.caption("Hohe Preissetzungsmacht")
        else:
            st.warning(f"⚠️ **Schwacher Burggraben** ({round(metrics['gross_margin'], 1)}%)")
        
        if metrics['rule_of_40'] > 40:
            st.success(f"🎯 **Weltklasse** (Rule of 40: {round(metrics['rule_of_40'], 1)}%)")
            st.caption("Perfekte Balance zwischen Wachstum & Profitabilität")
        elif metrics['rule_of_40'] > 20:
            st.info(f"✅ **Solide** (Rule of 40: {round(metrics['rule_of_40'], 1)}%)")
        else:
            st.warning(f"⚠️ **Schwach** (Rule of 40: {round(metrics['rule_of_40'], 1)}%)")
        
        if metrics['fcf_yield'] > 5:
            st.success(f"💰 **Viel Cashflow** (FCF Yield: {round(metrics['fcf_yield'], 1)}%)")
        elif metrics['fcf_yield'] > 2:
            st.info(f"✅ Akzeptabel (FCF Yield: {round(metrics['fcf_yield'], 1)}%)")
    
    st.divider()
    
    st.markdown("### 🤔 Der Camus / Bernays / Taleb Check")
    st.info("""
    **Ist das echte operative Exzellenz oder nur Hype-Betäubung?**
    
    - **Operative Metriken:** Rule of 40, FCF Margin, Burggraben
    - **Finanzielle Stabilität:** Schuldenquote, Liquidität
    - **Bewertung:** KGV vs. Wachstum (PEG-Ratio)
    """)

# ============= TAB 4: DETAILS =============
with tab4:
    st.subheader("📋 Detaillierte Metriken-Übersicht")
    
    # Create detailed dataframe
    details_data = {
        "Kategorie": [
            "Wachstum & Profitabilität",
            "", "",
            "Bewertung",
            "", "",
            "Finanzielle Stabilität",
            "", "",
            "Risiko & Volatilität",
            ""
        ],
        "Metrik": [
            "Rule of 40", "Revenue Growth", "FCF Margin",
            "Trailing P/E", "Forward P/E", "FCF Yield",
            "Debt/Equity", "Schuldenquote", "Marktkapitalisierung",
            "Beta", "52W Range"
        ],
        "Wert": [
            f"{round(metrics['rule_of_40'], 2)}%",
            f"{round(metrics['rev_growth'], 2)}%",
            f"{round(metrics['fcf_margin'], 2)}%",
            f"{round(metrics['trailing_pe'], 2)}" if metrics['trailing_pe'] > 0 else "N/A",
            f"{round(metrics['forward_pe'], 2)}" if metrics['forward_pe'] > 0 else "N/A",
            f"{round(metrics['fcf_yield'], 2)}%",
            f"{round(metrics['debt_to_equity'], 2)}×",
            f"{round(metrics['debt_to_equity'] * 100, 2)}%",
            f"${round(metrics['market_cap'] / 1e9, 2)}B",
            f"{round(metrics['beta'], 2)}",
            f"${round(metrics['52w_low'], 2)} - ${round(metrics['52w_high'], 2)}"
        ],
        "Status": [
            "✅" if conditions['rule_of_40_strong'] else "⚠️",
            "✅" if metrics['rev_growth'] > 15 else "⚠️",
            "✅" if metrics['fcf_margin'] > 15 else "⚠️",
            "✅" if 15 < metrics['trailing_pe'] < 30 else "⚠️",
            "✅" if 15 < metrics['forward_pe'] < 30 else "⚠️",
            "✅" if conditions['fcf_yield_good'] else "⚠️",
            "✅" if conditions['debt_low'] else "⚠️",
            "✅" if metrics['debt_to_equity'] < 0.5 else "⚠️",
            "✅",
            "✅" if conditions['beta_stable'] else "⚠️",
            "ℹ️"
        ]
    }
    
    df_details = pd.DataFrame(details_data)
    st.dataframe(df_details, use_container_width=True, hide_index=True)
    
    # Score breakdown
    with st.expander("📊 Score-Berechnung", expanded=False):
        st.markdown(f"""
        **Positive Faktoren:**
        - Rule of 40 > 40: +20 Punkte {'✅' if conditions['rule_of_40_strong'] else '❌'}
        - FCF Yield > 3%: +15 Punkte {'✅' if conditions['fcf_yield_good'] else '❌'}
        - Bruttomarge > 50%: +8 Punkte {'✅' if conditions['gross_margin_strong'] else '❌'}
        - Rule of 40 > 50: +5 Punkte {'✅' if metrics['rule_of_40'] > 50 else '❌'}
        
        **Negative Faktoren:**
        - KGV > 60: -20 Punkte {'❌' if metrics['pe_to_use'] > 60 else '✅'}
        - KGV > 40: -10 Punkte {'❌' if 40 < metrics['pe_to_use'] < 60 else '✅'}
        - D/E > 2.0: -10 Punkte {'❌' if metrics['debt_to_equity'] > 2.0 else '✅'}
        - Beta > 1.5: -8 Punkte {'❌' if metrics['beta'] > 1.5 else '✅'}
        
        **Finaler Score: {score}/45**
        """)

# Footer
st.divider()
st.caption(
    f"📊 Datenquelle: Yahoo Finance | Stand: {datetime.now().strftime('%d.%m.%Y %H:%M')} "
    f"| ⚠️ Keine Anlageberatung | Nur zu Informationszwecken"
)
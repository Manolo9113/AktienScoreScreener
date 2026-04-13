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

# ==================== CSS ====================
st.markdown("""
<style>
    .main { background: #0a0e27; color: #e8eef7; }
    h1 { font-size: 1.8rem; margin-bottom: 0.3rem; }
    .stTabs [data-baseweb="tab"] { font-size: 0.95rem; padding: 10px 14px; }
    @media (max-width: 640px) {
        h1 { font-size: 1.6rem; }
    }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Aktien-Tool Bäumer")
st.caption("Operative Exzellenz • Faire Bewertung • Langfristige Qualität")

# ==================== SESSION STATE ====================
if "ticker" not in st.session_state:
    st.session_state.ticker = "AVGO"

# ==================== SIDEBAR ====================
with st.sidebar:
    st.header("🔎 Ticker")
    ticker_input = st.text_input(
        "Aktien-Ticker", 
        value=st.session_state.ticker,
        placeholder="z.B. MSFT, NVDA"
    ).upper().strip()
    
    if ticker_input and ticker_input != st.session_state.ticker:
        st.session_state.ticker = ticker_input
        st.rerun()
    
    st.divider()
    st.markdown("**Schnellzugriff**")
    popular = ["MSFT", "AAPL", "NVDA", "GOOGL", "AMZN", "META"]
    cols = st.columns(3)
    for i, t in enumerate(popular):
        with cols[i % 3]:
            if st.button(t, use_container_width=True, key=f"btn_{t}"):
                st.session_state.ticker = t
                st.rerun()

ticker = st.session_state.ticker

# ==================== CACHED DATA ====================
@st.cache_data(ttl=1800, show_spinner=False)
def load_stock_data(ticker: str):
    stock = yf.Ticker(ticker)
    info = stock.info
    hist = stock.history(period="5y")
    return info, hist

if not ticker:
    st.warning("Bitte einen Ticker eingeben")
    st.stop()

with st.spinner(f"Lade {ticker}..."):
    try:
        info, hist = load_stock_data(ticker)
        
        if hist.empty or len(info) < 5:
            st.error("Keine Daten für diesen Ticker gefunden. Bitte anderen probieren.")
            st.stop()

        current_price = float(hist['Close'].iloc[-1])
        company_name = info.get('longName', ticker)
        sector = info.get('sector', 'Unbekannt')

        # Tages-Performance (für den neuen Metric)
        daily_change_pct = hist['Close'].pct_change().iloc[-1] * 100 if len(hist) > 1 else 0

        market_cap = info.get('marketCap', 0) or 1
        fcf = info.get('freeCashflow', 0) or 0
        fcf_yield = (fcf / market_cap * 100) if market_cap > 0 else 0
        rev_growth = (info.get('revenueGrowth') or 0) * 100
        rule_of_40 = rev_growth + fcf_yield
        gross_margin = (info.get('grossMargins') or 0) * 100
        
        trailing_pe = info.get('trailingPE') or 0
        forward_pe = info.get('forwardPE') or trailing_pe or 0
        pe_to_use = forward_pe if forward_pe > 0 else trailing_pe
        
        debt = info.get('debtToEquity') or 0
        debt_to_equity = debt / 100 if debt > 10 else debt
        beta = info.get('beta') or 1.0
        shares_outstanding = (info.get('sharesOutstanding') or 0) / 1_000_000

    except Exception as e:
        st.error(f"Fehler beim Laden von {ticker}: {str(e)[:120]}")
        st.stop()

# ==================== NEUER, WEICHERER & TRANSPARENTER SCORE ====================
rule_points = 18 if rule_of_40 > 35 else 6
fcf_points = 12 if fcf_yield > 2 else 4
margin_points = 10 if gross_margin > 50 else 5
rule_bonus = 5 if rule_of_40 > 45 else 0

pe_penalty = -16 if pe_to_use > 70 else -9 if pe_to_use > 50 else 0
debt_penalty = -8 if debt_to_equity > 2.0 else 0
beta_penalty = -7 if beta > 1.6 else 0

score = rule_points + fcf_points + margin_points + rule_bonus + pe_penalty + debt_penalty + beta_penalty
score = max(0, min(score, 45))

status = "🚀 ELITE-QUALITÄT" if score >= 36 else "✅ Gute Qualität" if score >= 28 else "🟡 Vorsicht" if score >= 18 else "🔴 Erhebliche Bedenken"
color = "green" if score >= 28 else "orange" if score >= 18 else "red"

# ==================== TABS ====================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Überblick", "📈 Growth Chart", "💰 Finanzentwicklung",
    "📋 Bilanz & Struktur", "⚖️ Bewertung & Risiko"
])

with tab1:
    # NEU: Aktueller Kurs + Tages-Performance direkt oben
    st.metric(
        label=f"**{company_name} ({ticker})**",
        value=f"${current_price:,.2f}",
        delta=f"{daily_change_pct:+.2f}% heute"
    )
    st.caption(f"Sektor: {sector}")

    # Score-Box
    st.markdown(f"""
    <div style="background:#1a2338; padding:1.5rem; border-radius:14px; text-align:center; border:2px solid {'#22c55e' if color=='green' else '#f97316' if color=='orange' else '#ef4444'}">
        <h2 style="margin:0; color:{'#22c55e' if color=='green' else '#f97316' if color=='orange' else '#ef4444'}">{score}/45</h2>
        <p style="margin:0.4rem 0 0 0; font-size:1.15rem;">{status}</p>
    </div>
    """, unsafe_allow_html=True)

    # NEU: Score-Breakdown (transparent)
    with st.expander("📊 Warum genau diese Punktzahl? (Score-Breakdown)"):
        st.write(f"**Rule of 40** ({round(rule_of_40,1)}%) → **{rule_points} Punkte**")
        st.write(f"**FCF Yield** ({round(fcf_yield,1)}%) → **{fcf_points} Punkte**")
        st.write(f"**Bruttomarge** ({round(gross_margin,1)}%) → **{margin_points} Punkte**")
        st.write(f"Rule of 40 > 45% → **{rule_bonus} Bonus-Punkte**")
        st.write(f"**KGV** ({round(pe_to_use,1)}) → **{pe_penalty} Punkte**")
        st.write(f"**Debt/Equity** ({round(debt_to_equity,2)}×) → **{debt_penalty} Punkte**")
        st.write(f"**Beta** ({round(beta,2)}) → **{beta_penalty} Punkte**")

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Rule of 40", f"{round(rule_of_40, 1)}%")
    with c2: st.metric("FCF Yield", f"{round(fcf_yield, 1)}%")
    with c3: st.metric("Forward P/E", f"{round(pe_to_use, 1)}" if pe_to_use > 0 else "N/A")

with tab2:
    st.subheader("📈 5-Jahres-Growth Chart")
    hist = hist.copy()
    hist['EMA200'] = hist['Close'].rolling(window=200).mean()
    last_ema = hist['EMA200'].iloc[-1] if not pd.isna(hist['EMA200'].iloc[-1]) else current_price

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='Kurs', line=dict(color='#60a5fa', width=2.5)))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA200'], name='EMA 200', line=dict(color='#fbbf24', dash='dot')))

    # NEU: realistische, lineare Zonen (kein Log mehr!)
    fig.add_hrect(
        y0=last_ema * 0.82, y1=last_ema,
        fillcolor="rgba(34,197,94,0.22)", line_width=0,
        annotation_text="🟢 Kaufzone (unterstützt)"
    )
    fig.add_hrect(
        y0=last_ema, y1=hist['Close'].max() * 1.12,
        fillcolor="rgba(239,68,68,0.22)", line_width=0,
        annotation_text="🔴 Teuer / Verkaufszone"
    )

    # NEU: Aktueller Kurs als dicke Linie
    fig.add_hline(
        y=current_price,
        line_dash="dash",
        line_color="#60a5fa",
        line_width=2.5,
        annotation_text=f"Aktueller Kurs ${current_price:,.2f}",
        annotation_position="top right"
    )

    fig.update_layout(
        height=480,
        template="plotly_dark",
        yaxis_type="linear",          # ← jetzt linear → viel schöner!
        hovermode="x unified",
        xaxis_rangeslider_visible=True
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("🟢 Unter ~18 % der EMA 200 = Kaufzone | 🔴 Über EMA 200 = Teuer")

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

st.caption("Daten von Yahoo Finance • Stand: gerade eben • Keine Anlageberatung")
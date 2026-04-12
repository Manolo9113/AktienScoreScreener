import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(
page_title=“Aktien-Tool Bäumer”,
page_icon=“🛡️”,
layout=“wide”,
initial_sidebar_state=“collapsed”
)

st.markdown(”””

<style>
    .main { background: #0a0e27; color: #e8eef7; }
    h1 { font-size: 1.8rem; margin-bottom: 0.3rem; }
    .stTabs [data-baseweb="tab"] { font-size: 0.95rem; padding: 10px 14px; }
    @media (max-width: 640px) { h1 { font-size: 1.6rem; } }
</style>

“””, unsafe_allow_html=True)

st.title(“🛡️ Aktien-Tool Bäumer”)
st.caption(“Operative Exzellenz • Faire Bewertung • Langfristige Qualität”)

with st.sidebar:
st.header(“🔎 Ticker”)
ticker = st.text_input(“Aktien-Ticker”, value=“AVGO”, placeholder=“z.B. MSFT, NVDA”).upper().strip()
st.divider()
st.markdown(”**Schnellzugriff**”)
popular = [“MSFT”, “AAPL”, “NVDA”, “GOOGL”, “AMZN”, “META”]
cols = st.columns(3)
for i, t in enumerate(popular):
with cols[i % 3]:
if st.button(t, use_container_width=True):
ticker = t
st.rerun()

def safe(val, fallback=0.0):
try:
r = float(val)
return r if r == r else fallback
except (TypeError, ValueError):
return fallback

def fmt_b(val):
v = safe(val)
return f”${v/1e9:.2f}B” if v != 0 else “N/A”

if ticker:
with st.spinner(f”Lade {ticker}…”):
try:
stock = yf.Ticker(ticker)
info  = stock.info
hist  = stock.history(period=“5y”)
if hist.empty or not info:
st.error(“Keine Daten gefunden.”)
st.stop()

```
        current_price  = safe(hist['Close'].iloc[-1])
        company_name   = info.get('longName') or ticker
        sector         = info.get('sector') or 'N/A'
        market_cap     = safe(info.get('marketCap'), 1) or 1
        free_cashflow  = safe(info.get('freeCashflow'))
        operating_cf   = safe(info.get('operatingCashflow'))
        total_revenue  = safe(info.get('totalRevenue'))
        total_debt     = safe(info.get('totalDebt'))
        total_cash     = safe(info.get('totalCash'))
        fcf_yield      = free_cashflow / market_cap * 100
        rev_growth     = safe(info.get('revenueGrowth')) * 100
        rule_of_40     = rev_growth + fcf_yield
        gross_margin   = safe(info.get('grossMargins')) * 100
        op_margin      = safe(info.get('operatingMargins')) * 100
        net_margin     = safe(info.get('profitMargins')) * 100
        trailing_pe    = safe(info.get('trailingPE'))
        forward_pe     = safe(info.get('forwardPE'))
        pe_to_use      = forward_pe if forward_pe > 0 else trailing_pe
        trailing_eps   = safe(info.get('trailingEps'))
        peg_ratio      = safe(info.get('pegRatio'))
        price_to_sales = safe(info.get('priceToSalesTrailing12Months'))
        price_to_book  = safe(info.get('priceToBook'))
        ev_to_ebitda   = safe(info.get('enterpriseToEbitda'))
        dte_raw        = safe(info.get('debtToEquity'))
        debt_to_equity = (dte_raw / 100) if dte_raw > 10 else dte_raw
        current_ratio  = safe(info.get('currentRatio'))
        beta           = safe(info.get('beta'), 1.0) or 1.0
        shares_out     = safe(info.get('sharesOutstanding')) / 1_000_000
        div_yield      = safe(info.get('dividendYield')) * 100
        roe            = safe(info.get('returnOnEquity')) * 100
        roa            = safe(info.get('returnOnAssets')) * 100
    except Exception as e:
        st.error(f"Fehler: {str(e)[:200]}")
        st.stop()

# SCORE
score = 0
score_details = []
def add(pts, label, good):
    score_details.append((label, f"+{pts}" if pts >= 0 else str(pts),
                           "#22c55e" if good == "green" else "#f97316" if good == "orange" else "#ef4444"))
    return pts

score += add(18 if rule_of_40 > 40 else 6,
             f"Rule of 40: {rule_of_40:.1f}% ({'> 40%' if rule_of_40 > 40 else '≤ 40%'})",
             "green" if rule_of_40 > 40 else "orange")
score += add(12 if fcf_yield > 3 else 4,
             f"FCF Yield: {fcf_yield:.1f}%", "green" if fcf_yield > 3 else "orange")
score += add(10 if gross_margin > 55 else 5,
             f"Bruttomarge: {gross_margin:.1f}%", "green" if gross_margin > 55 else "orange")
if rule_of_40 > 50:
    score += add(5, "Rule of 40 Bonus (> 50%)", "green")
if pe_to_use > 65:
    score += add(-16, f"Forward P/E zu hoch ({pe_to_use:.0f}x)", "red")
elif pe_to_use > 45:
    score += add(-9, f"Forward P/E erhöht ({pe_to_use:.0f}x)", "orange")
if debt_to_equity > 2.0:
    score += add(-8, f"Hohe Verschuldung (D/E {debt_to_equity:.2f}x)", "red")
if beta > 1.6:
    score += add(-7, f"Hohe Volatilität (Beta {beta:.2f})", "red")

score = max(0, min(score, 45))
status    = ("🚀 ELITE-QUALITÄT" if score >= 36 else "✅ Gute Qualität"
             if score >= 28 else "🟡 Vorsicht" if score >= 18 else "🔴 Erhebliche Bedenken")
hex_color = "#22c55e" if score >= 28 else "#f97316" if score >= 18 else "#ef4444"

# TABS
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Überblick", "📈 Growth Chart", "💰 Finanzentwicklung",
    "📋 Bilanz & Struktur", "⚖️ Bewertung & Risiko"
])

with tab1:
    st.subheader(f"{company_name} ({ticker})")
    st.caption(f"Sektor: {sector}")
    st.markdown(f"""
    <div style="background:#1a2338;padding:1.5rem;border-radius:14px;
                text-align:center;border:2px solid {hex_color};margin-bottom:1rem;">
        <h2 style="margin:0;color:{hex_color}">{score}/45</h2>
        <p style="margin:0.4rem 0 0 0;font-size:1.15rem;">{status}</p>
    </div>""", unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Kurs", f"${current_price:.2f}")
    with c2: st.metric("Rule of 40", f"{rule_of_40:.1f}%")
    with c3: st.metric("FCF Yield", f"{fcf_yield:.1f}%")
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Bruttomarge", f"{gross_margin:.1f}%")
    with c2: st.metric("Forward P/E", f"{pe_to_use:.1f}x" if pe_to_use > 0 else "N/A")
    with c3: st.metric("Beta", f"{beta:.2f}")
    st.divider()
    st.markdown("**Score-Aufschlüsselung**")
    for lbl, pts, clr in score_details:
        st.markdown(f"<span style='color:{clr};font-weight:600'>{pts}</span>&nbsp; {lbl}",
                    unsafe_allow_html=True)

with tab2:
    st.subheader("📈 5-Jahres-Growth Chart")
    hist['EMA200'] = hist['Close'].rolling(window=200).mean()
    ema_clean = hist['EMA200'].dropna()
    last_ema  = float(ema_clean.iloc[-1]) if not ema_clean.empty else current_price
    price_max = float(hist['Close'].max()) * 1.35
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='Kurs',
                              line=dict(color='#60a5fa', width=2.5)))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA200'], name='EMA 200',
                              line=dict(color='#fbbf24', dash='dot', width=1.8)))
    fig.add_hrect(y0=0, y1=last_ema, fillcolor="rgba(34,197,94,0.15)", line_width=0,
                  annotation_text="🟢 Kaufzone", annotation_position="top left")
    fig.add_hrect(y0=last_ema, y1=price_max, fillcolor="rgba(239,68,68,0.15)", line_width=0,
                  annotation_text="🔴 Zu teuer", annotation_position="top left")
    fig.update_layout(height=460, template="plotly_dark", yaxis_type="log",
                       hovermode="x unified", margin=dict(l=10,r=10,t=30,b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("🟢 Unter EMA 200 = Kaufzone  |  🔴 Über EMA 200 = Zu teuer")
    c1,c2,c3 = st.columns(3)
    with c1:
        p1 = ((hist['Close'].iloc[-1]/hist['Close'].iloc[-252])-1)*100 if len(hist)>252 else 0
        st.metric("1 Jahr", f"{p1:+.1f}%")
    with c2:
        p3 = ((hist['Close'].iloc[-1]/hist['Close'].iloc[-756])-1)*100 if len(hist)>756 else 0
        st.metric("3 Jahre", f"{p3:+.1f}%")
    with c3:
        p5 = ((hist['Close'].iloc[-1]/hist['Close'].iloc[0])-1)*100 if len(hist)>5 else 0
        st.metric("5 Jahre", f"{p5:+.1f}%")

with tab3:
    st.subheader("💰 Cashflow & Ertrag")
    c1,c2 = st.columns(2)
    with c1:
        st.metric("Operativer Cashflow", fmt_b(operating_cf))
        st.metric("Free Cash Flow",      fmt_b(free_cashflow))
        st.metric("Umsatz (TTM)",        fmt_b(total_revenue))
    with c2:
        st.metric("EPS (Trailing)",      f"${trailing_eps:.2f}" if trailing_eps else "N/A")
        st.metric("Umsatzwachstum",      f"{rev_growth:.1f}%",
                  delta="Stark" if rev_growth>15 else "Moderat" if rev_growth>5 else "Schwach")
        st.metric("FCF Yield",           f"{fcf_yield:.1f}%")
    st.divider()
    st.subheader("Margen")
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Bruttomarge",     f"{gross_margin:.1f}%")
    with c2: st.metric("Operative Marge", f"{op_margin:.1f}%")
    with c3: st.metric("Nettomarge",       f"{net_margin:.1f}%")
    if any([gross_margin, op_margin, net_margin]):
        fig_m = go.Figure(go.Bar(
            x=["Bruttomarge","Op. Marge","Nettomarge"],
            y=[gross_margin, op_margin, net_margin],
            marker_color=["#22c55e","#60a5fa","#a78bfa"],
            text=[f"{v:.1f}%" for v in [gross_margin, op_margin, net_margin]],
            textposition="outside"
        ))
        fig_m.update_layout(height=270, template="plotly_dark",
                             yaxis_title="%", margin=dict(l=10,r=10,t=20,b=10))
        st.plotly_chart(fig_m, use_container_width=True)
    st.divider()
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("ROE", f"{roe:.1f}%" if roe else "N/A")
    with c2: st.metric("ROA", f"{roa:.1f}%" if roa else "N/A")
    with c3: st.metric("Dividendenrendite", f"{div_yield:.2f}%" if div_yield>0 else "Keine")

with tab4:
    st.subheader("📋 Bilanzstruktur")
    net_debt = total_debt - total_cash
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Gesamtschulden",     fmt_b(total_debt))
    with c2: st.metric("Cash & Äquivalente", fmt_b(total_cash))
    with c3: st.metric("Nettoverschuldung",
                        fmt_b(net_debt) if (total_debt or total_cash) else "N/A",
                        delta="Netto-Cash ✅" if net_debt<0 else "Verschuldet")
    st.divider()
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Debt/Equity",  f"{debt_to_equity:.2f}x" if debt_to_equity else "N/A",
                        delta="OK" if debt_to_equity<1 else "Moderat" if debt_to_equity<2 else "Hoch ⚠️")
    with c2: st.metric("Current Ratio",f"{current_ratio:.2f}x" if current_ratio else "N/A",
                        delta="Liquide" if current_ratio>1.5 else "Knapp ⚠️")
    with c3: st.metric("EV/EBITDA",    f"{ev_to_ebitda:.1f}x"  if ev_to_ebitda else "N/A")
    c1,c2 = st.columns(2)
    with c1: st.metric("Aktienanzahl", f"{shares_out:.1f} Mio" if shares_out>0 else "N/A")
    with c2: st.metric("Beta",         f"{beta:.2f}")
    if total_debt>0 or total_cash>0:
        fig_dc = go.Figure(go.Bar(
            x=["Schulden","Cash"],
            y=[total_debt/1e9, total_cash/1e9],
            marker_color=["#ef4444","#22c55e"],
            text=[f"${v/1e9:.2f}B" for v in [total_debt, total_cash]],
            textposition="outside"
        ))
        fig_dc.update_layout(height=250, template="plotly_dark",
                              yaxis_title="Mrd. USD", margin=dict(l=10,r=10,t=20,b=10))
        st.plotly_chart(fig_dc, use_container_width=True)
    st.markdown(f"[📂 Bilanz auf Yahoo Finance ↗](https://finance.yahoo.com/quote/{ticker}/balance-sheet)")

with tab5:
    st.subheader("⚖️ Bewertungskennzahlen")
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Trailing P/E", f"{trailing_pe:.1f}x" if trailing_pe>0 else "N/A")
    with c2: st.metric("Forward P/E",  f"{forward_pe:.1f}x"  if forward_pe>0  else "N/A")
    with c3: st.metric("PEG Ratio",    f"{peg_ratio:.2f}x"   if peg_ratio>0   else "N/A",
                        delta="Günstig" if 0<peg_ratio<1.5 else "Teuer ⚠️" if peg_ratio>=1.5 else "")
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Price/Sales", f"{price_to_sales:.1f}x" if price_to_sales>0 else "N/A")
    with c2: st.metric("Price/Book",  f"{price_to_book:.1f}x"  if price_to_book>0  else "N/A")
    with c3: st.metric("EV/EBITDA",   f"{ev_to_ebitda:.1f}x"   if ev_to_ebitda>0   else "N/A")
    st.markdown(f"**Branchenübliches KGV:** {'25–35' if 'Technology' in sector else '15–25'}")
    if pe_to_use > 65:
        st.warning("⚠️ Sehr hohes KGV – Wachstumsnarrativ muss perfekt bleiben.")
    elif pe_to_use > 45:
        st.warning("⚠️ Erhöhtes KGV – wenig Spielraum für Enttäuschungen.")
    elif pe_to_use > 0:
        st.success("✅ Bewertung im vernünftigen Bereich.")
    st.divider()
    st.subheader("🎯 Risiko-Ampel")
    def ampel(g, y, lg, ly, lr):
        st.markdown(f"{'🟢' if g else '🟡' if y else '🔴'} {lg if g else ly if y else lr}")
    ampel(beta<1.2, beta<1.6,
          f"Stabile Aktie (Beta {beta:.2f})",
          f"Moderate Volatilität (Beta {beta:.2f})",
          f"Hohe Volatilität (Beta {beta:.2f})")
    ampel(0<pe_to_use<=30, pe_to_use<=50,
          f"Faire Bewertung (P/E {pe_to_use:.1f}x)",
          f"Erhöhte Bewertung (P/E {pe_to_use:.1f}x)",
          f"Sehr teuer (P/E {pe_to_use:.1f}x)" if pe_to_use>0 else "P/E nicht verfügbar")
    ampel(debt_to_equity<1, debt_to_equity<2,
          f"Geringe Verschuldung (D/E {debt_to_equity:.2f}x)",
          f"Moderate Verschuldung (D/E {debt_to_equity:.2f}x)",
          f"Hohe Verschuldung (D/E {debt_to_equity:.2f}x)" if debt_to_equity>0 else "D/E nicht verfügbar")
    ampel(gross_margin>55, gross_margin>30,
          f"Starke Bruttomarge ({gross_margin:.1f}%) – Wettbewerbsvorteil",
          f"Mittlere Bruttomarge ({gross_margin:.1f}%)",
          f"Niedrige Bruttomarge ({gross_margin:.1f}%) – Margendruck")
    ampel(rule_of_40>50, rule_of_40>40,
          f"Exzellente Rule of 40 ({rule_of_40:.1f}%)",
          f"Rule of 40 erfüllt ({rule_of_40:.1f}%)",
          f"Rule of 40 nicht erfüllt ({rule_of_40:.1f}%)")
    st.divider()
    st.markdown(f"""
    <div style="background:#1a2338;padding:1.1rem;border-radius:12px;
                border-left:4px solid {hex_color};">
        <strong>Gesamtbewertung: {score}/45 — {status}</strong><br>
        <span style="color:#94a3b8;font-size:0.88rem;">
        Keine Anlageberatung – rein informativ.
        </span>
    </div>""", unsafe_allow_html=True)

st.caption("Daten von Yahoo Finance • Keine Anlageberatung")
```

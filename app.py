import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(
page_title=‘Aktien-Tool Baeumer’,
page_icon=‘shield’,
layout=‘wide’,
initial_sidebar_state=‘collapsed’
)

st.markdown(
‘<style>’
‘.main { background: #0a0e27; color: #e8eef7; }’
‘h1 { font-size: 1.8rem; margin-bottom: 0.3rem; }’
‘@media (max-width: 640px) { h1 { font-size: 1.6rem; } }’
‘</style>’,
unsafe_allow_html=True
)

st.title(‘Aktien-Tool Baeumer’)
st.caption(‘Operative Exzellenz - Faire Bewertung - Langfristige Qualitaet’)

if ‘ticker’ not in st.session_state:
st.session_state.ticker = ‘AVGO’

with st.sidebar:
st.header(‘Ticker’)
ticker_input = st.text_input(‘Aktien-Ticker’, value=st.session_state.ticker, placeholder=‘z.B. MSFT, NVDA’).upper().strip()
if ticker_input and ticker_input != st.session_state.ticker:
st.session_state.ticker = ticker_input
st.rerun()
st.divider()
st.markdown(’**Schnellzugriff**’)
popular = [‘MSFT’, ‘AAPL’, ‘NVDA’, ‘GOOGL’, ‘AMZN’, ‘META’]
cols = st.columns(3)
for i, t in enumerate(popular):
with cols[i % 3]:
if st.button(t, use_container_width=True, key=‘btn_’ + t):
st.session_state.ticker = t
st.rerun()

ticker = st.session_state.ticker

@st.cache_data(ttl=1800, show_spinner=False)
def load_stock_data(sym):
stock = yf.Ticker(sym)
return stock.info, stock.history(period=‘5y’)

def safe(val, fallback=0.0):
try:
r = float(val)
return r if r == r else fallback
except (TypeError, ValueError):
return fallback

def fmt_b(val):
v = safe(val)
return (’$’ + f’{v/1e9:.2f}’ + ‘B’) if v != 0 else ‘N/A’

if not ticker:
st.warning(‘Bitte einen Ticker eingeben’)
st.stop()

with st.spinner(’Lade ’ + ticker + ‘…’):
try:
info, hist = load_stock_data(ticker)
if hist.empty or len(info) < 5:
st.error(‘Keine Daten gefunden. Anderen Ticker probieren.’)
st.stop()

```
    hist = hist.copy()
    current_price  = safe(hist['Close'].iloc[-1])
    daily_chg      = hist['Close'].pct_change().iloc[-1] * 100 if len(hist) > 1 else 0
    company_name   = info.get('longName') or ticker
    sector         = info.get('sector') or 'Unbekannt'
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
    st.error('Fehler: ' + str(e)[:200])
    st.stop()
```

rule_pts   = 18 if rule_of_40 > 35 else 6
fcf_pts    = 12 if fcf_yield > 2  else 4
margin_pts = 10 if gross_margin > 50 else 5
bonus_pts  = 5  if rule_of_40 > 45 else 0
pe_pen     = -16 if pe_to_use > 70 else -9 if pe_to_use > 50 else 0
debt_pen   = -8  if debt_to_equity > 2.0 else 0
beta_pen   = -7  if beta > 1.6 else 0
score = max(0, min(rule_pts + fcf_pts + margin_pts + bonus_pts + pe_pen + debt_pen + beta_pen, 45))

status = ‘ELITE’ if score >= 36 else ‘Gut’ if score >= 28 else ‘Vorsicht’ if score >= 18 else ‘Bedenken’
hx = ‘#22c55e’ if score >= 28 else ‘#f97316’ if score >= 18 else ‘#ef4444’

tab1, tab2, tab3, tab4, tab5 = st.tabs([
‘Ueberblick’, ‘Growth Chart’, ‘Finanzen’, ‘Bilanz’, ‘Bewertung’
])

with tab1:
st.metric(
label=company_name + ’ (’ + ticker + ‘)’,
value=’$’ + f’{current_price:,.2f}’,
delta=f’{daily_chg:+.2f}% heute’
)
st.caption(’Sektor: ’ + sector)

```
score_box = (
    '<div style=background:#1a2338;padding:1.5rem;border-radius:14px;'
    'text-align:center;border:2px solid ' + hx + ';>'
    '<h2 style=color:' + hx + ';>' + str(score) + '/45</h2>'
    '<p style=font-size:1.15rem;>' + status + '</p></div>'
)
st.markdown(score_box, unsafe_allow_html=True)

with st.expander('Score-Breakdown'):
    st.write('Rule of 40 (' + f'{rule_of_40:.1f}' + '%) -> ' + str(rule_pts) + ' Punkte')
    st.write('FCF Yield (' + f'{fcf_yield:.1f}' + '%) -> ' + str(fcf_pts) + ' Punkte')
    st.write('Bruttomarge (' + f'{gross_margin:.1f}' + '%) -> ' + str(margin_pts) + ' Punkte')
    st.write('Rule of 40 Bonus -> ' + str(bonus_pts) + ' Punkte')
    st.write('KGV-Abzug -> ' + str(pe_pen) + ' Punkte')
    st.write('Schulden-Abzug -> ' + str(debt_pen) + ' Punkte')
    st.write('Beta-Abzug -> ' + str(beta_pen) + ' Punkte')

c1, c2, c3 = st.columns(3)
with c1: st.metric('Kurs', '$' + f'{current_price:.2f}')
with c2: st.metric('Rule of 40', f'{rule_of_40:.1f}' + '%')
with c3: st.metric('FCF Yield', f'{fcf_yield:.1f}' + '%')
c1, c2, c3 = st.columns(3)
with c1: st.metric('Bruttomarge', f'{gross_margin:.1f}' + '%')
with c2: st.metric('Forward P/E', f'{pe_to_use:.1f}' + 'x' if pe_to_use > 0 else 'N/A')
with c3: st.metric('Beta', f'{beta:.2f}')
```

with tab2:
st.subheader(‘5-Jahres-Growth Chart’)
hist[‘EMA200’] = hist[‘Close’].rolling(window=200).mean()
ema_clean = hist[‘EMA200’].dropna()
last_ema = float(ema_clean.iloc[-1]) if not ema_clean.empty else current_price
price_max = float(hist[‘Close’].max()) * 1.12

```
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=hist.index, y=hist['Close'], name='Kurs',
    line=dict(color='#60a5fa', width=2.5)
))
fig.add_trace(go.Scatter(
    x=hist.index, y=hist['EMA200'], name='EMA 200',
    line=dict(color='#fbbf24', dash='dot', width=1.8)
))
fig.add_hrect(
    y0=last_ema * 0.82, y1=last_ema,
    fillcolor='rgba(34,197,94,0.22)', line_width=0,
    annotation_text='Kaufzone', annotation_position='top left'
)
fig.add_hrect(
    y0=last_ema, y1=price_max,
    fillcolor='rgba(239,68,68,0.22)', line_width=0,
    annotation_text='Teuer', annotation_position='top left'
)
fig.add_hline(
    y=current_price, line_dash='dash', line_color='#60a5fa', line_width=2,
    annotation_text='Kurs $' + f'{current_price:,.2f}',
    annotation_position='top right'
)
fig.update_layout(
    height=480, template='plotly_dark', yaxis_type='linear',
    hovermode='x unified', xaxis_rangeslider_visible=True,
    margin=dict(l=10, r=10, t=30, b=10)
)
st.plotly_chart(fig, use_container_width=True)
st.caption('Gruen: Kaufzone | Rot: Teuer')

c1, c2, c3 = st.columns(3)
with c1:
    p1 = ((hist['Close'].iloc[-1]/hist['Close'].iloc[-252])-1)*100 if len(hist)>252 else 0
    st.metric('1 Jahr', f'{p1:+.1f}' + '%')
with c2:
    p3 = ((hist['Close'].iloc[-1]/hist['Close'].iloc[-756])-1)*100 if len(hist)>756 else 0
    st.metric('3 Jahre', f'{p3:+.1f}' + '%')
with c3:
    p5 = ((hist['Close'].iloc[-1]/hist['Close'].iloc[0])-1)*100 if len(hist)>5 else 0
    st.metric('5 Jahre', f'{p5:+.1f}' + '%')
```

with tab3:
st.subheader(‘Finanzen’)
c1, c2 = st.columns(2)
with c1:
st.metric(‘Op. Cashflow’, fmt_b(operating_cf))
st.metric(‘Free Cash Flow’, fmt_b(free_cashflow))
st.metric(‘Umsatz (TTM)’, fmt_b(total_revenue))
with c2:
st.metric(‘EPS’, ‘$’ + f’{trailing_eps:.2f}’ if trailing_eps else ‘N/A’)
st.metric(‘Umsatzwachstum’, f’{rev_growth:.1f}’ + ‘%’)
st.metric(‘FCF Yield’, f’{fcf_yield:.1f}’ + ‘%’)
st.divider()
c1, c2, c3 = st.columns(3)
with c1: st.metric(‘Bruttomarge’, f’{gross_margin:.1f}’ + ‘%’)
with c2: st.metric(‘Op. Marge’, f’{op_margin:.1f}’ + ‘%’)
with c3: st.metric(‘Nettomarge’, f’{net_margin:.1f}’ + ‘%’)
if any([gross_margin, op_margin, net_margin]):
fig_m = go.Figure(go.Bar(
x=[‘Bruttomarge’, ‘Op. Marge’, ‘Nettomarge’],
y=[gross_margin, op_margin, net_margin],
marker_color=[’#22c55e’, ‘#60a5fa’, ‘#a78bfa’],
text=[f’{v:.1f}’ + ‘%’ for v in [gross_margin, op_margin, net_margin]],
textposition=‘outside’
))
fig_m.update_layout(height=270, template=‘plotly_dark’, yaxis_title=’%’,
margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(fig_m, use_container_width=True)
st.divider()
c1, c2, c3 = st.columns(3)
with c1: st.metric(‘ROE’, f’{roe:.1f}’ + ‘%’ if roe else ‘N/A’)
with c2: st.metric(‘ROA’, f’{roa:.1f}’ + ‘%’ if roa else ‘N/A’)
with c3: st.metric(‘Dividende’, f’{div_yield:.2f}’ + ‘%’ if div_yield > 0 else ‘Keine’)

with tab4:
st.subheader(‘Bilanz’)
net_debt = total_debt - total_cash
c1, c2, c3 = st.columns(3)
with c1: st.metric(‘Schulden’, fmt_b(total_debt))
with c2: st.metric(‘Cash’, fmt_b(total_cash))
with c3: st.metric(‘Netto-Schulden’, fmt_b(net_debt))
c1, c2, c3 = st.columns(3)
with c1: st.metric(‘Debt/Equity’, f’{debt_to_equity:.2f}’ + ‘x’ if debt_to_equity else ‘N/A’)
with c2: st.metric(‘Current Ratio’, f’{current_ratio:.2f}’ + ‘x’ if current_ratio else ‘N/A’)
with c3: st.metric(‘EV/EBITDA’, f’{ev_to_ebitda:.1f}’ + ‘x’ if ev_to_ebitda else ‘N/A’)
c1, c2 = st.columns(2)
with c1: st.metric(‘Aktien (Mio)’, f’{shares_out:.1f}’ if shares_out > 0 else ‘N/A’)
with c2: st.metric(‘Beta’, f’{beta:.2f}’)
if total_debt > 0 or total_cash > 0:
fig_dc = go.Figure(go.Bar(
x=[‘Schulden’, ‘Cash’],
y=[total_debt/1e9, total_cash/1e9],
marker_color=[’#ef4444’, ‘#22c55e’],
text=[’$’ + f’{v/1e9:.2f}’ + ‘B’ for v in [total_debt, total_cash]],
textposition=‘outside’
))
fig_dc.update_layout(height=250, template=‘plotly_dark’, yaxis_title=‘Mrd. USD’,
margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(fig_dc, use_container_width=True)
st.markdown(’[Bilanz auf Yahoo Finance](https://finance.yahoo.com/quote/’ + ticker + ‘/balance-sheet)’)

with tab5:
st.subheader(‘Bewertung & Risiko’)
c1, c2, c3 = st.columns(3)
with c1: st.metric(‘Trailing P/E’, f’{trailing_pe:.1f}’ + ‘x’ if trailing_pe > 0 else ‘N/A’)
with c2: st.metric(‘Forward P/E’, f’{forward_pe:.1f}’ + ‘x’ if forward_pe > 0 else ‘N/A’)
with c3: st.metric(‘PEG’, f’{peg_ratio:.2f}’ + ‘x’ if peg_ratio > 0 else ‘N/A’)
c1, c2, c3 = st.columns(3)
with c1: st.metric(‘P/S’, f’{price_to_sales:.1f}’ + ‘x’ if price_to_sales > 0 else ‘N/A’)
with c2: st.metric(‘P/B’, f’{price_to_book:.1f}’ + ‘x’ if price_to_book > 0 else ‘N/A’)
with c3: st.metric(‘EV/EBITDA’, f’{ev_to_ebitda:.1f}’ + ‘x’ if ev_to_ebitda > 0 else ‘N/A’)
if pe_to_use > 70:
st.warning(‘Sehr hohes KGV’)
elif pe_to_use > 50:
st.warning(‘Erhoehtes KGV’)
elif pe_to_use > 0:
st.success(‘Faire Bewertung’)
st.divider()
st.subheader(‘Risiko-Ampel’)
def ampel(g, y, lg, ly, lr):
icon = ‘GRUEN’ if g else ‘GELB’ if y else ‘ROT’
st.markdown(icon + ’ ’ + (lg if g else ly if y else lr))
ampel(beta<1.2, beta<1.6,
‘Stabile Aktie (Beta ’ + f’{beta:.2f}’ + ‘)’,
‘Moderate Volatilitaet (Beta ’ + f’{beta:.2f}’ + ‘)’,
‘Hohe Volatilitaet (Beta ’ + f’{beta:.2f}’ + ‘)’)
ampel(0<pe_to_use<=30, pe_to_use<=50,
‘Faire Bewertung (P/E ’ + f’{pe_to_use:.1f}’ + ‘x)’,
‘Erhoeht (P/E ’ + f’{pe_to_use:.1f}’ + ‘x)’,
‘Teuer (P/E ’ + f’{pe_to_use:.1f}’ + ‘x)’ if pe_to_use > 0 else ‘P/E N/A’)
ampel(debt_to_equity<1, debt_to_equity<2,
‘Geringe Schulden (D/E ’ + f’{debt_to_equity:.2f}’ + ‘x)’,
‘Moderate Schulden (D/E ’ + f’{debt_to_equity:.2f}’ + ‘x)’,
‘Hohe Schulden (D/E ’ + f’{debt_to_equity:.2f}’ + ‘x)’ if debt_to_equity > 0 else ‘D/E N/A’)
ampel(gross_margin>55, gross_margin>30,
‘Starke Marge (’ + f’{gross_margin:.1f}’ + ‘%)’,
‘Mittlere Marge (’ + f’{gross_margin:.1f}’ + ‘%)’,
‘Schwache Marge (’ + f’{gross_margin:.1f}’ + ‘%)’)
ampel(rule_of_40>50, rule_of_40>35,
‘Exzellente Rule of 40 (’ + f’{rule_of_40:.1f}’ + ‘%)’,
‘Rule of 40 ok (’ + f’{rule_of_40:.1f}’ + ‘%)’,
‘Rule of 40 schwach (’ + f’{rule_of_40:.1f}’ + ‘%)’)
st.divider()
final_box = (
‘<div style=background:#1a2338;padding:1.1rem;border-radius:12px;’
’border-left:4px solid ’ + hx + ‘;>’
’<b>Gesamtbewertung: ’ + str(score) + ’/45 - ’ + status + ‘</b>’
‘</div>’
)
st.markdown(final_box, unsafe_allow_html=True)

st.caption(‘Daten von Yahoo Finance - Keine Anlageberatung’)
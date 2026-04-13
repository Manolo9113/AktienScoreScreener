import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title=str(“Aktien-Tool”), layout=str(“wide”), initial_sidebar_state=str(“collapsed”))

st.markdown(”<style>.main{background:#0a0e27;color:#e8eef7}</style>”, unsafe_allow_html=True)
st.title(“Aktien-Tool Baeumer”)
st.caption(“Operative Exzellenz - Faire Bewertung - Langfristige Qualitaet”)

if “ticker” not in st.session_state:
st.session_state.ticker = “AVGO”

with st.sidebar:
st.header(“Ticker”)
inp = st.text_input(“Aktien-Ticker”, value=st.session_state.ticker).upper().strip()
if inp and inp != st.session_state.ticker:
st.session_state.ticker = inp
st.rerun()
st.divider()
st.markdown(”**Schnellzugriff**”)
for i, t in enumerate([“MSFT”,“AAPL”,“NVDA”,“GOOGL”,“AMZN”,“META”]):
with st.columns(3)[i % 3]:
if st.button(t, key=“b”+t, use_container_width=True):
st.session_state.ticker = t
st.rerun()

ticker = st.session_state.ticker

@st.cache_data(ttl=1800, show_spinner=False)
def load(sym):
s = yf.Ticker(sym)
return s.info, s.history(period=“5y”)

def safe(v, f=0.0):
try:
r = float(v)
return r if r==r else f
except: return f

def fmtb(v):
x = safe(v)
return f”${x/1e9:.2f}B” if x else “N/A”

if not ticker:
st.stop()

with st.spinner(f”Lade {ticker}…”):
try:
info, hist = load(ticker)
if hist.empty or len(info)<5:
st.error(“Keine Daten.”)
st.stop()
hist = hist.copy()
cp   = safe(hist[“Close”].iloc[-1])
dchg = hist[“Close”].pct_change().iloc[-1]*100 if len(hist)>1 else 0
name = info.get(“longName”) or ticker
sec  = info.get(“sector”) or “N/A”
mc   = safe(info.get(“marketCap”),1) or 1
fcf  = safe(info.get(“freeCashflow”))
ocf  = safe(info.get(“operatingCashflow”))
rev  = safe(info.get(“totalRevenue”))
dbt  = safe(info.get(“totalDebt”))
csh  = safe(info.get(“totalCash”))
fcfy = fcf/mc*100
rg   = safe(info.get(“revenueGrowth”))*100
r40  = rg+fcfy
gm   = safe(info.get(“grossMargins”))*100
om   = safe(info.get(“operatingMargins”))*100
nm   = safe(info.get(“profitMargins”))*100
tpe  = safe(info.get(“trailingPE”))
fpe  = safe(info.get(“forwardPE”))
pe   = fpe if fpe>0 else tpe
eps  = safe(info.get(“trailingEps”))
peg  = safe(info.get(“pegRatio”))
ps   = safe(info.get(“priceToSalesTrailing12Months”))
pb   = safe(info.get(“priceToBook”))
eve  = safe(info.get(“enterpriseToEbitda”))
dte  = safe(info.get(“debtToEquity”))
de   = dte/100 if dte>10 else dte
cr   = safe(info.get(“currentRatio”))
beta = safe(info.get(“beta”),1.0) or 1.0
shr  = safe(info.get(“sharesOutstanding”))/1e6
dy   = safe(info.get(“dividendYield”))*100
roe  = safe(info.get(“returnOnEquity”))*100
roa  = safe(info.get(“returnOnAssets”))*100
except Exception as e:
st.error(f”Fehler: {str(e)[:200]}”)
st.stop()

rp = 18 if r40>35 else 6
fp = 12 if fcfy>2  else 4
mp = 10 if gm>50   else 5
bp = 5  if r40>45  else 0
pp = -16 if pe>70 else -9 if pe>50 else 0
dp = -8  if de>2   else 0
vp = -7  if beta>1.6 else 0
score = max(0, min(rp+fp+mp+bp+pp+dp+vp, 45))
status = “ELITE” if score>=36 else “GUT” if score>=28 else “VORSICHT” if score>=18 else “BEDENKEN”
hx = “#22c55e” if score>=28 else “#f97316” if score>=18 else “#ef4444”

t1,t2,t3,t4,t5 = st.tabs([“Ueberblick”,“Chart”,“Finanzen”,“Bilanz”,“Bewertung”])

with t1:
st.metric(f”{name} ({ticker})”, f”${cp:,.2f}”, f”{dchg:+.2f}% heute”)
st.caption(f”Sektor: {sec}”)
st.markdown(f”<div style='background:#1a2338;padding:1.5rem;border-radius:14px;text-align:center;border:2px solid {hx}'><h2 style='color:{hx}'>{score}/45</h2><p>{status}</p></div>”, unsafe_allow_html=True)
with st.expander(“Score-Breakdown”):
for lbl,val in [(“Rule of 40”,rp),(“FCF Yield”,fp),(“Bruttomarge”,mp),(“Bonus”,bp),(“KGV”,pp),(“Schulden”,dp),(“Beta”,vp)]:
st.write(f”{lbl}: {val:+d} Punkte”)
c1,c2,c3 = st.columns(3)
with c1: st.metric(“Rule of 40”, f”{r40:.1f}%”)
with c2: st.metric(“FCF Yield”,  f”{fcfy:.1f}%”)
with c3: st.metric(“Forward P/E”,f”{pe:.1f}x” if pe>0 else “N/A”)
c1,c2,c3 = st.columns(3)
with c1: st.metric(“Bruttomarge”,f”{gm:.1f}%”)
with c2: st.metric(“Kurs”,       f”${cp:.2f}”)
with c3: st.metric(“Beta”,       f”{beta:.2f}”)

with t2:
hist[“EMA200”] = hist[“Close”].rolling(200).mean()
ec = hist[“EMA200”].dropna()
le = float(ec.iloc[-1]) if not ec.empty else cp
pm = float(hist[“Close”].max())*1.12
fig = go.Figure()
fig.add_trace(go.Scatter(x=hist.index,y=hist[“Close”],name=“Kurs”,line=dict(color=”#60a5fa”,width=2.5)))
fig.add_trace(go.Scatter(x=hist.index,y=hist[“EMA200”],name=“EMA200”,line=dict(color=”#fbbf24”,dash=“dot”)))
fig.add_hrect(y0=le*0.82,y1=le,fillcolor=“rgba(34,197,94,0.22)”,line_width=0,annotation_text=“Kaufzone”,annotation_position=“top left”)
fig.add_hrect(y0=le,y1=pm,fillcolor=“rgba(239,68,68,0.22)”,line_width=0,annotation_text=“Teuer”,annotation_position=“top left”)
fig.add_hline(y=cp,line_dash=“dash”,line_color=”#60a5fa”,annotation_text=f”${cp:,.2f}”,annotation_position=“top right”)
fig.update_layout(height=480,template=“plotly_dark”,hovermode=“x unified”,xaxis_rangeslider_visible=True)
st.plotly_chart(fig,use_container_width=True)
c1,c2,c3=st.columns(3)
with c1:
p1=((hist[“Close”].iloc[-1]/hist[“Close”].iloc[-252])-1)*100 if len(hist)>252 else 0
st.metric(“1 Jahr”,f”{p1:+.1f}%”)
with c2:
p3=((hist[“Close”].iloc[-1]/hist[“Close”].iloc[-756])-1)*100 if len(hist)>756 else 0
st.metric(“3 Jahre”,f”{p3:+.1f}%”)
with c3:
p5=((hist[“Close”].iloc[-1]/hist[“Close”].iloc[0])-1)*100 if len(hist)>5 else 0
st.metric(“5 Jahre”,f”{p5:+.1f}%”)

with t3:
c1,c2=st.columns(2)
with c1:
st.metric(“Op. Cashflow”,fmtb(ocf))
st.metric(“Free Cash Flow”,fmtb(fcf))
st.metric(“Umsatz TTM”,fmtb(rev))
with c2:
st.metric(“EPS”,f”${eps:.2f}” if eps else “N/A”)
st.metric(“Umsatzwachstum”,f”{rg:.1f}%”)
st.metric(“FCF Yield”,f”{fcfy:.1f}%”)
st.divider()
c1,c2,c3=st.columns(3)
with c1: st.metric(“Bruttomarge”,f”{gm:.1f}%”)
with c2: st.metric(“Op. Marge”,f”{om:.1f}%”)
with c3: st.metric(“Nettomarge”,f”{nm:.1f}%”)
if any([gm,om,nm]):
fm=go.Figure(go.Bar(x=[“Brutto”,“Op.”,“Netto”],y=[gm,om,nm],marker_color=[”#22c55e”,”#60a5fa”,”#a78bfa”],text=[f”{v:.1f}%” for v in [gm,om,nm]],textposition=“outside”))
fm.update_layout(height=250,template=“plotly_dark”,margin=dict(l=10,r=10,t=10,b=10))
st.plotly_chart(fm,use_container_width=True)
st.divider()
c1,c2,c3=st.columns(3)
with c1: st.metric(“ROE”,f”{roe:.1f}%” if roe else “N/A”)
with c2: st.metric(“ROA”,f”{roa:.1f}%” if roa else “N/A”)
with c3: st.metric(“Dividende”,f”{dy:.2f}%” if dy>0 else “Keine”)

with t4:
nd=dbt-csh
c1,c2,c3=st.columns(3)
with c1: st.metric(“Schulden”,fmtb(dbt))
with c2: st.metric(“Cash”,fmtb(csh))
with c3: st.metric(“Netto-Schulden”,fmtb(nd))
c1,c2,c3=st.columns(3)
with c1: st.metric(“Debt/Equity”,f”{de:.2f}x” if de else “N/A”)
with c2: st.metric(“Current Ratio”,f”{cr:.2f}x” if cr else “N/A”)
with c3: st.metric(“EV/EBITDA”,f”{eve:.1f}x” if eve else “N/A”)
c1,c2=st.columns(2)
with c1: st.metric(“Aktien (Mio)”,f”{shr:.1f}” if shr>0 else “N/A”)
with c2: st.metric(“Beta”,f”{beta:.2f}”)
if dbt>0 or csh>0:
fd=go.Figure(go.Bar(x=[“Schulden”,“Cash”],y=[dbt/1e9,csh/1e9],marker_color=[”#ef4444”,”#22c55e”],text=[f”${v/1e9:.2f}B” for v in [dbt,csh]],textposition=“outside”))
fd.update_layout(height=230,template=“plotly_dark”,margin=dict(l=10,r=10,t=10,b=10))
st.plotly_chart(fd,use_container_width=True)
st.markdown(f”[Bilanz auf Yahoo Finance](https://finance.yahoo.com/quote/{ticker}/balance-sheet)”)

with t5:
c1,c2,c3=st.columns(3)
with c1: st.metric(“Trailing P/E”,f”{tpe:.1f}x” if tpe>0 else “N/A”)
with c2: st.metric(“Forward P/E”,f”{fpe:.1f}x” if fpe>0 else “N/A”)
with c3: st.metric(“PEG”,f”{peg:.2f}x” if peg>0 else “N/A”)
c1,c2,c3=st.columns(3)
with c1: st.metric(“P/S”,f”{ps:.1f}x” if ps>0 else “N/A”)
with c2: st.metric(“P/B”,f”{pb:.1f}x” if pb>0 else “N/A”)
with c3: st.metric(“EV/EBITDA”,f”{eve:.1f}x” if eve>0 else “N/A”)
if pe>70: st.warning(“Sehr hohes KGV”)
elif pe>50: st.warning(“Erhoehtes KGV”)
elif pe>0: st.success(“Faire Bewertung”)
st.divider()
st.subheader(“Risiko-Ampel”)
def ampel(g,y,lg,ly,lr):
st.markdown((“GRUEN “ if g else “GELB “ if y else “ROT “)+(lg if g else ly if y else lr))
ampel(beta<1.2,beta<1.6,f”Stabil (Beta {beta:.2f})”,f”Moderat (Beta {beta:.2f})”,f”Volatil (Beta {beta:.2f})”)
ampel(0<pe<=30,pe<=50,f”Faire Bew. (P/E {pe:.1f}x)”,f”Erhoeht (P/E {pe:.1f}x)”,f”Teuer (P/E {pe:.1f}x)” if pe>0 else “P/E N/A”)
ampel(de<1,de<2,f”Geringe Schulden ({de:.2f}x)”,f”Moderate Schulden ({de:.2f}x)”,f”Hohe Schulden ({de:.2f}x)” if de>0 else “D/E N/A”)
ampel(gm>55,gm>30,f”Starke Marge ({gm:.1f}%)”,f”Mittlere Marge ({gm:.1f}%)”,f”Schwache Marge ({gm:.1f}%)”)
ampel(r40>50,r40>35,f”Exzellente R40 ({r40:.1f}%)”,f”R40 ok ({r40:.1f}%)”,f”R40 schwach ({r40:.1f}%)”)
st.divider()
st.markdown(f”<div style='background:#1a2338;padding:1rem;border-radius:12px;border-left:4px solid {hx}'><b>Gesamtbewertung: {score}/45 - {status}</b></div>”, unsafe_allow_html=True)

st.caption(“Daten von Yahoo Finance - Keine Anlageberatung”)
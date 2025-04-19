import streamlit as st
import requests
from lxml import html
import re
import yfinance as yf
import pandas as pd
import numpy as np

# ─── WACC CALCULATION ──────────────────────────────────────────────────────────

def get_tax_rate_gf(ticker: str) -> float:
    url = f"https://www.gurufocus.com/term/tax-rate/{ticker}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    tree = html.fromstring(resp.content)
    nodes = tree.xpath('/html/body/div[2]/div[2]/div/div/div/div[2]/h1/font')
    text = nodes[0].text_content().strip() if nodes else ""
    m = re.search(r"(\d+(?:\.\d+)?)%", text)
    return float(m.group(1)) / 100 if m else 0.21  # fallback

def get_risk_free_rate() -> float:
    data = yf.Ticker("^TNX").history(period="1d")["Close"]
    return data.iloc[-1] / 100 if not data.empty else 0.03

def compute_erp_range(rf: float) -> tuple[float, float]:
    return 0.085 - rf, 0.10 - rf

def get_raw_beta(ticker: str) -> float:
    beta = yf.Ticker(ticker).info.get("beta")
    return float(beta) if beta is not None else 1.0

def adjust_beta(raw_beta: float, tax: float, d_e: float):
    factor = (1 - tax) * d_e
    bu = raw_beta / (1 + factor)
    bl = bu * (1 + factor)
    badj = 0.67 * bl + 0.33
    return bu, bl, badj

def calculate_cost_of_debt(ticker: str):
    tk = yf.Ticker(ticker)
    qfin = tk.quarterly_financials
    rows = [r for r in qfin.index if "interest" in r.lower()]
    row = next((r for r in rows if "expense" in r.lower()), rows[0])
    ttm_int = abs(qfin.loc[row].iloc[:4].sum())
    info_debt = tk.info.get("totalDebt") or 0
    bd = info_debt if info_debt>0 else qfin.loc[[r for r in qfin.index if "debt" in r.lower()]].iloc[:,0].sum()
    return ttm_int, bd, (ttm_int/bd if bd else 0.05)

def compute_wacc_raw(ticker: str) -> float:
    tax = get_tax_rate_gf(ticker)
    rf  = get_risk_free_rate()
    erp_low, erp_high = compute_erp_range(rf)
    erp = (erp_low + erp_high)/2

    info      = yf.Ticker(ticker).info
    mc        = info.get("marketCap") or 0
    ttm_int, bd, kd = calculate_cost_of_debt(ticker)
    d_e       = bd/mc if mc else 0
    raw_b     = get_raw_beta(ticker)
    bu, bl, badj = adjust_beta(raw_b, tax, d_e)

    ke = rf + badj * erp
    we = mc / (mc + bd) if mc+bd else 0
    wd = bd / (mc + bd) if mc+bd else 0

    return we*ke + wd*kd*(1-tax)

# ─── DCF MODEL ─────────────────────────────────────────────────────────────────

def fetch_baseline(ticker):
    tk   = yf.Ticker(ticker)
    fin  = tk.financials.sort_index(axis=1)
    cf   = tk.cashflow.sort_index(axis=1)
    info = tk.info
    latest = fin.columns[-1]
    year   = pd.to_datetime(latest).year if hasattr(latest, "year") else pd.Timestamp.now().year
    return {
        "Ticker": ticker,
        "Name":   info.get("shortName", ticker),
        "Year":   year,
        "Price":  info.get("regularMarketPrice", np.nan),
        "EBITDA": fin.loc["EBITDA", latest] if "EBITDA" in fin.index else np.nan,
        "FCF":    cf.loc["Free Cash Flow", latest] if "Free Cash Flow" in cf.index else np.nan,
        "Cash":   info.get("totalCash", 0),
        "Debt":   info.get("totalDebt", 0),
        "Shares": info.get("sharesOutstanding", None)
    }

def forecast_5_years(val, rate=0.04, years=5):
    return {i: val * ((1+rate)**i) for i in range(1, years+1)}

def run_dcf_streamlit(ticker, wacc, fg, tg, years=5):
    base = fetch_baseline(ticker)
    st.markdown(
        "**Baseline financials** from Yahoo Finance:\n"
        "- `financials` → EBITDA\n"
        "- `cashflow`   → Free Cash Flow\n"
        "- `info`       → Price, Cash, Debt, Shares\n"
    )
    disp={}
    for k,v in base.items():
        disp[k] = f"${v:,.2f}" if k in {"Price","EBITDA","FCF","Cash","Debt"} else (f"{int(v):,}" if k=="Shares" else v)
    st.table(pd.DataFrame.from_dict(disp, orient="index", columns=["Value"]))

    # Projections
    e_proj = forecast_5_years(base["EBITDA"], fg, years)
    f_proj = forecast_5_years(base["FCF"],    fg, years)
    st.markdown(f"**5‑Year Projections** at {fg*100:.2f}%:")
    df_e = pd.DataFrame([{"Year":base["Year"]+i, "EBITDA":f"${e_proj[i]:,.2f}"} for i in e_proj])
    df_f = pd.DataFrame([{"Year":base["Year"]+i, "FCF":   f"${f_proj[i]:,.2f}"} for i in f_proj])
    st.table(df_e); st.table(df_f)

    # Discounted FCF
    st.markdown("**Discounted FCF** (mid‑year):")
    disc=[]; pv_sum=0
    for i in range(1, years+1):
        yr = base["Year"]+i; t=i-0.5
        proj=f_proj[i]; df=(1+wacc)**t; pv=proj/df; pv_sum+=pv
        disc.append({"Year":yr,"Timing":f"{t:.1f}", "Proj FCF":f"${proj:,.2f}", "DF":f"{df:.4f}", "PV":f"${pv:,.2f}"})
    st.table(pd.DataFrame(disc))

    # Terminal Value
    st.markdown(f"**Terminal Value** at {tg*100:.2f}%:")
    last=f_proj[years]
    tv  = last*(1+tg)/(wacc-tg)
    df_tv=(1+wacc)**(years-0.5); pv_tv=tv/df_tv
    term_df=pd.DataFrame([
        {"Item":f"FCF {base['Year']+years}", "Value":f"${last:,.2f}"},
        {"Item":"TV undisc",                "Value":f"${tv:,.2f}"},
        {"Item":"DF",                       "Value":f"{df_tv:.4f}"},
        {"Item":"PV",                       "Value":f"${pv_tv:,.2f}"}
    ])
    st.table(term_df)

    # Final Valuation & Upside
    ev= pv_sum+pv_tv; fair=ev/base["Shares"]; price=base["Price"]
    up=(fair-price)/price*100 if price else np.nan
    final_df=pd.DataFrame([
        {"Metric":"Enterprise Value",      "Value":f"${ev:,.2f}"},
        {"Metric":"Fair Price per Share",  "Value":f"${fair:,.2f}"},
        {"Metric":"Current Price",         "Value":f"${price:,.2f}"},
        {"Metric":"Upside/Downside (%)",   "Value":f"{up:.2f}%"}
    ])
    st.table(final_df)

    # === Sensitivity Analysis on WACC ===
    st.subheader("Sensitivity Analysis on WACC")
    scenarios = [wacc-0.01, wacc, wacc+0.01]
    sens=[]
    for w in scenarios:
        # recalc PVs
        pv_s= sum(f_proj[i]/((1+w)**(i-0.5)) for i in range(1,years+1))
        tv_s = last*(1+tg)/(w-tg)
        pv_tv_s = tv_s/((1+w)**(years-0.5))
        ev_s= pv_s+pv_tv_s
        fair_s= ev_s/base["Shares"]
        up_s = (fair_s-base["Price"])/base["Price"]*100
        sens.append({
            "WACC":           f"{w*100:.2f}%",
            "Fair Price":     f"${fair_s:,.2f}",
            "Upside/Downside":f"{up_s:.2f}%"
        })
    st.table(pd.DataFrame(sens))

# ─── STREAMLIT UI ────────────────────────────────────────────────────────────────

st.title("DCF Calculator with Upside/Downside & WACC Sensitivity")

with st.sidebar:
    st.header("Model Inputs")
    tickers      = st.text_input("Tickers (comma‑separated)", "")
    adjust_pct   = st.number_input("WACC adjust (%)",       value=-1.71, step=0.1, format="%.2f")
    forecast_pct = st.number_input("Forecast growth (%)",   value=4.0,  step=0.1, format="%.2f")
    terminal_pct = st.number_input("Terminal growth (%)",   value=4.0,  step=0.1, format="%.2f")
    run          = st.button("Run Model")

if run and tickers:
    adj  = adjust_pct/100
    fg   = forecast_pct/100
    tg   = terminal_pct/100

    for t in [s.strip().upper() for s in tickers.split(",") if s.strip()]:
        st.header(t)
        raw  = compute_wacc_raw(t)
        wacc = raw + adj
        st.markdown(f"**Raw WACC:** {raw*100:.2f}%  \n**Adj WACC:** {wacc*100:.2f}%")
        run_dcf_streamlit(t, wacc, fg, tg)

import streamlit as st
import requests
from lxml import html
import re
import yfinance as yf
import pandas as pd
import numpy as np

# ─── FORMATTERS ────────────────────────────────────────────────────────────────

def fmt_currency(x):
    try:
        return f"${x:,.2f}"
    except:
        return x

def fmt_pct(x):
    try:
        return f"{x*100:.2f}%"
    except:
        return x

# ─── WACC CALCULATION ──────────────────────────────────────────────────────────

def get_tax_rate_gf(ticker: str) -> float:
    url = f"https://www.gurufocus.com/term/tax-rate/{ticker}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    tree = html.fromstring(resp.content)
    node = tree.xpath('/html/body/div[2]/div[2]/div/div/div/div[2]/h1/font')
    text = node[0].text_content().strip() if node else ""
    m = re.search(r"(\d+(?:\.\d+)?)%", text)
    return float(m.group(1))/100 if m else 0.21

def get_risk_free_rate() -> float:
    data = yf.Ticker("^TNX").history(period="1d")["Close"]
    return float(data.iloc[-1])/100 if not data.empty else 0.035

def compute_erp_range(rf, low=0.085, high=0.10):
    return (low - rf, high - rf)

def get_raw_beta(ticker: str) -> float:
    b = yf.Ticker(ticker).info.get("beta")
    return float(b) if b else 1.0

def adjust_beta(raw_beta, tax, d_e):
    factor = (1 - tax) * d_e
    bu = raw_beta / (1 + factor)
    bl_p = bu * (1 + factor)
    badj = 0.67 * bl_p + 0.33
    return badj

def calculate_cost_of_debt(ticker: str):
    tk = yf.Ticker(ticker)
    qfin = tk.quarterly_financials
    rows = [r for r in qfin.index if "interest" in r.lower()] if not qfin.empty else []
    ttm_int = abs(qfin.loc[rows[0]].iloc[:4].sum()) if rows else 0
    debt = tk.info.get("totalDebt") or 0
    if debt == 0:
        bs = tk.quarterly_balance_sheet
        keys = [r for r in bs.index if "debt" in r.lower()] if not bs.empty else []
        debt = bs.loc[keys, bs.columns[0]].sum() if keys else 0
    rate = (ttm_int/debt) if debt else 0
    return ttm_int, debt, rate

def compute_wacc_raw(ticker: str) -> float:
    tax = get_tax_rate_gf(ticker)
    rf  = get_risk_free_rate()
    erp_low, erp_high = compute_erp_range(rf)
    erp = (erp_low + erp_high) / 2

    info      = yf.Ticker(ticker).info
    mcap      = info.get("marketCap") or 0
    ttm_int, debt, kd = calculate_cost_of_debt(ticker)
    d_e       = debt/mcap if mcap else 0
    beta_adj  = adjust_beta(get_raw_beta(ticker), tax, d_e)

    ke = rf + beta_adj * erp
    we = mcap/(mcap + debt) if (mcap+debt) else 0
    wd = debt/(mcap + debt) if (mcap+debt) else 0

    return we * ke + wd * kd * (1 - tax)

# ─── DCF MODEL ─────────────────────────────────────────────────────────────────

def fetch_baseline(ticker):
    tk   = yf.Ticker(ticker)
    fin  = tk.financials.sort_index(axis=1)
    cf   = tk.cashflow.sort_index(axis=1)
    info = tk.info
    col  = fin.columns[-1] if not fin.empty else pd.Timestamp.now()
    yr   = pd.to_datetime(col).year if hasattr(col, 'year') else pd.Timestamp.now().year
    return {
        "Ticker": ticker,
        "Name":   info.get("shortName", ticker),
        "Year":   yr,
        "Price":  info.get("regularMarketPrice", np.nan),
        "EBITDA": fin.loc["EBITDA", col] if "EBITDA" in fin.index else np.nan,
        "FCF":    cf.loc["Free Cash Flow", col] if "Free Cash Flow" in cf.index else np.nan,
        "Cash":   info.get("totalCash", 0),
        "Debt":   info.get("totalDebt", 0),
        "Shares": info.get("sharesOutstanding", np.nan)
    }

def forecast_5_years(val, rate=0.04, years=5):
    return {i: val * ((1+rate)**i) for i in range(1, years+1)}

def run_dcf_streamlit(ticker, wacc, ltg=0.03, fg=0.03, years=5):
    base = fetch_baseline(ticker)
    if not base["Shares"] or pd.isna(base["EBITDA"]) or pd.isna(base["FCF"]):
        st.warning("Insufficient data for DCF.")
        return

    # Baseline Financials
    base_df = pd.DataFrame.from_dict(base, orient="index", columns=["Value"])
    def _fmt(idx, val):
        if idx in ["Price","EBITDA","FCF","Cash","Debt"]:
            return fmt_currency(val)
        if idx == "Shares":
            return f"{int(val):,}"
        return val
    base_df["Value"] = [ _fmt(i,v) for i,v in zip(base_df.index, base_df["Value"]) ]
    st.subheader("Baseline Financials")
    st.table(base_df.style.set_properties(**{"text-align":"right"}))

    # Projections
    e_proj = forecast_5_years(base["EBITDA"], fg, years)
    f_proj = forecast_5_years(base["FCF"], fg, years)

    e_df = pd.DataFrame.from_dict(e_proj, orient="index", columns=["EBITDA"])
    e_df["EBITDA"] = e_df["EBITDA"].apply(fmt_currency)
    st.subheader("EBITDA Projections")
    st.table(e_df.style.set_properties(**{"text-align":"right"}))

    f_df = pd.DataFrame.from_dict(f_proj, orient="index", columns=["FCF"])
    f_df["FCF"] = f_df["FCF"].apply(fmt_currency)
    st.subheader("FCF Projections")
    st.table(f_df.style.set_properties(**{"text-align":"right"}))

    # Discounted Cash Flow
    df_rows, total_pv = [], 0
    for i in range(1, years+1):
        t    = i - 0.5
        pv   = f_proj[i] / ((1+wacc)**t)
        df   = 1/((1+wacc)**t)
        df_rows.append({
            "Year": base["Year"]+i,
            "Proj FCF": fmt_currency(f_proj[i]),
            "DF":        fmt_pct(df),
            "PV":        fmt_currency(pv)
        })
        total_pv += pv
    dcf_df = pd.DataFrame(df_rows).set_index("Year")
    st.subheader("Discounted FCF")
    st.table(dcf_df.style.set_properties(**{"text-align":"right"}))

    # Terminal Value
    last  = f_proj[years]
    tv    = last * (1+ltg) / (wacc - ltg)
    pv_tv = tv / ((1+wacc)**(years-0.5))
    term_df = pd.DataFrame([
        ["FCF in " + str(base["Year"]+years), fmt_currency(last)],
        ["Terminal Value",            fmt_currency(tv)],
        ["PV of Terminal",            fmt_currency(pv_tv)]
    ], columns=["Metric","Value"]).set_index("Metric")
    st.subheader("Terminal Value")
    st.table(term_df.style.set_properties(**{"text-align":"right"}))

    # Final Valuation
    ent_val = total_pv + pv_tv
    fair    = ent_val / base["Shares"]
    curr    = base["Price"]
    upside  = (fair - curr)/curr if curr else 0
    fin_df = pd.DataFrame([
        ["Current Price",       fmt_currency(curr)],
        ["Fair Price per Share",fmt_currency(fair)],
        ["Upside/Downside",     fmt_pct(upside)]
    ], columns=["Metric","Value"]).set_index("Metric")
    st.subheader("Final Valuation")
    st.table(fin_df.style.set_properties(**{"text-align":"right"}))

# ─── STREAMLIT UI ────────────────────────────────────────────────────────────────

st.title("DCF Calculator with Auto‑WACC")

tickers  = st.text_input("1) Enter ticker(s) (comma‑separated)")
wacc_adj = st.number_input("2) WACC adjuster (%)", value=-2.4, step=0.1, format="%.2f")
fg_pct   = st.number_input("3) Forecast growth rate (%)", value=3.0, step=0.1, format="%.2f")
ltg_pct  = st.number_input("4) Terminal growth rate (%)", value=3.0, step=0.1, format="%.2f")
if st.button("Run Model") and tickers:
    for t in [s.strip().upper() for s in tickers.split(",") if s.strip()]:
        st.header(t)
        try:
            raw  = compute_wacc_raw(t)
            wacc = raw + wacc_adj/100
            st.markdown(f"**Raw WACC:** {fmt_pct(raw)}    **Adjusted WACC:** {fmt_pct(wacc)}")
            run_dcf_streamlit(t, wacc, ltg=ltg_pct/100, fg=fg_pct/100)
        except Exception as e:
            st.error(f"Error for {t}: {e}")

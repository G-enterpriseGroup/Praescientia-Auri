import streamlit as st
import requests
from lxml import html
import re
import yfinance as yf
import pandas as pd
import numpy as np
import locale

# Set locale for currency formatting
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except locale.Error:
    # fallback if the environment doesn't support the locale
    pass

# ─── HELPERS ───────────────────────────────────────────────────────────────────

def fmt_currency(x):
    try:
        return locale.currency(x, grouping=True)
    except Exception:
        return f"${x:,.2f}"

def fmt_pct(x):
    return f"{x*100:.2f}%"

# ─── WACC CALCULATION ──────────────────────────────────────────────────────────

def get_tax_rate_gf(ticker: str) -> float:
    url = f"https://www.gurufocus.com/term/tax-rate/{ticker}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    tree = html.fromstring(resp.content)
    node = tree.xpath('/html/body/div[2]/div[2]/div/div/div/div[2]/h1/font')
    text = node[0].text_content().strip() if node else ""
    m = re.search(r"(\d+(?:\.\d+)?)%", text)
    return float(m.group(1))/100 if m else 0.21  # default ~21%

def get_risk_free_rate() -> float:
    data = yf.Ticker("^TNX").history(period="1d")["Close"]
    return float(data.iloc[-1])/100 if not data.empty else 0.035

def compute_erp(rf: float, low=0.085, high=0.10) -> float:
    return ((low - rf) + (high - rf)) / 2

def get_raw_beta(ticker: str) -> float:
    beta = yf.Ticker(ticker).info.get("beta")
    return float(beta) if beta else 1.0

def adjust_beta(raw_b, tax, d_e):
    unlev = raw_b / (1 + (1-tax)*d_e)
    re_lever = unlev * (1 + (1-tax)*d_e)
    adj = 0.67*re_lever + 0.33
    return adj

def calculate_cost_of_debt(ticker: str):
    tk = yf.Ticker(ticker)
    qfin = tk.quarterly_financials
    rows = [r for r in qfin.index if "interest" in r.lower()] if not qfin.empty else []
    ttm_int = abs(qfin.loc[rows[0]].iloc[:4].sum()) if rows else 0
    debt = tk.info.get("totalDebt") or 0
    if debt == 0 and not qfin.empty:
        bs = tk.quarterly_balance_sheet
        keys = [r for r in bs.index if "debt" in r.lower()]
        debt = bs.loc[keys, bs.columns[0]].sum() if keys else 0
    rate = (ttm_int/debt) if debt else 0
    return ttm_int, debt, rate

def compute_wacc_raw(ticker: str) -> float:
    tax = get_tax_rate_gf(ticker)
    rf = get_risk_free_rate()
    erp = compute_erp(rf)
    info = yf.Ticker(ticker).info
    mcap = info.get("marketCap") or 0
    ttm_int, debt, kd = calculate_cost_of_debt(ticker)
    d_e = (debt/mcap) if mcap else 0
    beta_adj = adjust_beta(get_raw_beta(ticker), tax, d_e)
    ke = rf + beta_adj * erp
    we = mcap/(mcap + debt) if (mcap+debt) else 0
    wd = debt/(mcap + debt) if (mcap+debt) else 0
    return we*ke + wd*kd*(1-tax)

# ─── DCF MODEL ─────────────────────────────────────────────────────────────────

def fetch_baseline(ticker):
    tk = yf.Ticker(ticker)
    fin = tk.financials.sort_index(axis=1)
    cf = tk.cashflow.sort_index(axis=1)
    info = tk.info
    col = fin.columns[-1] if not fin.empty else pd.Timestamp.now()
    year = pd.to_datetime(col).year if hasattr(col, 'year') else pd.Timestamp.now().year
    return {
        "Ticker": ticker,
        "Name": info.get("shortName", ticker),
        "Year": year,
        "Price": info.get("regularMarketPrice", np.nan),
        "EBITDA": fin.loc["EBITDA", col] if "EBITDA" in fin.index else np.nan,
        "FCF": cf.loc["Free Cash Flow", col] if "Free Cash Flow" in cf.index else np.nan,
        "Cash": info.get("totalCash", 0),
        "Debt": info.get("totalDebt", 0),
        "Shares": info.get("sharesOutstanding", np.nan)
    }

def forecast(vals, rate, years):
    return {i: vals*((1+rate)**i) for i in range(1, years+1)}

def run_dcf(ticker, wacc, ltg, fg, years):
    base = fetch_baseline(ticker)
    st.subheader(f"🔍 {base['Name']} ({ticker})")
    # Two‑column summary
    col1, col2, col3 = st.columns(3)
    col1.metric("Price", fmt_currency(base["Price"]))
    col1.metric("Shares", f"{int(base['Shares']):,}")
    col2.metric("EBITDA", fmt_currency(base["EBITDA"]))
    col2.metric("FCF", fmt_currency(base["FCF"]))
    col3.metric("Cash", fmt_currency(base["Cash"]))
    col3.metric("Debt", fmt_currency(base["Debt"]))

    # Projections
    e_proj = forecast(base["EBITDA"], fg, years)
    f_proj = forecast(base["FCF"], fg, years)
    st.table(pd.DataFrame.from_dict(e_proj, orient="index", columns=["EBITDA"])
                 .rename_axis("Year Offset"))
    st.table(pd.DataFrame.from_dict(f_proj, orient="index", columns=["FCF"])
                 .rename_axis("Year Offset"))

    # Discounting
    df_rows, total_pv = [], 0
    for i in range(1, years+1):
        t = i - 0.5
        pv = f_proj[i] / ((1+wacc)**t)
        df_rows.append({
            "Year": base["Year"]+i,
            "Proj FCF": fmt_currency(f_proj[i]),
            "DF": fmt_pct(1/((1+wacc)**t)),
            "PV": fmt_currency(pv)
        })
        total_pv += pv
    st.table(pd.DataFrame(df_rows))

    # Terminal
    last = f_proj[years]
    tv = last*(1+ltg)/(wacc-ltg)
    df_tv = (1+wacc)**(years-0.5)
    pv_tv = tv/df_tv
    st.table(pd.DataFrame([
        ["Terminal Undisc FCF", fmt_currency(last)],
        ["Terminal Value", fmt_currency(tv)],
        ["PV of Terminal", fmt_currency(pv_tv)]
    ], columns=["Metric","Value"]))

    # Final
    ent = total_pv + pv_tv
    fair = ent/base["Shares"] if base["Shares"] else np.nan
    upside = (fair - base["Price"])/base["Price"] if base["Price"] else 0

    final = pd.DataFrame([
        ["Enterprise Value", fmt_currency(ent)],
        ["Fair Price", fmt_currency(fair)],
        ["Upside/Downside", fmt_pct(upside)]
    ], columns=["Metric","Value"])
    st.table(final)

# ─── UI ───────────────────────────────────────────────────────────────────────

st.title("📊 DCF & Auto‑WACC Calculator")
with st.sidebar:
    tickers = st.text_input("Ticker(s), comma‑separated").upper()
    wacc_adj = st.number_input("WACC adjust (%)", value=-2.4, format="%.2f")
    fg = st.number_input("Forecast Growth (%)", value=3.0, format="%.2f")/100
    ltg = st.number_input("Terminal Growth (%)", value=3.0, format="%.2f")/100
    years = st.slider("Forecast Years", 3, 10, 5)
    run = st.button("Run")

if run and tickers:
    for t in [x.strip() for x in tickers.split(",") if x.strip()]:
        try:
            raw = compute_wacc_raw(t)
            adj_wacc = raw + wacc_adj/100
            st.markdown(f"**Raw WACC:** {fmt_pct(raw)}  &nbsp;&nbsp; **Adj WACC:** {fmt_pct(adj_wacc)}")
            run_dcf(t, adj_wacc, ltg, fg, years)
        except Exception as e:
            st.error(f"{t}: {e}")

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
    if not nodes:
        raise ValueError("Tax rate not found")
    text = nodes[0].text_content().strip()
    m = re.search(r"(\d+(?:\.\d+)?)%", text)
    if not m:
        raise ValueError(f"Could not parse tax rate from '{text}'")
    return float(m.group(1)) / 100

def get_risk_free_rate() -> float:
    data = yf.Ticker("^TNX").history(period="1d")["Close"]
    if data.empty:
        raise ValueError("Could not fetch 10‑yr yield")
    return data.iloc[-1] / 100

def compute_erp_range(rf: float,
                      market_return_low: float = 0.085,
                      market_return_high: float = 0.10) -> tuple[float, float]:
    return market_return_low - rf, market_return_high - rf

def get_raw_beta(ticker: str) -> float:
    beta = yf.Ticker(ticker).info.get("beta")
    if beta is None:
        raise ValueError("Beta not available")
    return float(beta)

def adjust_beta(raw_beta: float, tax: float, d_e: float) -> tuple[float, float, float]:
    factor = (1 - tax) * d_e
    bu = raw_beta / (1 + factor)
    bl_p = bu * (1 + factor)
    badj = 0.67 * bl_p + 0.33
    return bu, bl_p, badj

def calculate_cost_of_debt(ticker: str) -> tuple[float, float, float]:
    tk = yf.Ticker(ticker)
    qfin = tk.quarterly_financials
    if qfin.empty:
        raise ValueError("Quarterly income not found")
    rows = [r for r in qfin.index if "interest" in r.lower()]
    if not rows:
        raise KeyError("Interest row not found")
    row = next((r for r in rows if "expense" in r.lower()), rows[0])
    ttm_int = abs(qfin.loc[row].iloc[:4].sum())

    info_debt = tk.info.get("totalDebt") or 0
    if info_debt > 0:
        bd = info_debt
    else:
        qbs = tk.quarterly_balance_sheet
        if qbs.empty:
            raise ValueError("Quarterly BS not found")
        keys = [r for r in qbs.index
                if "short term debt" in r.lower() or "long term debt" in r.lower()]
        if not keys:
            raise KeyError("Debt lines not found")
        bd = qbs.loc[keys, qbs.columns[0]].sum()

    if bd == 0:
        raise ZeroDivisionError("Book debt is zero")
    return ttm_int, bd, ttm_int / bd

def compute_wacc_raw(ticker: str) -> float:
    tax = get_tax_rate_gf(ticker)
    rf  = get_risk_free_rate()
    erp_low, erp_high = compute_erp_range(rf)
    erp_avg = (erp_low + erp_high) / 2

    info       = yf.Ticker(ticker).info
    market_cap = info.get("marketCap") or 0
    ttm_int, book_debt, kd = calculate_cost_of_debt(ticker)
    d_e        = book_debt / market_cap

    raw_b      = get_raw_beta(ticker)
    _, _, badj = adjust_beta(raw_b, tax, d_e)

    ke = rf + badj * erp_avg
    we = market_cap / (market_cap + book_debt)
    wd = book_debt / (market_cap + book_debt)

    return we * ke + wd * kd * (1 - tax)

# ─── DCF MODEL ─────────────────────────────────────────────────────────────────

def fetch_baseline(ticker):
    tk = yf.Ticker(ticker)
    fin = tk.financials.sort_index(axis=1)
    cf  = tk.cashflow.sort_index(axis=1)
    info = tk.info

    latest = fin.columns[-1]
    try:
        year = pd.to_datetime(latest).year
    except:
        year = pd.Timestamp.now().year

    base = {
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
    return base

def forecast_5_years(val, rate=0.04, years=5):
    return {i: val * ((1+rate)**i) for i in range(1, years+1)}

def run_dcf_streamlit(ticker, wacc, ltg=0.04, fg=0.04, years=5):
    base = fetch_baseline(ticker)
    if not base["Shares"] or pd.isna(base["EBITDA"]) or pd.isna(base["FCF"]):
        st.warning("Insufficient data for DCF.")
        return

    # Baseline table
    baseline_df = pd.DataFrame.from_dict(base, orient="index", columns=["Value"])
    st.table(baseline_df)

    # Projections
    e_proj = forecast_5_years(base["EBITDA"], fg, years)
    f_proj = forecast_5_years(base["FCF"],   fg, years)
    ebitda_df = pd.DataFrame(list(e_proj.items()), columns=["Year","EBITDA"])
    fcf_df    = pd.DataFrame(list(f_proj.items()), columns=["Year","FCF"])
    st.subheader("EBITDA Projections"); st.table(ebitda_df)
    st.subheader("FCF Projections");    st.table(fcf_df)

    # Discount FCF
    rows = []
    total_pv = 0
    for i in range(1, years+1):
        t = i - 0.5
        df = (1 + wacc)**t
        pv = f_proj[i] / df
        rows.append({
            "Year": base["Year"]+i,
            "Timing": t,
            "Projected FCF": f_proj[i],
            "Discount Factor": df,
            "PV of FCF": pv
        })
        total_pv += pv
    disc_df = pd.DataFrame(rows)
    st.subheader("Discounted FCF"); st.table(disc_df)

    # Terminal Value
    last = f_proj[years]
    tv   = last * (1+ltg) / (wacc - ltg)
    df_tv = (1 + wacc)**(years - 0.5)
    pv_tv = tv / df_tv
    term_df = pd.DataFrame({
        "Item": [
            f"FCF in {base['Year']+years}",
            "Terminal Value (undiscounted)",
            "Discount Factor",
            "PV of Terminal Value"
        ],
        "Value": [
            last, tv, df_tv, pv_tv
        ]
    })
    st.subheader("Terminal Value"); st.table(term_df)

    # Final Valuation
    ent_val = total_pv + pv_tv
    fair    = ent_val / base["Shares"]
    final_df = pd.DataFrame({
        "Metric": ["Enterprise Value","Shares Outstanding","Fair Price"],
        "Value":  [ent_val, base["Shares"], fair]
    })
    st.subheader("Final Valuation"); st.table(final_df)

# ─── STREAMLIT UI ────────────────────────────────────────────────────────────────

st.title("DCF Calculator with Auto‑WACC")

tickers = st.text_input("1) Enter ticker(s) (comma‑separated)", "")
adjuster = st.number_input("2) WACC adjuster (%)", value=-2.4, step=0.1, format="%.2f")
if st.button("Run Model") and tickers:
    for t in [x.strip().upper() for x in tickers.split(",") if x.strip()]:
        st.header(f"{t}")
        try:
            raw = compute_wacc_raw(t)
            wacc = raw + adjuster/100
            st.markdown(f"**Raw WACC:** {raw*100:.2f}%  
**Adjusted WACC:** {wacc*100:.2f}%")
            run_dcf_streamlit(t, wacc)
        except Exception as e:
            st.error(f"Error for {t}: {e}")

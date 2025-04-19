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
    rows = [r for r in qfin.index if "interest" in r.lower()]
    row = next((r for r in rows if "expense" in r.lower()), rows[0])
    ttm_int = abs(qfin.loc[row].iloc[:4].sum())
    info_debt = tk.info.get("totalDebt") or 0
    if info_debt > 0:
        bd = info_debt
    else:
        qbs = tk.quarterly_balance_sheet
        keys = [r for r in qbs.index
                if "short term debt" in r.lower() or "long term debt" in r.lower()]
        bd = qbs.loc[keys, qbs.columns[0]].sum()
    return ttm_int, bd, ttm_int / bd

def compute_wacc_raw(ticker: str) -> float:
    """
    Compute raw WACC:
     1. Tax rate from GuruFocus
     2. Risk-free rate = 10‑yr Treasury yield
     3. ERP = (8.5%–10%) – rf
     4. Beta adjustment (unlever, relever, 0.67/0.33 adjust)
     5. Ke = rf + β_adj * ERP_avg
     6. Kd = TTM interest / book debt
     7. We = E/(E+D), Wd = D/(E+D)
     8. WACC = We·Ke + Wd·Kd·(1–tax)
    """
    tax = get_tax_rate_gf(ticker)
    rf  = get_risk_free_rate()
    erp_low, erp_high = compute_erp_range(rf)
    erp_avg = (erp_low + erp_high) / 2

    info       = yf.Ticker(ticker).info
    market_cap = info.get("marketCap") or 0
    ttm_int, book_debt, kd = calculate_cost_of_debt(ticker)
    d_e = book_debt / market_cap

    raw_b      = get_raw_beta(ticker)
    _, _, badj = adjust_beta(raw_b, tax, d_e)

    ke = rf + badj * erp_avg
    we = market_cap / (market_cap + book_debt)
    wd = book_debt / (market_cap + book_debt)

    return we * ke + wd * kd * (1 - tax)

# ─── DCF MODEL ─────────────────────────────────────────────────────────────────

def fetch_baseline(ticker):
    """
    Baseline financials via Yahoo Finance:
    • ticker.financials → most recent annual EBITDA
    • ticker.cashflow   → most recent annual Free Cash Flow
    • ticker.info       → price, cash, debt, shares outstanding
    """
    tk  = yf.Ticker(ticker)
    fin = tk.financials.sort_index(axis=1)
    cf  = tk.cashflow.sort_index(axis=1)
    info = tk.info
    latest = fin.columns[-1]
    year = pd.to_datetime(latest).year if hasattr(latest, "year") else pd.Timestamp.now().year
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
    """Project val forward at constant rate."""
    return {i: val * ((1+rate)**i) for i in range(1, years+1)}

def run_dcf_streamlit(ticker, wacc, forecast_growth, terminal_growth, years=5):
    base = fetch_baseline(ticker)
    # Explanation
    st.markdown(
        "**Baseline financials** are pulled directly from Yahoo Finance:\n"
        "- `financials` → EBITDA\n"
        "- `cashflow`   → Free Cash Flow\n"
        "- `info`       → Market Price, Cash, Debt, Shares\n"
    )
    # Display baseline
    disp = {}
    for k,v in base.items():
        if k in {"Price","EBITDA","FCF","Cash","Debt"}:
            disp[k] = f"${v:,.2f}"
        elif k == "Shares":
            disp[k] = f"{int(v):,}" if v else "N/A"
        else:
            disp[k] = v
    st.table(pd.DataFrame.from_dict(disp, orient="index", columns=["Value"]))

    # Projections
    st.markdown(f"**5‑Year projections** at {forecast_growth*100:.2f}% growth:")
    e_proj = forecast_5_years(base["EBITDA"], forecast_growth, years)
    f_proj = forecast_5_years(base["FCF"],    forecast_growth, years)
    df_e = pd.DataFrame([{"Year": base["Year"]+i, "EBITDA": f"${e_proj[i]:,.2f}"} for i in e_proj])
    df_f = pd.DataFrame([{"Year": base["Year"]+i, "FCF":    f"${f_proj[i]:,.2f}"} for i in f_proj])
    st.table(df_e); st.table(df_f)

    # Discounted FCF
    st.markdown("**Discounted FCF** using mid‑year convention:")
    disc, total_pv = [], 0
    for i in range(1, years+1):
        year = base["Year"]+i; t = i-0.5
        proj = f_proj[i]; df=(1+wacc)**t; pv=proj/df; total_pv+=pv
        disc.append({
            "Year":year,
            "Timing":f"{t:.1f}",
            "Projected FCF":f"${proj:,.2f}",
            "Discount Factor":f"{df:.4f}",
            "PV of FCF":f"${pv:,.2f}"
        })
    st.table(pd.DataFrame(disc))

    # Terminal Value
    st.markdown(f"**Terminal Value** at {terminal_growth*100:.2f}% growth:")
    last = f_proj[years]
    tv   = last*(1+terminal_growth)/(wacc-terminal_growth)
    df_tv=(1+wacc)**(years-0.5)
    pv_tv=tv/df_tv
    term_df = pd.DataFrame([
        {"Item":f"FCF in {base['Year']+years}", "Value":f"${last:,.2f}"},
        {"Item":"TV (undisc)",                "Value":f"${tv:,.2f}"},
        {"Item":"Discount Factor",            "Value":f"{df_tv:.4f}"},
        {"Item":"PV of Terminal Value",       "Value":f"${pv_tv:,.2f}"}
    ])
    st.table(term_df)

    # Final Valuation + Upside/Downside
    st.markdown("**Final Valuation**:")
    ev    = total_pv + pv_tv
    fair  = ev / base["Shares"]
    price = base["Price"]
    upside_pct = (fair - price) / price * 100 if price and not np.isnan(price) else np.nan

    final_df = pd.DataFrame([
        {"Metric":"Enterprise Value",        "Value":f"${ev:,.2f}"},
        {"Metric":"Fair Price per Share",    "Value":f"${fair:,.2f}"},
        {"Metric":"Current Market Price",    "Value":f"${price:,.2f}"},
        {"Metric":"Upside / Downside (%)",   "Value":f"{upside_pct:.2f}%"}
    ])
    st.table(final_df)

# ─── STREAMLIT UI ────────────────────────────────────────────────────────────────

st.title("DCF Calculator with Upside/Downside Analysis")

with st.sidebar:
    st.header("Model Inputs")
    tickers      = st.text_input("Tickers (comma‑separated)", "")
    adjust_pct   = st.number_input("WACC adjust (%)",       value=-0.0, step=0.1, format="%.2f")
    forecast_pct = st.number_input("Forecast growth (%)",   value=4.0,  step=0.1, format="%.2f")
    terminal_pct = st.number_input("Terminal growth (%)",   value=4.0,  step=0.1, format="%.2f")
    run          = st.button("Run Model")

if run and tickers:
    adj  = adjust_pct/100.0
    fore = forecast_pct/100.0
    term = terminal_pct/100.0

    for t in [s.strip().upper() for s in tickers.split(",") if s.strip()]:
        st.header(t)
        raw  = compute_wacc_raw(t)
        wacc = raw + adj
        st.markdown(
            f"**Raw WACC:** {raw*100:.2f}%  \n"
            f"**Adjusted WACC:** {wacc*100:.2f}%"
        )
        run_dcf_streamlit(t, wacc, fore, term)

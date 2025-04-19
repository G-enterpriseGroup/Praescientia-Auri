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

# ─── DCF MODEL ─────────────────────────────────────────────────────────────────

def fetch_baseline(ticker):
    """
    Baseline financials via yfinance:
    • fin = ticker.financials → annual EBITDA
    • cf  = ticker.cashflow   → annual Free Cash Flow
    • info = ticker.info      → price, cash, debt, shares
    """
    tk  = yf.Ticker(ticker)
    fin = tk.financials.sort_index(axis=1)
    cf  = tk.cashflow.sort_index(axis=1)
    info = tk.info
    latest = fin.columns[-1]
    year = pd.to_datetime(latest).year if isinstance(latest, (pd.Timestamp, str)) else pd.Timestamp.now().year
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
    st.markdown(
        "### Baseline Financials\n"
        "Pulled from **Yahoo Finance**:\n"
        "- `ticker.financials` → EBITDA\n"
        "- `ticker.cashflow`   → Free Cash Flow\n"
        "- `ticker.info`       → Price, Cash, Debt, Shares\n"
    )
    # Format baseline
    disp = {}
    for k,v in base.items():
        if k in {"Price","EBITDA","FCF","Cash","Debt"}:
            disp[k] = f"${v:,.2f}"
        elif k=="Shares":
            disp[k] = f"{int(v):,}" if v else "N/A"
        else:
            disp[k] = v
    st.table(pd.DataFrame.from_dict(disp, orient="index", columns=["Value"]))

    st.markdown(
        f"### 5‑Year Projections\n"
        f"Grown at **{forecast_growth*100:.2f}%** annually.\n"
    )
    e_proj = forecast_5_years(base["EBITDA"], forecast_growth, years)
    f_proj = forecast_5_years(base["FCF"],    forecast_growth, years)
    e_rows = [{"Year": base["Year"]+i, "EBITDA": f"${e_proj[i]:,.2f}"} for i in e_proj]
    f_rows = [{"Year": base["Year"]+i, "FCF":    f"${f_proj[i]:,.2f}"} for i in f_proj]
    st.table(pd.DataFrame(e_rows)); st.table(pd.DataFrame(f_rows))

    st.markdown(
        "### Discounted Cash Flows\n"
        "Mid‑year discount at **WACC**.\n"
    )
    disc, total_pv = [], 0
    for i in range(1, years+1):
        year = base["Year"]+i; t = i-0.5
        proj = f_proj[i]; df=(1+wacc)**t; pv=proj/df
        total_pv += pv
        disc.append({
            "Year":year,"Timing":f"{t:.1f}",
            "Proj FCF":f"${proj:,.2f}",
            "DF":f"{df:.4f}","PV":f"${pv:,.2f}"
        })
    st.table(pd.DataFrame(disc))

    st.markdown(
        "### Terminal Value\n"
        f"Gordon Growth at **{terminal_growth*100:.2f}%**:\n"
        "TV = FCF_last×(1+g)/(WACC−g)\n"
    )
    last=f_proj[years]; tv=last*(1+terminal_growth)/(wacc-terminal_growth)
    df_tv=(1+wacc)**(years-0.5); pv_tv=tv/df_tv
    term_tab = [
        ["FCF in "+str(base["Year"]+years),f"${last:,.2f}"],
        ["TV (undisc)",f"${tv:,.2f}"],
        ["DF",f"{df_tv:.4f}"],["PV",f"${pv_tv:,.2f}"]
    ]
    st.table(pd.DataFrame(term_tab,columns=["Item","Value"]))

    st.markdown(
        "### Final Valuation\n"
        "- EV = Σ PV(FCF) + PV(TV)\n"
        "- Fair Price = EV / Shares\n"
    )
    ev=total_pv+pv_tv; fair=ev/base["Shares"]
    final_tab=[
        ["Enterprise Value",f"${ev:,.2f}"],
        ["Shares Outstanding",f"{int(base['Shares']):,}"],
        ["Fair Price",f"${fair:,.2f}"]
    ]
    st.table(pd.DataFrame(final_tab,columns=["Metric","Value"]))

# ─── STREAMLIT UI ────────────────────────────────────────────────────────────────

st.title("DCF Calculator with Full Calculation Details")

with st.sidebar:
    st.header("Model Inputs")
    tickers      = st.text_input("Tickers (comma‑separated)", "")
    adjust_pct   = st.number_input("WACC adjust (%)",       value=-2.4, step=0.1, format="%.2f")
    forecast_pct = st.number_input("Forecast growth (%)",   value=4.0,  step=0.1, format="%.2f")
    terminal_pct = st.number_input("Terminal growth (%)",   value=4.0,  step=0.1, format="%.2f")
    run          = st.button("Run Model")

if run and tickers:
    adj = adjust_pct/100; fore=forecast_pct/100; term=terminal_pct/100

    for t in [x.strip().upper() for x in tickers.split(",") if x.strip()]:
        st.header(t)

        # Compute all WACC pieces
        tax       = get_tax_rate_gf(t)
        rf        = get_risk_free_rate()
        erp_low, erp_high = compute_erp_range(rf)
        erp_avg   = (erp_low+erp_high)/2

        info      = yf.Ticker(t).info
        mc        = info.get("marketCap") or 0
        ttm_int, bd, kd   = calculate_cost_of_debt(t)
        d_e       = bd/mc

        raw_b     = get_raw_beta(t)
        bu, blp, badj    = adjust_beta(raw_b, tax, d_e)

        ke        = rf + badj*erp_avg
        we        = mc/(mc+bd)
        wd        = bd/(mc+bd)
        raw_wacc  = we*ke + wd*kd*(1-tax)
        adj_wacc  = raw_wacc + adj

        # WACC explanation + table
        st.markdown("### WACC Calculation Details")
        st.markdown(
            "- **Tax Rate** from GuruFocus  \n"
            "- **RF** = 10‑yr Treasury  \n"
            "- **ERP** = (8.5%–10%) – RF  \n"
            "- **Beta**: raw, unlever, relever, adjusted  \n"
            "- **Ke** = RF + β_adj·ERP  \n"
            "- **Kd** = interest/ debt  \n"
            "- **Weights** = E/(E+D), D/(E+D)  \n"
            "- **WACC** = We·Ke + Wd·Kd·(1–T)"
        )
        wacc_details = [
            ("Tax Rate",               f"{tax*100:.2f}%"),
            ("Risk‑Free Rate",         f"{rf*100:.2f}%"),
            ("ERP Range",              f"{erp_low*100:.2f}%–{erp_high*100:.2f}%"),
            ("ERP Avg",                f"{erp_avg*100:.2f}%"),
            ("Raw Beta (βL)",          f"{raw_b:.4f}"),
            ("Unlevered Beta (βU)",    f"{bu:.4f}"),
            ("Relevered Beta (βL')",   f"{blp:.4f}"),
            ("Adjusted Beta (βadj)",   f"{badj:.4f}"),
            ("Cost of Equity (Ke)",    f"{ke*100:.2f}%"),
            ("TTM Interest Exp.",      f"${ttm_int:,.2f}"),
            ("Book Debt",              f"${bd:,.2f}"),
            ("Cost of Debt (Kd)",      f"{kd*100:.2f}%"),
            ("Market Cap",             f"${mc:,.2f}"),
            ("D/E Ratio",              f"{d_e:.2f}"),
            ("We (Equity)",            f"{we*100:.2f}%"),
            ("Wd (Debt)",              f"{wd*100:.2f}%"),
            ("Raw WACC",               f"{raw_wacc*100:.2f}%"),
            ("Adjusted WACC",          f"{adj_wacc*100:.2f}%")
        ]
        st.table(pd.DataFrame(wacc_details, columns=["Metric","Value"]))

        # DCF sections
        run_dcf_streamlit(t, adj_wacc, fore, term)

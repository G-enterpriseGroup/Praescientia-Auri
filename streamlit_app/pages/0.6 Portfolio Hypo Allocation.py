# streamlit_app.py
# PortfolioDownload(6).csv -> Bloomberg 90s orange Streamlit app
# CHANGE:
# 1) Auto-pull BUY dividend yield from StockAnalysis (ETF + stock pages) so you don't type it manually
# 2) Removed Net Account Value from KPI strip + What-If summary (no longer tracked/displayed)
# NO calc/what-if math logic changed other than sourcing buy_yield automatically.

import csv
import re
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from datetime import datetime

# =========================
# Page + Theme (Bloomberg 90s Orange)
# =========================
st.set_page_config(page_title="Portfolio Yield Lab (90s Orange)", layout="wide")  # keep sidebar visible

CSS = """
<style>
html, body, [class*="css"]  {
  background: #000000 !important;
  color: #ff9900 !important;
  font-family: "Courier New", Courier, monospace !important;
}

section[data-testid="stSidebar"] { display: block !important; }

.block-container {
  padding-top: 1.0rem;
  padding-bottom: 1.0rem;
  max-width: 1600px;
}

h1, h2, h3, h4, h5, h6 {
  color: #ff9900 !important;
  font-family: "Courier New", Courier, monospace !important;
  letter-spacing: 0.4px;
}

input, textarea {
  background: #0b0b0b !important;
  color: #ff9900 !important;
  border: 2px solid #ff9900 !important;
  border-radius: 0px !important;
  box-shadow: none !important;
}
div[data-baseweb="input"] > div {
  background: #0b0b0b !important;
  border: 2px solid #ff9900 !important;
  border-radius: 0px !important;
}
div[data-baseweb="select"] > div {
  background: #0b0b0b !important;
  border: 2px solid #ff9900 !important;
  border-radius: 0px !important;
}

div[data-testid="stFileUploader"] {
  border: 2px solid #ff9900 !important;
  background: #050505 !important;
  padding: 12px !important;
}

.stButton > button {
  background: linear-gradient(#ffb347, #ff9900) !important;
  color: #000000 !important;
  border: 2px solid #ffcc66 !important;
  border-radius: 0px !important;
  box-shadow:
    0px 0px 0px 2px #000000 inset,
    0px 6px 0px 0px #b36b00,
    0px 10px 20px rgba(0,0,0,0.65) !important;
  padding: 0.55rem 1.1rem !important;
  font-weight: 800 !important;
  letter-spacing: 0.5px !important;
}
.stButton > button:active {
  transform: translateY(4px) !important;
  box-shadow:
    0px 0px 0px 2px #000000 inset,
    0px 2px 0px 0px #b36b00,
    0px 8px 16px rgba(0,0,0,0.65) !important;
}

[data-testid="stDataFrame"] {
  border: 2px solid #ff9900 !important;
}

div[data-testid="metric-container"] {
  border: 2px solid #ff9900 !important;
  background: #050505 !important;
  padding: 10px !important;
}
div[data-testid="metric-container"] * {
  color: #ff9900 !important;
}

/* small header boxes */
.bb_hdr {
  border: 2px solid #ff9900;
  background: #0b0b0b;
  padding: 10px;
  font-weight: 900;
  text-align: center;
  letter-spacing: 0.6px;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

NOTE_HOLD = "*Holdings yield = dividend $ / total holdings MV (excludes options/cash from dividends).*"
NOTE_ETRADE = "*E*TRADE-like yield ≈ weighted dividend yield on income-producing holdings (excludes options/cash/zero-yield holdings). Small differences can remain due to rounding and money-market yield methodology.*"
NOTE_SA = "*Buy Yield% auto-pulled from StockAnalysis dividend page (ETF or stock). If blocked/changed, fallback tries yfinance.*"

st.title("PORTFOLIO YIELD LAB — 90s ORANGE")
st.caption("Upload your E*TRADE PortfolioDownload CSV, compute Holdings Yield + E*TRADE-like Yield, then run a VMFXX→Buy what-if.")

# =========================
# Helpers
# =========================
def _to_float(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return pd.NA
    s = str(x).strip()
    if s in {"", "--", "—", "nan", "NaN", "<NA>"}:
        return pd.NA

    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1].strip()

    s = s.replace("$", "").replace(",", "").replace("%", "").strip()
    if s.startswith("-."):
        s = "-0." + s[2:]
    elif s.startswith("."):
        s = "0." + s[1:]

    try:
        v = float(s)
        return -v if neg else v
    except Exception:
        return pd.NA

def _safe_text(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="replace")

@st.cache_data(ttl=60 * 10, show_spinner=False)
def get_last_price_yf(ticker: str):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d", auto_adjust=False)
        if hist is None or hist.empty:
            return None
        return float(hist["Close"].dropna().iloc[-1])
    except Exception:
        return None

# =========================
# StockAnalysis dividend yield fetch
# =========================
SA_XPATH = "/html/body/div[1]/div[1]/div[2]/main/div[2]/div/div[2]/div[1]/div"
SA_ETF_URL = "https://stockanalysis.com/etf/{}/dividend/"
SA_STOCK_URL = "https://stockanalysis.com/stocks/{}/dividend/"

def _extract_first_percent(text: str):
    if not text:
        return None
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*%", text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None

@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)  # cache yields for 6 hours
def get_dividend_yield_stockanalysis(ticker: str):
    """
    Returns dividend yield as a percent (e.g., 3.45 for 3.45%).
    Tries ETF page, then stock page.
    Uses provided xpath first; falls back to scanning for 'Dividend Yield' text.
    """
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return None, None

    try:
        import requests
    except Exception:
        return None, "requests_not_available"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    }

    def fetch(url: str):
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return None, f"http_{r.status_code}"
        return r.text, None

    # Try ETF then stock
    for kind, url in [("ETF", SA_ETF_URL.format(ticker)), ("STOCK", SA_STOCK_URL.format(ticker))]:
        html, err = fetch(url)
        if not html:
            continue

        # 1) XPATH attempt (your provided xpath)
        try:
            import lxml.html as LH
            tree = LH.fromstring(html)
            nodes = tree.xpath(SA_XPATH)
            if nodes:
                txt = " ".join([n.text_content().strip() for n in nodes if hasattr(n, "text_content")]).strip()
                y = _extract_first_percent(txt)
                if y is not None:
                    return y, f"stockanalysis_{kind.lower()}_xpath"
        except Exception:
            pass

        # 2) Fallback: find "Dividend Yield" line anywhere and pull percent
        try:
            m = re.search(r"Dividend\s*Yield[^%]{0,60}(\d+(?:\.\d+)?)\s*%", html, flags=re.IGNORECASE)
            if m:
                return float(m.group(1)), f"stockanalysis_{kind.lower()}_regex"
        except Exception:
            pass

    return None, "stockanalysis_not_found"

@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def get_dividend_yield_yfinance_fallback(ticker: str):
    """
    Returns dividend yield percent via yfinance (dividendYield * 100) if available.
    """
    try:
        info = yf.Ticker(ticker).info or {}
        dy = info.get("dividendYield", None)
        if dy is None:
            return None
        dy = float(dy)
        if dy <= 0:
            return None
        return dy * 100.0
    except Exception:
        return None

# =========================
# Option parsing + grouping
# =========================
_MONTH_MAP = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,"Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}

def parse_option_symbol(sym: str):
    s = str(sym).strip()
    under = s.split(" ")[0].strip() if s else pd.NA

    m = re.search(
        r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b\s+(\d{1,2})\s+'(\d{2})\s+\$([\d.]+)\s+\b(Put|Call)\b",
        s
    )
    if not m:
        return {"UNDER": under, "EXP_DT": pd.NaT, "STRIKE": pd.NA, "CP": pd.NA}

    mon, day, yy, strike, cp = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
    year = 2000 + int(yy)
    month = _MONTH_MAP.get(mon)

    try:
        exp = pd.Timestamp(year=year, month=month, day=int(day))
    except Exception:
        exp = pd.NaT

    return {"UNDER": under, "EXP_DT": exp, "STRIKE": _to_float(strike), "CP": ("P" if cp.lower() == "put" else "C")}

def group_options_under_equities(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "SYM" not in df.columns or "SEC_TYPE" not in df.columns:
        return df

    out = df.copy()
    is_opt = out["SEC_TYPE"].astype(str).str.upper().eq("OPTION")

    for c in ["UNDER","EXP_DT","STRIKE","CP"]:
        out[c] = pd.NA
    parsed = out.loc[is_opt, "SYM"].apply(parse_option_symbol).apply(pd.Series)
    out.loc[is_opt, ["UNDER","EXP_DT","STRIKE","CP"]] = parsed[["UNDER","EXP_DT","STRIKE","CP"]].values

    out["GROUP"] = out["SYM"].astype(str)
    out.loc[is_opt, "GROUP"] = out.loc[is_opt, "UNDER"].fillna(out.loc[is_opt, "SYM"]).astype(str)

    eq_groups = set(out.loc[~is_opt, "SYM"].astype(str).unique())
    out["HAS_EQUITY"] = out["GROUP"].astype(str).isin(eq_groups)

    if "WGT_PCT" in out.columns:
        eq_weight = out.loc[~is_opt].set_index("SYM")["WGT_PCT"].to_dict()
        out["GROUP_WGT"] = out["GROUP"].map(eq_weight)
        out["GROUP_WGT"] = out["GROUP_WGT"].fillna(out.groupby("GROUP")["WGT_PCT"].transform("max"))
    else:
        out["GROUP_WGT"] = 0.0

    out["ROW_KIND"] = is_opt.astype(int)
    out["EXP_SORT"] = pd.to_datetime(out["EXP_DT"], errors="coerce")
    out["STRIKE_SORT"] = out["STRIKE"].map(_to_float)
    out["CP_SORT"] = out["CP"].astype(str).replace({"<NA>": ""})

    out.sort_values(
        by=["HAS_EQUITY","GROUP_WGT","GROUP","ROW_KIND","EXP_SORT","STRIKE_SORT","CP_SORT"],
        ascending=[False, False, True, True, True, True, True],
        inplace=True
    )

    out["DISPLAY_SYM"] = out["SYM"].astype(str)
    out.loc[is_opt, "DISPLAY_SYM"] = "  ↳ " + out.loc[is_opt, "SYM"].astype(str)

    out.reset_index(drop=True, inplace=True)
    out.drop(columns=["EXP_SORT","STRIKE_SORT","CP_SORT"], inplace=True, errors="ignore")
    return out

# =========================
# CSV parsing
# =========================
ACCT_COLS_8 = [
    "ACCOUNT","NET_ACCT_VALUE","TOTAL_GAIN_$","TOTAL_GAIN_PCT",
    "DAY_GAIN_$","DAY_GAIN_PCT","AVAIL_WITHDRAWAL","CASH_PURCH_POWER"
]
HOLD_COLS_15 = [
    "SYM","WGT_PCT","LAST","COST_SH","QTY","COST_TOT","GAIN_$","MV_$","GAIN_PCT",
    "DAY_$","DAY_PCT","DIV_YLD_PCT","DIV_PAY_DT","DIV_$","ACQ_DT"
]

def parse_portfolio_text(text: str):
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    acct_df = pd.DataFrame()
    acct_hdr_idx = next((i for i, l in enumerate(lines) if l.startswith("Account,Net Account Value")), None)
    if acct_hdr_idx is not None:
        data_rows = []
        for j in range(acct_hdr_idx + 1, len(lines)):
            if lines[j].strip() == "":
                break
            data_rows.append(next(csv.reader([lines[j]])))
        if data_rows and len(data_rows[0]) == 8:
            acct_df = pd.DataFrame(data_rows, columns=ACCT_COLS_8)
            for c in acct_df.columns:
                if c != "ACCOUNT":
                    acct_df[c] = acct_df[c].map(_to_float)

    holdings_df = pd.DataFrame()
    hold_hdr_idx = next((i for i, l in enumerate(lines) if l.startswith("Symbol,% of Portfolio")), None)
    if hold_hdr_idx is not None:
        rows = []
        for j in range(hold_hdr_idx + 1, len(lines)):
            if lines[j].strip() == "" or lines[j].startswith("Generated at "):
                break
            rows.append(next(csv.reader([lines[j]])))

        norm_rows = []
        for r in rows:
            if len(r) >= 15:
                norm_rows.append(r[:15])
            else:
                norm_rows.append(r + [""] * (15 - len(r)))

        holdings_df = pd.DataFrame(norm_rows, columns=HOLD_COLS_15)

        num_cols = ["WGT_PCT","LAST","COST_SH","QTY","COST_TOT","GAIN_$","MV_$","GAIN_PCT","DAY_$","DAY_PCT","DIV_YLD_PCT","DIV_$"]
        for c in num_cols:
            holdings_df[c] = holdings_df[c].map(_to_float)

        for dc in ["DIV_PAY_DT","ACQ_DT"]:
            holdings_df[dc] = pd.to_datetime(holdings_df[dc], errors="coerce")

        sym_u = holdings_df["SYM"].astype(str).str.upper()
        opt_mask = holdings_df["SYM"].astype(str).str.contains(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", regex=True) & \
                   holdings_df["SYM"].astype(str).str.contains(r"\b(?:Put|Call)\b", regex=True)

        holdings_df["SEC_TYPE"] = "EQUITY/ETF"
        holdings_df.loc[opt_mask, "SEC_TYPE"] = "OPTION"
        holdings_df.loc[sym_u.eq("CASH"), "SEC_TYPE"] = "CASH"
        holdings_df.loc[sym_u.eq("TOTAL"), "SEC_TYPE"] = "TOTAL"

        holdings_df = holdings_df[holdings_df["SEC_TYPE"] != "TOTAL"].copy()
        holdings_df = group_options_under_equities(holdings_df)

    return acct_df, holdings_df

# =========================
# Yield math
# =========================
def apply_yield_overrides(df: pd.DataFrame, overrides: dict) -> pd.Series:
    y = pd.to_numeric(df.get("DIV_YLD_PCT", 0), errors="coerce").fillna(0.0).astype(float)
    if overrides:
        sym = df["SYM"].astype(str).str.upper()
        for k, v in overrides.items():
            if v is None or (isinstance(v, float) and np.isnan(v)):
                continue
            y = np.where(sym.eq(str(k).upper()), float(v), y)
    return pd.Series(y, index=df.index)

def dividend_dollars_annual(holdings: pd.DataFrame, overrides: dict = None) -> float:
    if holdings is None or holdings.empty:
        return float("nan")
    df = holdings.copy()
    df["MV_$"] = pd.to_numeric(df["MV_$"], errors="coerce").fillna(0.0)

    sec = df["SEC_TYPE"].astype(str).str.upper()
    is_opt_or_cash = sec.isin(["OPTION", "CASH"])

    y = apply_yield_overrides(df, overrides or {})
    y = np.where(is_opt_or_cash, 0.0, y)

    return float((df["MV_$"] * (y / 100.0)).sum())

def holdings_yield_pct(holdings: pd.DataFrame, overrides: dict = None) -> float:
    if holdings is None or holdings.empty:
        return float("nan")
    mv_total = float(pd.to_numeric(holdings["MV_$"], errors="coerce").fillna(0.0).sum())
    if mv_total <= 0:
        return floa

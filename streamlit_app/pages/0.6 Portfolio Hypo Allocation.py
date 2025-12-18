# streamlit_app.py
# PortfolioDownload(6).csv -> Bloomberg 90s orange Streamlit app
# CHANGE (per your request):
# 1) Remove ACCOUNT SUMMARY tab entirely (and account parsing/state).
# 2) Make COST_SH (cost/share) prominent in tables AND ensure scenario COST_SH updates via weighted-average cost when adding to an existing ticker.
# Everything else stays the same.

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

def _num(x, default=0.0) -> float:
    try:
        v = pd.to_numeric(x, errors="coerce")
        if pd.isna(v):
            return float(default)
        return float(v)
    except Exception:
        return float(default)

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

    for kind, url in [("ETF", SA_ETF_URL.format(ticker)), ("STOCK", SA_STOCK_URL.format(ticker))]:
        html, _err = fetch(url)
        if not html:
            continue

        # Try XPath (if lxml available)
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

        # Fallback: regex in HTML
        try:
            m = re.search(r"Dividend\s*Yield[^%]{0,80}(\d+(?:\.\d+)?)\s*%", html, flags=re.IGNORECASE)
            if m:
                return float(m.group(1)), f"stockanalysis_{kind.lower()}_regex"
        except Exception:
            pass

    return None, "stockanalysis_not_found"

@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def get_dividend_yield_yfinance_fallback(ticker: str):
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
# CSV parsing (HOLDINGS ONLY)
# =========================
HOLD_COLS_15 = [
    "SYM","WGT_PCT","LAST","COST_SH","QTY","COST_TOT","GAIN_$","MV_$","GAIN_PCT",
    "DAY_$","DAY_PCT","DIV_YLD_PCT","DIV_PAY_DT","DIV_$","ACQ_DT"
]

def parse_portfolio_text(text: str):
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

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

    return holdings_df

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
        return float("nan")
    div_usd = dividend_dollars_annual(holdings, overrides=overrides)
    return float(div_usd / mv_total * 100.0)

def etrade_like_yield_pct(holdings: pd.DataFrame, overrides: dict = None) -> float:
    if holdings is None or holdings.empty:
        return float("nan")

    df = holdings.copy()
    df["MV_$"] = pd.to_numeric(df["MV_$"], errors="coerce").fillna(0.0)
    sec = df["SEC_TYPE"].astype(str).str.upper()

    y = apply_yield_overrides(df, overrides or {})
    y = np.where(sec.isin(["OPTION", "CASH"]), 0.0, y)

    income_mask = (y > 0.0) & (~sec.isin(["OPTION", "CASH"]))
    income_mv = float(df.loc[income_mask, "MV_$"].sum())
    if income_mv <= 0:
        return float("nan")

    income_div = float((df.loc[income_mask, "MV_$"] * (y[income_mask] / 100.0)).sum())
    return float(income_div / income_mv * 100.0)

# =========================
# What-if: sell VMFXX -> buy new
# =========================
def apply_sell_vmfxx_buy_new(holdings: pd.DataFrame, buy_ticker: str, buy_qty: float, buy_yield_pct: float):
    df = holdings.copy()

    buy_ticker = (buy_ticker or "").strip().upper()
    if not buy_ticker:
        raise ValueError("Buy ticker is blank.")

    px = get_last_price_yf(buy_ticker)
    if px is None:
        raise ValueError(f"Could not fetch price for {buy_ticker} from yfinance.")

    buy_qty = float(buy_qty)
    buy_yield_pct = float(buy_yield_pct)
    buy_mv = px * buy_qty

    vm_mask = (df["SYM"].astype(str).str.upper() == "VMFXX") & (df["SEC_TYPE"].astype(str).str.upper() != "OPTION")
    if vm_mask.sum() == 0:
        raise ValueError("VMFXX row not found in holdings.")
    vm_idx = df.index[vm_mask][0]
    vm_mv = float(pd.to_numeric(df.loc[vm_idx, "MV_$"], errors="coerce") or 0.0)

    sold_mv = min(vm_mv, buy_mv)
    shortfall = max(0.0, buy_mv - vm_mv)

    df.loc[vm_idx, "MV_$"] = vm_mv - sold_mv
    df.loc[vm_idx, "QTY"] = df.loc[vm_idx, "MV_$"]   # VMFXX ~ $1 NAV
    df.loc[vm_idx, "LAST"] = 1.0

    eq_mask = (df["SYM"].astype(str).str.upper() == buy_ticker) & (df["SEC_TYPE"].astype(str).str.upper() == "EQUITY/ETF")
    if eq_mask.sum() > 0:
        idx = df.index[eq_mask][0]

        # --- weighted average cost update ---
        old_qty = _num(df.loc[idx, "QTY"], 0.0)

        old_cost_tot = _num(df.loc[idx, "COST_TOT"], np.nan)
        if np.isnan(old_cost_tot) or old_cost_tot <= 0:
            old_cost_sh = _num(df.loc[idx, "COST_SH"], np.nan)
            if not np.isnan(old_cost_sh) and old_cost_sh > 0 and old_qty > 0:
                old_cost_tot = old_cost_sh * old_qty
            else:
                old_cost_tot = 0.0

        new_qty = old_qty + buy_qty
        new_cost_tot = old_cost_tot + buy_mv
        new_cost_sh = (new_cost_tot / new_qty) if new_qty > 0 else 0.0

        df.loc[idx, "QTY"] = new_qty
        df.loc[idx, "COST_TOT"] = new_cost_tot
        df.loc[idx, "COST_SH"] = new_cost_sh

        df.loc[idx, "MV_$"] = _num(df.loc[idx, "MV_$"], 0.0) + buy_mv
        df.loc[idx, "LAST"] = px
        df.loc[idx, "DIV_YLD_PCT"] = buy_yield_pct

        # keep scenario row consistent
        df.loc[idx, "GAIN_$"] = _num(df.loc[idx, "MV_$"], 0.0) - _num(df.loc[idx, "COST_TOT"], 0.0)
        ct = _num(df.loc[idx, "COST_TOT"], 0.0)
        df.loc[idx, "GAIN_PCT"] = (df.loc[idx, "GAIN_$"] / ct * 100.0) if ct > 0 else 0.0

        df.loc[idx, "DISPLAY_SYM"] = buy_ticker
        df.loc[idx, "GROUP"] = buy_ticker
        df.loc[idx, "HAS_EQUITY"] = True
        df.loc[idx, "ROW_KIND"] = 0

    else:
        for col in ["DISPLAY_SYM","SEC_TYPE","UNDER","EXP_DT","STRIKE","CP","GROUP","HAS_EQUITY","GROUP_WGT","ROW_KIND"]:
            if col not in df.columns:
                df[col] = pd.NA

        new_row = {c: pd.NA for c in df.columns}
        new_row.update({
            "DISPLAY_SYM": buy_ticker,
            "SYM": buy_ticker,
            "WGT_PCT": pd.NA,
            "LAST": px,
            "COST_SH": px,
            "QTY": buy_qty,
            "COST_TOT": buy_mv,
            "GAIN_$": 0.0,
            "MV_$": buy_mv,
            "GAIN_PCT": 0.0,
            "DAY_$": 0.0,
            "DAY_PCT": 0.0,
            "DIV_YLD_PCT": buy_yield_pct,
            "DIV_PAY_DT": pd.NaT,
            "DIV_$": pd.NA,
            "ACQ_DT": pd.NaT,
            "SEC_TYPE": "EQUITY/ETF",
            "UNDER": pd.NA,
            "EXP_DT": pd.NaT,
            "STRIKE": pd.NA,
            "CP": pd.NA,
            "GROUP": buy_ticker,
            "HAS_EQUITY": True,
            "GROUP_WGT": pd.NA,
            "ROW_KIND": 0
        })
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df["MV_$"] = pd.to_numeric(df["MV_$"], errors="coerce").fillna(0.0)
    total_mv = float(df["MV_$"].sum())
    df["WGT_PCT"] = np.where(total_mv > 0, df["MV_$"] / total_mv * 100.0, 0.0)

    df = group_options_under_equities(df)
    return df, {"buy_price": px, "buy_mv": buy_mv, "sold_vmfxx_mv": sold_mv, "shortfall_mv": shortfall, "holdings_total_mv": total_mv}

# =========================
# Formatting (accounting)
# =========================
def fmt_money(x):
    try:
        v = float(x)
        if np.isnan(v):
            return ""
        return f"${v:,.2f}"
    except Exception:
        return ""

def fmt_pct4(x):
    try:
        v = float(x)
        if np.isnan(v):
            return ""
        return f"{v:.4f}%"
    except Exception:
        return ""

def fmt_pp(x):
    try:
        v = float(x)
        if np.isnan(v):
            return ""
        sign = "+" if v >= 0 else ""
        return f"{sign}{v:.4f} pp"
    except Exception:
        return ""

def fmt_money_delta(x):
    try:
        v = float(x)
        if np.isnan(v):
            return ""
        sign = "+" if v >= 0 else "-"
        return f"{sign}${abs(v):,.2f}"
    except Exception:
        return ""

def pretty_holdings(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()

    # COST_SH moved up (prominent)
    front = ["DISPLAY_SYM","SEC_TYPE","WGT_PCT","MV_$","COST_SH","COST_TOT","GAIN_$","GAIN_PCT","DIV_YLD_PCT","LAST","QTY"]
    cols = front + [c for c in out.columns if c not in front]
    cols = [c for c in cols if c in out.columns]
    out = out[cols]

    if "WGT_PCT" in out.columns:
        out["WGT_PCT"] = out["WGT_PCT"].apply(lambda v: fmt_pct4(v))
    if "GAIN_PCT" in out.columns:
        out["GAIN_PCT"] = out["GAIN_PCT"].apply(lambda v: fmt_pct4(v))
    if "DIV_YLD_PCT" in out.columns:
        out["DIV_YLD_PCT"] = out["DIV_YLD_PCT"].apply(lambda v: fmt_pct4(v))
    for c in ["MV_$","COST_SH","COST_TOT","GAIN_$","LAST","DAY_$","DIV_$"]:
        if c in out.columns:
            out[c] = out[c].apply(lambda v: fmt_money(v))
    return out

# =========================
# What-if compare renderer (STREAMLIT NATIVE)
# =========================
def render_whatif_summary(payload: dict):
    st.subheader("WHAT-IF SUMMARY (OLD vs NEW)")

    d1, d2, d3, d4, d5, d6, d7 = st.columns(7, gap="medium")
    d1.metric("Buy Ticker", payload["buy_ticker"])
    d2.metric("Buy Price", fmt_money(payload["buy_price"]))
    d3.metric("Buy QTY", f'{payload["buy_qty"]:,.4f}')
    d4.metric("Buy MV $", fmt_money(payload["buy_mv"]))
    d5.metric("Buy Yield %", fmt_pct4(payload["buy_yield"]))
    d6.metric("Sold VMFXX $", fmt_money(payload["sold_vmfxx_mv"]))
    d7.metric("Shortfall $", fmt_money(payload["shortfall_mv"]))

    st.markdown(NOTE_HOLD)
    st.markdown(NOTE_ETRADE)
    st.markdown(NOTE_SA)
    st.markdown("---")

    h1, h2, h3, h4 = st.columns([2.2, 1.0, 1.0, 1.0], gap="medium")
    h1.markdown("<div class='bb_hdr'>METRIC</div>", unsafe_allow_html=True)
    h2.markdown("<div class='bb_hdr'>OLD</div>", unsafe_allow_html=True)
    h3.markdown("<div class='bb_hdr'>NEW</div>", unsafe_allow_html=True)
    h4.markdown("<div class='bb_hdr'>CHANGE</div>", unsafe_allow_html=True)

    rows = [
        ("Holdings Yield %", payload["old_hy"], payload["new_hy"], "pp"),
        ("E*TRADE-like Yield %", payload["old_ey"], payload["new_ey"], "pp"),
        ("Annual Dividend $ (est.)", payload["old_div"], payload["new_div"], "$"),
        ("Holdings MV $", payload["old_mv_total"], payload["new_mv_total"], "$"),
    ]

    for name, oldv, newv, kind in rows:
        c1, c2, c3, c4 = st.columns([2.2, 1.0, 1.0, 1.0], gap="medium")
        c1.markdown(f"**{name}**")

        if kind == "pp":
            c2.metric(" ", fmt_pct4(oldv))
            c3.metric(" ", fmt_pct4(newv))
            c4.metric(" ", fmt_pp(float(newv) - float(oldv)))
        else:
            c2.metric(" ", fmt_money(oldv))
            c3.metric(" ", fmt_money(newv))
            c4.metric(" ", fmt_money_delta(float(newv) - float(oldv)))

    st.caption(f"Buy yield source: {payload.get('buy_yield_source','unknown')}")

# =========================
# UI — organized (KPIs top, data bottom)
# =========================
if "hold_df" not in st.session_state:
    st.session_state.hold_df = None
if "last_scenario_df" not in st.session_state:
    st.session_state.last_scenario_df = None
if "last_whatif_payload" not in st.session_state:
    st.session_state.last_whatif_payload = None
if "buy_qty" not in st.session_state:
    st.session_state.buy_qty = 0.0

top1, top2, top3 = st.columns([1.3, 1.0, 1.2], gap="large")

with top1:
    st.subheader("UPLOAD")
    f = st.file_uploader("Upload PortfolioDownload.csv", type=["csv"], label_visibility="collapsed")

with top2:
    st.subheader("CALIBRATE (Optional)")
    vmfxx_override_str = st.text_input(
        "VMFXX Yield % override (optional)",
        value="",
        help="Leave blank to use CSV yield.",
    )
    vmfxx_override = _to_float(vmfxx_override_str) if vmfxx_override_str.strip() else np.nan

with top3:
    st.subheader("ACTIONS")
    parse_clicked = st.button("PARSE FILE", use_container_width=True)
    clear_clicked = st.button("CLEAR STATE", use_container_width=True)

st.subheader("VMFXX → BUY (WHAT-IF)")
w1, w2, w3 = st.columns([1.3, 1.1, 1.1], gap="medium")

with w1:
    buy_ticker_raw = st.text_input("Buy Ticker", value="", help="Auto uppercased.")
    buy_ticker = (buy_ticker_raw or "").upper()

with w2:
    st.markdown("**Buy QTY (shares)**")
    p1, p2, p3, p4 = st.columns([1, 1, 1, 1], gap="small")

    if p1.button("25", use_container_width=True):
        st.session_state.buy_qty = float(st.session_state.buy_qty) + 25.0
    if p2.button("50", use_container_width=True):
        st.session_state.buy_qty = float(st.session_state.buy_qty) + 50.0
    if p3.button("100", use_container_width=True):
        st.session_state.buy_qty = float(st.session_state.buy_qty) + 100.0
    if p4.button("RESET", use_container_width=True):
        st.session_state.buy_qty = 0.0

    buy_qty = float(st.session_state.buy_qty)
    st.markdown(f"**Current QTY:** `{buy_qty:,.4f}`")

with w3:
    run_clicked = st.button("RUN WHAT-IF (auto yield)", use_container_width=True)
    st.markdown("**TIP:** Buy yield auto-pulls from StockAnalysis")

st.divider()

if clear_clicked:
    st.session_state.hold_df = None
    st.session_state.last_scenario_df = None
    st.session_state.last_whatif_payload = None
    st.session_state.buy_qty = 0.0
    st.cache_data.clear()
    st.rerun()

def overrides_dict():
    d = {}
    if vmfxx_override is not None and not (isinstance(vmfxx_override, float) and np.isnan(vmfxx_override)):
        d["VMFXX"] = float(vmfxx_override)
    return d

if parse_clicked:
    if f is None:
        st.error("Upload a CSV first.")
    else:
        try:
            text = _safe_text(f.getvalue())
            hold_df = parse_portfolio_text(text)
            st.session_state.hold_df = hold_df
            st.success("Parsed successfully.")
        except Exception as e:
            st.error(f"Parse error: {e}")

hold_df = st.session_state.hold_df
ovr = overrides_dict()

# Top KPI strip
if hold_df is not None and not hold_df.empty:
    annual_div = dividend_dollars_annual(hold_df, overrides=ovr)
    hy = holdings_yield_pct(hold_df, overrides=ovr)
    ey = etrade_like_yield_pct(hold_df, overrides=ovr)
    mv_total = float(pd.to_numeric(hold_df["MV_$"], errors="coerce").fillna(0.0).sum())

    k1, k2, k3, k4 = st.columns(4, gap="medium")
    k1.metric("Annual Dividend $ (est.)", fmt_money(annual_div))
    k2.metric("Holdings MV $", fmt_money(mv_total))
    k3.metric("Holdings Yield %", fmt_pct4(hy))
    k4.metric("E*TRADE-like Yield %", fmt_pct4(ey))
else:
    st.info("Upload + PARSE to view yields and run what-if.")

# Run what-if (auto yield from StockAnalysis)
if run_clicked:
    if hold_df is None or hold_df.empty:
        st.error("Parse the file first.")
    elif not buy_ticker:
        st.error("Enter a Buy Ticker.")
    elif buy_qty <= 0:
        st.error("Buy QTY must be > 0.")
    else:
        try:
            buy_yield, src = get_dividend_yield_stockanalysis(buy_ticker)
            if buy_yield is None:
                yf_y = get_dividend_yield_yfinance_fallback(buy_ticker)
                if yf_y is not None:
                    buy_yield, src = yf_y, "yfinance_fallback"
            if buy_yield is None:
                raise ValueError(f"Could not fetch dividend yield for {buy_ticker} from StockAnalysis (or yfinance fallback).")

            base_div = dividend_dollars_annual(hold_df, overrides=ovr)
            old_hy = holdings_yield_pct(hold_df, overrides=ovr)
            old_ey = etrade_like_yield_pct(hold_df, overrides=ovr)
            old_mv_total = float(pd.to_numeric(hold_df["MV_$"], errors="coerce").fillna(0.0).sum())

            scen_df, info = apply_sell_vmfxx_buy_new(
                hold_df,
                buy_ticker=buy_ticker,
                buy_qty=buy_qty,
                buy_yield_pct=buy_yield
            )

            new_div = dividend_dollars_annual(scen_df, overrides=ovr)
            new_hy = holdings_yield_pct(scen_df, overrides=ovr)
            new_ey = etrade_like_yield_pct(scen_df, overrides=ovr)
            new_mv_total = float(info.get("holdings_total_mv", np.nan))

            st.session_state.last_scenario_df = scen_df
            st.session_state.last_whatif_payload = dict(
                buy_ticker=buy_ticker,
                buy_price=info["buy_price"],
                buy_qty=buy_qty,
                buy_mv=info["buy_mv"],
                buy_yield=float(buy_yield),
                buy_yield_source=src,
                sold_vmfxx_mv=info["sold_vmfxx_mv"],
                shortfall_mv=info["shortfall_mv"],
                old_hy=old_hy, new_hy=new_hy,
                old_ey=old_ey, new_ey=new_ey,
                old_div=base_div, new_div=new_div,
                old_mv_total=old_mv_total, new_mv_total=new_mv_total,
            )

            st.success("What-if calculated successfully.")
        except Exception as e:
            st.error(f"What-if error: {e}")

# Render summary
payload = st.session_state.last_whatif_payload
if isinstance(payload, dict):
    render_whatif_summary(payload)

    scen_df = st.session_state.last_scenario_df
    if isinstance(scen_df, pd.DataFrame) and not scen_df.empty:
        scen_csv = scen_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "DOWNLOAD holdings_scenario.csv",
            data=scen_csv,
            file_name="holdings_scenario.csv",
            mime="text/csv",
            use_container_width=True
        )

# Bottom: data tables
st.divider()
st.subheader("DATA (DETAILS)")

tabs = st.tabs(["HOLDINGS (Grouped)", "SCENARIO HOLDINGS"])

with tabs[0]:
    if hold_df is not None and not hold_df.empty:
        st.dataframe(pretty_holdings(hold_df), use_container_width=True, hide_index=True)
        csv_bytes = hold_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "DOWNLOAD holdings_grouped.csv",
            data=csv_bytes,
            file_name="holdings_grouped.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("No holdings loaded yet.")

with tabs[1]:
    scen_df = st.session_state.last_scenario_df
    if isinstance(scen_df, pd.DataFrame) and not scen_df.empty:
        st.dataframe(pretty_holdings(scen_df), use_container_width=True, hide_index=True)
    else:
        st.info("Run a what-if to populate scenario holdings here.")

st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

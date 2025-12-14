# streamlit_app.py
# PortfolioDownload(6).csv -> Bloomberg 90s orange Streamlit app (no controls in sidebar, sidebar stays visible)

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
st.set_page_config(page_title="Portfolio Yield Lab (90s Orange)", layout="wide")  # ALWAYS WIDE; do NOT collapse/hide sidebar

CSS = """
<style>
/* Global */
html, body, [class*="css"]  {
  background: #000000 !important;
  color: #ff9900 !important;
  font-family: "Courier New", Courier, monospace !important;
}

/* Keep sidebar visible and untouched; DO NOT hide it */
section[data-testid="stSidebar"] { display: block !important; }

/* Main container */
.block-container {
  padding-top: 1.0rem;
  padding-bottom: 1.0rem;
  max-width: 1800px;
}

/* Headings */
h1, h2, h3, h4, h5, h6 {
  color: #ff9900 !important;
  font-family: "Courier New", Courier, monospace !important;
  letter-spacing: 0.4px;
}

/* Inputs */
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

/* File uploader */
div[data-testid="stFileUploader"] {
  border: 2px solid #ff9900 !important;
  background: #050505 !important;
  padding: 12px !important;
}

/* 3D Buttons */
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

/* Dataframes */
[data-testid="stDataFrame"] {
  border: 2px solid #ff9900 !important;
}

/* Metrics */
div[data-testid="metric-container"] {
  border: 2px solid #ff9900 !important;
  background: #050505 !important;
  padding: 10px !important;
}
div[data-testid="metric-container"] * {
  color: #ff9900 !important;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

NOTE = "*Holdings yield = good for investment-focused tracking; Account yield = best for “what my account actually earns.”*"
NOTE2 = "*E*TRADE-like yield ≈ dividend yield on income-producing holdings (excludes options/cash/zero-yield holdings). Small differences can remain due to rounding and money-market yield methodology.*"

st.title("PORTFOLIO YIELD LAB — 90s ORANGE")
st.caption("Upload your E*TRADE PortfolioDownload CSV, compute Holdings Yield + Account Yield + E*TRADE-like Yield, then run a VMFXX→Buy what-if.")

# =========================
# Helpers
# =========================
def _to_float(x):
    """
    Convert strings like '$1,234.50', '(1,234.50)', '-.02', '.25' to float.
    Returns pd.NA if not numeric.
    """
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

@st.cache_data(ttl=60*10, show_spinner=False)
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

    return {"UNDER": under, "EXP_DT": exp, "STRIKE": _to_float(strike), "CP": ("P" if cp.lower()=="put" else "C")}

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

    # Account Summary
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

    # Holdings
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

def get_net_account_value(acct_df: pd.DataFrame) -> float:
    if acct_df is not None and not acct_df.empty and "NET_ACCT_VALUE" in acct_df.columns:
        v = acct_df["NET_ACCT_VALUE"].iloc[0]
        if pd.notna(v) and float(v) > 0:
            return float(v)
    return float("nan")

# =========================
# Yield math (3 methods)
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

def account_yield_pct(holdings: pd.DataFrame, net_account_value: float, overrides: dict = None) -> float:
    if net_account_value is None or pd.isna(net_account_value) or float(net_account_value) <= 0:
        return float("nan")
    div_usd = dividend_dollars_annual(holdings, overrides=overrides)
    return float(div_usd / float(net_account_value) * 100.0)

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
    df.loc[vm_idx, "QTY"] = df.loc[vm_idx, "MV_$"]
    df.loc[vm_idx, "LAST"] = 1.0

    eq_mask = (df["SYM"].astype(str).str.upper() == buy_ticker) & (df["SEC_TYPE"].astype(str).str.upper() == "EQUITY/ETF")
    if eq_mask.sum() > 0:
        idx = df.index[eq_mask][0]
        df.loc[idx, "QTY"] = float(pd.to_numeric(df.loc[idx, "QTY"], errors="coerce") or 0.0) + buy_qty
        df.loc[idx, "MV_$"] = float(pd.to_numeric(df.loc[idx, "MV_$"], errors="coerce") or 0.0) + buy_mv
        df.loc[idx, "LAST"] = px
        df.loc[idx, "DIV_YLD_PCT"] = buy_yield_pct
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

def pretty_holdings(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    front = ["DISPLAY_SYM","SEC_TYPE","WGT_PCT","MV_$","DIV_YLD_PCT","LAST","QTY"]
    cols = front + [c for c in out.columns if c not in front]
    cols = [c for c in cols if c in out.columns]
    out = out[cols]

    if "WGT_PCT" in out.columns:
        out["WGT_PCT"] = out["WGT_PCT"].apply(lambda v: fmt_pct4(v))
    if "DIV_YLD_PCT" in out.columns:
        out["DIV_YLD_PCT"] = out["DIV_YLD_PCT"].apply(lambda v: fmt_pct4(v))
    for c in ["MV_$","LAST","COST_SH","COST_TOT","GAIN_$","DAY_$","DIV_$"]:
        if c in out.columns:
            out[c] = out[c].apply(lambda v: fmt_money(v))
    return out

# =========================
# UI — no sidebar controls
# =========================
top_left, top_right = st.columns([1.35, 1.0], gap="large")

with top_left:
    st.subheader("1) Upload Portfolio CSV")
    f = st.file_uploader("Upload PortfolioDownload.csv", type=["csv"], label_visibility="collapsed")

with top_right:
    st.subheader("2) Optional yield override (to calibrate)")
    vmfxx_override_str = st.text_input(
        "VMFXX Yield % override (optional)",
        value="",
        help="Leave blank to use CSV yield. You can enter 3.86 or 3.86% or $-style strings; it will parse.",
    )
    vmfxx_override = _to_float(vmfxx_override_str) if vmfxx_override_str.strip() else np.nan

st.divider()

b1, b2, b3, b4 = st.columns([1, 1, 1.2, 1.8], gap="medium")
with b1:
    parse_clicked = st.button("PARSE FILE", use_container_width=True)
with b2:
    clear_clicked = st.button("CLEAR STATE", use_container_width=True)
with b3:
    run_clicked = st.button("RUN VMFXX→BUY WHAT-IF", use_container_width=True)
with b4:
    st.markdown("**TIP:** Inputs accept accounting format like `$1,000.00` or `(1,000.00)`")

if "acct_df" not in st.session_state:
    st.session_state.acct_df = None
if "hold_df" not in st.session_state:
    st.session_state.hold_df = None
if "net_val" not in st.session_state:
    st.session_state.net_val = np.nan

if clear_clicked:
    st.session_state.acct_df = None
    st.session_state.hold_df = None
    st.session_state.net_val = np.nan
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
            acct_df, hold_df = parse_portfolio_text(text)
            st.session_state.acct_df = acct_df
            st.session_state.hold_df = hold_df
            st.session_state.net_val = get_net_account_value(acct_df)
            st.success("Parsed successfully.")
        except Exception as e:
            st.error(f"Parse error: {e}")

acct_df = st.session_state.acct_df
hold_df = st.session_state.hold_df
net_val = st.session_state.net_val
ovr = overrides_dict()

if acct_df is not None and not acct_df.empty:
    st.subheader("ACCOUNT SUMMARY")
    acct_disp = acct_df.copy()
    for c in acct_disp.columns:
        if c != "ACCOUNT":
            acct_disp[c] = acct_disp[c].apply(lambda v: fmt_money(v) if "PCT" not in c else fmt_pct4(v))
    st.dataframe(acct_disp, use_container_width=True, hide_index=True)

if hold_df is not None and not hold_df.empty:
    st.subheader("HOLDINGS (grouped: equity then its options)")
    st.dataframe(pretty_holdings(hold_df), use_container_width=True, hide_index=True)

    annual_div = dividend_dollars_annual(hold_df, overrides=ovr)
    hy = holdings_yield_pct(hold_df, overrides=ovr)
    ay = account_yield_pct(hold_df, net_val, overrides=ovr)
    ey = etrade_like_yield_pct(hold_df, overrides=ovr)

    mv_total = float(pd.to_numeric(hold_df["MV_$"], errors="coerce").fillna(0.0).sum())

    m1, m2, m3, m4, m5 = st.columns(5, gap="medium")
    m1.metric("Annual Dividend $ (est.)", fmt_money(annual_div))
    m2.metric("Holdings MV $", fmt_money(mv_total))
    m3.metric("Holdings Yield %", fmt_pct4(hy))
    m4.metric("Account Yield %", fmt_pct4(ay))
    m5.metric("E*TRADE-like Yield %", fmt_pct4(ey))

    st.markdown(NOTE)
    st.markdown(NOTE2)

    csv_bytes = hold_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "DOWNLOAD holdings_grouped.csv",
        data=csv_bytes,
        file_name="holdings_grouped.csv",
        mime="text/csv",
        use_container_width=True
    )

st.divider()

st.subheader("VMFXX → BUY (WHAT-IF)")

c1, c2, c3 = st.columns([1.2, 1.0, 1.0], gap="medium")

# ---- Ticker: auto uppercases IN THE BOX (session_state snap) ----
if "buy_ticker" not in st.session_state:
    st.session_state.buy_ticker = ""

buy_ticker_raw = st.text_input("Buy Ticker", key="buy_ticker", help="Auto uppercased as you type.")
buy_ticker_up = (buy_ticker_raw or "").upper()
if buy_ticker_raw != buy_ticker_up:
    st.session_state.buy_ticker = buy_ticker_up
    st.rerun()

with c2:
    buy_qty_str = st.text_input("Buy QTY (shares)", value="0", help="Accounting format allowed, e.g., 1,000")
    buy_qty = _to_float(buy_qty_str)
    buy_qty = float(buy_qty) if pd.notna(buy_qty) else 0.0
with c3:
    buy_yield_str = st.text_input("Buy Yield %", value="0", help="Enter like 18.91 or 18.91%")
    buy_yield = _to_float(buy_yield_str)
    buy_yield = float(buy_yield) if pd.notna(buy_yield) else 0.0

# Place the ticker input column output (after rerun-safe section)
with c1:
    buy_ticker = st.session_state.buy_ticker

if run_clicked:
    if hold_df is None or hold_df.empty:
        st.error("Parse the file first.")
    elif not buy_ticker:
        st.error("Enter a Buy Ticker.")
    elif buy_qty <= 0:
        st.error("Buy QTY must be > 0.")
    else:
        try:
            base_div = dividend_dollars_annual(hold_df, overrides=ovr)
            old_hy = holdings_yield_pct(hold_df, overrides=ovr)
            old_ay = account_yield_pct(hold_df, net_val, overrides=ovr)
            old_ey = etrade_like_yield_pct(hold_df, overrides=ovr)

            scen_df, info = apply_sell_vmfxx_buy_new(
                hold_df,
                buy_ticker=buy_ticker,
                buy_qty=buy_qty,
                buy_yield_pct=buy_yield
            )

            new_div = dividend_dollars_annual(scen_df, overrides=ovr)
            new_hy = holdings_yield_pct(scen_df, overrides=ovr)
            new_ay = account_yield_pct(scen_df, net_val, overrides=ovr)
            new_ey = etrade_like_yield_pct(scen_df, overrides=ovr)

            st.success("What-if calculated successfully.")

            summary = pd.DataFrame([{
                "Buy Ticker": buy_ticker,
                "Buy Price": info["buy_price"],
                "Buy QTY": buy_qty,
                "Buy MV $": info["buy_mv"],
                "Sold VMFXX MV $": info["sold_vmfxx_mv"],
                "Shortfall MV $": info["shortfall_mv"],

                "Old Holdings Yield %": old_hy,
                "New Holdings Yield %": new_hy,
                "Δ Holdings (pp)": (new_hy - old_hy),

                "Old Account Yield %": old_ay,
                "New Account Yield %": new_ay,
                "Δ Account (pp)": (new_ay - old_ay),

                "Old E*TRADE-like Yield %": old_ey,
                "New E*TRADE-like Yield %": new_ey,
                "Δ E*TRADE-like (pp)": (new_ey - old_ey),

                "Old Annual Dividend $": base_div,
                "New Annual Dividend $": new_div,
                "Net Account Value $": net_val,
            }])

            disp = summary.copy()
            for c in ["Buy MV $","Sold VMFXX MV $","Shortfall MV $","Old Annual Dividend $","New Annual Dividend $","Net Account Value $"]:
                disp[c] = disp[c].apply(fmt_money)
            disp["Buy Price"] = disp["Buy Price"].apply(fmt_money)

            for c in [
                "Old Holdings Yield %","New Holdings Yield %","Δ Holdings (pp)",
                "Old Account Yield %","New Account Yield %","Δ Account (pp)",
                "Old E*TRADE-like Yield %","New E*TRADE-like Yield %","Δ E*TRADE-like (pp)"
            ]:
                disp[c] = disp[c].apply(fmt_pct4)

            st.subheader("WHAT-IF SUMMARY (OLD vs NEW)")
            st.dataframe(disp, use_container_width=True, hide_index=True)
            st.markdown(NOTE)
            st.markdown(NOTE2)

            st.subheader("SCENARIO HOLDINGS (grouped)")
            st.dataframe(pretty_holdings(scen_df), use_container_width=True, hide_index=True)

            scen_csv = scen_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "DOWNLOAD holdings_scenario.csv",
                data=scen_csv,
                file_name="holdings_scenario.csv",
                mime="text/csv",
                use_container_width=True
            )

        except Exception as e:
            st.error(f"What-if error: {e}")

st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

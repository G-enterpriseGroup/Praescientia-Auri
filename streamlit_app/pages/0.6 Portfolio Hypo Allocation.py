# streamlit_app.py
# PortfolioDownload(6).csv -> Bloomberg 90s orange Streamlit app
# UPDATE:
# - Auto-pull Buy Yield % from StockAnalysis (etf + stocks dividend pages)
# - Remove Net Account Value KPI + remove Account Summary tab
# - Buy QTY preset buttons (25/50/100) that add each click (FIXED using callbacks)
# - Scenario holdings: when adding to existing ticker, update COST_TOT + COST_SH using weighted average,
#   and also update GAIN_$ + GAIN_PCT to keep the row consistent.
# - UI: Make "METRIC" column label font match OLD/NEW sizing in WHAT-IF table.
# - NEW: Basket buys: allow up to 10 rows (multiple investments in one run)
# - NEW: Purchasing Power (H3): use cash first, then VMFXX, then Shortfall.

import csv
import re
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import requests
from datetime import datetime

N_BUYS = 10

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

/* BIG left-side metric labels to match st.metric sizing */
.bb_metric_name {
  font-size: 2.05rem;          /* close to Streamlit st.metric value size */
  font-weight: 900;
  line-height: 1.05;
  padding-top: 0.65rem;         /* aligns vertically with st.metric value */
  padding-bottom: 0.65rem;
  white-space: nowrap;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

NOTE_HOLD = "*Holdings yield = dividend $ / total holdings MV (excludes options/cash from dividends).*"
NOTE_ETRADE = "*E*TRADE-like yield ≈ weighted dividend yield on income-producing holdings (excludes options/cash/zero-yield holdings). Small differences can remain due to rounding and money-market yield methodology.*"
NOTE_YIELD = "*Buy Yield % auto-fills from StockAnalysis when ticker changes. You can still override it manually.*"
NOTE_BASKET = "*Basket: fill up to 10 buy rows. Each row uses Purchasing Power (H3) first, then sells VMFXX for any remaining funding.*"

st.title("PORTFOLIO YIELD LAB — 90s ORANGE")
st.caption("Upload your E*TRADE PortfolioDownload CSV, compute Holdings Yield + E*TRADE-like Yield, then run a VMFXX→Buy what-if (basket) with optional Purchasing Power cash (H3).")

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

@st.cache_data(ttl=60 * 60, show_spinner=False)
def get_dividend_yield_stockanalysis(ticker: str):
    """
    Pull Dividend Yield % from StockAnalysis dividend page.
    Tries ETF URL first, then Stocks URL.
    Returns float yield percent (e.g., 4.21) or None.
    """
    t = (ticker or "").strip().upper()
    if not t:
        return None

    urls = [
        f"https://stockanalysis.com/etf/{t}/dividend/",
        f"https://stockanalysis.com/stocks/{t}/dividend/",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:146.0) Gecko/20100101 Firefox/146.0"
    }

    patterns = [
        r"Dividend Yield[^0-9]{0,300}([\d.]+)\s*%",
        r"Dividend Yield\s*</[^>]+>\s*<[^>]+>\s*([\d.]+)\s*%",
        r"Dividend\s*Yield[^%]{0,300}([\d.]+)%",
    ]

    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code != 200:
                continue
            html = r.text or ""
            for pat in patterns:
                m = re.search(pat, html, flags=re.IGNORECASE | re.DOTALL)
                if m:
                    v = _to_float(m.group(1))
                    if pd.notna(v):
                        return float(v)
        except Exception:
            continue

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
# What-if: sell VMFXX -> buy new (single, with optional VMFXX cap + price override)
# =========================
def _num(df, idx, col, default=np.nan):
    try:
        v = pd.to_numeric(df.loc[idx, col], errors="coerce")
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default

def apply_sell_vmfxx_buy_new(
    holdings: pd.DataFrame,
    buy_ticker: str,
    buy_qty: float,
    buy_yield_pct: float,
    vmfxx_sell_max_mv: float = None,
    buy_price_override: float = None,
):
    """
    Apply a single buy funded by selling VMFXX.
    vmfxx_sell_max_mv: optional cap on how much VMFXX MV to sell for this buy.
    buy_price_override: optional last price, to avoid re-calling yfinance if already fetched.
    """
    df = holdings.copy()

    buy_ticker = (buy_ticker or "").strip().upper()
    if not buy_ticker:
        raise ValueError("Buy ticker is blank.")

    if buy_price_override is not None:
        px = float(buy_price_override)
    else:
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

    # Target funding from VMFXX for this buy
    if vmfxx_sell_max_mv is None:
        vm_target = buy_mv
    else:
        try:
            vm_target = float(vmfxx_sell_max_mv)
        except Exception:
            vm_target = buy_mv
        vm_target = max(0.0, min(buy_mv, vm_target))

    sold_mv = min(vm_mv, vm_target)
    shortfall = max(0.0, buy_mv - sold_mv)

    df.loc[vm_idx, "MV_$"] = vm_mv - sold_mv
    df.loc[vm_idx, "QTY"] = df.loc[vm_idx, "MV_$"]   # VMFXX ~ $1 NAV
    df.loc[vm_idx, "LAST"] = 1.0

    eq_mask = (df["SYM"].astype(str).str.upper() == buy_ticker) & (df["SEC_TYPE"].astype(str).str.upper() == "EQUITY/ETF")
    if eq_mask.sum() > 0:
        idx = df.index[eq_mask][0]

        prev_qty = _num(df, idx, "QTY", default=0.0)
        prev_cost_sh = _num(df, idx, "COST_SH", default=np.nan)
        prev_cost_tot = _num(df, idx, "COST_TOT", default=np.nan)

        if not np.isfinite(prev_cost_tot) or prev_cost_tot <= 0:
            if np.isfinite(prev_cost_sh) and prev_qty > 0:
                prev_cost_tot = prev_qty * prev_cost_sh
            else:
                prev_last = _num(df, idx, "LAST", default=px)
                prev_cost_tot = prev_qty * (prev_last if np.isfinite(prev_last) else px)

        new_purchase_cost = buy_qty * px
        new_total_cost = prev_cost_tot + new_purchase_cost
        new_total_qty = prev_qty + buy_qty
        new_cost_sh = (new_total_cost / new_total_qty) if new_total_qty > 0 else px

        df.loc[idx, "QTY"] = new_total_qty
        df.loc[idx, "MV_$"] = _num(df, idx, "MV_$", default=0.0) + buy_mv
        df.loc[idx, "LAST"] = px
        df.loc[idx, "DIV_YLD_PCT"] = buy_yield_pct

        df.loc[idx, "COST_TOT"] = new_total_cost
        df.loc[idx, "COST_SH"] = new_cost_sh

        mv_now = _num(df, idx, "MV_$", default=0.0)
        gain_now = mv_now - new_total_cost
        df.loc[idx, "GAIN_$"] = gain_now
        df.loc[idx, "GAIN_PCT"] = (gain_now / new_total_cost * 100.0) if new_total_cost > 0 else 0.0

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
    return df, {
        "buy_price": px,
        "buy_mv": buy_mv,
        "sold_vmfxx_mv": sold_mv,
        "shortfall_mv": shortfall,
        "holdings_total_mv": total_mv
    }

# =========================
# What-if: basket buys (up to 10) with Purchasing Power
# =========================
def apply_sell_vmfxx_buy_basket(
    holdings: pd.DataFrame,
    buys: list,
    purchasing_power: float = 0.0,
    use_purchasing_power_first: bool = True,
):
    """
    buys: list of dicts: {"ticker": str, "qty": float, "yield": float}
    purchasing_power: cash/margin (H3) to use BEFORE selling VMFXX.
    Applies sequentially, returning final df + basket info + per-row details.
    Funding order per buy: Purchasing Power -> VMFXX -> Shortfall.
    """
    if holdings is None or holdings.empty:
        raise ValueError("Holdings are empty.")

    df = holdings.copy()
    details = []
    total_buy_mv = 0.0
    total_sold_vmfxx = 0.0
    total_shortfall = 0.0
    total_pp_used = 0.0

    # validate VMFXX exists once up-front
    vm_mask = (df["SYM"].astype(str).str.upper() == "VMFXX") & (df["SEC_TYPE"].astype(str).str.upper() != "OPTION")
    if vm_mask.sum() == 0:
        raise ValueError("VMFXX row not found in holdings.")

    cash_remaining = 0.0
    if use_purchasing_power_first:
        try:
            cash_remaining = max(0.0, float(purchasing_power or 0.0))
        except Exception:
            cash_remaining = 0.0

    for b in buys:
        t = (b.get("ticker") or "").strip().upper()
        q = b.get("qty", 0.0)
        y = b.get("yield", 0.0)

        if not t:
            continue
        try:
            qf = float(q)
        except Exception:
            qf = 0.0
        if qf <= 0:
            continue

        try:
            yf_ = float(y)
        except Exception:
            yf_ = 0.0

        # Get price once here for cash logic
        px = get_last_price_yf(t)
        if px is None:
            raise ValueError(f"Could not fetch price for {t} from yfinance.")
        buy_mv = px * qf

        # Use Purchasing Power (cash) first
        cash_used = 0.0
        if cash_remaining > 0.0:
            cash_used = min(cash_remaining, buy_mv)
            cash_remaining -= cash_used
            total_pp_used += cash_used

        # Remaining funding needed from VMFXX
        vm_needed = buy_mv - cash_used
        if vm_needed < 0:
            vm_needed = 0.0

        # Apply VMFXX sale + position update
        df, info = apply_sell_vmfxx_buy_new(
            df,
            buy_ticker=t,
            buy_qty=qf,
            buy_yield_pct=yf_,
            vmfxx_sell_max_mv=vm_needed,
            buy_price_override=px,
        )

        sold_vmfxx_mv = float(info["sold_vmfxx_mv"])

        # Anything not covered by Purchasing Power + VMFXX is Shortfall
        shortfall_row = max(0.0, buy_mv - (cash_used + sold_vmfxx_mv))

        details.append({
            "Ticker": t,
            "Qty": qf,
            "Yield %": yf_,
            "Price": float(info["buy_price"]),
            "Buy MV $": float(info["buy_mv"]),
            "Cash Used $": float(cash_used),
            "Sold VMFXX $": float(sold_vmfxx_mv),
            "Shortfall $": float(shortfall_row),
        })

        total_buy_mv += float(info["buy_mv"])
        total_sold_vmfxx += float(sold_vmfxx_mv)
        total_shortfall += float(shortfall_row)

    if not details:
        raise ValueError("No valid buy rows found (need ticker + qty > 0).")

    df["MV_$"] = pd.to_numeric(df["MV_$"], errors="coerce").fillna(0.0)
    total_mv = float(df["MV_$"].sum())

    return df, {
        "total_buy_mv": total_buy_mv,
        "total_sold_vmfxx_mv": total_sold_vmfxx,
        "total_shortfall_mv": total_shortfall,
        "total_pp_used_mv": total_pp_used,
        "holdings_total_mv": total_mv,
        "details_df": pd.DataFrame(details)
    }

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

    front = ["DISPLAY_SYM","SEC_TYPE","WGT_PCT","MV_$","DIV_YLD_PCT","LAST","QTY","COST_SH","COST_TOT","GAIN_$","GAIN_PCT"]
    cols = front + [c for c in out.columns if c not in front]
    cols = [c for c in cols if c in out.columns]
    out = out[cols]

    if "WGT_PCT" in out.columns:
        out["WGT_PCT"] = out["WGT_PCT"].apply(lambda v: fmt_pct4(v))
    if "DIV_YLD_PCT" in out.columns:
        out["DIV_YLD_PCT"] = out["DIV_YLD_PCT"].apply(lambda v: fmt_pct4(v))
    if "GAIN_PCT" in out.columns:
        out["GAIN_PCT"] = out["GAIN_PCT"].apply(lambda v: fmt_pct4(v))

    for c in ["MV_$","LAST","COST_SH","COST_TOT","GAIN_$","DAY_$","DIV_$"]:
        if c in out.columns:
            out[c] = out[c].apply(lambda v: fmt_money(v))
    return out

def pretty_basket_details(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    out["Qty"] = out["Qty"].map(lambda v: f"{float(v):,.4f}")
    out["Yield %"] = out["Yield %"].map(lambda v: fmt_pct4(v))
    out["Price"] = out["Price"].map(lambda v: fmt_money(v))
    for c in ["Buy MV $","Cash Used $","Sold VMFXX $","Shortfall $"]:
        if c in out.columns:
            out[c] = out[c].map(lambda v: fmt_money(v))
    return out

# =========================
# What-if compare renderer (STREAMLIT NATIVE)
# =========================
def render_whatif_summary(payload: dict):
    st.subheader("WHAT-IF SUMMARY (OLD vs NEW)")

    d1, d2, d3, d4, d5 = st.columns(5, gap="medium")
    d1.metric("Buy Rows Used", str(payload.get("buy_rows_used", 0)))
    d2.metric("Total Buy MV $", fmt_money(payload.get("total_buy_mv", 0.0)))
    d3.metric("Purchasing Power Used $", fmt_money(payload.get("pp_used_mv", 0.0)))
    d4.metric("Sold VMFXX $", fmt_money(payload.get("sold_vmfxx_mv", 0.0)))
    d5.metric("Shortfall $", fmt_money(payload.get("shortfall_mv", 0.0)))

    st.markdown(NOTE_HOLD)
    st.markdown(NOTE_ETRADE)
    st.markdown(NOTE_BASKET)
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

        # BIG metric label (matches st.metric visual weight)
        c1.markdown(f"<div class='bb_metric_name'>{name}</div>", unsafe_allow_html=True)

        if kind == "pp":
            c2.metric(" ", fmt_pct4(oldv))
            c3.metric(" ", fmt_pct4(newv))
            c4.metric(" ", fmt_pp(float(newv) - float(oldv)))
        else:
            c2.metric(" ", fmt_money(oldv))
            c3.metric(" ", fmt_money(newv))
            c4.metric(" ", fmt_money_delta(float(newv) - float(oldv)))

# =========================
# State
# =========================
if "hold_df" not in st.session_state:
    st.session_state.hold_df = None
if "last_scenario_df" not in st.session_state:
    st.session_state.last_scenario_df = None
if "last_whatif_payload" not in st.session_state:
    st.session_state.last_whatif_payload = None
if "last_basket_details" not in st.session_state:
    st.session_state.last_basket_details = None

# basket input state
for i in range(N_BUYS):
    if f"buy_ticker_{i}" not in st.session_state:
        st.session_state[f"buy_ticker_{i}"] = ""
    if f"buy_qty_{i}" not in st.session_state:
        st.session_state[f"buy_qty_{i}"] = "0"
    if f"buy_yield_{i}" not in st.session_state:
        st.session_state[f"buy_yield_{i}"] = "0"
    if f"last_yield_ticker_{i}" not in st.session_state:
        st.session_state[f"last_yield_ticker_{i}"] = ""

# purchasing power state
if "pp_cash_str" not in st.session_state:
    st.session_state.pp_cash_str = ""
if "use_pp_first" not in st.session_state:
    st.session_state.use_pp_first = True

def add_qty_row(i: int, delta: float):
    key = f"buy_qty_{i}"
    cur = _to_float(st.session_state.get(key, "0"))
    cur = float(cur) if pd.notna(cur) else 0.0
    st.session_state[key] = f"{cur + float(delta):.0f}"

# =========================
# Upload + calibrate + actions
# =========================
top1, top2, top3 = st.columns([1.3, 1.0, 1.3], gap="large")

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
    st.subheader("PURCHASING POWER (H3)")
    st.text_input(
        "Purchasing Power Cash $ to use before VMFXX (H3)",
        key="pp_cash_str",
        help="Enter your cash / margin purchasing power (e.g., H3). This is used BEFORE selling VMFXX.",
    )
    st.checkbox(
        "Use purchasing power before selling VMFXX",
        key="use_pp_first",
        value=st.session_state.get("use_pp_first", True),
        help="If unchecked, basket will ignore purchasing power and only sell VMFXX.",
    )
    st.subheader("ACTIONS")
    parse_clicked = st.button("PARSE FILE", use_container_width=True)
    clear_clicked = st.button("CLEAR STATE", use_container_width=True)

# =========================
# Basket UI
# =========================
st.subheader("VMFXX → BUY (WHAT-IF) — BASKET (up to 10 rows)")
st.caption(NOTE_BASKET)

# auto-fill yields on ticker change (row-by-row)
for i in range(N_BUYS):
    t = (st.session_state.get(f"buy_ticker_{i}") or "").strip().upper()
    if t and t != st.session_state.get(f"last_yield_ticker_{i}", ""):
        y = get_dividend_yield_stockanalysis(t)
        if y is not None:
            st.session_state[f"buy_yield_{i}"] = f"{y:.4f}"
        st.session_state[f"last_yield_ticker_{i}"] = t

# header
h1, h2, h3c, h4 = st.columns([1.2, 1.2, 1.1, 1.4], gap="small")
h1.markdown("<div class='bb_hdr'>TICKER</div>", unsafe_allow_html=True)
h2.markdown("<div class='bb_hdr'>QTY</div>", unsafe_allow_html=True)
h3c.markdown("<div class='bb_hdr'>YIELD %</div>", unsafe_allow_html=True)
h4.markdown("<div class='bb_hdr'>PRESETS</div>", unsafe_allow_html=True)

for i in range(N_BUYS):
    c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.1, 1.4], gap="small")

    with c1:
        st.text_input(
            f"Buy Ticker #{i+1}",
            key=f"buy_ticker_{i}",
            label_visibility="collapsed",
            help="Auto uppercased; yield auto-fills when ticker changes.",
        )

    with c2:
        st.text_input(
            f"Buy QTY #{i+1}",
            key=f"buy_qty_{i}",
            label_visibility="collapsed",
            help="Type shares (or use presets).",
        )

    with c3:
        st.text_input(
            f"Buy Yield #{i+1}",
            key=f"buy_yield_{i}",
            label_visibility="collapsed",
            help="Auto-filled from StockAnalysis on ticker change. You can override.",
        )

    with c4:
        b1, b2, b3 = st.columns(3, gap="small")
        with b1:
            st.button(f"+25 #{i+1}", use_container_width=True, on_click=add_qty_row, args=(i, 25))
        with b2:
            st.button(f"+50 #{i+1}", use_container_width=True, on_click=add_qty_row, args=(i, 50))
        with b3:
            st.button(f"+100 #{i+1}", use_container_width=True, on_click=add_qty_row, args=(i, 100))

st.caption(NOTE_YIELD)

run_clicked = st.button("RUN WHAT-IF (BASKET)", use_container_width=True)
st.divider()

if clear_clicked:
    st.session_state.hold_df = None
    st.session_state.last_scenario_df = None
    st.session_state.last_whatif_payload = None
    st.session_state.last_basket_details = None
    for i in range(N_BUYS):
        st.session_state[f"buy_ticker_{i}"] = ""
        st.session_state[f"buy_qty_{i}"] = "0"
        st.session_state[f"buy_yield_{i}"] = "0"
        st.session_state[f"last_yield_ticker_{i}"] = ""
    st.session_state.pp_cash_str = ""
    st.session_state.use_pp_first = True
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

def collect_buys():
    buys = []
    for i in range(N_BUYS):
        t = (st.session_state.get(f"buy_ticker_{i}") or "").strip().upper()
        q = _to_float(st.session_state.get(f"buy_qty_{i}", "0"))
        q = float(q) if pd.notna(q) else 0.0
        y = _to_float(st.session_state.get(f"buy_yield_{i}", "0"))
        y = float(y) if pd.notna(y) else 0.0
        if t and q > 0:
            buys.append({"ticker": t, "qty": q, "yield": y})
    return buys

if run_clicked:
    if hold_df is None or hold_df.empty:
        st.error("Parse the file first.")
    else:
        buys = collect_buys()
        if not buys:
            st.error("Enter at least 1 valid buy row (ticker + qty > 0).")
        else:
            try:
                base_div = dividend_dollars_annual(hold_df, overrides=ovr)
                old_hy = holdings_yield_pct(hold_df, overrides=ovr)
                old_ey = etrade_like_yield_pct(hold_df, overrides=ovr)
                old_mv_total = float(pd.to_numeric(hold_df["MV_$"], errors="coerce").fillna(0.0).sum())

                pp_val = _to_float(st.session_state.get("pp_cash_str", "0"))
                pp_val = float(pp_val) if pd.notna(pp_val) else 0.0
                use_pp_first = bool(st.session_state.get("use_pp_first", True))

                scen_df, info = apply_sell_vmfxx_buy_basket(
                    hold_df,
                    buys=buys,
                    purchasing_power=pp_val,
                    use_purchasing_power_first=use_pp_first,
                )
                details_df = info.get("details_df")

                new_div = dividend_dollars_annual(scen_df, overrides=ovr)
                new_hy = holdings_yield_pct(scen_df, overrides=ovr)
                new_ey = etrade_like_yield_pct(scen_df, overrides=ovr)
                new_mv_total = float(info.get("holdings_total_mv", np.nan))

                st.session_state.last_scenario_df = scen_df
                st.session_state.last_basket_details = details_df
                st.session_state.last_whatif_payload = dict(
                    buy_rows_used=len(buys),
                    total_buy_mv=info["total_buy_mv"],
                    sold_vmfxx_mv=info["total_sold_vmfxx_mv"],
                    shortfall_mv=info["total_shortfall_mv"],
                    pp_used_mv=info.get("total_pp_used_mv", 0.0),
                    old_hy=old_hy, new_hy=new_hy,
                    old_ey=old_ey, new_ey=new_ey,
                    old_div=base_div, new_div=new_div,
                    old_mv_total=old_mv_total, new_mv_total=new_mv_total,
                )

                st.success("Basket what-if calculated successfully.")
            except Exception as e:
                st.error(f"What-if error: {e}")

payload = st.session_state.last_whatif_payload
if isinstance(payload, dict):
    render_whatif_summary(payload)

    details_df = st.session_state.last_basket_details
    if isinstance(details_df, pd.DataFrame) and not details_df.empty:
        st.subheader("BASKET DETAILS")
        st.dataframe(pretty_basket_details(details_df), use_container_width=True, hide_index=True)

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

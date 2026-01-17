# app.py / Report Pro.py
# E*TRADE Asset Allocation Analyzer + 1-Page PDF Report
# - Robust PortfolioDownload.csv parser (cell-by-cell)
# - Allocation % by: Asset Class, Sector, Industry
# - yfinance metadata per ticker
# - NEW: richer client descriptions: What it is + How it makes money + Key risks
# - PDF-safe text sanitization (prevents FPDFUnicodeEncodingException)

import io
import re
import csv
import hashlib
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from fpdf import FPDF

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


# -----------------------------
# PDF text sanitizer
# -----------------------------
_PDF_CHAR_MAP = {
    "\u2013": "-", "\u2014": "-", "\u2212": "-",
    "\u2026": "...",
    "\u2018": "'", "\u2019": "'",
    "\u201C": '"', "\u201D": '"',
    "\u00A0": " ",
    "\u2022": "-",
    "\u2122": "TM",
    "\u00AE": "(R)",
    "\u00A9": "(C)",
}

def pdf_safe(x: Any) -> str:
    if x is None:
        s = ""
    else:
        s = str(x)
    for k, v in _PDF_CHAR_MAP.items():
        s = s.replace(k, v)
    try:
        s = s.encode("latin-1", errors="replace").decode("latin-1")
    except Exception:
        s = "".join(ch if ord(ch) < 256 else "?" for ch in s)
    return s


# -----------------------------
# Helpers
# -----------------------------
def _safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip()
    if s == "" or s == "--":
        return None
    s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return None


def _to_num_series(s: pd.Series) -> pd.Series:
    return s.astype(str).replace({"": None, "--": None}).apply(_safe_float)


def _shorten(s: str, max_len: int) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3].rstrip() + "..."


def _pct_from_decimal_or_pct(x: Any) -> Optional[float]:
    v = _safe_float(x)
    if v is None:
        return None
    return v * 100.0 if v <= 1 else v


def _fmt_money(x: Any) -> str:
    v = _safe_float(x)
    return "" if v is None else f"${v:,.2f}"


def _fmt_pct(x: Any, digits: int = 2) -> str:
    v = _safe_float(x)
    return "" if v is None else f"{v:.{digits}f}%"


# -----------------------------
# CSV loader (cell-by-cell robust)
# -----------------------------
def _find_holdings_header_row(rows: List[List[str]]) -> Tuple[int, List[str]]:
    for i, r in enumerate(rows):
        if not r:
            continue
        first = (r[0] or "").strip()
        if first == "Symbol" and ("% of Portfolio" in r) and ("Value $" in r):
            return i, [c.strip() for c in r]
    raise ValueError("Could not find holdings header row (Symbol + % of Portfolio + Value $).")


def _extract_account_last4(text_lines: List[str], header_idx_line_guess: int) -> Optional[str]:
    for i in range(0, min(len(text_lines), max(0, header_idx_line_guess + 1))):
        line = text_lines[i]
        if "For Account" in line:
            m = re.search(r"(\d{4})\D*$", line.strip())
            if m:
                return m.group(1)
    for i in range(0, min(len(text_lines), 40)):
        if " -0" in text_lines[i]:
            m = re.search(r"-0(\d{3,4})", text_lines[i])
            if m:
                return m.group(1)[-4:]
    return None


def _extract_generated_at(text_lines: List[str]) -> Optional[str]:
    for line in text_lines:
        if line.startswith("Generated at"):
            return line.replace("Generated at", "").strip()
    return None


def load_etrade_portfolio_csv(uploaded_file):
    content_bytes = uploaded_file.getvalue()
    text = content_bytes.decode("utf-8", errors="ignore")
    text_lines = text.splitlines()

    rows: List[List[str]] = list(csv.reader(io.StringIO(text)))
    header_idx, header = _find_holdings_header_row(rows)
    n = len(header)

    account_last4 = _extract_account_last4(text_lines, header_idx_line_guess=header_idx)
    generated_at = _extract_generated_at(text_lines) or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data_rows: List[List[str]] = []
    for r in rows[header_idx + 1 :]:
        if not r:
            continue
        first = (r[0] or "").strip().upper()
        if first == "TOTAL":
            break
        if (r[0] or "").startswith("Generated at"):
            break
        if (r[0] or "").strip() == "":
            continue

        if len(r) < n:
            r = r + [""] * (n - len(r))
        elif len(r) > n:
            extra = r[n:]
            if any(str(x).strip() for x in extra):
                r = r[: n - 1] + [",".join(r[n - 1 :])]
            else:
                r = r[:n]

        data_rows.append([c.strip() if isinstance(c, str) else c for c in r])

    df = pd.DataFrame(data_rows, columns=header)

    rename_map = {
        "Symbol": "Ticker",
        "% of Portfolio": "PctOfPortfolio",
        "Last Price $": "LastPrice",
        "Cost/Share": "CostPerShare",
        "Qty #": "Qty",
        "Total Cost": "TotalCost",
        "Total Gain $": "TotalGain",
        "Value $": "Value",
        "Total Gain %": "TotalGainPct",
        "Day's Gain $": "DaysGain",
        "Day's Gain %": "DaysGainPct",
        "Dividend Yield %": "DividendYield",
        "Dividend Pay Date": "DividendPayDate",
        "Dividend": "Dividend",
        "Date Acquired": "DateAcquired",
    }
    for k, v in rename_map.items():
        if k in df.columns:
            df.rename(columns={k: v}, inplace=True)

    if "Ticker" not in df.columns or "Value" not in df.columns:
        raise ValueError("Holdings table missing required columns (Ticker/Symbol or Value $).")

    df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    df = df[df["Ticker"] != ""].copy()

    for c in ["PctOfPortfolio", "LastPrice", "CostPerShare", "Qty", "TotalCost", "TotalGain", "Value", "DividendYield"]:
        if c in df.columns:
            df[c] = _to_num_series(df[c])

    try:
        dt = pd.to_datetime(generated_at, errors="coerce")
        report_month_label = dt.strftime("%b %y") if pd.notna(dt) else datetime.now().strftime("%b %y")
    except Exception:
        report_month_label = datetime.now().strftime("%b %y")

    return df, account_last4, generated_at, report_month_label


# -----------------------------
# yfinance metadata + classification + richer descriptions
# -----------------------------
def _ensure_yfinance() -> bool:
    if yf is None:
        st.warning("yfinance is not installed. Install: pip install yfinance")
        return False
    return True


@lru_cache(maxsize=None)
def lookup_yf_info(ticker: str) -> Dict[str, Any]:
    if not _ensure_yfinance():
        return {}
    if not isinstance(ticker, str) or not ticker.strip():
        return {}
    base = ticker.strip().upper()
    try:
        return yf.Ticker(base).info or {}
    except Exception:
        return {}


def classify_asset_class(
    ticker: str,
    quote_type: str,
    name: str,
    category: str,
    fund_family: str,
    sector: str,
    industry: str,
) -> str:
    t = (ticker or "").upper().strip()
    qt = (quote_type or "").upper().strip()
    nm = (name or "").upper()
    cat = (category or "").upper()

    if t == "CASH":
        return "Cash"

    if t.endswith("XX") or "MONEY MARKET" in nm or "MMKT" in nm or "MONEY MARKET" in cat:
        return "Cash & Cash Equivalents"

    if "GOLD" in nm or "SILVER" in nm or "PRECIOUS" in cat or "COMMODIT" in cat:
        return "Commodities"

    fi_kw = [
        "BOND", "TREASURY", "T-BILL", "ULTRA SHORT", "ULTRASHORT", "SHORT TERM", "SHORT-TERM",
        "FLOATING", "LOAN", "CREDIT", "MUNICIPAL", "MUNI", "AGGREGATE", "INCOME", "DURATION",
    ]
    if any(k in nm for k in fi_kw) or any(k in cat for k in fi_kw):
        return "Fixed Income"

    if qt == "EQUITY":
        return "Equity"
    if sector or industry:
        return "Equity"

    if qt in {"ETF", "MUTUALFUND"}:
        if any(k in cat for k in fi_kw):
            return "Fixed Income"
        if "COMMODIT" in cat or "PRECIOUS" in cat:
            return "Commodities"
        if "EQUITY" in cat:
            return "Equity"
        return "Fund / Other"

    return "Other"


def _money_engine_text(asset_class: str, quote_type: str, category: str, sector: str, industry: str, name: str, ticker: str) -> str:
    ac = (asset_class or "").lower()
    qt = (quote_type or "").lower()
    cat = (category or "").lower()
    nm = (name or "").lower()

    if ticker.upper() == "CASH":
        return "Acts as cash on hand; it does not earn much unless the broker pays interest."

    if "commod" in ac or "gold" in nm or "silver" in nm or "precious" in cat:
        return "Tracks commodity prices. Returns come from price moves (and sometimes futures roll yield); typically no operating cash flow."

    if "fixed income" in ac or "bond" in cat or "treasury" in cat:
        return "Earns interest (coupon income) from bonds/loans held in the fund; price also moves with rates and credit spreads."

    if "cash & cash" in ac or "money market" in nm:
        return "Earns short-term interest from very short maturity instruments; designed for stability/liquidity."

    if qt in {"etf", "mutualfund"}:
        # Equity ETF default
        if "equity" in cat or (sector or industry):
            return "Owns a basket of stocks. Returns come from underlying companies' earnings growth and dividends (minus fees)."
        return "Owns a diversified basket of assets. Returns come from the underlying holdings' income and price changes (minus fees)."

    # Single stocks
    if "equity" in ac or qt == "equity":
        # Slightly tailored based on sector
        s = (sector or "").lower()
        if "financial" in s:
            return "Makes money via lending/spreads, fees, and investment income; stock returns come from profits and valuation changes."
        if "technology" in s:
            return "Makes money by selling software/hardware/services; returns come from revenue growth, margins, and valuation changes."
        if "health" in s:
            return "Makes money via drugs/devices/services; returns come from product demand, pricing, and innovation pipeline outcomes."
        if "consumer" in s:
            return "Makes money by selling goods/services to consumers; returns depend on demand, pricing power, and margins."
        if "energy" in s:
            return "Makes money from producing/transporting energy; returns depend heavily on commodity prices and costs."
        if "industrials" in s:
            return "Makes money by manufacturing/building/services; returns depend on economic cycle, orders, and operating efficiency."
        if "utilities" in s:
            return "Makes money from regulated services; returns often driven by dividends, rates, and regulatory environment."
        if "real estate" in s:
            return "Makes money from rents/leases and property values; returns depend on occupancy, cap rates, and financing costs."
        return "Makes money from selling products/services. Stock returns come from earnings, dividends, and changes in market valuation."

    return "Returns depend on the asset's income (if any) and market price changes."


def _risk_text(asset_class: str, quote_type: str, category: str, sector: str, industry: str, name: str, ticker: str) -> str:
    ac = (asset_class or "").lower()
    qt = (quote_type or "").lower()
    cat = (category or "").lower()
    nm = (name or "").lower()

    if ticker.upper() == "CASH":
        return "Low market risk; inflation risk and potential opportunity cost."

    if "commod" in ac or "gold" in nm or "silver" in nm or "precious" in cat:
        return "High price volatility; no cash-flow support; can be sensitive to USD and real rates."

    if "fixed income" in ac or "bond" in cat or "treasury" in cat:
        return "Interest-rate risk; credit risk (if not Treasuries); liquidity risk in stressed markets."

    if "cash & cash" in ac or "money market" in nm:
        return "Low risk; yield moves with short-term rates; small chance of liquidity stress in extreme events."

    if qt in {"etf", "mutualfund"}:
        if "equity" in cat or (sector or industry):
            return "Equity market risk; sector/style concentration if specialized; fee drag."
        return "Underlying asset risks plus fund structure risks (tracking error/fees)."

    if "equity" in ac or qt == "equity":
        return "Business/earnings risk; valuation risk; broader market drawdowns."

    return "Risk depends on underlying holdings and market conditions."


def build_description(meta: Dict[str, Any], asset_class: str, ticker: str) -> str:
    qt = (meta.get("quoteType") or "").strip()
    name = (meta.get("shortName") or meta.get("longName") or ticker).strip()
    sector = (meta.get("sector") or "").strip()
    industry = (meta.get("industry") or "").strip()
    category = (meta.get("category") or "").strip()
    fund_family = (meta.get("fundFamily") or "").strip()

    exp = meta.get("annualReportExpenseRatio")
    if exp is None:
        exp = meta.get("expenseRatio")
    exp_pct = _pct_from_decimal_or_pct(exp)

    yld = meta.get("yield")
    if yld is None:
        yld = meta.get("trailingAnnualDividendYield")
    yld_pct = _pct_from_decimal_or_pct(yld)

    # What it is (client friendly)
    if ticker.upper() == "CASH":
        what = "Cash position"
    elif (qt or "").lower() in {"etf", "mutualfund"}:
        what = "Fund (ETF/Mutual Fund)"
    elif (qt or "").lower() == "equity":
        what = "Single stock"
    else:
        what = "Holding"

    exposure = ""
    if category:
        exposure = category
    elif sector and industry:
        exposure = f"{sector} / {industry}"
    elif sector:
        exposure = sector
    elif fund_family:
        exposure = fund_family

    how = _money_engine_text(asset_class, qt, category, sector, industry, name, ticker)
    risk = _risk_text(asset_class, qt, category, sector, industry, name, ticker)

    stats = []
    if exp_pct is not None and exp_pct >= 0:
        stats.append(f"Fee {exp_pct:.2f}%")
    if yld_pct is not None and yld_pct >= 0:
        stats.append(f"Yield {yld_pct:.2f}%")
    stats_txt = (" | " + ", ".join(stats)) if stats else ""

    title = f"{name} ({ticker})"
    line = f"{title}: {what}. Focus: {asset_class}"
    if exposure:
        line += f" - {exposure}"
    line += f". How it makes money: {how} Key risks: {risk}{stats_txt}"

    return _shorten(line.strip(), 340)


def enrich_holdings(df: pd.DataFrame, meta_mode: str, meta_top_n: int) -> pd.DataFrame:
    df = df.copy()
    df["Value"] = df["Value"].fillna(0.0)

    total_value = float(df["Value"].sum())
    df["WeightPct"] = (df["Value"] / total_value * 100.0) if total_value > 0 else 0.0

    tickers = df["Ticker"].astype(str).str.upper().tolist()
    unique = list(dict.fromkeys([t for t in tickers if t]))

    fetch_set: set = set()
    if meta_mode == "All":
        fetch_set = set(unique)
    elif meta_mode == "Top N by Value":
        top = df.sort_values("Value", ascending=False).head(int(meta_top_n))
        fetch_set = set(top["Ticker"].astype(str).str.upper().tolist())
    elif meta_mode == "None":
        fetch_set = set()

    metas: Dict[str, Dict[str, Any]] = {}
    if fetch_set and _ensure_yfinance():
        for t in fetch_set:
            metas[t] = lookup_yf_info(t)

    def meta_get(t: str, k: str) -> str:
        m = metas.get(t, {}) if metas else {}
        v = m.get(k)
        return (str(v).strip() if v is not None else "")

    df["QuoteType"] = df["Ticker"].map(lambda t: meta_get(t, "quoteType"))
    df["Name"] = df["Ticker"].map(lambda t: _shorten(meta_get(t, "shortName") or meta_get(t, "longName") or t, 28))
    df["Sector"] = df["Ticker"].map(lambda t: meta_get(t, "sector"))
    df["Industry"] = df["Ticker"].map(lambda t: meta_get(t, "industry"))
    df["Category"] = df["Ticker"].map(lambda t: meta_get(t, "category"))
    df["FundFamily"] = df["Ticker"].map(lambda t: meta_get(t, "fundFamily"))

    def _expense_ratio_pct(t: str) -> Optional[float]:
        m = metas.get(t, {}) if metas else {}
        v = m.get("annualReportExpenseRatio")
        if v is None:
            v = m.get("expenseRatio")
        return _pct_from_decimal_or_pct(v)

    def _trailing_yield_pct(t: str) -> Optional[float]:
        m = metas.get(t, {}) if metas else {}
        v = m.get("yield")
        if v is None:
            v = m.get("trailingAnnualDividendYield")
        return _pct_from_decimal_or_pct(v)

    df["ExpenseRatio"] = df["Ticker"].map(_expense_ratio_pct)
    df["TrailingYield"] = df["Ticker"].map(_trailing_yield_pct)

    df["AssetClass"] = df.apply(
        lambda r: classify_asset_class(
            ticker=r.get("Ticker", ""),
            quote_type=r.get("QuoteType", ""),
            name=r.get("Name", ""),
            category=r.get("Category", ""),
            fund_family=r.get("FundFamily", ""),
            sector=r.get("Sector", ""),
            industry=r.get("Industry", ""),
        ),
        axis=1,
    )

    def _desc(t: str) -> str:
        if t == "CASH":
            return "Cash position. How it makes money: typically none (or broker interest). Key risks: inflation/opportunity cost."
        if t in metas:
            ac = str(df.loc[df["Ticker"] == t, "AssetClass"].iloc[0]) if (df["Ticker"] == t).any() else "Other"
            return build_description(metas.get(t, {}), ac, t)
        return _shorten(f"{t}: Holding (metadata not fetched).", 340)

    df["Description"] = df["Ticker"].map(_desc)

    df.loc[df["Ticker"] == "CASH", ["Name", "QuoteType", "AssetClass", "Sector", "Industry", "Category"]] = [
        "Cash", "CASH", "Cash", "", "", ""
    ]

    return df


def allocation_tables(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    def agg(group_col: str) -> pd.DataFrame:
        t = (
            df.groupby(group_col, dropna=False, as_index=False)
            .agg(Value=("Value", "sum"), WeightPct=("WeightPct", "sum"))
            .sort_values("WeightPct", ascending=False)
        )
        t[group_col] = t[group_col].replace({None: "", "": "(Unclassified)"})
        t["WeightPct"] = t["WeightPct"].round(4)
        return t

    return {"AssetClass": agg("AssetClass"), "Sector": agg("Sector"), "Industry": agg("Industry")}


# -----------------------------
# Layout + PDF helpers
# -----------------------------
def _safe_align(a: str) -> str:
    a = (a or "").upper().strip()
    return a if a in {"L", "C", "R"} else "L"


def _fit_widths_to_page(pdf: FPDF, widths: List[float], min_w: float = 6.0) -> List[float]:
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    widths = [float(w) for w in widths]
    s = sum(widths) if widths else 0.0
    if s <= 0:
        n = max(1, len(widths))
        return [usable / n] * n
    scale = usable / s
    scaled = [max(min_w, w * scale) for w in widths]
    s2 = sum(scaled)
    if s2 > usable and len(scaled) > 0:
        drift = s2 - usable
        scaled[-1] = max(min_w, scaled[-1] - drift)
    return scaled


def add_key_value(pdf: FPDF, label: str, value: str, body_font: int):
    pdf.set_font("Times", "", body_font)
    usable = pdf.w - pdf.l_margin - pdf.r_margin

    label_text = pdf_safe(f"{label} ")
    value_text = pdf_safe(str(value))

    label_w = pdf.get_string_width(label_text)
    value_w = pdf.get_string_width(value_text)
    dot_w = pdf.get_string_width(".") or 0.5

    dots_w = usable - label_w - value_w
    n_dots = 3 if dots_w < dot_w * 3 else int(dots_w / dot_w)
    dots = "." * max(3, n_dots)

    line = pdf_safe(f"{label_text}{dots} {value_text}")
    pdf.set_x(pdf.l_margin)
    pdf.cell(usable, 5, line, 0, 1, "L")


def add_table_header(pdf: FPDF, cols: List[str], widths: List[float], header_font: int):
    pdf.set_font("Times", "B", header_font)
    for col, w in zip(cols, widths):
        pdf.cell(w, 6, pdf_safe(col), border="B", align="L")
    pdf.ln(6)


def add_table_row(pdf: FPDF, vals: List[str], widths: List[float], aligns: List[str], body_font: int, row_h: float = 5.0):
    pdf.set_font("Times", "", body_font)
    aligns = [_safe_align(a) for a in (aligns or ["L"] * len(vals))]
    for val, w, a in zip(vals, widths, aligns):
        pdf.cell(w, row_h, pdf_safe(val), border=0, align=a)
    pdf.ln(row_h)


class AllocationPDF(FPDF):
    def header(self):
        pass


def build_pdf(report: dict, layout: Dict[str, Any]) -> bytes:
    pdf = AllocationPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    title_font = int(layout.get("title_font", 14))
    sub_font = int(layout.get("sub_font", 8))
    section_font = int(layout.get("section_font", 12))
    header_font = int(layout.get("header_font", 10))
    body_font = int(layout.get("body_font", 10))
    row_h = float(layout.get("row_height", 5.0))
    section_gap = float(layout.get("section_gap", 2.0))

    pdf.set_font("Times", "B", title_font)
    pdf.cell(0, 8, pdf_safe("E*TRADE Asset Allocation Report"), ln=1, align="C")
    pdf.set_font("Times", "", sub_font)
    pdf.cell(0, 4, pdf_safe(report.get("header_line", "")), ln=1, align="C")
    pdf.ln(3)

    totals = report["totals"]
    alloc_asset = report["alloc_asset"]
    alloc_sector = report["alloc_sector"]
    alloc_industry = report["alloc_industry"]
    holdings = report["holdings"]
    holdings_full = report["holdings_full"]

    order = layout.get("section_order") or [
        "Summary",
        "Allocation by Asset Class",
        "Allocation by Sector",
        "Allocation by Industry",
        "Top Holdings",
        "Holding Descriptions (Top N)",
    ]

    for idx, sec in enumerate(order, start=1):
        pdf.set_font("Times", "B", section_font)
        pdf.cell(0, 7, pdf_safe(f"{idx}. {sec}"), ln=1)
        pdf.ln(1)

        if sec == "Summary":
            add_key_value(pdf, "Total Portfolio Value", _fmt_money(totals.get("TotalValue")), body_font)
            add_key_value(pdf, "Holdings Count", str(int(totals.get("HoldingsCount", 0))), body_font)
            add_key_value(pdf, "Largest Holding", totals.get("LargestHolding", ""), body_font)
            add_key_value(pdf, "Largest Holding Weight", _fmt_pct(totals.get("LargestHoldingWeight"), 2), body_font)
            pdf.ln(section_gap)
            continue

        if sec == "Allocation by Asset Class":
            cols = ["Asset Class", "Value", "% Weight"]
            widths = _fit_widths_to_page(pdf, layout.get("tables", {}).get("asset", {}).get("widths", [70, 40, 30]))
            aligns = layout.get("tables", {}).get("asset", {}).get("aligns", ["L", "R", "R"])
            add_table_header(pdf, cols, widths, header_font)
            for _, row in alloc_asset.iterrows():
                vals = [str(row["AssetClass"])[:35], _fmt_money(row["Value"]), _fmt_pct(row["WeightPct"], 2)]
                add_table_row(pdf, vals, widths, aligns, body_font, row_h=row_h)
            pdf.ln(section_gap)
            continue

        if sec == "Allocation by Sector":
            cols = ["Sector", "Value", "% Weight"]
            widths = _fit_widths_to_page(pdf, layout.get("tables", {}).get("sector", {}).get("widths", [70, 40, 30]))
            aligns = layout.get("tables", {}).get("sector", {}).get("aligns", ["L", "R", "R"])
            add_table_header(pdf, cols, widths, header_font)
            for _, row in alloc_sector.iterrows():
                sector = row["Sector"] if str(row["Sector"]).strip() else "(Unclassified)"
                vals = [_shorten(str(sector), 35), _fmt_money(row["Value"]), _fmt_pct(row["WeightPct"], 2)]
                add_table_row(pdf, vals, widths, aligns, body_font, row_h=row_h)
            pdf.ln(section_gap)
            continue

        if sec == "Allocation by Industry":
            cols = ["Industry", "Value", "% Weight"]
            widths = _fit_widths_to_page(pdf, layout.get("tables", {}).get("industry", {}).get("widths", [70, 40, 30]))
            aligns = layout.get("tables", {}).get("industry", {}).get("aligns", ["L", "R", "R"])
            add_table_header(pdf, cols, widths, header_font)
            for _, row in alloc_industry.iterrows():
                ind = row["Industry"] if str(row["Industry"]).strip() else "(Unclassified)"
                vals = [_shorten(str(ind), 35), _fmt_money(row["Value"]), _fmt_pct(row["WeightPct"], 2)]
                add_table_row(pdf, vals, widths, aligns, body_font, row_h=row_h)
            pdf.ln(section_gap)
            continue

        if sec == "Top Holdings":
            cols = ["Ticker / Name", "Asset", "% Wt", "Value"]
            widths = _fit_widths_to_page(pdf, layout.get("tables", {}).get("holdings", {}).get("widths", [70, 20, 20, 30]))
            aligns = layout.get("tables", {}).get("holdings", {}).get("aligns", ["L", "L", "R", "R"])
            add_table_header(pdf, cols, widths, header_font)
            for _, row in holdings.iterrows():
                label = f"{row['Ticker']}  {row['Name']}".strip()
                vals = [_shorten(label, 45), _shorten(str(row["AssetClass"]), 12), _fmt_pct(row["WeightPct"], 2), _fmt_money(row["Value"])]
                add_table_row(pdf, vals, widths, aligns, body_font, row_h=row_h)
            pdf.ln(section_gap)
            continue

        if sec == "Holding Descriptions (Top N)":
            pdf.set_font("Times", "", body_font)
            top_desc = holdings_full.sort_values("Value", ascending=False).head(12)
            for _, r in top_desc.iterrows():
                # Multi-line wrap using multi_cell
                txt = pdf_safe(r.get("Description", ""))
                pdf.multi_cell(0, 5, txt)
                pdf.ln(1)
            pdf.ln(section_gap)
            continue

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1", errors="replace")
    return bytes(out)


@st.cache_data(show_spinner=False)
def render_pdf_page1_png(pdf_bytes: bytes, zoom: float = 1.5) -> bytes:
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) not installed.")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(0)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    png = pix.tobytes("png")
    doc.close()
    return png


def _md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def _default_layout() -> Dict[str, Any]:
    return {
        "title_font": 14,
        "sub_font": 8,
        "section_font": 12,
        "header_font": 10,
        "body_font": 10,
        "row_height": 5.0,
        "section_gap": 2.0,
        "section_order": [
            "Summary",
            "Allocation by Asset Class",
            "Allocation by Sector",
            "Allocation by Industry",
            "Top Holdings",
            "Holding Descriptions (Top N)",
        ],
        "tables": {
            "asset": {"widths": [70, 40, 30], "aligns": ["L", "R", "R"]},
            "sector": {"widths": [70, 40, 30], "aligns": ["L", "R", "R"]},
            "industry": {"widths": [70, 40, 30], "aligns": ["L", "R", "R"]},
            "holdings": {"widths": [70, 20, 20, 30], "aligns": ["L", "L", "R", "R"]},
        },
    }


def compute_report(df_raw: pd.DataFrame, meta_mode: str, meta_top_n: int, holdings_top_n: int) -> dict:
    df = enrich_holdings(df_raw, meta_mode=meta_mode, meta_top_n=int(meta_top_n))

    total_value = float(df["Value"].fillna(0).sum())
    holdings_count = int(df.shape[0])

    if holdings_count > 0:
        top = df.sort_values("Value", ascending=False).head(1).iloc[0]
        largest_holding = f"{top['Ticker']} {top['Name']}"
        largest_wt = float(top["WeightPct"]) if pd.notna(top["WeightPct"]) else 0.0
    else:
        largest_holding = ""
        largest_wt = 0.0

    tables = allocation_tables(df)
    holdings_pdf = df.sort_values("Value", ascending=False).head(int(holdings_top_n)).copy()

    totals = {
        "TotalValue": total_value,
        "HoldingsCount": holdings_count,
        "LargestHolding": largest_holding,
        "LargestHoldingWeight": largest_wt,
    }

    return {
        "totals": totals,
        "alloc_asset": tables["AssetClass"].rename(columns={"AssetClass": "AssetClass"}),
        "alloc_sector": tables["Sector"].rename(columns={"Sector": "Sector"}),
        "alloc_industry": tables["Industry"].rename(columns={"Industry": "Industry"}),
        "holdings": holdings_pdf,
        "holdings_full": df,
    }


def main():
    st.set_page_config(page_title="E*TRADE Asset Allocation Report Generator", layout="wide")

    st.title("E*TRADE Asset Allocation Report Generator")
    st.caption("Upload PortfolioDownload.csv -> allocation + richer descriptions -> 1-page PDF.")

    if "layout" not in st.session_state:
        st.session_state.layout = _default_layout()

    with st.sidebar:
        st.header("Layout Controls (PDF)")
        if st.button("Reset layout to defaults"):
            st.session_state.layout = _default_layout()

        lay = st.session_state.layout
        st.subheader("Section Order")
        lay["section_order"] = st.multiselect(
            "Order (top -> bottom)",
            options=[
                "Summary",
                "Allocation by Asset Class",
                "Allocation by Sector",
                "Allocation by Industry",
                "Top Holdings",
                "Holding Descriptions (Top N)",
            ],
            default=lay.get("section_order", _default_layout()["section_order"]),
        )

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        meta_mode = st.selectbox("Metadata fetch", ["Top N by Value", "All", "None"], index=0)
    with c2:
        meta_top_n = st.number_input("Top N (for metadata)", min_value=5, max_value=300, value=60, step=5)
    with c3:
        holdings_top_n = st.number_input("Top holdings shown in PDF", min_value=10, max_value=200, value=30, step=5)

    uploaded_file = st.file_uploader("Upload E*TRADE PortfolioDownload.csv", type=["csv"])
    if not uploaded_file:
        return

    try:
        df_raw, account_last4, generated_at, report_month_label = load_etrade_portfolio_csv(uploaded_file)
    except Exception as e:
        st.error(f"Could not parse CSV: {e}")
        return

    report_calc = compute_report(
        df_raw=df_raw,
        meta_mode=meta_mode,
        meta_top_n=int(meta_top_n),
        holdings_top_n=int(holdings_top_n),
    )

    acct = account_last4 or "XXXX"
    header_line = f"Account {acct} | Generated {generated_at}"

    report_for_pdf = {"header_line": header_line, **report_calc}

    # UI Tables
    st.subheader("Holdings (with descriptions)")
    df_full = report_calc["holdings_full"].copy()
    show_cols = ["Ticker","Name","AssetClass","Sector","Industry","Category","Value","WeightPct","DividendYield","TrailingYield","ExpenseRatio","Description"]
    existing = [c for c in show_cols if c in df_full.columns]
    df_show = df_full[existing].copy()
    if "Value" in df_show.columns:
        df_show["Value"] = df_show["Value"].map(_fmt_money)
    if "WeightPct" in df_show.columns:
        df_show["WeightPct"] = df_show["WeightPct"].map(lambda x: _fmt_pct(x, 2))
    if "DividendYield" in df_show.columns:
        df_show["DividendYield"] = df_show["DividendYield"].map(lambda x: _fmt_pct(x, 2))
    if "TrailingYield" in df_show.columns:
        df_show["TrailingYield"] = df_show["TrailingYield"].map(lambda x: _fmt_pct(x, 2))
    if "ExpenseRatio" in df_show.columns:
        df_show["ExpenseRatio"] = df_show["ExpenseRatio"].map(lambda x: _fmt_pct(x, 2))
    st.dataframe(df_show, use_container_width=True)

    st.markdown("---")

    pdf_bytes = build_pdf(report_for_pdf, st.session_state.layout)

    st.subheader("PDF Preview (Page 1)")
    if fitz is None:
        st.info("PDF preview requires PyMuPDF. Install: `pip install pymupdf`")
    else:
        try:
            png_bytes = render_pdf_page1_png(pdf_bytes, zoom=1.6)
            st.image(png_bytes, caption="Preview", use_container_width=True)
        except Exception as e:
            st.warning(f"Could not render PDF preview: {e}")

    file_name = f"{acct} Allocation Report {report_month_label}.pdf"
    st.download_button(
        label="Download PDF Asset Allocation Report",
        data=pdf_bytes,
        file_name=file_name,
        mime="application/pdf",
    )


if __name__ == "__main__":
    main()

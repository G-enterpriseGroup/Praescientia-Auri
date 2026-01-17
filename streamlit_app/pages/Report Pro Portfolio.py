# app.py / Report Pro.py
# E*TRADE Asset Allocation Analyzer + 1-Page PDF Report
# - Parses E*TRADE PortfolioDownload.csv (holdings export) robustly (cell-by-cell)
# - Fixes malformed rows (e.g., CASH line has extra trailing comma -> 16 fields)
# - Calculates allocation % by: Asset Class, Sector, Industry
# - Pulls metadata via yfinance: quoteType, name, sector, industry, category, fundFamily, yields/expense ratio (when available)
# - Generates concise client-friendly descriptions per holding
# - PDF filename: "<last4> Allocation Report <Mon YY>.pdf"
# - PDF body font 10, headers 12
# - Summary lines use dotted leaders: "Label .... Value"
# + OPTION A: PDF preview + robust layout controls (column widths, alignments, font sizes, section order)

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

# Optional: PDF preview renderer (recommended)
# pip install pymupdf
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


# -----------------------------
# Helpers: Safe parsing / formatting
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
    return (
        s.astype(str)
        .replace({"": None, "--": None})
        .apply(_safe_float)
    )


def _shorten(s: str, max_len: int) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"


def _pct_from_decimal_or_pct(x: Any) -> Optional[float]:
    v = _safe_float(x)
    if v is None:
        return None
    if v <= 1:
        return v * 100.0
    return v


def _fmt_money(x: Any) -> str:
    v = _safe_float(x)
    if v is None:
        return ""
    return f"${v:,.2f}"


def _fmt_pct(x: Any, digits: int = 2) -> str:
    v = _safe_float(x)
    if v is None:
        return ""
    return f"{v:.{digits}f}%"


# -----------------------------
# E*TRADE PortfolioDownload.csv loader (cell-by-cell, robust)
# -----------------------------
def _find_holdings_header_row(rows: List[List[str]]) -> Tuple[int, List[str]]:
    """
    Find holdings table header row. We expect something like:
      Symbol,% of Portfolio,Last Price $,Cost/Share,Qty #,Total Cost,Total Gain $,Value $,...
    """
    for i, r in enumerate(rows):
        if not r:
            continue
        first = (r[0] or "").strip()
        if first == "Symbol" and ("% of Portfolio" in r) and ("Value $" in r):
            header = [c.strip() for c in r]
            return i, header
    raise ValueError("Could not find holdings header row (Symbol + % of Portfolio + Value $).")


def _extract_account_last4(text_lines: List[str], header_idx_line_guess: int) -> Optional[str]:
    # Search the top part of file for "For Account" or account line
    for i in range(0, min(len(text_lines), max(0, header_idx_line_guess + 1))):
        line = text_lines[i]
        if "For Account" in line:
            m = re.search(r"(\d{4})\D*$", line.strip())
            if m:
                return m.group(1)
    # Fallback: sometimes account appears as "Name -0057"
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
    """
    Reads E*TRADE PortfolioDownload.csv safely using csv.reader (cell-by-cell).

    Returns:
      df_holdings, account_last4, generated_at_label, report_month_label
    """
    content_bytes = uploaded_file.getvalue()
    text = content_bytes.decode("utf-8", errors="ignore")
    text_lines = text.splitlines()

    # Cell-by-cell parse (this avoids pandas C-engine tokenization crashes)
    rows: List[List[str]] = list(csv.reader(io.StringIO(text)))

    header_idx, header = _find_holdings_header_row(rows)
    n = len(header)

    account_last4 = _extract_account_last4(text_lines, header_idx_line_guess=header_idx)
    generated_at = _extract_generated_at(text_lines) or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Read holdings rows until TOTAL / Generated at
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

        # Normalize row length to header length:
        # - If extra trailing commas => extra empty cells -> truncate
        # - If extra non-empty cells => merge into last column
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

    # Standardize columns
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

    # Clean core fields
    df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    df = df[df["Ticker"] != ""].copy()

    for c in ["PctOfPortfolio", "LastPrice", "CostPerShare", "Qty", "TotalCost", "TotalGain", "Value", "DividendYield"]:
        if c in df.columns:
            df[c] = _to_num_series(df[c])

    # Month label for filename
    try:
        dt = pd.to_datetime(generated_at, errors="coerce")
        report_month_label = dt.strftime("%b %y") if pd.notna(dt) else datetime.now().strftime("%b %y")
    except Exception:
        report_month_label = datetime.now().strftime("%b %y")

    return df, account_last4, generated_at, report_month_label


# -----------------------------
# yfinance metadata + classification + descriptions
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

    # Money market / cash equivalents
    if t.endswith("XX") or "MONEY MARKET" in nm or "MMKT" in nm or "MONEY MARKET" in cat:
        return "Cash & Cash Equivalents"

    # Commodities
    if "GOLD" in nm or "SILVER" in nm or "PRECIOUS" in cat or "COMMODIT" in cat:
        return "Commodities"

    # Fixed income
    fi_kw = [
        "BOND", "TREASURY", "T-BILL", "ULTRA SHORT", "ULTRASHORT", "SHORT TERM", "SHORT-TERM",
        "FLOATING", "LOAN", "CREDIT", "MUNICIPAL", "MUNI", "AGGREGATE", "INCOME", "DURATION",
    ]
    if any(k in nm for k in fi_kw) or any(k in cat for k in fi_kw):
        return "Fixed Income"

    # Equity
    if qt == "EQUITY":
        return "Equity"
    if sector or industry:
        return "Equity"

    # Funds fallback
    if qt in {"ETF", "MUTUALFUND"}:
        if any(k in cat for k in fi_kw):
            return "Fixed Income"
        if "COMMODIT" in cat or "PRECIOUS" in cat:
            return "Commodities"
        if "EQUITY" in cat:
            return "Equity"
        return "Fund / Other"

    return "Other"


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

    exposure = ""
    if category:
        exposure = category
    elif sector and industry:
        exposure = f"{sector} / {industry}"
    elif sector:
        exposure = sector
    elif fund_family:
        exposure = fund_family

    wrapper = qt.title() if qt else "Holding"
    head = f"{name} ({ticker})"
    mid = f"{wrapper} — {asset_class}".strip()

    stats = []
    if exp_pct is not None:
        stats.append(f"Exp {exp_pct:.2f}%")
    if yld_pct is not None:
        stats.append(f"Yield {yld_pct:.2f}%")
    stats_txt = f" | {', '.join(stats)}" if stats else ""

    if exposure:
        s = f"{head}: {mid} focused on {exposure}.{stats_txt}"
    else:
        s = f"{head}: {mid}.{stats_txt}"

    return _shorten(s.strip(), 210)


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
            return "Cash position."
        if t in metas:
            # asset class is on the df row
            ac = str(df.loc[df["Ticker"] == t, "AssetClass"].iloc[0]) if (df["Ticker"] == t).any() else "Other"
            return build_description(metas.get(t, {}), ac, t)
        return _shorten(f"{t}: Holding (metadata not fetched).", 210)

    df["Description"] = df["Ticker"].map(_desc)

    # Ensure CASH line is clean
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

    return {
        "AssetClass": agg("AssetClass"),
        "Sector": agg("Sector"),
        "Industry": agg("Industry"),
    }


# -----------------------------
# Layout + PDF Helpers
# -----------------------------
def _safe_align(a: str) -> str:
    a = (a or "").upper().strip()
    return a if a in {"L", "C", "R"} else "L"


def _clamp_int(x, lo: int, hi: int, default: int) -> int:
    try:
        v = int(x)
    except Exception:
        v = int(default)
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


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
        over = s2 - usable
        adjustable = [i for i, w in enumerate(scaled) if w > min_w]
        if adjustable:
            while over > 1e-6 and adjustable:
                per = over / len(adjustable)
                new_adjustable = []
                for i in adjustable:
                    take = min(per, scaled[i] - min_w)
                    scaled[i] -= take
                    over -= take
                    if scaled[i] > min_w + 1e-6:
                        new_adjustable.append(i)
                adjustable = new_adjustable
        s3 = sum(scaled)
        if s3 > 0:
            drift = s3 - usable
            scaled[-1] = max(min_w, scaled[-1] - drift)

    return scaled


def add_key_value(pdf: FPDF, label: str, value: str, body_font: int):
    pdf.set_font("Times", "", body_font)
    pdf.set_text_color(0, 0, 0)

    usable = pdf.w - pdf.l_margin - pdf.r_margin
    label_text = f"{label} "
    value_text = str(value)

    label_w = pdf.get_string_width(label_text)
    value_w = pdf.get_string_width(value_text)
    dot_w = pdf.get_string_width(".") or 0.5

    dots_w = usable - label_w - value_w
    n_dots = 3 if dots_w < dot_w * 3 else int(dots_w / dot_w)
    dots = "." * max(3, n_dots)
    line = f"{label_text}{dots} {value_text}"

    pdf.set_x(pdf.l_margin)
    pdf.cell(usable, 5, line, 0, 1, "L")


def add_table_header(pdf: FPDF, cols: List[str], widths: List[float], header_font: int):
    pdf.set_font("Times", "B", header_font)
    pdf.set_text_color(0, 0, 0)
    for col, w in zip(cols, widths):
        pdf.cell(w, 6, col, border="B", align="L")
    pdf.ln(6)


def add_table_row(
    pdf: FPDF,
    vals: List[str],
    widths: List[float],
    aligns: List[str],
    body_font: int,
    row_h: float = 5.0,
):
    pdf.set_font("Times", "", body_font)
    pdf.set_text_color(0, 0, 0)
    aligns = [_safe_align(a) for a in (aligns or ["L"] * len(vals))]
    for val, w, a in zip(vals, widths, aligns):
        s = "" if val is None else str(val)
        pdf.cell(w, row_h, s, border=0, align=a)
    pdf.ln(row_h)


# -----------------------------
# PDF Builder (layout-controlled)
# -----------------------------
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
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, "E*TRADE Asset Allocation Report", ln=1, align="C")
    pdf.set_font("Times", "", sub_font)
    pdf.cell(0, 4, report.get("header_line", ""), ln=1, align="C")
    pdf.ln(3)

    totals = report["totals"]
    alloc_asset = report["alloc_asset"]
    alloc_sector = report["alloc_sector"]
    alloc_industry = report["alloc_industry"]
    holdings = report["holdings"]

    order = layout.get("section_order") or [
        "Summary",
        "Allocation by Asset Class",
        "Allocation by Sector",
        "Allocation by Industry",
        "Top Holdings",
    ]

    for idx, sec in enumerate(order, start=1):
        pdf.set_font("Times", "B", section_font)
        pdf.cell(0, 7, f"{idx}. {sec}", ln=1)
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
            default_widths = [70, 40, 30]
            default_aligns = ["L", "R", "R"]
            cfg = layout.get("tables", {}).get("asset", {})
            widths = _fit_widths_to_page(pdf, cfg.get("widths", default_widths))
            aligns = cfg.get("aligns", default_aligns)
            max_rows = int(cfg.get("max_rows", 5000))

            add_table_header(pdf, cols, widths, header_font)
            for r_i, (_, row) in enumerate(alloc_asset.iterrows()):
                if r_i >= max_rows:
                    pdf.set_font("Times", "", body_font)
                    pdf.cell(0, 5, f"... ({len(alloc_asset) - max_rows} more rows not shown)", ln=1)
                    break
                vals = [
                    str(row["AssetClass"])[:35],
                    _fmt_money(row["Value"]),
                    _fmt_pct(row["WeightPct"], 2),
                ]
                add_table_row(pdf, vals, widths, aligns, body_font, row_h=row_h)
            pdf.ln(section_gap)
            continue

        if sec == "Allocation by Sector":
            cols = ["Sector", "Value", "% Weight"]
            default_widths = [70, 40, 30]
            default_aligns = ["L", "R", "R"]
            cfg = layout.get("tables", {}).get("sector", {})
            widths = _fit_widths_to_page(pdf, cfg.get("widths", default_widths))
            aligns = cfg.get("aligns", default_aligns)
            max_rows = int(cfg.get("max_rows", 5000))

            add_table_header(pdf, cols, widths, header_font)
            for r_i, (_, row) in enumerate(alloc_sector.iterrows()):
                if r_i >= max_rows:
                    pdf.set_font("Times", "", body_font)
                    pdf.cell(0, 5, f"... ({len(alloc_sector) - max_rows} more rows not shown)", ln=1)
                    break
                sector = row["Sector"] if str(row["Sector"]).strip() else "(Unclassified)"
                vals = [
                    _shorten(str(sector), 35),
                    _fmt_money(row["Value"]),
                    _fmt_pct(row["WeightPct"], 2),
                ]
                add_table_row(pdf, vals, widths, aligns, body_font, row_h=row_h)
            pdf.ln(section_gap)
            continue

        if sec == "Allocation by Industry":
            cols = ["Industry", "Value", "% Weight"]
            default_widths = [70, 40, 30]
            default_aligns = ["L", "R", "R"]
            cfg = layout.get("tables", {}).get("industry", {})
            widths = _fit_widths_to_page(pdf, cfg.get("widths", default_widths))
            aligns = cfg.get("aligns", default_aligns)
            max_rows = int(cfg.get("max_rows", 5000))

            add_table_header(pdf, cols, widths, header_font)
            for r_i, (_, row) in enumerate(alloc_industry.iterrows()):
                if r_i >= max_rows:
                    pdf.set_font("Times", "", body_font)
                    pdf.cell(0, 5, f"... ({len(alloc_industry) - max_rows} more rows not shown)", ln=1)
                    break
                ind = row["Industry"] if str(row["Industry"]).strip() else "(Unclassified)"
                vals = [
                    _shorten(str(ind), 35),
                    _fmt_money(row["Value"]),
                    _fmt_pct(row["WeightPct"], 2),
                ]
                add_table_row(pdf, vals, widths, aligns, body_font, row_h=row_h)
            pdf.ln(section_gap)
            continue

        if sec == "Top Holdings":
            cols = ["Ticker / Name", "Asset", "% Wt", "Value"]
            default_widths = [70, 20, 20, 30]
            default_aligns = ["L", "L", "R", "R"]
            cfg = layout.get("tables", {}).get("holdings", {})
            widths = _fit_widths_to_page(pdf, cfg.get("widths", default_widths))
            aligns = cfg.get("aligns", default_aligns)
            max_rows = int(cfg.get("max_rows", 25))

            add_table_header(pdf, cols, widths, header_font)
            shown = 0
            for _, row in holdings.iterrows():
                if shown >= max_rows:
                    pdf.set_font("Times", "", body_font)
                    pdf.cell(0, 5, f"... ({len(holdings) - max_rows} more holdings not shown)", ln=1)
                    break
                label = f"{row['Ticker']}  {row['Name']}".strip()
                vals = [
                    _shorten(label, 45),
                    _shorten(str(row["AssetClass"]), 12),
                    _fmt_pct(row["WeightPct"], 2),
                    _fmt_money(row["Value"]),
                ]
                add_table_row(pdf, vals, widths, aligns, body_font, row_h=row_h)
                shown += 1

            pdf.ln(section_gap)
            continue

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)


# -----------------------------
# PDF Preview (Page 1 image)
# -----------------------------
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


# -----------------------------
# Streamlit UI (Bloomberg Orange + layout controls + preview)
# -----------------------------
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
        ],
        "tables": {
            "asset": {"widths": [70, 40, 30], "aligns": ["L", "R", "R"], "max_rows": 5000},
            "sector": {"widths": [70, 40, 30], "aligns": ["L", "R", "R"], "max_rows": 5000},
            "industry": {"widths": [70, 40, 30], "aligns": ["L", "R", "R"], "max_rows": 5000},
            "holdings": {"widths": [70, 20, 20, 30], "aligns": ["L", "L", "R", "R"], "max_rows": 25},
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

    st.markdown(
        """
        <style>
        :root { --primary-color: #ff7f0e; }
        body { background-color: #000000; }
        [data-testid="stAppViewContainer"] { background-color: #000000; color: #f3f3f3; }
        [data-testid="stSidebar"] { background-color: #111111; }
        .stMarkdown, .stDataFrame, .stMetric { color: #f3f3f3; }
        .stMetric label { color: #ffbf69 !important; }
        .stMetric div[data-testid="stMetricValue"] { color: #ffffff !important; }
        .stDownloadButton button, .stButton button {
            background-color: #ff7f0e; color: #000000; border-radius: 4px; border: 1px solid #ffbf69;
        }
        .stDownloadButton button:hover, .stButton button:hover {
            background-color: #ffa64d; color: #000000;
        }
        hr { border-color: #333333; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("E*TRADE Asset Allocation Report Generator")
    st.caption("Upload PortfolioDownload.csv → compute allocation → preview & tweak layout → download 1-page PDF.")

    if "layout" not in st.session_state:
        st.session_state.layout = _default_layout()

    with st.sidebar:
        st.header("Layout Controls (PDF)")

        if st.button("Reset layout to defaults"):
            st.session_state.layout = _default_layout()

        lay = st.session_state.layout

        st.subheader("Fonts & Spacing")
        lay["title_font"] = st.slider("Title font", 10, 20, int(lay.get("title_font", 14)))
        lay["section_font"] = st.slider("Section header font", 10, 16, int(lay.get("section_font", 12)))
        lay["header_font"] = st.slider("Table header font", 8, 14, int(lay.get("header_font", 10)))
        lay["body_font"] = st.slider("Body font", 8, 12, int(lay.get("body_font", 10)))
        lay["row_height"] = st.slider("Row height", 4.0, 7.0, float(lay.get("row_height", 5.0)), 0.1)
        lay["section_gap"] = st.slider("Gap between sections", 0.0, 6.0, float(lay.get("section_gap", 2.0)), 0.5)

        st.subheader("Section Order")
        lay["section_order"] = st.multiselect(
            "Order (top → bottom)",
            options=[
                "Summary",
                "Allocation by Asset Class",
                "Allocation by Sector",
                "Allocation by Industry",
                "Top Holdings",
            ],
            default=lay.get("section_order", _default_layout()["section_order"]),
        )

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        meta_mode = st.selectbox("Metadata fetch", ["Top N by Value", "All", "None"], index=0)
    with c2:
        meta_top_n = st.number_input("Top N (for metadata)", min_value=5, max_value=300, value=40, step=5)
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

    df_full = report_calc["holdings_full"].copy()

    acct = account_last4 or "XXXX"
    header_line = f"Account {acct} | Generated {generated_at}"

    report_for_pdf = {
        "header_line": header_line,
        **report_calc,
    }

    st.subheader("Summary")
    t = report_calc["totals"]
    colA, colB, colC, colD = st.columns(4)
    with colA:
        st.metric("Total Value", _fmt_money(t.get("TotalValue")))
    with colB:
        st.metric("Holdings", str(int(t.get("HoldingsCount", 0))))
    with colC:
        st.metric("Largest Holding", _shorten(str(t.get("LargestHolding", "")), 26))
    with colD:
        st.metric("Largest Weight", _fmt_pct(t.get("LargestHoldingWeight"), 2))

    st.markdown("---")

    st.subheader("Details")
    tab1, tab2, tab3, tab4 = st.tabs(["Holdings", "Asset Class", "Sector", "Industry"])

    with tab1:
        show_cols = [
            "Ticker", "Name", "AssetClass", "QuoteType", "Sector", "Industry", "Category",
            "Value", "WeightPct", "DividendYield", "TrailingYield", "ExpenseRatio", "Description"
        ]
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

    with tab2:
        a = report_calc["alloc_asset"].copy()
        a["Value"] = a["Value"].map(_fmt_money)
        a["WeightPct"] = a["WeightPct"].map(lambda x: _fmt_pct(x, 2))
        st.dataframe(a, use_container_width=True)

    with tab3:
        s = report_calc["alloc_sector"].copy()
        s["Sector"] = s["Sector"].replace({"": "(Unclassified)"})
        s["Value"] = s["Value"].map(_fmt_money)
        s["WeightPct"] = s["WeightPct"].map(lambda x: _fmt_pct(x, 2))
        st.dataframe(s, use_container_width=True)

    with tab4:
        i = report_calc["alloc_industry"].copy()
        i["Industry"] = i["Industry"].replace({"": "(Unclassified)"})
        i["Value"] = i["Value"].map(_fmt_money)
        i["WeightPct"] = i["WeightPct"].map(lambda x: _fmt_pct(x, 2))
        st.dataframe(i, use_container_width=True)

    st.markdown("---")

    pdf_bytes = build_pdf(report_for_pdf, st.session_state.layout)

    st.subheader("PDF Preview (Page 1)")
    if fitz is None:
        st.info("PDF preview requires PyMuPDF. Install: `pip install pymupdf`")
    else:
        try:
            _ = _md5(pdf_bytes)
            png_bytes = render_pdf_page1_png(pdf_bytes, zoom=1.6)
            st.image(png_bytes, caption="Preview updates as you change Layout Controls", use_container_width=True)
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

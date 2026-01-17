#!/usr/bin/env python3
"""
Asset Allocation Report Generator (E*TRADE PortfolioDownload.csv)

Reads an E*TRADE-style PortfolioDownload.csv (with sections), extracts holdings,
pulls metadata from Yahoo Finance via yfinance, and produces:
  - asset_allocation_report.xlsx (client-ready)
  - asset_allocation_report.html (easy-to-share)

Usage:
  python asset_allocation_report.py --input /path/to/PortfolioDownload.csv --outdir /path/to/out

Notes:
  - Requires internet access for yfinance.
  - If yfinance is missing, the script will attempt to install it.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def _ensure_yfinance() -> None:
    try:
        import yfinance  # noqa: F401
    except Exception:
        import subprocess

        print("yfinance not found. Installing...", file=sys.stderr)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "yfinance>=0.2.40"],
            stdout=sys.stderr,
        )


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


def _safe_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def _find_holdings_table_rows(csv_path: str) -> Tuple[List[str], List[List[str]]]:
    """
    Locate the holdings table within a PortfolioDownload.csv.

    It searches for the row that begins with:
      Symbol,% of Portfolio,Last Price $,...

    Then captures rows until it hits TOTAL or Generated at.
    Returns (header, rows).
    """
    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        all_rows = [row for row in reader]

    header_idx = None
    for i, row in enumerate(all_rows):
        if not row:
            continue
        if len(row) >= 2 and row[0].strip() == "Symbol" and "% of Portfolio" in row[1]:
            header_idx = i
            break

    if header_idx is None:
        raise ValueError("Could not find holdings table header row (Symbol,% of Portfolio,...) in the CSV.")

    header = [c.strip() for c in all_rows[header_idx]]

    rows: List[List[str]] = []
    for row in all_rows[header_idx + 1 :]:
        if not row:
            continue
        first = row[0].strip() if row else ""
        if first.upper() in {"TOTAL"}:
            break
        if first.startswith("Generated at"):
            break
        rows.append(row)

    cleaned = [r for r in rows if len(r) > 0 and r[0].strip()]

    # Normalize row length to header length (E*TRADE sometimes emits extra trailing commas)
    normed: List[List[str]] = []
    n = len(header)
    for r in cleaned:
        if len(r) < n:
            normed.append(r + [""] * (n - len(r)))
        elif len(r) > n:
            normed.append(r[:n])
        else:
            normed.append(r)

    return header, normed


def _extract_generated_at(csv_path: str) -> Optional[str]:
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        text = f.read()
    m = re.search(r"Generated at\s+(.*)$", text, flags=re.MULTILINE)
    return m.group(1).strip() if m else None


@dataclass
class TickerMeta:
    ticker: str
    quote_type: str = ""
    long_name: str = ""
    short_name: str = ""
    currency: str = ""
    sector: str = ""
    industry: str = ""
    category: str = ""
    fund_family: str = ""
    asset_class_guess: str = ""
    expense_ratio: Optional[float] = None
    trailing_yield: Optional[float] = None
    website: str = ""
    summary: str = ""


def _classify_asset_class(meta: TickerMeta) -> str:
    """
    Heuristic classification into a client-meaningful asset class bucket.
    Uses yfinance fields when available; falls back to ticker + name clues.
    """
    t = meta.ticker.upper()
    qt = (meta.quote_type or "").upper()
    name = (meta.long_name or meta.short_name or "").upper()
    cat = (meta.category or "").upper()

    if t in {"CASH"}:
        return "Cash"

    # Money market / cash equivalents
    if "MONEY MARKET" in name or "MONEY MARKET" in cat or t.endswith("XX"):
        return "Cash & Cash Equivalents"

    # Commodities (common categories/names)
    if "COMMODITIES" in cat or "PRECIOUS METALS" in cat or "GOLD" in name or "SILVER" in name:
        return "Commodities"

    # Fixed income (bond/loan/ultrashort/treasury/etc.)
    fi_keywords = [
        "BOND", "FIXED INCOME", "TREASURY", "T-BILL", "ULTRA SHORT", "ULTRASHORT",
        "FLOATING", "LOAN", "CREDIT", "INCOME", "MUNICIPAL", "MUNI", "CORPORATE",
        "DURATION", "AGGREGATE", "SHORT TERM", "SHORT-TERM", "INTERMEDIATE", "GOVERNMENT",
    ]
    if any(k in name for k in fi_keywords) or any(k in cat for k in fi_keywords):
        return "Fixed Income"

    # Equity clues
    eq_keywords = ["EQUITY", "STOCK", "DIVIDEND", "GROWTH", "VALUE", "SMALL CAP", "LARGE CAP", "MID CAP"]
    if any(k in name for k in eq_keywords) or (meta.sector and meta.industry):
        return "Equity"

    # QuoteType-based defaulting
    if qt in {"ETF", "MUTUALFUND"}:
        if meta.category:
            if any(k in cat for k in fi_keywords):
                return "Fixed Income"
            if "COMMODITIES" in cat or "PRECIOUS METALS" in cat:
                return "Commodities"
        return "Fund / Other"

    if qt in {"EQUITY"}:
        return "Equity"

    return "Other"


def _first_sentence(text: str, max_chars: int = 220) -> str:
    if not text:
        return ""
    s = re.sub(r"\s+", " ", text).strip()
    # split on sentence end
    parts = re.split(r"(?<=[.!?])\s+", s)
    out = parts[0].strip() if parts else s
    if len(out) > max_chars:
        out = out[: max_chars - 1].rstrip() + "…"
    return out


def _format_pct(x: Optional[float], digits: int = 2) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    return f"{x:.{digits}f}%"


def _format_money(x: Optional[float], digits: int = 2) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    return f"${x:,.{digits}f}"


def _build_description(meta: TickerMeta) -> str:
    """
    Short, client-friendly, fast-readable description.
    Avoids long business summaries; uses name/category/sector/industry + a couple stats.
    """
    name = meta.long_name or meta.short_name or meta.ticker
    qt = meta.quote_type.upper() if meta.quote_type else ""
    ac = meta.asset_class_guess

    # Core focus line
    focus = ""
    if meta.category:
        focus = meta.category
    elif meta.sector and meta.industry:
        focus = f"{meta.sector} / {meta.industry}"
    elif meta.sector:
        focus = meta.sector

    bits = []
    if qt:
        bits.append(qt.title())
    if ac:
        bits.append(ac)

    header = f"{name} ({meta.ticker})"
    sub = " — ".join([b for b in bits if b]).strip()

    # Add compact stats (if available)
    stats = []
    if meta.expense_ratio is not None:
        stats.append(f"Exp {meta.expense_ratio:.2f}%")
    if meta.trailing_yield is not None:
        stats.append(f"Yield {meta.trailing_yield:.2f}%")
    stats_txt = f" | " + ", ".join(stats) if stats else ""

    if focus:
        return f"{header}: {sub} focused on {focus}.{stats_txt}".strip()
    return f"{header}: {sub}.{stats_txt}".strip()


def _fetch_yf_meta(ticker: str, pause_s: float = 0.35) -> TickerMeta:
    _ensure_yfinance()
    import yfinance as yf  # type: ignore

    t = ticker.strip().upper()
    meta = TickerMeta(ticker=t)

    if t in {"CASH"}:
        meta.quote_type = "CASH"
        meta.long_name = "Cash"
        meta.asset_class_guess = "Cash"
        meta.summary = "Cash position."
        return meta

    try:
        tk = yf.Ticker(t)
        info: Dict[str, Any] = {}
        # prefer fast_info when possible; info may be slower but has sector/industry/category
        try:
            info = tk.info or {}
        except Exception:
            info = {}

        meta.quote_type = _safe_str(info.get("quoteType"))
        meta.long_name = _safe_str(info.get("longName"))
        meta.short_name = _safe_str(info.get("shortName"))
        meta.currency = _safe_str(info.get("currency"))
        meta.sector = _safe_str(info.get("sector"))
        meta.industry = _safe_str(info.get("industry"))
        meta.category = _safe_str(info.get("category"))
        meta.fund_family = _safe_str(info.get("fundFamily"))
        meta.website = _safe_str(info.get("website"))

        er = info.get("annualReportExpenseRatio")
        if er is None:
            er = info.get("expenseRatio")
        meta.expense_ratio = _safe_float(er)
        if meta.expense_ratio is not None:
            # yfinance often returns expense ratio as decimal (0.004) or as pct; normalize to pct
            if meta.expense_ratio <= 1:
                meta.expense_ratio *= 100

        yld = info.get("yield")
        if yld is None:
            yld = info.get("trailingAnnualDividendYield")
        meta.trailing_yield = _safe_float(yld)
        if meta.trailing_yield is not None:
            if meta.trailing_yield <= 1:
                meta.trailing_yield *= 100

        lbs = _safe_str(info.get("longBusinessSummary"))
        meta.summary = _first_sentence(lbs, max_chars=220)

    except Exception as e:
        meta.summary = f"Metadata not available ({type(e).__name__})."

    # Classification + description
    meta.asset_class_guess = _classify_asset_class(meta)
    time.sleep(pause_s)
    return meta


def _make_tables(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Build allocation tables (asset class, sector, industry, security type).
    df must include: Value, WeightPct, AssetClass, Sector, Industry, QuoteType
    """
    def agg_table(group_col: str) -> pd.DataFrame:
        t = (
            df.groupby(group_col, dropna=False, as_index=False)
            .agg(Value=("Value", "sum"), WeightPct=("WeightPct", "sum"))
            .sort_values("WeightPct", ascending=False)
        )
        t["WeightPct"] = t["WeightPct"].round(4)
        return t

    tables = {
        "Allocation_AssetClass": agg_table("AssetClass"),
        "Allocation_Sector": agg_table("Sector"),
        "Allocation_Industry": agg_table("Industry"),
        "Allocation_SecurityType": agg_table("QuoteType"),
    }
    return tables


def _to_html_report(
    generated_at: str,
    account_name: str,
    total_value: float,
    df_holdings: pd.DataFrame,
    tables: Dict[str, pd.DataFrame],
    out_path: str,
) -> None:
    def df_to_html(d: pd.DataFrame, max_rows: int = 200) -> str:
        d2 = d.copy()
        if "Value" in d2.columns:
            d2["Value"] = d2["Value"].map(lambda x: _format_money(x))
        if "WeightPct" in d2.columns:
            d2["WeightPct"] = d2["WeightPct"].map(lambda x: _format_pct(x, 2))
        return d2.head(max_rows).to_html(index=False, escape=False)

    holdings_cols = [
        "Ticker",
        "Name",
        "QuoteType",
        "AssetClass",
        "Sector",
        "Industry",
        "Category",
        "Value",
        "WeightPct",
        "DividendYield",
        "ExpenseRatio",
        "Description",
    ]
    h = df_holdings[holdings_cols].copy()
    h["Value"] = h["Value"].map(_format_money)
    h["WeightPct"] = h["WeightPct"].map(lambda x: _format_pct(x, 2))
    h["DividendYield"] = h["DividendYield"].map(lambda x: _format_pct(x, 2) if pd.notna(x) else "")
    h["ExpenseRatio"] = h["ExpenseRatio"].map(lambda x: _format_pct(x, 2) if pd.notna(x) else "")

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Asset Allocation Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #111; }}
    h1 {{ margin: 0 0 8px 0; }}
    .meta {{ margin: 0 0 18px 0; color: #555; }}
    .box {{ border: 1px solid #e5e5e5; border-radius: 8px; padding: 12px 14px; margin: 14px 0; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #eaeaea; padding: 8px; font-size: 13px; vertical-align: top; }}
    th {{ background: #fafafa; text-align: left; }}
    .small {{ font-size: 12px; color: #666; }}
  </style>
</head>
<body>
  <h1>Asset Allocation Report</h1>
  <p class="meta">
    <b>Account:</b> {account_name or "N/A"}<br/>
    <b>Total Value:</b> {_format_money(total_value)}<br/>
    <b>Generated At:</b> {generated_at or "N/A"}
  </p>

  <div class="box">
    <h2>Allocation by Asset Class</h2>
    {df_to_html(tables["Allocation_AssetClass"])}
  </div>

  <div class="box">
    <h2>Allocation by Sector</h2>
    {df_to_html(tables["Allocation_Sector"])}
    <p class="small">Note: Sector/industry may be blank for some funds (depends on Yahoo metadata).</p>
  </div>

  <div class="box">
    <h2>Allocation by Industry</h2>
    {df_to_html(tables["Allocation_Industry"])}
  </div>

  <div class="box">
    <h2>Holdings (with concise descriptions)</h2>
    {h.to_html(index=False, escape=False)}
  </div>
</body>
</html>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


def _write_excel(
    generated_at: str,
    account_name: str,
    total_value: float,
    df_holdings: pd.DataFrame,
    tables: Dict[str, pd.DataFrame],
    out_path: str,
) -> None:
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        # Summary sheet
        summary = pd.DataFrame(
            [
                ["Account", account_name],
                ["Generated At", generated_at],
                ["Total Value", total_value],
            ],
            columns=["Field", "Value"],
        )
        summary.to_excel(writer, index=False, sheet_name="Summary")

        # Allocation sheets
        for name, t in tables.items():
            out = t.copy()
            out.to_excel(writer, index=False, sheet_name=name[:31])

        # Holdings sheet (client readable)
        cols = [
            "Ticker",
            "Name",
            "QuoteType",
            "AssetClass",
            "Sector",
            "Industry",
            "Category",
            "Value",
            "WeightPct",
            "TotalCost",
            "TotalGain",
            "DividendYield",
            "ExpenseRatio",
            "Description",
        ]
        df_holdings[cols].to_excel(writer, index=False, sheet_name="Holdings")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to E*TRADE PortfolioDownload.csv")
    ap.add_argument("--outdir", required=True, help="Output directory")
    ap.add_argument("--pause", type=float, default=0.35, help="Pause between yfinance calls (seconds)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    generated_at = _extract_generated_at(args.input) or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    header, rows = _find_holdings_table_rows(args.input)
    df_raw = pd.DataFrame(rows, columns=header)

    # Rename/standardize core columns we need
    colmap = {
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
    df = df_raw.rename(columns=colmap).copy()

    # Coerce numeric fields
    for c in ["PctOfPortfolio", "LastPrice", "CostPerShare", "Qty", "TotalCost", "TotalGain", "Value", "DividendYield"]:
        if c in df.columns:
            df[c] = df[c].apply(_safe_float)

    # Drop empty rows
    df["Ticker"] = df["Ticker"].astype(str).str.strip()
    df = df[df["Ticker"] != ""].copy()

    # If CASH row exists, keep it as a holding but treat as Cash
    # Many E*TRADE exports have CASH with Value in the 8th field (Value $ column)
    # Ensure Value exists
    if "Value" not in df.columns:
        raise ValueError("Could not find 'Value $' column in holdings table.")

    # Compute weights from Value (more reliable than % of Portfolio in some exports)
    total_value = float(df["Value"].fillna(0).sum())
    if total_value <= 0:
        raise ValueError("Total portfolio value computed as 0. Check the CSV parsing.")

    df["WeightPct"] = (df["Value"].fillna(0) / total_value) * 100

    # Fetch metadata for each ticker
    tickers = df["Ticker"].str.upper().tolist()
    metas: Dict[str, TickerMeta] = {}

    for t in tickers:
        if t in metas:
            continue
        meta = _fetch_yf_meta(t, pause_s=max(0.0, args.pause))
        # classification might depend on filled fields
        if not meta.asset_class_guess:
            meta.asset_class_guess = _classify_asset_class(meta)
        metas[t] = meta

    # Build enriched holdings table
    def pick_name(m: TickerMeta) -> str:
        return m.long_name or m.short_name or m.ticker

    df["QuoteType"] = df["Ticker"].str.upper().map(lambda t: metas[t].quote_type if t in metas else "")
    df["Name"] = df["Ticker"].str.upper().map(lambda t: pick_name(metas[t]) if t in metas else t)
    df["Sector"] = df["Ticker"].str.upper().map(lambda t: metas[t].sector if t in metas else "")
    df["Industry"] = df["Ticker"].str.upper().map(lambda t: metas[t].industry if t in metas else "")
    df["Category"] = df["Ticker"].str.upper().map(lambda t: metas[t].category if t in metas else "")
    df["AssetClass"] = df["Ticker"].str.upper().map(lambda t: metas[t].asset_class_guess if t in metas else "Other")
    df["ExpenseRatio"] = df["Ticker"].str.upper().map(lambda t: metas[t].expense_ratio if t in metas else None)
    df["Description"] = df["Ticker"].str.upper().map(lambda t: _build_description(metas[t]) if t in metas else t)

    # Keep dividend yield from E*TRADE if present; if missing, leave blank
    # (We still add yfinance trailing_yield into description if available)
    # Ensure CASH has sensible labels
    df.loc[df["Ticker"].str.upper() == "CASH", ["Name", "AssetClass", "QuoteType", "Description"]] = [
        "Cash",
        "Cash",
        "CASH",
        "Cash position.",
    ]

    # Allocation tables
    tables = _make_tables(df)

    # Attempt to pull account name from the header section (optional)
    account_name = ""
    try:
        with open(args.input, "r", encoding="utf-8-sig") as f:
            text = f.read()
        m = re.search(r"\"([^\"]+)\"\s*,\s*\\d", text)
        if m:
            account_name = m.group(1)
    except Exception:
        pass

    out_xlsx = os.path.join(args.outdir, "asset_allocation_report.xlsx")
    out_html = os.path.join(args.outdir, "asset_allocation_report.html")

    _write_excel(generated_at, account_name, total_value, df, tables, out_xlsx)
    _to_html_report(generated_at, account_name, total_value, df, tables, out_html)

    print("Saved:")
    print(f" - {out_xlsx}")
    print(f" - {out_html}")


if __name__ == "__main__":
    main()

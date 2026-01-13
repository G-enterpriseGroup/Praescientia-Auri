# app.py / Report Pro.py
# E*TRADE Earnings Analyzer + 1-Page PDF Report
# - Realized PnL only (equity + options)
# - Dividends (equities), VMFXX, other MMF/bank interest
# - Company names (via yfinance, 18 chars)
# - % contribution per item within each category
# - PDF filename: "<last4> Report Pro <MinMon YY> - <MaxMon YY>.pdf"
# - PDF body font 10, headers 12, plus dates per line where useful
# - Summary lines use dotted leaders: "Label .... Value"
# + OPTION A: PDF preview + robust layout controls (column widths, alignments, font sizes, section order)

import io
import re
import hashlib
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List

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
# Helpers: Load & Clean CSV + Metadata
# -----------------------------
def load_etrade_csv(uploaded_file):
    """
    Detect the correct header row (E*TRADE has 'For Account:' above),
    return:
      df, account_last4, start_label, end_label
    where start_label/end_label are "Mon YY" based on min/max
    values in the TransactionDate column (column A).
    """
    content_bytes = uploaded_file.getvalue()
    text = content_bytes.decode("utf-8", errors="ignore")
    lines = text.splitlines()

    # --- Find header row ---
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith("TransactionDate,TransactionType"):
            header_idx = i
            break

    if header_idx is None:
        st.error("Could not find the 'TransactionDate,TransactionType' header in the CSV.")
        return None, None, None, None

    # --- Find account last4 from "For Account" line above header ---
    account_last4 = None
    for i in range(header_idx):
        line = lines[i]
        if "For Account" in line:
            m = re.search(r"(\d{4})\D*$", line)
            if m:
                account_last4 = m.group(1)
            break

    # --- Load dataframe from header down ---
    data_io = io.StringIO("\n".join(lines[header_idx:]))
    df = pd.read_csv(data_io)

    # Basic cleaning
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    df["Commission"] = pd.to_numeric(df["Commission"], errors="coerce")
    df["Description"] = df["Description"].astype(str)

    # Parse dates from TransactionDate (column A)
    df["TransactionDate"] = pd.to_datetime(
        df["TransactionDate"],
        format="%m/%d/%y",
        errors="coerce",
    )

    # --- Date range labels based on min/max TransactionDate ---
    start_label = end_label = None
    valid_dates = df["TransactionDate"].dropna()
    if not valid_dates.empty:
        dmin = valid_dates.min()
        dmax = valid_dates.max()
        start_label = dmin.strftime("%b %y")  # e.g. Jan 25
        end_label = dmax.strftime("%b %y")    # e.g. Dec 25

    return df, account_last4, start_label, end_label


# -----------------------------
# Symbol → Company Name via yfinance
# -----------------------------
@lru_cache(maxsize=None)
def lookup_company_name(ticker: str) -> str:
    """
    Look up a short company name for a ticker using yfinance.
    Returns a name truncated to 18 characters.
    If yfinance isn't available or lookup fails, returns "".
    """
    if yf is None:
        return ""

    if not isinstance(ticker, str) or not ticker:
        return ""

    base = ticker.strip().upper()
    # For option strings like "SPYM Jan 16 '26 85 Put"
    # take the first token as the underlying
    if " " in base:
        base = base.split()[0]

    try:
        info = yf.Ticker(base).info
        name = info.get("shortName") or info.get("longName") or ""
    except Exception:
        name = ""

    if not name:
        return ""

    name = name.strip()
    if len(name) > 18:
        name = name[:18]
    return name


# -----------------------------
# Equity FIFO Realized PnL Engine
# -----------------------------
def compute_equity_fifo(df: pd.DataFrame) -> pd.DataFrame:
    """
    FIFO lot-based realized PnL for equities.

    For each symbol:
      - Walk buys and sells in date order.
      - Maintain inventory of buy lots (qty, net cost per share).
      - On each sell, match against inventory FIFO and book realized PnL.
      - Uses Amount/Quantity to include commissions in net prices.
      - ONLY realized for shares that have both a buy and a sell
        (no PnL on unmatched sells).
    """
    eq = df[
        (df["SecurityType"] == "EQ")
        & (df["TransactionType"].isin(["Bought", "Sold"]))
    ].copy()

    if eq.empty:
        return pd.DataFrame(columns=["Symbol", "Net PnL ($)", "FirstBuyDate", "LastSellDate"])

    eq.sort_values(["Symbol", "TransactionDate"], inplace=True)

    results = {}
    first_buy_date = {}
    last_sell_date = {}

    for sym, grp in eq.groupby("Symbol"):
        g = grp.sort_values("TransactionDate")
        inventory = []   # list of [remaining_qty, cost_per_share]
        realized = 0.0
        fb = None
        ls = None
        had_buy = False
        had_sell = False

        for _, row in g.iterrows():
            q = row["Quantity"]
            amt = row["Amount"]
            dt = row["TransactionDate"]
            ttype = row["TransactionType"]

            if ttype == "Bought":
                had_buy = True
                # Buys: Quantity positive, Amount negative (cash out)
                if q is None or amt is None or q <= 0 or amt >= 0:
                    cost_per_share = row["Price"]
                else:
                    cost_per_share = -amt / q  # includes commission
                inventory.append([q, cost_per_share])
                fb = fb or dt

            elif ttype == "Sold":
                had_sell = True
                # Sells: Quantity negative, Amount positive (cash in)
                if q is None or amt is None or q >= 0:
                    continue
                sell_qty = -q  # q is negative
                if sell_qty <= 0:
                    continue

                sale_per_share = amt / sell_qty  # net of commission
                remaining = sell_qty

                # Match against inventory FIFO
                while remaining > 0 and inventory:
                    lot_qty, cps = inventory[0]
                    take = min(lot_qty, remaining)
                    realized += (sale_per_share - cps) * take
                    lot_qty -= take
                    remaining -= take
                    if lot_qty == 0:
                        inventory.pop(0)
                    else:
                        inventory[0][0] = lot_qty

                # If remaining > 0 and no inventory, ignore it (no artificial PnL)
                ls = dt

        # Only keep symbols where we actually had both a buy and a sell
        if had_buy and had_sell:
            results[sym] = realized
            first_buy_date[sym] = fb
            last_sell_date[sym] = ls

    rows = []
    for sym, pnl in results.items():
        rows.append(
            {
                "Symbol": sym,
                "Net PnL ($)": pnl,
                "FirstBuyDate": first_buy_date.get(sym),
                "LastSellDate": last_sell_date.get(sym),
            }
        )

    res_df = pd.DataFrame(rows)
    if not res_df.empty:
        res_df["FirstBuyDate"] = res_df["FirstBuyDate"].dt.strftime("%m/%d/%y")
        res_df["LastSellDate"] = res_df["LastSellDate"].dt.strftime("%m/%d/%y")
        res_df.sort_values("Net PnL ($)", ascending=False, inplace=True)

    return res_df


# -----------------------------
# Core Calculations (Realized Only)
# -----------------------------
def compute_report(df: pd.DataFrame):
    """
    Compute:
    - Equity realized PnL (closed positions via FIFO) + buy/sell dates
    - Options PnL (closed positions only) + open/close dates
    - Company dividends + first/last dividend dates
    - VMFXX dividends (monthly)
    - Other MMF/bank interest (row level)
    """

    df = df.copy()

    # ---- VMFXX Dividends (using Description) ----
    vm_mask = df["Description"].str.contains(
        "VANGUARD FEDERAL MMKT INV DIV PAYMENT", case=False, na=False
    )
    vm_div = df[vm_mask]
    vm_div_credits = vm_div[vm_div["Amount"] > 0]
    vm_div_total = float(vm_div_credits["Amount"].sum())

    # Monthly breakdown for VMFXX, label as Mon YYYY
    vm_div_monthly = (
        vm_div_credits.assign(
            Month=lambda x: x["TransactionDate"].dt.strftime("%b %Y")
        )
        .groupby("Month")["Amount"]
        .sum()
        .reset_index()
        .rename(columns={"Amount": "VMFXX Dividends ($)"})
        .sort_values("Month")
    )

    # ---- Other MMF / Bank Interest (e.g., MSPBNA) ----
    mmf_interest = df[
        (df["SecurityType"] == "MMF")
        & (df["TransactionType"].isin(["Interest Income", "Dividend"]))
        & (~vm_mask)
    ]
    mmf_interest_credits = mmf_interest[mmf_interest["Amount"] > 0].copy()
    mmf_interest_credits["DateStr"] = mmf_interest_credits["TransactionDate"].dt.strftime(
        "%m/%d/%y"
    )
    mmf_interest_total = float(mmf_interest_credits["Amount"].sum())

    # ---- Company Dividends (EQ only) ----
    div = df[df["TransactionType"].isin(["Dividend", "Qualified Dividend"])]
    company_div = div[(div["SecurityType"] == "EQ")].copy()
    company_div_total = float(company_div["Amount"].sum())

    div_first = (
        company_div.groupby("Symbol")["TransactionDate"]
        .min()
        .dt.strftime("%m/%d/%y")
        .rename("FirstDivDate")
    )
    div_last = (
        company_div.groupby("Symbol")["TransactionDate"]
        .max()
        .dt.strftime("%m/%d/%y")
        .rename("LastDivDate")
    )

    company_div_by_sym = (
        company_div.groupby("Symbol")["Amount"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={"Amount": "Dividends ($)"})
    )
    company_div_by_sym = (
        company_div_by_sym.merge(div_first, on="Symbol", how="left")
        .merge(div_last, on="Symbol", how="left")
    )
    company_div_by_sym["Name"] = company_div_by_sym["Symbol"].apply(lookup_company_name)

    # ---- Equity Realized PnL (Closed positions via FIFO) ----
    eq_pnl_by_sym = compute_equity_fifo(df)
    if not eq_pnl_by_sym.empty:
        eq_pnl_by_sym["Name"] = eq_pnl_by_sym["Symbol"].apply(lookup_company_name)
    eq_total = float(eq_pnl_by_sym["Net PnL ($)"].sum()) if not eq_pnl_by_sym.empty else 0.0

    # ---- Options PnL (Closed positions only) ----
    opt = df[df["SecurityType"] == "OPTN"].copy()
    closed_types = ["Sold To Close", "Option Exercised", "Option Expired"]
    allowed_types = ["Bought To Open"] + closed_types

    closed_symbols = opt[opt["TransactionType"].isin(closed_types)]["Symbol"].unique().tolist()
    opt_closed = opt[
        (opt["Symbol"].isin(closed_symbols))
        & (opt["TransactionType"].isin(allowed_types))
    ].copy()

    opt_pnl_by_sym = (
        opt_closed.groupby("Symbol")["Amount"]
        .sum()
        .reset_index()
        .rename(columns={"Amount": "Net PnL ($)"})
    )

    opt_open = (
        opt_closed[opt_closed["TransactionType"] == "Bought To Open"]
        .groupby("Symbol")["TransactionDate"]
        .min()
        .dt.strftime("%m/%d/%y")
        .rename("OpenDate")
    )
    opt_close = (
        opt_closed[opt_closed["TransactionType"].isin(closed_types)]
        .groupby("Symbol")["TransactionDate"]
        .max()
        .dt.strftime("%m/%d/%y")
        .rename("CloseDate")
    )

    opt_pnl_by_sym = (
        opt_pnl_by_sym.merge(opt_open, on="Symbol", how="left")
        .merge(opt_close, on="Symbol", how="left")
    )

    def _opt_name(sym: str) -> str:
        if not isinstance(sym, str):
            return ""
        base = sym.split()[0]
        return lookup_company_name(base)

    if not opt_pnl_by_sym.empty:
        opt_pnl_by_sym["Name"] = opt_pnl_by_sym["Symbol"].apply(_opt_name)
    opt_total = float(opt_pnl_by_sym["Net PnL ($)"].sum()) if not opt_pnl_by_sym.empty else 0.0

    # ---- Totals (all realized) ----
    totals = {
        "Equity Realized PnL ($)": round(eq_total, 2),
        "Options Net PnL ($)": round(opt_total, 2),
        "Company Dividends ($)": round(company_div_total, 2),
        "VMFXX Dividends ($)": round(vm_div_total, 2),
        "Other MMF/Bank Interest ($)": round(mmf_interest_total, 2),
    }
    total_earnings = round(sum(totals.values()), 2)

    # ---- % contribution columns ----
    if eq_total != 0 and not eq_pnl_by_sym.empty:
        eq_pnl_by_sym["Pct of Equity PnL (%)"] = (eq_pnl_by_sym["Net PnL ($)"] / eq_total * 100.0)
    else:
        eq_pnl_by_sym["Pct of Equity PnL (%)"] = 0.0

    if opt_total != 0 and not opt_pnl_by_sym.empty:
        opt_pnl_by_sym["Pct of Options PnL (%)"] = (opt_pnl_by_sym["Net PnL ($)"] / opt_total * 100.0)
    else:
        opt_pnl_by_sym["Pct of Options PnL (%)"] = 0.0

    if company_div_total != 0 and not company_div_by_sym.empty:
        company_div_by_sym["Pct of Dividends (%)"] = (company_div_by_sym["Dividends ($)"] / company_div_total * 100.0)
    else:
        company_div_by_sym["Pct of Dividends (%)"] = 0.0

    if vm_div_total != 0 and not vm_div_monthly.empty:
        vm_div_monthly["Pct of VMFXX Divs (%)"] = (vm_div_monthly["VMFXX Dividends ($)"] / vm_div_total * 100.0)
    else:
        vm_div_monthly["Pct of VMFXX Divs (%)"] = 0.0

    if mmf_interest_total != 0 and not mmf_interest_credits.empty:
        mmf_interest_credits["Pct of MMF Int (%)"] = (mmf_interest_credits["Amount"] / mmf_interest_total * 100.0)
    else:
        mmf_interest_credits["Pct of MMF Int (%)"] = 0.0

    return {
        "totals": totals,
        "total_earnings": total_earnings,
        "eq_pnl_by_sym": eq_pnl_by_sym,
        "opt_pnl_by_sym": opt_pnl_by_sym,
        "company_div_by_sym": company_div_by_sym,
        "vm_div_monthly": vm_div_monthly,
        "vm_div_credits": vm_div_credits,
        "mmf_interest_credits": mmf_interest_credits,
    }


# -----------------------------
# Layout + PDF Helpers
# -----------------------------
def _safe_align(a: str) -> str:
    a = (a or "").upper().strip()
    return a if a in {"L", "C", "R"} else "L"


def _clamp_int(x, lo: int, hi: int, default: int) -> int:
    """
    Robust clamp for Streamlit widgets that have min/max.
    Prevents StreamlitValueAboveMaxError / BelowMinError when session_state has old values.
    """
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
    """
    Ensures widths fit the available PDF width.
    If sum(widths) != usable, scale proportionally and enforce a minimum width.
    """
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
    """Print 'Label ..... Value' with dotted leader across the available width."""
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
class EarningsPDF(FPDF):
    def header(self):
        # Header rendered in build_pdf
        pass


def build_pdf(report: dict, layout: Dict[str, Any]) -> bytes:
    pdf = EarningsPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Layout basics
    title_font = int(layout.get("title_font", 14))
    sub_font = int(layout.get("sub_font", 8))
    section_font = int(layout.get("section_font", 12))
    header_font = int(layout.get("header_font", 10))
    body_font = int(layout.get("body_font", 10))
    row_h = float(layout.get("row_height", 5.0))
    section_gap = float(layout.get("section_gap", 2.0))

    # ----- PDF top header -----
    pdf.set_font("Times", "B", title_font)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, "E*TRADE Earnings Report", ln=1, align="C")
    pdf.set_font("Times", "", sub_font)
    pdf.cell(0, 4, datetime.now().strftime("Generated on %Y-%m-%d %H:%M"), ln=1, align="C")
    pdf.ln(3)

    totals = report["totals"]
    total_earnings = report["total_earnings"]
    eq_pnl_by_sym = report["eq_pnl_by_sym"]
    opt_pnl_by_sym = report["opt_pnl_by_sym"]
    company_div_by_sym = report["company_div_by_sym"]
    vm_div_monthly = report["vm_div_monthly"]
    mmf_interest_credits = report["mmf_interest_credits"]

    order = layout.get("section_order") or [
        "Summary",
        "Equity Realized PnL",
        "Options PnL",
        "Company Dividends",
        "VMFXX Monthly Dividends",
        "Other MMF / Bank Interest",
    ]
    order = [s for s in order if s in {
        "Summary",
        "Equity Realized PnL",
        "Options PnL",
        "Company Dividends",
        "VMFXX Monthly Dividends",
        "Other MMF / Bank Interest",
    }]

    for idx, sec in enumerate(order, start=1):
        pdf.set_font("Times", "B", section_font)
        pdf.cell(0, 7, f"{idx}. {sec}", ln=1)
        pdf.ln(1)

        if sec == "Summary":
            add_key_value(pdf, "Total Earnings ($)", f"{total_earnings:,.2f}", body_font)
            for k, v in totals.items():
                add_key_value(pdf, k, f"{v:,.2f}", body_font)
            pdf.ln(section_gap)
            continue

        if sec == "Equity Realized PnL":
            if eq_pnl_by_sym.empty:
                pdf.set_font("Times", "", body_font)
                pdf.cell(0, 5, "No closed equity positions.", ln=1)
                pdf.ln(section_gap)
                continue

            cols = ["Symbol / Name", "Buy - Sell Dates", "Net PnL ($)", "% of Eq PnL"]
            default_widths = [70, 55, 30, 25]
            default_aligns = ["L", "L", "R", "R"]

            cfg = layout.get("tables", {}).get("equity", {})
            widths = _fit_widths_to_page(pdf, cfg.get("widths", default_widths))
            aligns = cfg.get("aligns", default_aligns)
            max_rows = int(cfg.get("max_rows", 5000))

            add_table_header(pdf, cols, widths, header_font)
            for r_i, (_, row) in enumerate(eq_pnl_by_sym.iterrows()):
                if r_i >= max_rows:
                    pdf.set_font("Times", "", body_font)
                    pdf.cell(0, 5, f"... ({len(eq_pnl_by_sym) - max_rows} more rows not shown)", ln=1)
                    break

                name = row.get("Name", "") or ""
                label = str(row["Symbol"])
                if name:
                    label = f"{label}  {name}"
                fb = row.get("FirstBuyDate")
                ls = row.get("LastSellDate")
                if pd.notna(fb) and pd.notna(ls):
                    date_range = f"{fb} - {ls}"
                elif pd.notna(fb):
                    date_range = f"{fb} -"
                elif pd.notna(ls):
                    date_range = f"- {ls}"
                else:
                    date_range = ""
                pct = row.get("Pct of Equity PnL (%)", 0.0)

                vals = [
                    label[:50],
                    str(date_range)[:25],
                    f"{row['Net PnL ($)']:,.2f}",
                    f"{pct:,.1f}%",
                ]
                add_table_row(pdf, vals, widths, aligns, body_font, row_h=row_h)

            pdf.ln(section_gap)
            continue

        if sec == "Options PnL":
            if opt_pnl_by_sym.empty:
                pdf.set_font("Times", "", body_font)
                pdf.cell(0, 5, "No closed option positions.", ln=1)
                pdf.ln(section_gap)
                continue

            cols = ["Contract / Underlying", "Open - Close Dates", "Net PnL ($)", "% of Opt PnL"]
            default_widths = [70, 55, 30, 25]
            default_aligns = ["L", "L", "R", "R"]

            cfg = layout.get("tables", {}).get("options", {})
            widths = _fit_widths_to_page(pdf, cfg.get("widths", default_widths))
            aligns = cfg.get("aligns", default_aligns)
            max_rows = int(cfg.get("max_rows", 5000))

            add_table_header(pdf, cols, widths, header_font)
            for r_i, (_, row) in enumerate(opt_pnl_by_sym.iterrows()):
                if r_i >= max_rows:
                    pdf.set_font("Times", "", body_font)
                    pdf.cell(0, 5, f"... ({len(opt_pnl_by_sym) - max_rows} more rows not shown)", ln=1)
                    break

                name = row.get("Name", "") or ""
                label = str(row["Symbol"])
                if name:
                    label = f"{label}  {name}"
                od = row.get("OpenDate")
                cd = row.get("CloseDate")
                if pd.notna(od) and pd.notna(cd):
                    dr = f"{od} - {cd}"
                elif pd.notna(od):
                    dr = f"{od} -"
                elif pd.notna(cd):
                    dr = f"- {cd}"
                else:
                    dr = ""
                pct = row.get("Pct of Options PnL (%)", 0.0)

                vals = [
                    label[:50],
                    str(dr)[:25],
                    f"{row['Net PnL ($)']:,.2f}",
                    f"{pct:,.1f}%",
                ]
                add_table_row(pdf, vals, widths, aligns, body_font, row_h=row_h)

            pdf.ln(section_gap)
            continue

        if sec == "Company Dividends":
            if company_div_by_sym.empty:
                pdf.set_font("Times", "", body_font)
                pdf.cell(0, 5, "No equity dividends.", ln=1)
                pdf.ln(section_gap)
                continue

            cols = ["Symbol / Name", "Div Date Range", "Dividends ($)", "% of Divs"]
            default_widths = [70, 55, 30, 25]
            default_aligns = ["L", "L", "R", "R"]

            cfg = layout.get("tables", {}).get("dividends", {})
            widths = _fit_widths_to_page(pdf, cfg.get("widths", default_widths))
            aligns = cfg.get("aligns", default_aligns)
            max_rows = int(cfg.get("max_rows", 5000))

            add_table_header(pdf, cols, widths, header_font)
            for r_i, (_, row) in enumerate(company_div_by_sym.iterrows()):
                if r_i >= max_rows:
                    pdf.set_font("Times", "", body_font)
                    pdf.cell(0, 5, f"... ({len(company_div_by_sym) - max_rows} more rows not shown)", ln=1)
                    break

                name = row.get("Name", "") or ""
                label = str(row["Symbol"])
                if name:
                    label = f"{label}  {name}"
                fr = row.get("FirstDivDate")
                lr = row.get("LastDivDate")
                if pd.notna(fr) and pd.notna(lr):
                    dr = f"{fr} - {lr}"
                elif pd.notna(fr):
                    dr = f"{fr} -"
                elif pd.notna(lr):
                    dr = f"- {lr}"
                else:
                    dr = ""
                pct = row.get("Pct of Dividends (%)", 0.0)

                vals = [
                    label[:50],
                    str(dr)[:25],
                    f"{row['Dividends ($)']:,.2f}",
                    f"{pct:,.1f}%",
                ]
                add_table_row(pdf, vals, widths, aligns, body_font, row_h=row_h)

            pdf.ln(section_gap)
            continue

        if sec == "VMFXX Monthly Dividends":
            if vm_div_monthly.empty:
                pdf.set_font("Times", "", body_font)
                pdf.cell(0, 5, "No VMFXX dividend payments.", ln=1)
                pdf.ln(section_gap)
                continue

            cols = ["Month", "VMFXX Dividends ($)", "% of VMFXX"]
            default_widths = [90, 35, 25]
            default_aligns = ["L", "R", "R"]

            cfg = layout.get("tables", {}).get("vmfxx", {})
            widths = _fit_widths_to_page(pdf, cfg.get("widths", default_widths))
            aligns = cfg.get("aligns", default_aligns)
            max_rows = int(cfg.get("max_rows", 5000))

            add_table_header(pdf, cols, widths, header_font)
            for r_i, (_, row) in enumerate(vm_div_monthly.iterrows()):
                if r_i >= max_rows:
                    pdf.set_font("Times", "", body_font)
                    pdf.cell(0, 5, f"... ({len(vm_div_monthly) - max_rows} more rows not shown)", ln=1)
                    break

                pct = row.get("Pct of VMFXX Divs (%)", 0.0)
                vals = [
                    str(row["Month"])[:20],
                    f"{row['VMFXX Dividends ($)']:,.2f}",
                    f"{pct:,.1f}%",
                ]
                add_table_row(pdf, vals, widths, aligns, body_font, row_h=row_h)

            pdf.ln(section_gap)
            continue

        if sec == "Other MMF / Bank Interest":
            if mmf_interest_credits.empty:
                pdf.set_font("Times", "", body_font)
                pdf.cell(0, 5, "No additional MMF/bank interest.", ln=1)
                pdf.ln(section_gap)
                continue

            cols = ["Date / Description", "Amount ($)", "% of MMF Int"]
            default_widths = [95, 30, 25]
            default_aligns = ["L", "R", "R"]

            cfg = layout.get("tables", {}).get("mmf", {})
            widths = _fit_widths_to_page(pdf, cfg.get("widths", default_widths))
            aligns = cfg.get("aligns", default_aligns)
            max_rows = int(cfg.get("max_rows", 5000))

            add_table_header(pdf, cols, widths, header_font)
            for r_i, (_, row) in enumerate(mmf_interest_credits.iterrows()):
                if r_i >= max_rows:
                    pdf.set_font("Times", "", body_font)
                    pdf.cell(0, 5, f"... ({len(mmf_interest_credits) - max_rows} more rows not shown)", ln=1)
                    break

                date_str = row.get("DateStr") or ""
                desc = row.get("Description") or ""
                left = f"{date_str}  {desc}"
                pct = row.get("Pct of MMF Int (%)", 0.0)

                vals = [
                    left[:60],
                    f"{row['Amount']:,.2f}",
                    f"{pct:,.1f}%",
                ]
                add_table_row(pdf, vals, widths, aligns, body_font, row_h=row_h)

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
    """
    Render first page of PDF -> PNG bytes for Streamlit preview.
    Requires PyMuPDF (fitz).
    """
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
    # IMPORTANT: max_rows defaults to 5000 to match widget max_value and avoid state crashes.
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
            "Equity Realized PnL",
            "Options PnL",
            "Company Dividends",
            "VMFXX Monthly Dividends",
            "Other MMF / Bank Interest",
        ],
        "tables": {
            "equity": {"widths": [70, 55, 30, 25], "aligns": ["L", "L", "R", "R"], "max_rows": 5000},
            "options": {"widths": [70, 55, 30, 25], "aligns": ["L", "L", "R", "R"], "max_rows": 5000},
            "dividends": {"widths": [70, 55, 30, 25], "aligns": ["L", "L", "R", "R"], "max_rows": 5000},
            "vmfxx": {"widths": [90, 35, 25], "aligns": ["L", "R", "R"], "max_rows": 5000},
            "mmf": {"widths": [95, 30, 25], "aligns": ["L", "R", "R"], "max_rows": 5000},
        },
    }


def main():
    st.set_page_config(page_title="E*TRADE Earnings Report Generator", layout="wide")

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

    st.title("E*TRADE Earnings Report Generator")
    st.caption("Upload your E*TRADE CSV → compute realized earnings → preview & tweak layout → download PDF.")

    # Init layout state
    if "layout" not in st.session_state:
        st.session_state.layout = _default_layout()

    # Sidebar: layout editor
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
                "Equity Realized PnL",
                "Options PnL",
                "Company Dividends",
                "VMFXX Monthly Dividends",
                "Other MMF / Bank Interest",
            ],
            default=lay.get("section_order", _default_layout()["section_order"]),
        )

        st.subheader("Table Columns")

        def _align_picker(label: str, current: str, key: str) -> str:
            cur = _safe_align(current)
            return st.selectbox(label, options=["L", "C", "R"], index=["L", "C", "R"].index(cur), key=key)

        # Equity
        with st.expander("Equity table settings", expanded=False):
            t = lay["tables"]["equity"]
            t["max_rows"] = st.number_input(
                "Max rows (Equity)",
                min_value=5,
                max_value=5000,
                value=_clamp_int(t.get("max_rows", 5000), 5, 5000, 5000),
                step=5,
                key="max_rows_equity",
            )
            w1 = st.slider("Col1 width (Symbol/Name)", 30, 120, int(t["widths"][0]), key="eq_w1")
            w2 = st.slider("Col2 width (Dates)", 20, 100, int(t["widths"][1]), key="eq_w2")
            w3 = st.slider("Col3 width (PnL)", 15, 70, int(t["widths"][2]), key="eq_w3")
            w4 = st.slider("Col4 width (% share)", 15, 70, int(t["widths"][3]), key="eq_w4")
            t["widths"] = [w1, w2, w3, w4]
            a1 = _align_picker("Col1 align", t["aligns"][0], "eq_a1")
            a2 = _align_picker("Col2 align", t["aligns"][1], "eq_a2")
            a3 = _align_picker("Col3 align", t["aligns"][2], "eq_a3")
            a4 = _align_picker("Col4 align", t["aligns"][3], "eq_a4")
            t["aligns"] = [a1, a2, a3, a4]

        # Options
        with st.expander("Options table settings", expanded=False):
            t = lay["tables"]["options"]
            t["max_rows"] = st.number_input(
                "Max rows (Options)",
                min_value=5,
                max_value=5000,
                value=_clamp_int(t.get("max_rows", 5000), 5, 5000, 5000),
                step=5,
                key="max_rows_options",
            )
            w1 = st.slider("Col1 width (Contract)", 30, 120, int(t["widths"][0]), key="op_w1")
            w2 = st.slider("Col2 width (Dates)", 20, 100, int(t["widths"][1]), key="op_w2")
            w3 = st.slider("Col3 width (PnL)", 15, 70, int(t["widths"][2]), key="op_w3")
            w4 = st.slider("Col4 width (% share)", 15, 70, int(t["widths"][3]), key="op_w4")
            t["widths"] = [w1, w2, w3, w4]
            a1 = _align_picker("Col1 align", t["aligns"][0], "op_a1")
            a2 = _align_picker("Col2 align", t["aligns"][1], "op_a2")
            a3 = _align_picker("Col3 align", t["aligns"][2], "op_a3")
            a4 = _align_picker("Col4 align", t["aligns"][3], "op_a4")
            t["aligns"] = [a1, a2, a3, a4]

        # Dividends
        with st.expander("Dividends table settings", expanded=False):
            t = lay["tables"]["dividends"]
            t["max_rows"] = st.number_input(
                "Max rows (Dividends)",
                min_value=5,
                max_value=5000,
                value=_clamp_int(t.get("max_rows", 5000), 5, 5000, 5000),
                step=5,
                key="max_rows_dividends",
            )
            w1 = st.slider("Col1 width (Symbol/Name)", 30, 120, int(t["widths"][0]), key="dv_w1")
            w2 = st.slider("Col2 width (Date range)", 20, 100, int(t["widths"][1]), key="dv_w2")
            w3 = st.slider("Col3 width ($)", 15, 70, int(t["widths"][2]), key="dv_w3")
            w4 = st.slider("Col4 width (% share)", 15, 70, int(t["widths"][3]), key="dv_w4")
            t["widths"] = [w1, w2, w3, w4]
            a1 = _align_picker("Col1 align", t["aligns"][0], "dv_a1")
            a2 = _align_picker("Col2 align", t["aligns"][1], "dv_a2")
            a3 = _align_picker("Col3 align", t["aligns"][2], "dv_a3")
            a4 = _align_picker("Col4 align", t["aligns"][3], "dv_a4")
            t["aligns"] = [a1, a2, a3, a4]

        # VMFXX
        with st.expander("VMFXX table settings", expanded=False):
            t = lay["tables"]["vmfxx"]
            t["max_rows"] = st.number_input(
                "Max rows (VMFXX)",
                min_value=5,
                max_value=5000,
                value=_clamp_int(t.get("max_rows", 5000), 5, 5000, 5000),
                step=5,
                key="max_rows_vmfxx",
            )
            w1 = st.slider("Col1 width (Month)", 40, 140, int(t["widths"][0]), key="vm_w1")
            w2 = st.slider("Col2 width ($)", 15, 80, int(t["widths"][1]), key="vm_w2")
            w3 = st.slider("Col3 width (% share)", 15, 80, int(t["widths"][2]), key="vm_w3")
            t["widths"] = [w1, w2, w3]
            a1 = _align_picker("Col1 align", t["aligns"][0], "vm_a1")
            a2 = _align_picker("Col2 align", t["aligns"][1], "vm_a2")
            a3 = _align_picker("Col3 align", t["aligns"][2], "vm_a3")
            t["aligns"] = [a1, a2, a3]

        # MMF
        with st.expander("Other MMF/Interest table settings", expanded=False):
            t = lay["tables"]["mmf"]
            t["max_rows"] = st.number_input(
                "Max rows (MMF/Interest)",
                min_value=5,
                max_value=5000,
                value=_clamp_int(t.get("max_rows", 5000), 5, 5000, 5000),
                step=5,
                key="max_rows_mmf",
            )
            w1 = st.slider("Col1 width (Date/Desc)", 40, 160, int(t["widths"][0]), key="mm_w1")
            w2 = st.slider("Col2 width ($)", 15, 80, int(t["widths"][1]), key="mm_w2")
            w3 = st.slider("Col3 width (% share)", 15, 80, int(t["widths"][2]), key="mm_w3")
            t["widths"] = [w1, w2, w3]
            a1 = _align_picker("Col1 align", t["aligns"][0], "mm_a1")
            a2 = _align_picker("Col2 align", t["aligns"][1], "mm_a2")
            a3 = _align_picker("Col3 align", t["aligns"][2], "mm_a3")
            t["aligns"] = [a1, a2, a3]

        st.caption("Note: widths are auto-scaled to fit the PDF page margins.")

    uploaded_file = st.file_uploader("Upload E*TRADE CSV", type=["csv"])
    if not uploaded_file:
        return

    df, account_last4, start_label, end_label = load_etrade_csv(uploaded_file)
    if df is None:
        return

    report = compute_report(df)

    # ---- Top Summary ----
    st.subheader("Summary")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Earnings ($)", f"{report['total_earnings']:,.2f}")
    with c2:
        st.metric("Equity Realized PnL ($)", f"{report['totals']['Equity Realized PnL ($)']:,.2f}")
    with c3:
        st.metric("Options Net PnL ($)", f"{report['totals']['Options Net PnL ($)']:,.2f}")

    c4, c5, c6 = st.columns(3)
    with c4:
        st.metric("Company Dividends ($)", f"{report['totals']['Company Dividends ($)']:,.2f}")
    with c5:
        st.metric("VMFXX Dividends ($)", f"{report['totals']['VMFXX Dividends ($)']:,.2f}")
    with c6:
        st.metric("Other MMF/Bank Interest ($)", f"{report['totals']['Other MMF/Bank Interest ($)']:,.2f}")

    st.markdown("---")

    # ---- Details (tables in-app) ----
    st.subheader("Details")
    with st.expander("Equity Realized PnL (Closed Positions)", expanded=True):
        st.dataframe(report["eq_pnl_by_sym"], use_container_width=True)

    with st.expander("Options PnL (Closed Positions Only)", expanded=False):
        st.dataframe(report["opt_pnl_by_sym"], use_container_width=True)

    with st.expander("Company Dividends by Symbol", expanded=False):
        st.dataframe(report["company_div_by_sym"], use_container_width=True)

    with st.expander("VMFXX Monthly Dividend Breakdown", expanded=False):
        st.dataframe(report["vm_div_monthly"], use_container_width=True)

    with st.expander("Other MMF / Bank Interest Rows", expanded=False):
        st.dataframe(report["mmf_interest_credits"], use_container_width=True)

    st.markdown("---")

    # ---- Build PDF with current layout settings ----
    pdf_bytes = build_pdf(report, st.session_state.layout)

    # ---- PDF Preview ----
    st.subheader("PDF Preview (Page 1)")
    if fitz is None:
        st.info("PDF preview requires PyMuPDF. Install: `pip install pymupdf`")
    else:
        try:
            _ = _md5(pdf_bytes)  # stable cache key basis
            png_bytes = render_pdf_page1_png(pdf_bytes, zoom=1.6)
            st.image(png_bytes, caption="Preview updates as you change Layout Controls", use_container_width=True)
        except Exception as e:
            st.warning(f"Could not render PDF preview: {e}")

    # ---- One-click PDF Download ----
    acct_str = account_last4 or "XXXX"
    if start_label and end_label:
        date_range = f"{start_label} - {end_label}"
    else:
        date_range = "Dates"
    file_name = f"{acct_str} Report Pro {date_range}.pdf"

    st.download_button(
        label="Download PDF Earnings Report",
        data=pdf_bytes,
        file_name=file_name,
        mime="application/pdf",
    )


if __name__ == "__main__":
    main()

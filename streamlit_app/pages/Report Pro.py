# app.py / Report Pro.py
# E*TRADE Earnings Analyzer + PDF Report + Donut/Bar Charts
#
# - Realized PnL only (equity + options, FIFO for equities)
# - Dividends (equities), VMFXX, other MMF/bank interest
# - Per-symbol % of each category
# - Company names (via yfinance, 18 chars)
# - Donut-hole pies:
#      * Category breakdown (abs amounts)
#      * Equity PnL % by symbol (all trades)
#      * Options PnL % by symbol (all trades)
# - Monthly bar charts:
#      * VMFXX dividends by month
#      * Other income (company divs + MMF interest) by month
# - Charts in Streamlit AND in the PDF
# - PDF filename: "<last4> Report Pro <MinMon YY> - <MaxMon YY>.pdf"
# - PDF body font 10, headers 12, Times New Roman

import io
import re
from datetime import datetime
from functools import lru_cache

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from fpdf import FPDF

try:
    import yfinance as yf
except ImportError:
    yf = None


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

                # IMPORTANT: if remaining > 0 here (sell with no prior inventory),
                # we do NOT book extra PnL. Only matched shares count.
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
    - MMF/bank interest
    - Monthly aggregates for bar charts
    - % share columns for each category
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
            MonthDate=lambda x: x["TransactionDate"].dt.to_period("M").dt.to_timestamp()
        )
        .groupby("MonthDate")["Amount"]
        .sum()
        .reset_index()
        .rename(columns={"Amount": "VMFXX Dividends ($)"})
    )
    if not vm_div_monthly.empty:
        vm_div_monthly["MonthLabel"] = vm_div_monthly["MonthDate"].dt.strftime("%b %Y")
        vm_div_monthly.sort_values("MonthDate", inplace=True)
        vm_div_monthly["Pct of VMFXX (%)"] = (
            vm_div_monthly["VMFXX Dividends ($)"].abs()
            / vm_div_monthly["VMFXX Dividends ($)"].abs().sum()
            * 100
        ).round(1)

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

    # Monthly MMF/interest
    mmf_interest_monthly = (
        mmf_interest_credits.assign(
            MonthDate=lambda x: x["TransactionDate"].dt.to_period("M").dt.to_timestamp()
        )
        .groupby("MonthDate")["Amount"]
        .sum()
        .reset_index()
        .rename(columns={"Amount": "MMF/Interest ($)"})
    )
    if not mmf_interest_monthly.empty:
        mmf_interest_monthly["MonthLabel"] = mmf_interest_monthly["MonthDate"].dt.strftime(
            "%b %Y"
        )
        mmf_interest_monthly.sort_values("MonthDate", inplace=True)

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
    if not company_div_by_sym.empty and company_div_total != 0:
        company_div_by_sym["Pct of Dividends (%)"] = (
            company_div_by_sym["Dividends ($)"].abs() / abs(company_div_total) * 100
        ).round(1)

    # Company dividends by month (for bar chart)
    company_div_monthly = (
        company_div.assign(
            MonthDate=lambda x: x["TransactionDate"].dt.to_period("M").dt.to_timestamp()
        )
        .groupby("MonthDate")["Amount"]
        .sum()
        .reset_index()
        .rename(columns={"Amount": "Company Dividends ($)"})
    )
    if not company_div_monthly.empty:
        company_div_monthly["MonthLabel"] = company_div_monthly["MonthDate"].dt.strftime(
            "%b %Y"
        )
        company_div_monthly.sort_values("MonthDate", inplace=True)

    # ---- Equity Realized PnL (Closed positions via FIFO) ----
    eq_pnl_by_sym = compute_equity_fifo(df)
    if not eq_pnl_by_sym.empty:
        eq_pnl_by_sym["Name"] = eq_pnl_by_sym["Symbol"].apply(lookup_company_name)
        eq_pnl_by_sym["AbsPnL"] = eq_pnl_by_sym["Net PnL ($)"].abs()
        total_abs_eq = eq_pnl_by_sym["AbsPnL"].sum()
        if total_abs_eq != 0:
            eq_pnl_by_sym["Pct of Equity PnL (%)"] = (
                eq_pnl_by_sym["AbsPnL"] / total_abs_eq * 100
            ).round(1)
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
        opt_pnl_by_sym["AbsPnL"] = opt_pnl_by_sym["Net PnL ($)"].abs()
        total_abs_opt = opt_pnl_by_sym["AbsPnL"].sum()
        if total_abs_opt != 0:
            opt_pnl_by_sym["Pct of Options PnL (%)"] = (
                opt_pnl_by_sym["AbsPnL"] / total_abs_opt * 100
            ).round(1)
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

    # Combined "other income" by month (company divs + MMF interest)
    income_monthly = None
    if not company_div_monthly.empty or not mmf_interest_monthly.empty:
        frames = []
        if not company_div_monthly.empty:
            frames.append(
                company_div_monthly[["MonthDate", "Company Dividends ($)"]]
                .rename(columns={"Company Dividends ($)": "Amount"})
            )
        if not mmf_interest_monthly.empty:
            frames.append(
                mmf_interest_monthly[["MonthDate", "MMF/Interest ($)"]]
                .rename(columns={"MMF/Interest ($)": "Amount"})
            )
        income_monthly = (
            pd.concat(frames, ignore_index=True)
            .groupby("MonthDate")["Amount"]
            .sum()
            .reset_index()
            .rename(columns={"Amount": "Income ($)"})
        )
        if not income_monthly.empty:
            income_monthly["MonthLabel"] = income_monthly["MonthDate"].dt.strftime("%b %Y")
            income_monthly.sort_values("MonthDate", inplace=True)

    return {
        "totals": totals,
        "total_earnings": total_earnings,
        "eq_pnl_by_sym": eq_pnl_by_sym,
        "opt_pnl_by_sym": opt_pnl_by_sym,
        "company_div_by_sym": company_div_by_sym,
        "vm_div_monthly": vm_div_monthly,
        "vm_div_credits": vm_div_credits,
        "mmf_interest_credits": mmf_interest_credits,
        "company_div_monthly": company_div_monthly,
        "mmf_interest_monthly": mmf_interest_monthly,
        "income_monthly": income_monthly,
    }


# -----------------------------
# Matplotlib helpers (donut + bar)
# -----------------------------
def plot_donut_with_callouts(ax, labels, values, title):
    """Donut pie with % labels and callout lines."""
    values = np.array(values, dtype=float)
    if values.size == 0 or np.all(values == 0):
        ax.axis("off")
        ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=9)
        ax.set_title(title, fontsize=10)
        return

    # Normalize to positive for sizes
    values = np.abs(values)
    total = values.sum()
    if total == 0:
        ax.axis("off")
        ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=9)
        ax.set_title(title, fontsize=10)
        return

    # Basic donut
    wedges, _ = ax.pie(
        values,
        labels=None,
        startangle=90,
        counterclock=False,
        wedgeprops=dict(width=0.4, edgecolor="white"),
    )

    # Callout labels around
    for i, w in enumerate(wedges):
        ang = (w.theta2 + w.theta1) / 2.0
        ang_rad = np.deg2rad(ang)
        x = np.cos(ang_rad)
        y = np.sin(ang_rad)
        # start at donut outer edge
        sx, sy = 0.7 * x, 0.7 * y
        ex, ey = 1.1 * np.sign(x), 1.1 * y
        ax.plot([sx, ex], [sy, ey], color="gray", linewidth=0.6)
        pct = values[i] / total * 100
        label = f"{labels[i]} ({pct:.1f}%)"
        ha = "left" if ex >= 0 else "right"
        ax.text(ex, ey, label, ha=ha, va="center", fontsize=7)

    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10)


def plot_monthly_barh(ax, df, amount_col, title):
    """Horizontal bar (x = amount, y = month label)."""
    if df is None or df.empty:
        ax.axis("off")
        ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=9)
        ax.set_title(title, fontsize=10)
        return

    y_labels = df["MonthLabel"]
    x_vals = df[amount_col]
    ax.barh(y_labels, x_vals)
    ax.set_xlabel("Amount ($)")
    ax.set_title(title, fontsize=10)
    ax.invert_yaxis()  # latest month at top
    for i, v in enumerate(x_vals):
        ax.text(v, i, f" {v:,.0f}", va="center", fontsize=7)


def make_donut_fig(report):
    totals = report["totals"]
    eq = report["eq_pnl_by_sym"]
    opt = report["opt_pnl_by_sym"]

    fig, axes = plt.subplots(1, 3, figsize=(9, 3))

    # Category donut (use absolute values of totals)
    cat_labels = list(totals.keys())
    cat_values = [abs(v) for v in totals.values()]
    plot_donut_with_callouts(axes[0], cat_labels, cat_values, "By Category")

    # Equity donut (all trades, abs PnL)
    if eq.empty:
        axes[1].axis("off")
        axes[1].text(0.5, 0.5, "No equity trades", ha="center", va="center", fontsize=9)
        axes[1].set_title("Equity PnL %", fontsize=10)
    else:
        labels = eq["Symbol"].tolist()
        values = eq["AbsPnL"].tolist()
        plot_donut_with_callouts(axes[1], labels, values, "Equity PnL %")

    # Options donut (all trades, abs PnL)
    if opt.empty:
        axes[2].axis("off")
        axes[2].text(0.5, 0.5, "No options trades", ha="center", va="center", fontsize=9)
        axes[2].set_title("Options PnL %", fontsize=10)
    else:
        labels = opt["Symbol"].tolist()
        values = opt["AbsPnL"].tolist()
        plot_donut_with_callouts(axes[2], labels, values, "Options PnL %")

    fig.tight_layout()
    return fig


def make_bar_fig(report):
    vm_monthly = report["vm_div_monthly"]
    income_monthly = report["income_monthly"]

    fig, axes = plt.subplots(1, 2, figsize=(9, 3))

    # VMFXX monthly
    if vm_monthly is None or vm_monthly.empty:
        axes[0].axis("off")
        axes[0].text(0.5, 0.5, "No VMFXX data", ha="center", va="center", fontsize=9)
        axes[0].set_title("VMFXX Monthly Divs", fontsize=10)
    else:
        plot_monthly_barh(axes[0], vm_monthly, "VMFXX Dividends ($)", "VMFXX Monthly Divs")

    # Other income monthly (company divs + MMF interest)
    if income_monthly is None or income_monthly.empty:
        axes[1].axis("off")
        axes[1].text(0.5, 0.5, "No income data", ha="center", va="center", fontsize=9)
        axes[1].set_title("Other Income Monthly", fontsize=10)
    else:
        plot_monthly_barh(axes[1], income_monthly, "Income ($)", "Dividends + Interest by Month")

    fig.tight_layout()
    return fig


# -----------------------------
# PDF Builder (Times New Roman, 10pt body, 12pt headers)
# -----------------------------
class EarningsPDF(FPDF):
    def header(self):
        # Title
        self.set_font("Times", "B", 14)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, "E*TRADE Earnings Report", ln=1, align="C")
        self.set_font("Times", "", 8)
        self.cell(0, 4, datetime.now().strftime("Generated on %Y-%m-%d %H:%M"), ln=1, align="C")
        self.ln(3)


def add_key_value(pdf: EarningsPDF, label: str, value: str):
    """
    Print 'Label ..... Value' with dotted leader across the available width.
    """
    pdf.set_font("Times", "", 10)
    pdf.set_text_color(0, 0, 0)

    usable = pdf.w - pdf.l_margin - pdf.r_margin
    label_text = f"{label} "
    value_text = str(value)

    label_w = pdf.get_string_width(label_text)
    value_w = pdf.get_string_width(value_text)
    dot_w = pdf.get_string_width(".") or 0.5

    dots_w = usable - label_w - value_w
    if dots_w < dot_w * 3:
        n_dots = 3
    else:
        n_dots = int(dots_w / dot_w)

    dots = "." * max(3, n_dots)
    line = f"{label_text}{dots} {value_text}"

    pdf.set_x(pdf.l_margin)
    pdf.cell(usable, 5, line, 0, 1, "L")


def add_table_header(pdf: EarningsPDF, cols, widths):
    pdf.set_font("Times", "B", 10)
    pdf.set_text_color(0, 0, 0)
    for col, w in zip(cols, widths):
        pdf.cell(w, 6, col, border="B", align="L")
    pdf.ln(6)


def add_table_row(pdf: EarningsPDF, vals, widths, aligns=None):
    pdf.set_font("Times", "", 10)
    pdf.set_text_color(0, 0, 0)
    if aligns is None:
        aligns = ["L"] * len(vals)
    for val, w, a in zip(vals, widths, aligns):
        pdf.cell(w, 5, val, border=0, align=a)
    pdf.ln(5)


def build_pdf(report: dict) -> bytes:
    pdf = EarningsPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    totals = report["totals"]
    total_earnings = report["total_earnings"]
    eq_pnl_by_sym = report["eq_pnl_by_sym"]
    opt_pnl_by_sym = report["opt_pnl_by_sym"]
    company_div_by_sym = report["company_div_by_sym"]
    vm_div_monthly = report["vm_div_monthly"]
    mmf_interest_credits = report["mmf_interest_credits"]

    # ---------- 1. Summary ----------
    pdf.set_font("Times", "B", 12)
    pdf.cell(0, 7, "1. Summary", ln=1)
    pdf.ln(1)

    add_key_value(pdf, "Total Earnings ($)", f"{total_earnings:,.2f}")
    for k, v in totals.items():
        add_key_value(pdf, k, f"{v:,.2f}")

    pdf.ln(2)

    # ---------- 2. Equity Realized PnL ----------
    pdf.set_font("Times", "B", 12)
    pdf.cell(0, 7, "2. Equity Realized PnL (Closed Positions)", ln=1)
    pdf.ln(1)

    if eq_pnl_by_sym.empty:
        pdf.set_font("Times", "", 10)
        pdf.cell(0, 5, "No closed equity positions.", ln=1)
    else:
        cols = ["Symbol / Name", "Buy - Sell Dates", "Net PnL ($)"]
        widths = [85, 60, 35]
        add_table_header(pdf, cols, widths)
        for _, row in eq_pnl_by_sym.iterrows():
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
            vals = [
                label,
                date_range,
                f"{row['Net PnL ($)']:,.2f}",
            ]
            aligns = ["L", "L", "R"]
            add_table_row(pdf, vals, widths, aligns)

    pdf.ln(2)

    # ---------- 3. Options PnL ----------
    pdf.set_font("Times", "B", 12)
    pdf.cell(0, 7, "3. Options PnL (Closed Positions Only)", ln=1)
    pdf.ln(1)

    if opt_pnl_by_sym.empty:
        pdf.set_font("Times", "", 10)
        pdf.cell(0, 5, "No closed option positions.", ln=1)
    else:
        cols = ["Contract / Underlying", "Open - Close Dates", "Net PnL ($)"]
        widths = [85, 60, 35]
        add_table_header(pdf, cols, widths)
        for _, row in opt_pnl_by_sym.iterrows():
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
            vals = [
                label,
                dr,
                f"{row['Net PnL ($)']:,.2f}",
            ]
            aligns = ["L", "L", "R"]
            add_table_row(pdf, vals, widths, aligns)

    pdf.ln(2)

    # ---------- 4. Company Dividends ----------
    pdf.set_font("Times", "B", 12)
    pdf.cell(0, 7, "4. Company Dividends (Equities)", ln=1)
    pdf.ln(1)

    if company_div_by_sym.empty:
        pdf.set_font("Times", "", 10)
        pdf.cell(0, 5, "No equity dividends.", ln=1)
    else:
        cols = ["Symbol / Name", "Div Date Range", "Dividends ($)"]
        widths = [85, 60, 35]
        add_table_header(pdf, cols, widths)
        for _, row in company_div_by_sym.iterrows():
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
            vals = [
                label,
                dr,
                f"{row['Dividends ($)']:,.2f}",
            ]
            aligns = ["L", "L", "R"]
            add_table_row(pdf, vals, widths, aligns)

    pdf.ln(2)

    # ---------- 5. VMFXX Monthly Dividends ----------
    pdf.set_font("Times", "B", 12)
    pdf.cell(0, 7, "5. VMFXX Monthly Dividends", ln=1)
    pdf.ln(1)

    if vm_div_monthly.empty:
        pdf.set_font("Times", "", 10)
        pdf.cell(0, 5, "No VMFXX dividend payments.", ln=1)
    else:
        cols = ["Month", "VMFXX Dividends ($)"]
        widths = [110, 35]
        add_table_header(pdf, cols, widths)
        for _, row in vm_div_monthly.iterrows():
            vals = [
                row["MonthLabel"],
                f"{row['VMFXX Dividends ($)']:,.2f}",
            ]
            aligns = ["L", "R"]
            add_table_row(pdf, vals, widths, aligns)

    pdf.ln(2)

    # ---------- 6. Other MMF / Bank Interest ----------
    pdf.set_font("Times", "B", 12)
    pdf.cell(0, 7, "6. Other MMF / Bank Interest", ln=1)
    pdf.ln(1)

    if mmf_interest_credits.empty:
        pdf.set_font("Times", "", 10)
        pdf.cell(0, 5, "No additional MMF/bank interest.", ln=1)
    else:
        cols = ["Date / Description", "Amount ($)"]
        widths = [110, 35]
        add_table_header(pdf, cols, widths)
        for _, row in mmf_interest_credits.iterrows():
            date_str = row.get("DateStr") or ""
            desc = row.get("Description") or ""
            left = f"{date_str}  {desc}"
            vals = [
                left[:80],
                f"{row['Amount']:,.2f}",
            ]
            aligns = ["L", "R"]
            add_table_row(pdf, vals, widths, aligns)

    # ---------- 7. Charts (new page) ----------
    donut_fig = make_donut_fig(report)
    bar_fig = make_bar_fig(report)

    # Donut page
    pdf.add_page()
    pdf.set_font("Times", "B", 12)
    pdf.cell(0, 7, "7. Donut Charts (Category & Trade % Breakdown)", ln=1)
    pdf.ln(2)
    buf1 = io.BytesIO()
    donut_fig.savefig(buf1, format="png", dpi=150, bbox_inches="tight")
    plt.close(donut_fig)
    buf1.seek(0)
    pdf.image(buf1, x=pdf.l_margin, y=None, w=pdf.w - pdf.l_margin - pdf.r_margin)

    # Bar page
    pdf.add_page()
    pdf.set_font("Times", "B", 12)
    pdf.cell(0, 7, "8. Monthly Income Bar Charts", ln=1)
    pdf.ln(2)
    buf2 = io.BytesIO()
    bar_fig.savefig(buf2, format="png", dpi=150, bbox_inches="tight")
    plt.close(bar_fig)
    buf2.seek(0)
    pdf.image(buf2, x=pdf.l_margin, y=None, w=pdf.w - pdf.l_margin - pdf.r_margin)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        pdf_bytes = out.encode("latin-1")
    else:
        pdf_bytes = bytes(out)
    return pdf_bytes


# -----------------------------
# Streamlit UI (Bloomberg Orange)
# -----------------------------
def main():
    st.set_page_config(page_title="E*TRADE Earnings Report Generator", layout="wide")

    st.markdown(
        """
        <style>
        :root {
            --primary-color: #ff7f0e;
        }
        body {
            background-color: #000000;
        }
        [data-testid="stAppViewContainer"] {
            background-color: #000000;
            color: #f3f3f3;
        }
        [data-testid="stSidebar"] {
            background-color: #111111;
        }
        .stMarkdown, .stDataFrame, .stMetric {
            color: #f3f3f3;
        }
        .stMetric label {
            color: #ffbf69 !important;
        }
        .stMetric div[data-testid="stMetricValue"] {
            color: #ffffff !important;
        }
        .stDownloadButton button, .stButton button {
            background-color: #ff7f0e;
            color: #000000;
            border-radius: 4px;
            border: 1px solid #ffbf69;
        }
        .stDownloadButton button:hover, .stButton button:hover {
            background-color: #ffa64d;
            color: #000000;
        }
        hr {
            border-color: #333333;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("E*TRADE Earnings Report Generator")
    st.caption("Upload your E*TRADE CSV → compute realized earnings → download a dated, structured PDF.")

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

    # ---- Detailed Tables (optional drill-down) ----
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

    # ---- Charts (Streamlit) ----
    st.subheader("Charts")

    donut_fig = make_donut_fig(report)
    st.pyplot(donut_fig)

    bar_fig = make_bar_fig(report)
    st.pyplot(bar_fig)

    st.markdown("---")

    # ---- One-click PDF Download ----
    pdf_bytes = build_pdf(report)

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

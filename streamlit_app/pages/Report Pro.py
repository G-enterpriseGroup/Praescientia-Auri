# app.py / Report Pro.py
# E*TRADE Earnings Analyzer + PDF Report with Donut Charts
# - Realized PnL only (equity + options)
# - Dividends (equities), VMFXX, other MMF/bank interest
# - Company names (via yfinance, 18 chars)
# - % contribution per item within each category
# - Donut hole pie charts (no bar charts) in Streamlit + PDF
# - PDF filename: "<last4> Report Pro <MinMon YY> - <MaxMon YY>.pdf"
# - PDF body font 10, headers 12, plus dates per line where useful
# - Summary lines use dotted leaders: "Label .... Value"

import io
import os
import re
import tempfile
from datetime import datetime
from functools import lru_cache

import pandas as pd
import streamlit as st
from fpdf import FPDF
import matplotlib.pyplot as plt
import plotly.express as px

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
    header_idx = None    # IMPORTANT: header_idx is used after the loop
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

                # If there is remaining > 0 and no inventory, ignore (no fake PnL).
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

    # ---- % contribution columns (for tables + donut charts) ----
    if eq_total != 0 and not eq_pnl_by_sym.empty:
        eq_pnl_by_sym["Pct of Equity PnL (%)"] = (
            eq_pnl_by_sym["Net PnL ($)"] / eq_total * 100.0
        )
    else:
        eq_pnl_by_sym["Pct of Equity PnL (%)"] = 0.0

    if opt_total != 0 and not opt_pnl_by_sym.empty:
        opt_pnl_by_sym["Pct of Options PnL (%)"] = (
            opt_pnl_by_sym["Net PnL ($)"] / opt_total * 100.0
        )
    else:
        opt_pnl_by_sym["Pct of Options PnL (%)"] = 0.0

    if company_div_total != 0 and not company_div_by_sym.empty:
        company_div_by_sym["Pct of Dividends (%)"] = (
            company_div_by_sym["Dividends ($)"] / company_div_total * 100.0
        )
    else:
        company_div_by_sym["Pct of Dividends (%)"] = 0.0

    if vm_div_total != 0 and not vm_div_monthly.empty:
        vm_div_monthly["Pct of VMFXX Divs (%)"] = (
            vm_div_monthly["VMFXX Dividends ($)"] / vm_div_total * 100.0
        )
    else:
        vm_div_monthly["Pct of VMFXX Divs (%)"] = 0.0

    if mmf_interest_total != 0 and not mmf_interest_credits.empty:
        mmf_interest_credits["Pct of MMF Int (%)"] = (
            mmf_interest_credits["Amount"] / mmf_interest_total * 100.0
        )
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


def add_donut_chart_to_pdf(pdf: EarningsPDF, labels, percentages, title: str):
    """
    Create a colorful donut chart (using % values) and embed it into the PDF.
    Negative/zero percentages are dropped for the chart.
    """
    if not labels or not percentages:
        return

    data = [(l, p) for l, p in zip(labels, percentages) if p > 0]
    if not data:
        return

    labels, percentages = zip(*data)

    fig, ax = plt.subplots(figsize=(3, 3), dpi=150)
    wedges, texts, autotexts = ax.pie(
        percentages,
        labels=None,
        autopct="%1.1f%%",
        pctdistance=0.75,
        startangle=90,
        wedgeprops=dict(width=0.35, edgecolor="white"),
    )
    ax.set(aspect="equal")
    ax.set_title(title, fontsize=8)
    ax.legend(
        wedges,
        labels,
        title="Legend",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
        fontsize=6,
    )
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.write(buf.getvalue())
    tmp.close()

    # Insert image; width ~80mm to fit nicely
    pdf.image(tmp.name, w=80)
    pdf.ln(4)

    os.unlink(tmp.name)


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
        cols = ["Symbol / Name", "Buy - Sell Dates", "Net PnL ($)", "% of Eq PnL"]
        widths = [70, 55, 30, 25]
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
            pct = row.get("Pct of Equity PnL (%)", 0.0)
            vals = [
                label,
                date_range,
                f"{row['Net PnL ($)']:,.2f}",
                f"{pct:,.1f}%",
            ]
            aligns = ["L", "L", "R", "R"]
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
        cols = ["Contract / Underlying", "Open - Close Dates", "Net PnL ($)", "% of Opt PnL"]
        widths = [70, 55, 30, 25]
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
            pct = row.get("Pct of Options PnL (%)", 0.0)
            vals = [
                label,
                dr,
                f"{row['Net PnL ($)']:,.2f}",
                f"{pct:,.1f}%",
            ]
            aligns = ["L", "L", "R", "R"]
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
        cols = ["Symbol / Name", "Div Date Range", "Dividends ($)", "% of Divs"]
        widths = [70, 55, 30, 25]
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
            pct = row.get("Pct of Dividends (%)", 0.0)
            vals = [
                label,
                dr,
                f"{row['Dividends ($)']:,.2f}",
                f"{pct:,.1f}%",
            ]
            aligns = ["L", "L", "R", "R"]
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
        cols = ["Month", "VMFXX Dividends ($)", "% of VMFXX"]
        widths = [90, 35, 25]
        add_table_header(pdf, cols, widths)
        for _, row in vm_div_monthly.iterrows():
            pct = row.get("Pct of VMFXX Divs (%)", 0.0)
            vals = [
                str(row["Month"]),
                f"{row['VMFXX Dividends ($)']:,.2f}",
                f"{pct:,.1f}%",
            ]
            aligns = ["L", "R", "R"]
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
        cols = ["Date / Description", "Amount ($)", "% of MMF Int"]
        widths = [95, 30, 25]
        add_table_header(pdf, cols, widths)
        for _, row in mmf_interest_credits.iterrows():
            date_str = row.get("DateStr") or ""
            desc = row.get("Description") or ""
            left = f"{date_str}  {desc}"
            pct = row.get("Pct of MMF Int (%)", 0.0)
            vals = [
                left[:70],
                f"{row['Amount']:,.2f}",
                f"{pct:,.1f}%",
            ]
            aligns = ["L", "R", "R"]
            add_table_row(pdf, vals, widths, aligns)

    # ---------- 7. Donut Charts ----------
    pdf.add_page()
    pdf.set_font("Times", "B", 12)
    pdf.cell(0, 7, "7. Donut Charts (Category % Breakdown)", ln=1)
    pdf.ln(2)

    # Overall category donut (using |Amount| so it doesn't blow up on negatives)
    cat_labels = list(totals.keys())
    cat_vals = [abs(v) for v in totals.values()]
    add_donut_chart_to_pdf(pdf, cat_labels, cat_vals, "Categories (Abs Amount Share)")

    # Equity donut
    if not eq_pnl_by_sym.empty:
        labels = eq_pnl_by_sym["Symbol"].tolist()
        pct = eq_pnl_by_sym["Pct of Equity PnL (%)"].clip(lower=0).tolist()
        add_donut_chart_to_pdf(pdf, labels, pct, "Equity PnL % (Winners Only)")

    # Options donut
    if not opt_pnl_by_sym.empty:
        labels = opt_pnl_by_sym["Symbol"].tolist()
        pct = opt_pnl_by_sym["Pct of Options PnL (%)"].clip(lower=0).tolist()
        add_donut_chart_to_pdf(pdf, labels, pct, "Options PnL % (Winners Only)")

    # Dividends donut
    if not company_div_by_sym.empty:
        labels = company_div_by_sym["Symbol"].tolist()
        pct = company_div_by_sym["Pct of Dividends (%)"].clip(lower=0).tolist()
        add_donut_chart_to_pdf(pdf, labels, pct, "Company Dividends %")

    # VMFXX donut
    if not vm_div_monthly.empty:
        labels = vm_div_monthly["Month"].tolist()
        pct = vm_div_monthly["Pct of VMFXX Divs (%)"].clip(lower=0).tolist()
        add_donut_chart_to_pdf(pdf, labels, pct, "VMFXX Monthly Divs %")

    # MMF interest donut
    if not mmf_interest_credits.empty:
        labels = mmf_interest_credits["DateStr"].tolist()
        pct = mmf_interest_credits["Pct of MMF Int (%)"].clip(lower=0).tolist()
        add_donut_chart_to_pdf(pdf, labels, pct, "MMF / Bank Interest % by Date")

    out = pdf.output(dest="S")
    if isinstance(out, str):
        pdf_bytes = out.encode("latin-1")
    else:
        pdf_bytes = bytes(out)
    return pdf_bytes


# -----------------------------
# Streamlit donut chart helper
# -----------------------------
def donut_chart(df: pd.DataFrame, names_col: str, values_col: str, title: str):
    """
    Streamlit donut (hole) pie chart using Plotly.
    Drops non-positive values.
    """
    if df is None or df.empty or names_col not in df or values_col not in df:
        return
    data = df[df[values_col] > 0].copy()
    if data.empty:
        return

    fig = px.pie(
        data,
        names=names_col,
        values=values_col,
        hole=0.5,
        title=title,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# Streamlit UI (Bloomberg Orange + donut charts)
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
        st.metric(
            "Other MMF/Bank Interest ($)",
            f"{report['totals']['Other MMF/Bank Interest ($)']:,.2f}",
        )

    # Category donut (using absolute amounts)
    st.markdown("### Category Donut (Abs Amount Share)")
    cat_df = pd.DataFrame(
        {
            "Category": list(report["totals"].keys()),
            "Amount": list(report["totals"].values()),
        }
    )
    cat_df["AbsAmount"] = cat_df["Amount"].abs()
    donut_chart(cat_df, "Category", "AbsAmount", "Categories (Abs Amount Share)")

    st.markdown("---")

    # ---- Detailed Tables (optional drill-down) ----
    st.subheader("Details")

    # Equity
    with st.expander("Equity Realized PnL (Closed Positions)", expanded=True):
        st.dataframe(report["eq_pnl_by_sym"], use_container_width=True)
        eq_df = report["eq_pnl_by_sym"]
        if not eq_df.empty:
            eq_pos = eq_df[eq_df["Pct of Equity PnL (%)"] > 0].copy()
            if not eq_pos.empty:
                eq_pos["Label"] = eq_pos["Symbol"]
                st.markdown("**Equity PnL Donut (Winners Only)**")
                donut_chart(eq_pos, "Label", "Pct of Equity PnL (%)", "Equity PnL % (Winners Only)")

    # Options
    with st.expander("Options PnL (Closed Positions Only)", expanded=False):
        st.dataframe(report["opt_pnl_by_sym"], use_container_width=True)
        opt_df = report["opt_pnl_by_sym"]
        if not opt_df.empty:
            opt_pos = opt_df[opt_df["Pct of Options PnL (%)"] > 0].copy()
            if not opt_pos.empty:
                opt_pos["Label"] = opt_pos["Symbol"]
                st.markdown("**Options PnL Donut (Winners Only)**")
                donut_chart(opt_pos, "Label", "Pct of Options PnL (%)", "Options PnL % (Winners Only)")

    # Dividends
    with st.expander("Company Dividends by Symbol", expanded=False):
        st.dataframe(report["company_div_by_sym"], use_container_width=True)
        div_df = report["company_div_by_sym"]
        if not div_df.empty:
            div_pos = div_df[div_df["Pct of Dividends (%)"] > 0].copy()
            if not div_pos.empty:
                div_pos["Label"] = div_pos["Symbol"]
                st.markdown("**Company Dividends Donut**")
                donut_chart(div_pos, "Label", "Pct of Dividends (%)", "Company Dividends %")

    # VMFXX
    with st.expander("VMFXX Monthly Dividend Breakdown", expanded=False):
        st.dataframe(report["vm_div_monthly"], use_container_width=True)
        vm_df = report["vm_div_monthly"]
        if not vm_df.empty:
            vm_pos = vm_df[vm_df["Pct of VMFXX Divs (%)"] > 0].copy()
            if not vm_pos.empty:
                st.markdown("**VMFXX Monthly Dividends Donut**")
                donut_chart(vm_pos, "Month", "Pct of VMFXX Divs (%)", "VMFXX Monthly Divs %")

    with st.expander("Raw VMFXX Dividend Rows", expanded=False):
        st.dataframe(report["vm_div_credits"], use_container_width=True)

    # MMF interest
    with st.expander("Other MMF / Bank Interest Rows", expanded=False):
        st.dataframe(report["mmf_interest_credits"], use_container_width=True)
        mmf_df = report["mmf_interest_credits"]
        if not mmf_df.empty:
            mmf_pos = mmf_df[mmf_df["Pct of MMF Int (%)"] > 0].copy()
            if not mmf_pos.empty:
                st.markdown("**MMF / Bank Interest Donut**")
                donut_chart(mmf_pos, "DateStr", "Pct of MMF Int (%)", "MMF / Bank Interest % by Date")

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

# app.py / Report Pro.py
# E*TRADE Earnings Analyzer + 1-Page PDF Report (Structured Layout + Company Names)
#
# PDF filename pattern:
# "<last4> Report Pro <MinMon YY> - <MaxMon YY>.pdf"
#  - last4 from "For Account:" line (top of CSV)
#  - date range from min/max TransactionDate (column A), formatted as Mon YY

import io
import re
from datetime import datetime
from functools import lru_cache

import pandas as pd
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
    where start_label/end_label are like "Jan 25" based on the
    min/max values in the TransactionDate column (column A).
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

    # --- Find account last4 from "For Account:" line above header ---
    account_last4 = None
    for i in range(header_idx):
        line = lines[i]
        if "For Account" in line:
            # Grab last 4 consecutive digits
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
        # Mon YY format, e.g. Jan 25
        start_label = dmin.strftime("%b %y")
        end_label = dmax.strftime("%b %y")

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
# Core Calculations (Realized Only)
# -----------------------------
def compute_report(df: pd.DataFrame):
    """
    Compute:
    - Equity realized PnL (closed positions)
    - Options PnL (closed positions only)
    - Company dividends
    - VMFXX dividends
    - Other MMF/bank interest
    """

    df = df.copy()

    # ---- VMFXX Dividends (using Description) ----
    vm_mask = df["Description"].str.contains(
        "VANGUARD FEDERAL MMKT INV DIV PAYMENT", case=False, na=False
    )
    vm_div = df[vm_mask]
    vm_div_credits = vm_div[vm_div["Amount"] > 0]
    vm_div_total = float(vm_div_credits["Amount"].sum())

    # Monthly breakdown for VMFXX
    vm_div_monthly = (
        vm_div_credits.assign(
            Month=lambda x: x["TransactionDate"].dt.to_period("M").astype(str)
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
    mmf_interest_credits = mmf_interest[mmf_interest["Amount"] > 0]
    mmf_interest_total = float(mmf_interest_credits["Amount"].sum())

    # ---- Company Dividends (EQ only) ----
    div = df[df["TransactionType"].isin(["Dividend", "Qualified Dividend"])]
    company_div = div[(div["SecurityType"] == "EQ")]
    company_div_total = float(company_div["Amount"].sum())
    company_div_by_sym = (
        company_div.groupby("Symbol")["Amount"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={"Amount": "Dividends ($)"})
    )
    company_div_by_sym["Name"] = company_div_by_sym["Symbol"].apply(lookup_company_name)

    # ---- Equity Realized PnL (Closed positions only) ----
    sold_syms = df[df["TransactionType"] == "Sold"]["Symbol"].unique().tolist()
    eq_trades = df[
        (df["SecurityType"] == "EQ")
        & (df["Symbol"].isin(sold_syms))
        & (df["TransactionType"].isin(["Bought", "Sold"]))
    ]
    eq_pnl_by_sym = (
        eq_trades.groupby("Symbol")["Amount"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={"Amount": "Net PnL ($)"})
    )
    eq_pnl_by_sym["Name"] = eq_pnl_by_sym["Symbol"].apply(lookup_company_name)
    eq_total = float(eq_pnl_by_sym["Net PnL ($)"].sum()) if not eq_pnl_by_sym.empty else 0.0

    # ---- Options PnL (Closed positions only) ----
    opt = df[df["SecurityType"] == "OPTN"]
    closed_types = ["Sold To Close", "Option Exercised", "Option Expired"]
    allowed_types = ["Bought To Open", "Sold To Close", "Option Exercised", "Option Expired"]
    closed_symbols = opt[opt["TransactionType"].isin(closed_types)]["Symbol"].unique().tolist()
    opt_closed = opt[
        (opt["Symbol"].isin(closed_symbols))
        & (opt["TransactionType"].isin(allowed_types))
    ]
    opt_pnl_by_sym = (
        opt_closed.groupby("Symbol")["Amount"]
        .sum()
        .reset_index()
        .rename(columns={"Amount": "Net PnL ($)"})
    )

    def _opt_name(sym: str) -> str:
        if not isinstance(sym, str):
            return ""
        base = sym.split()[0]
        return lookup_company_name(base)

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
# PDF Builder (Times New Roman, Structured Tables)
# -----------------------------
class EarningsPDF(FPDF):
    def header(self):
        self.set_font("Times", "B", 18)
        self.set_text_color(0, 0, 0)  # black
        self.cell(0, 10, "E*TRADE Earnings Report", ln=1, align="C")
        self.set_font("Times", "", 10)
        self.cell(0, 6, datetime.now().strftime("Generated on %Y-%m-%d %H:%M"), ln=1, align="C")
        self.ln(4)


def add_key_value(pdf: EarningsPDF, label: str, value: str):
    pdf.set_font("Times", "", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(90, 6, label, 0, 0, "L")
    pdf.cell(0, 6, value, 0, 1, "R")


def add_table_header(pdf: EarningsPDF, col1: str, col2: str, w1: int = 110, w2: int = 40):
    pdf.set_font("Times", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(w1, 7, col1, border="B", align="L")
    pdf.cell(w2, 7, col2, border="B", ln=1, align="R")


def add_table_row(pdf: EarningsPDF, left: str, right: str, w1: int = 110, w2: int = 40):
    pdf.set_font("Times", "", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(w1, 6, left, border=0, align="L")
    pdf.cell(w2, 6, right, border=0, ln=1, align="R")


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

    # Section 1: Summary
    pdf.set_font("Times", "B", 18)
    pdf.cell(0, 9, "1. Summary", ln=1)
    pdf.ln(1)

    add_key_value(pdf, "Total Earnings ($)", f"{total_earnings:,.2f}")
    for k, v in totals.items():
        add_key_value(pdf, k, f"{v:,.2f}")

    pdf.ln(3)

    # Section 2: Equity Realized PnL (Closed)
    pdf.set_font("Times", "B", 18)
    pdf.cell(0, 9, "2. Equity Realized PnL (Closed Positions)", ln=1)
    pdf.ln(1)
    if eq_pnl_by_sym.empty:
        pdf.set_font("Times", "", 12)
        pdf.cell(0, 6, "No closed equity positions.", ln=1)
    else:
        add_table_header(pdf, "Symbol / Name", "Net PnL ($)")
        for _, row in eq_pnl_by_sym.iterrows():
            name = row.get("Name", "") or ""
            label = str(row["Symbol"])
            if name:
                label = f"{label}  {name}"
            add_table_row(pdf, label, f"{row['Net PnL ($)']:,.2f}")

    pdf.ln(3)

    # Section 3: Options PnL (Closed Only)
    pdf.set_font("Times", "B", 18)
    pdf.cell(0, 9, "3. Options PnL (Closed Positions Only)", ln=1)
    pdf.ln(1)
    if opt_pnl_by_sym.empty:
        pdf.set_font("Times", "", 12)
        pdf.cell(0, 6, "No closed option positions.", ln=1)
    else:
        add_table_header(pdf, "Contract / Underlying", "Net PnL ($)")
        for _, row in opt_pnl_by_sym.iterrows():
            name = row.get("Name", "") or ""
            label = str(row["Symbol"])
            if name:
                label = f"{label}  {name}"
            add_table_row(pdf, label, f"{row['Net PnL ($)']:,.2f}")

    pdf.ln(3)

    # Section 4: Company Dividends (Equities)
    pdf.set_font("Times", "B", 18)
    pdf.cell(0, 9, "4. Company Dividends (Equities)", ln=1)
    pdf.ln(1)
    if company_div_by_sym.empty:
        pdf.set_font("Times", "", 12)
        pdf.cell(0, 6, "No equity dividends.", ln=1)
    else:
        add_table_header(pdf, "Symbol / Name", "Dividends ($)")
        for _, row in company_div_by_sym.iterrows():
            name = row.get("Name", "") or ""
            label = str(row["Symbol"])
            if name:
                label = f"{label}  {name}"
            add_table_row(pdf, label, f"{row['Dividends ($)']:,.2f}")

    pdf.ln(3)

    # Section 5: VMFXX Monthly Dividends
    pdf.set_font("Times", "B", 18)
    pdf.cell(0, 9, "5. VMFXX Monthly Dividends", ln=1)
    pdf.ln(1)
    if vm_div_monthly.empty:
        pdf.set_font("Times", "", 12)
        pdf.cell(0, 6, "No VMFXX dividend payments.", ln=1)
    else:
        add_table_header(pdf, "Month", "VMFXX Dividends ($)")
        for _, row in vm_div_monthly.iterrows():
            add_table_row(pdf, str(row["Month"]), f"{row['VMFXX Dividends ($)']:,.2f}")

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
    st.caption("Upload your E*TRADE CSV → compute realized earnings → download a structured 1-page PDF.")

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

    with st.expander("Raw VMFXX Dividend Rows", expanded=False):
        st.dataframe(report["vm_div_credits"], use_container_width=True)

    with st.expander("Other MMF / Bank Interest Rows", expanded=False):
        st.dataframe(report["mmf_interest_credits"], use_container_width=True)

    st.markdown("---")

    # ---- One-click PDF Download ----
    pdf_bytes = build_pdf(report)

    # Filename based on account_last4 and min/max TransactionDate (Mon YY)
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

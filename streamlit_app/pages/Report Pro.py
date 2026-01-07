# app.py / Report Pro.py
# E*TRADE 2025 Earnings Analyzer + 1-Page PDF Report
#
# What it does:
# - Upload E*TRADE CSV (with "For Account:" header)
# - Computes:
#     * Equity realized PnL (closed positions only)
#     * Options PnL (closed positions only – requires a sell/expire/exercise)
#     * Company dividends (equities)
#     * VMFXX dividends via "VANGUARD FEDERAL MMKT INV DIV PAYMENT"
#     * Other MMF/bank interest (e.g., MSPBNA)
# - Streamlit UI (Bloomberg-style dark/orange)
# - One-click PDF download:
#   1. Summary
#   2. Equity Realized PnL (Closed Positions)
#   3. Options PnL (Closed Positions Only)
#   4. Company Dividends (Equities)
#   5. VMFXX Monthly Dividends
#
# PDF formatting:
# - Font: Times New Roman (Times) black
# - Body: size 12
# - Section headers: size 18, bold
# - Designed to fit on a single page for your 2025 data.

import io
from datetime import datetime

import pandas as pd
import streamlit as st
from fpdf import FPDF


# -----------------------------
# Helpers: Load & Clean CSV
# -----------------------------
def load_etrade_csv(uploaded_file) -> pd.DataFrame | None:
    """
    Detect the correct header row (E*TRADE has 'For Account:' above)
    and return a clean DataFrame.
    """
    content_bytes = uploaded_file.getvalue()
    text = content_bytes.decode("utf-8", errors="ignore")
    lines = text.splitlines()

    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith("TransactionDate,TransactionType"):
            header_idx = i
            break

    if header_idx is None:
        st.error("Could not find the 'TransactionDate,TransactionType' header in the CSV.")
        return None

    data_io = io.StringIO("\n".join(lines[header_idx:]))
    df = pd.read_csv(data_io)

    # Basic cleaning
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    df["Commission"] = pd.to_numeric(df["Commission"], errors="coerce")
    df["Description"] = df["Description"].astype(str)

    # Parse dates
    df["TransactionDate"] = pd.to_datetime(
        df["TransactionDate"],
        format="%m/%d/%y",
        errors="coerce"
    )

    return df


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

    # ---- Equity Realized PnL (Closed positions only) ----
    # Logic:
    # - Take symbols that have at least one 'Sold'
    # - For those symbols, sum all Bought + Sold Amount for EQ
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
    eq_total = float(eq_pnl_by_sym["Net PnL ($)"].sum()) if not eq_pnl_by_sym.empty else 0.0

    # ---- Options PnL (Closed positions only) ----
    # Logic:
    # - Consider only symbols where we see a "closing" leg:
    #   Sold To Close / Option Exercised / Option Expired
    # - For those, include cash from:
    #   Bought To Open / Sold To Close / Option Exercised / Option Expired
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
# PDF Builder (Times New Roman, 1 Page)
# -----------------------------
class EarningsPDF(FPDF):
    def header(self):
        # Title header
        self.set_font("Times", "B", 18)
        self.set_text_color(0, 0, 0)  # black
        self.cell(0, 10, "E*TRADE Earnings Report", ln=1, align="C")
        self.set_font("Times", "", 10)
        self.cell(0, 6, datetime.now().strftime("Generated on %Y-%m-%d %H:%M"), ln=1, align="C")
        self.ln(4)


def add_key_value(pdf: EarningsPDF, label: str, value: str):
    pdf.set_font("Times", "", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(80, 6, label, 0, 0, "L")
    pdf.cell(0, 6, value, 0, 1, "R")


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

    # To help keep it on 1 page for your data:
    eq_pnl_by_sym = eq_pnl_by_sym.copy()
    opt_pnl_by_sym = opt_pnl_by_sym.copy()
    company_div_by_sym = company_div_by_sym.copy()

    # Section 1: Summary
    pdf.set_font("Times", "B", 18)
    pdf.cell(0, 10, "1. Summary", ln=1)
    pdf.ln(2)

    add_key_value(pdf, "Total Earnings ($)", f"{total_earnings:,.2f}")
    for k, v in totals.items():
        add_key_value(pdf, k, f"{v:,.2f}")

    pdf.ln(4)

    # Section 2: Equity Realized PnL (Closed)
    pdf.set_font("Times", "B", 18)
    pdf.cell(0, 10, "2. Equity Realized PnL (Closed Positions)", ln=1)
    pdf.ln(2)
    pdf.set_font("Times", "", 12)

    if eq_pnl_by_sym.empty:
        pdf.cell(0, 6, "No closed equity positions.", ln=1)
    else:
        # print all rows (your 2025 file is small enough to fit)
        for _, row in eq_pnl_by_sym.iterrows():
            pdf.cell(
                0, 6,
                f"{row['Symbol']}: {row['Net PnL ($)']:,.2f}",
                ln=1,
            )

    pdf.ln(4)

    # Section 3: Options PnL (Closed Only)
    pdf.set_font("Times", "B", 18)
    pdf.cell(0, 10, "3. Options PnL (Closed Positions Only)", ln=1)
    pdf.ln(2)
    pdf.set_font("Times", "", 12)

    if opt_pnl_by_sym.empty:
        pdf.cell(0, 6, "No closed option positions.", ln=1)
    else:
        for _, row in opt_pnl_by_sym.iterrows():
            pdf.cell(
                0, 6,
                f"{row['Symbol']}: {row['Net PnL ($)']:,.2f}",
                ln=1,
            )

    pdf.ln(4)

    # Section 4: Company Dividends (Equities)
    pdf.set_font("Times", "B", 18)
    pdf.cell(0, 10, "4. Company Dividends (Equities)", ln=1)
    pdf.ln(2)
    pdf.set_font("Times", "", 12)

    if company_div_by_sym.empty:
        pdf.cell(0, 6, "No equity dividends.", ln=1)
    else:
        for _, row in company_div_by_sym.iterrows():
            pdf.cell(
                0, 6,
                f"{row['Symbol']}: {row['Dividends ($)']:,.2f}",
                ln=1,
            )

    pdf.ln(4)

    # Section 5: VMFXX Monthly Dividends
    pdf.set_font("Times", "B", 18)
    pdf.cell(0, 10, "5. VMFXX Monthly Dividends", ln=1)
    pdf.ln(2)
    pdf.set_font("Times", "", 12)

    if vm_div_monthly.empty:
        pdf.cell(0, 6, "No VMFXX dividend payments.", ln=1)
    else:
        for _, row in vm_div_monthly.iterrows():
            pdf.cell(
                0, 6,
                f"{row['Month']}: {row['VMFXX Dividends ($)']:,.2f}",
                ln=1,
            )

    # Output as bytes for Streamlit
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

    # Bloomberg-style orange/dark CSS (UI only, PDF is pure black text)
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
    st.caption("Upload your E*TRADE CSV → compute realized earnings → download a 1-page PDF.")

    uploaded_file = st.file_uploader("Upload E*TRADE CSV", type=["csv"])

    if not uploaded_file:
        return

    df = load_etrade_csv(uploaded_file)
    if df is None:
        return

    report = compute_report(df)

    # ---- Top Summary ----
    st.subheader("Summary")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Earnings ($)", f"{report['total_earnings']:,.2f}")
    with col2:
        st.metric("Equity Realized PnL ($)", f"{report['totals']['Equity Realized PnL ($)']:,.2f}")
    with col3:
        st.metric("Options Net PnL ($)", f"{report['totals']['Options Net PnL ($)']:,.2f}")

    col4, col5 = st.columns(2)
    with col4:
        st.metric("Company Dividends ($)", f"{report['totals']['Company Dividends ($)']:,.2f}")
    with col5:
        st.metric("VMFXX Dividends ($)", f"{report['totals']['VMFXX Dividends ($)']:,.2f}")

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
    st.download_button(
        label="Download PDF Earnings Report",
        data=pdf_bytes,
        file_name="etrade_earnings_report.pdf",
        mime="application/pdf",
    )


if __name__ == "__main__":
    main()

# app.py
# E*TRADE 2025 Earnings Analyzer + PDF Report
#
# Features:
# - Upload E*TRADE CSV (with "For Account:" header)
# - Auto-detect header row
# - Compute:
#     * Equity realized PnL (per symbol + total)
#     * Options PnL (per contract + total)
#     * Company dividends (per symbol + total)
#     * VMFXX dividends via "VANGUARD FEDERAL MMKT INV DIV PAYMENT"
#     * Other MMF/bank interest (e.g., MSPBNA)
# - Show results in Streamlit
# - Generate a professional PDF summary to download

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
    df["TransactionDate"] = pd.to_datetime(df["TransactionDate"], format="%m/%d/%y", errors="coerce")

    return df


# -----------------------------
# Core Calculations
# -----------------------------
def compute_report(df: pd.DataFrame):
    """
    Compute:
    - Equity realized PnL
    - Options PnL
    - Company dividends
    - VMFXX dividends (via description)
    - Other MMF/bank interest
    Also returns detailed tables for display and PDF.
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
        vm_div_credits.assign(Month=lambda x: x["TransactionDate"].dt.to_period("M").astype(str))
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

    # ---- Equity Realized PnL (Closed positions) ----
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

    # ---- Options PnL ----
    opt = df[df["SecurityType"] == "OPTN"]
    opt_pnl_by_sym = (
        opt[opt["TransactionType"].isin(["Bought To Open", "Sold To Close"])]
        .groupby("Symbol")["Amount"]
        .sum()
        .reset_index()
        .rename(columns={"Amount": "Net PnL ($)"})
    )
    opt_total = float(opt_pnl_by_sym["Net PnL ($)"].sum()) if not opt_pnl_by_sym.empty else 0.0

    # ---- Totals ----
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
# PDF Builder
# -----------------------------
class EarningsPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 8, "E*TRADE Earnings Report", ln=1, align="C")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, datetime.now().strftime("Generated on %Y-%m-%d %H:%M"), ln=1, align="C")
        self.ln(3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)


def add_key_value(pdf: EarningsPDF, label: str, value: str):
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(70, 6, label, 0, 0, "L")
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

    # ---- Summary Section ----
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, "1. Summary", ln=1)
    pdf.ln(2)

    add_key_value(pdf, "Total Earnings ($)", f"{total_earnings:,.2f}")
    for k, v in totals.items():
        add_key_value(pdf, k, f"{v:,.2f}")

    pdf.ln(5)

    # ---- Equity Realized PnL ----
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, "2. Equity Realized PnL (Closed Positions)", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(1)

    if eq_pnl_by_sym.empty:
        pdf.cell(0, 6, "No closed equity positions detected.", ln=1)
    else:
        for _, row in eq_pnl_by_sym.iterrows():
            pdf.cell(0, 6, f"{row['Symbol']}: {row['Net PnL ($)']:,.2f}", ln=1)

    pdf.ln(5)

    # ---- Options PnL ----
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, "3. Options PnL", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(1)

    if opt_pnl_by_sym.empty:
        pdf.cell(0, 6, "No option trades detected.", ln=1)
    else:
        for _, row in opt_pnl_by_sym.iterrows():
            pdf.cell(0, 6, f"{row['Symbol']}: {row['Net PnL ($)']:,.2f}", ln=1)

    pdf.ln(5)

    # ---- Dividends (Companies) ----
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, "4. Company Dividends (Equities)", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(1)

    if company_div_by_sym.empty:
        pdf.cell(0, 6, "No equity dividends detected.", ln=1)
    else:
        for _, row in company_div_by_sym.iterrows():
            pdf.cell(0, 6, f"{row['Symbol']}: {row['Dividends ($)']:,.2f}", ln=1)

    pdf.ln(5)

    # ---- VMFXX Monthly Dividends ----
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, "5. VMFXX Monthly Dividends", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(1)

    if vm_div_monthly.empty:
        pdf.cell(0, 6, "No VMFXX dividend payments detected.", ln=1)
    else:
        for _, row in vm_div_monthly.iterrows():
            pdf.cell(0, 6, f"{row['Month']}: {row['VMFXX Dividends ($)']:,.2f}", ln=1)

    # Output as bytes (handle both str and bytes/bytearray from fpdf2)
    out = pdf.output(dest="S")
    if isinstance(out, str):
        pdf_bytes = out.encode("latin-1")
    else:
        pdf_bytes = bytes(out)

    return pdf_bytes


# -----------------------------
# Streamlit UI
# -----------------------------
def main():
    st.set_page_config(page_title="E*TRADE Earnings Report Generator", layout="wide")

    st.title("E*TRADE Earnings Report Generator")
    st.write("Upload your E*TRADE transaction CSV to analyze trades, dividends, and generate a PDF.")

    uploaded_file = st.file_uploader("Upload E*TRADE CSV", type=["csv"])

    if not uploaded_file:
        return

    df = load_etrade_csv(uploaded_file)
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

    c4, c5 = st.columns(2)
    with c4:
        st.metric("Company Dividends ($)", f"{report['totals']['Company Dividends ($)']:,.2f}")
    with c5:
        vmf = report["totals"]["VMFXX Dividends ($)"]
        st.metric("VMFXX Dividends ($)", f"{vmf:,.2f}")

    st.markdown("---")

    # ---- Detailed Tables (Expandable) ----
    with st.expander("Equity Realized PnL by Symbol", expanded=True):
        st.dataframe(report["eq_pnl_by_sym"], use_container_width=True)

    with st.expander("Options PnL by Contract", expanded=False):
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

    # ---- Generate PDF ----
    if st.button("Generate PDF Report"):
        pdf_bytes = build_pdf(report)
        st.download_button(
            label="Download PDF Earnings Report",
            data=pdf_bytes,
            file_name="etrade_earnings_report.pdf",
            mime="application/pdf",
        )


if __name__ == "__main__":
    main()

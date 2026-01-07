# app.py
# E*TRADE Earnings Analyzer + PDF Report (Realized vs Unrealized)
#
# Features:
# - Upload E*TRADE CSV (with "For Account:" header)
# - Auto-detect header row
# - Compute:
#     * Realized equity PnL (per symbol, FIFO lots)
#     * Unrealized equity PnL (open positions, using yfinance last price)
#     * Average holding period (days) for sold symbols
#     * Options PnL (net cash, by contract)
#     * Company dividends (per symbol + total)
#     * VMFXX dividends via "VANGUARD FEDERAL MMKT INV DIV PAYMENT"
#     * Other MMF/bank interest (e.g., MSPBNA)
# - Bloomberg-style orange/dark UI
# - One-click PDF download (no separate "generate" step)

import io
from datetime import datetime

import pandas as pd
import streamlit as st
from fpdf import FPDF
import yfinance as yf


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
# Equity Lot Engine (Realized + Unrealized)
# -----------------------------
def compute_equity_lots(df: pd.DataFrame):
    """
    FIFO lot-based realized and unrealized PnL for share equities (SecurityType == 'EQ').

    Returns:
      - realized_df: Symbol, Realized_PnL, Realized_Qty, Avg_Days_Held
      - unrealized_df: Symbol, Quantity, Cost_Basis, Cost_per_share,
                       Current_Price, Market_Value, Unrealized_PnL
      - total_realized (float)
    """

    # Filter only equity trades (shares)
    trades = df[
        (df["SecurityType"] == "EQ")
        & (df["TransactionType"].isin(["Bought", "Sold"]))
    ].copy()

    if trades.empty:
        cols_real = ["Symbol", "Realized_PnL", "Realized_Qty", "Avg_Days_Held"]
        cols_unrl = [
            "Symbol",
            "Quantity",
            "Cost_Basis",
            "Cost_per_share",
            "Current_Price",
            "Market_Value",
            "Unrealized_PnL",
        ]
        return (
            pd.DataFrame(columns=cols_real),
            pd.DataFrame(columns=cols_unrl),
            0.0,
        )

    trades.sort_values(["Symbol", "TransactionDate"], inplace=True)

    lots = {}  # symbol -> list of dicts: {qty, cost_per_share, date}
    realized_pnl = {}
    realized_qty = {}
    holding_days_weighted = {}  # symbol -> sum(q * days)
    holding_qty_sum = {}  # symbol -> total closed qty for holding days

    for _, row in trades.iterrows():
        sym = row["Symbol"]
        ttype = row["TransactionType"]
        qty = row["Quantity"]
        amt = row["Amount"]
        date = row["TransactionDate"]

        if sym not in lots:
            lots[sym] = []
        if sym not in realized_pnl:
            realized_pnl[sym] = 0.0
            realized_qty[sym] = 0.0
            holding_days_weighted[sym] = 0.0
            holding_qty_sum[sym] = 0.0

        if ttype == "Bought":
            # Amount is negative (cash out), so cost_per_share is -Amount / qty
            if qty and amt is not None:
                cost_ps = -amt / qty if qty != 0 else 0.0
                lots[sym].append({"qty": qty, "cost_ps": cost_ps, "date": date})
        elif ttype == "Sold":
            # Amount is positive (cash in)
            if qty and amt is not None and qty != 0:
                sell_ps = amt / qty
                sell_qty = qty
                while sell_qty > 0 and lots[sym]:
                    lot = lots[sym][0]
                    lot_qty = lot["qty"]
                    take = min(sell_qty, lot_qty)

                    # Realized PnL
                    pnl_per_share = sell_ps - lot["cost_ps"]
                    realized_pnl[sym] += pnl_per_share * take
                    realized_qty[sym] += take

                    # Holding days (for this portion)
                    if pd.notna(lot["date"]) and pd.notna(date):
                        days_held = (date - lot["date"]).days
                        holding_days_weighted[sym] += take * days_held
                        holding_qty_sum[sym] += take

                    lot["qty"] -= take
                    sell_qty -= take

                    if lot["qty"] <= 0:
                        lots[sym].pop(0)

    # Build realized DataFrame
    realized_rows = []
    for sym in realized_pnl:
        if realized_qty[sym] > 0:
            avg_days = (
                holding_days_weighted[sym] / holding_qty_sum[sym]
                if holding_qty_sum[sym] > 0
                else 0.0
            )
            realized_rows.append(
                {
                    "Symbol": sym,
                    "Realized_PnL": round(realized_pnl[sym], 2),
                    "Realized_Qty": realized_qty[sym],
                    "Avg_Days_Held": round(avg_days, 1),
                }
            )

    realized_df = pd.DataFrame(realized_rows).sort_values(
        "Realized_PnL", ascending=False
    )

    # Build unrealized (open lots)
    unreal_rows = []
    for sym, lot_list in lots.items():
        if not lot_list:
            continue
        total_qty = sum(l["qty"] for l in lot_list)
        if total_qty <= 0:
            continue
        cost_basis = sum(l["qty"] * l["cost_ps"] for l in lot_list)
        cost_ps = cost_basis / total_qty if total_qty != 0 else 0.0
        unreal_rows.append(
            {
                "Symbol": sym,
                "Quantity": total_qty,
                "Cost_Basis": cost_basis,
                "Cost_per_share": cost_ps,
            }
        )

    unrealized_df = pd.DataFrame(unreal_rows)
    if unrealized_df.empty:
        unrealized_df = pd.DataFrame(
            columns=[
                "Symbol",
                "Quantity",
                "Cost_Basis",
                "Cost_per_share",
                "Current_Price",
                "Market_Value",
                "Unrealized_PnL",
            ]
        )
    else:
        # Fetch current prices via yfinance (for symbols that look like regular tickers)
        prices = {}
        for sym in unrealized_df["Symbol"]:
            # Skip option-like strings with spaces
            if " " in sym:
                prices[sym] = None
                continue
            try:
                data = yf.Ticker(sym).history(period="1d")
                if not data.empty:
                    prices[sym] = float(data["Close"].iloc[-1])
                else:
                    prices[sym] = None
            except Exception:
                prices[sym] = None

        unrealized_df["Current_Price"] = unrealized_df["Symbol"].map(prices)
        unrealized_df["Market_Value"] = (
            unrealized_df["Quantity"] * unrealized_df["Current_Price"]
        )
        unrealized_df["Unrealized_PnL"] = (
            unrealized_df["Market_Value"] - unrealized_df["Cost_Basis"]
        )

    total_realized = float(realized_df["Realized_PnL"].sum()) if not realized_df.empty else 0.0

    return realized_df, unrealized_df, total_realized


# -----------------------------
# Core Calculations
# -----------------------------
def compute_report(df: pd.DataFrame):
    """
    Compute:
    - Realized equity PnL + holding period
    - Unrealized equity PnL
    - Options PnL
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

    # ---- Equity Realized + Unrealized (lot-based) ----
    realized_df, unrealized_df, realized_total = compute_equity_lots(df)

    # ---- Options PnL (net cash) ----
    opt = df[df["SecurityType"] == "OPTN"]
    opt_pnl_by_sym = (
        opt[opt["TransactionType"].isin(["Bought To Open", "Sold To Close", "Option Exercised", "Option Expired"])]
        .groupby("Symbol")["Amount"]
        .sum()
        .reset_index()
        .rename(columns={"Amount": "Net_PnL"})
    )
    options_total = float(opt_pnl_by_sym["Net_PnL"].sum()) if not opt_pnl_by_sym.empty else 0.0

    # ---- Totals (realized earnings) ----
    totals = {
        "Realized Equity PnL ($)": round(realized_total, 2),
        "Realized Options PnL ($)": round(options_total, 2),
        "Company Dividends ($)": round(company_div_total, 2),
        "VMFXX Dividends ($)": round(vm_div_total, 2),
        "Other MMF/Bank Interest ($)": round(mmf_interest_total, 2),
    }
    total_realized_earnings = round(sum(totals.values()), 2)

    # Unrealized summary
    unreal_total_pnl = (
        float(unrealized_df["Unrealized_PnL"].sum())
        if ("Unrealized_PnL" in unrealized_df.columns and not unrealized_df.empty)
        else 0.0
    )

    return {
        "totals": totals,
        "total_realized_earnings": total_realized_earnings,
        "unreal_total_pnl": unreal_total_pnl,
        "realized_df": realized_df,
        "unrealized_df": unrealized_df,
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
        self.set_text_color(255, 127, 0)  # orange title
        self.cell(0, 8, "E*TRADE Earnings Report", ln=1, align="C")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(200, 200, 200)
        self.cell(0, 5, datetime.now().strftime("Generated on %Y-%m-%d %H:%M"), ln=1, align="C")
        self.ln(3)
        self.set_draw_color(255, 127, 0)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)


def add_key_value(pdf: EarningsPDF, label: str, value: str):
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(230, 230, 230)
    pdf.cell(80, 6, label, 0, 0, "L")
    pdf.cell(0, 6, value, 0, 1, "R")


def build_pdf(report: dict) -> bytes:
    pdf = EarningsPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    totals = report["totals"]
    total_realized_earnings = report["total_realized_earnings"]
    unreal_total_pnl = report["unreal_total_pnl"]
    realized_df = report["realized_df"]
    unrealized_df = report["unrealized_df"]
    opt_pnl_by_sym = report["opt_pnl_by_sym"]
    company_div_by_sym = report["company_div_by_sym"]
    vm_div_monthly = report["vm_div_monthly"]

    # ---- Summary Section ----
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(255, 127, 0)
    pdf.cell(0, 7, "1. Summary", ln=1)
    pdf.ln(2)

    pdf.set_text_color(230, 230, 230)
    add_key_value(pdf, "Total Realized Earnings ($)", f"{total_realized_earnings:,.2f}")
    for k, v in totals.items():
        add_key_value(pdf, k, f"{v:,.2f}")
    add_key_value(pdf, "Unrealized Equity PnL ($)", f"{unreal_total_pnl:,.2f}")

    pdf.ln(5)

    # ---- Realized Equity ----
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(255, 127, 0)
    pdf.cell(0, 7, "2. Realized Equity PnL (FIFO, Closed)", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(230, 230, 230)
    pdf.ln(1)

    if realized_df.empty:
        pdf.cell(0, 6, "No realized equity PnL detected.", ln=1)
    else:
        for _, row in realized_df.iterrows():
            pdf.cell(
                0,
                6,
                f"{row['Symbol']}: PnL {row['Realized_PnL']:,.2f} | Qty {row['Realized_Qty']:.0f} | Avg Days Held {row['Avg_Days_Held']}",
                ln=1,
            )

    pdf.ln(5)

    # ---- Unrealized Equity ----
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(255, 127, 0)
    pdf.cell(0, 7, "3. Unrealized Equity PnL (Open Positions)", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(230, 230, 230)
    pdf.ln(1)

    if unrealized_df.empty:
        pdf.cell(0, 6, "No open equity positions detected.", ln=1)
    else:
        for _, row in unrealized_df.iterrows():
            symbol = row["Symbol"]
            qty = row["Quantity"]
            cost = row["Cost_Basis"]
            mv = row.get("Market_Value", float("nan"))
            upnl = row.get("Unrealized_PnL", float("nan"))
            pdf.cell(
                0,
                6,
                f"{symbol}: Qty {qty:.0f} | Cost {cost:,.2f} | MV {mv:,.2f} | U-PnL {upnl:,.2f}",
                ln=1,
            )

    pdf.ln(5)

    # ---- Options PnL ----
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(255, 127, 0)
    pdf.cell(0, 7, "4. Options PnL (Net Cash)", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(230, 230, 230)
    pdf.ln(1)

    if opt_pnl_by_sym.empty:
        pdf.cell(0, 6, "No option trades detected.", ln=1)
    else:
        for _, row in opt_pnl_by_sym.iterrows():
            pdf.cell(0, 6, f"{row['Symbol']}: {row['Net_PnL']:,.2f}", ln=1)

    pdf.ln(5)

    # ---- Company Dividends ----
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(255, 127, 0)
    pdf.cell(0, 7, "5. Company Dividends (Equities)", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(230, 230, 230)
    pdf.ln(1)

    if company_div_by_sym.empty:
        pdf.cell(0, 6, "No equity dividends detected.", ln=1)
    else:
        for _, row in company_div_by_sym.iterrows():
            pdf.cell(0, 6, f"{row['Symbol']}: {row['Dividends ($)']:,.2f}", ln=1)

    pdf.ln(5)

    # ---- VMFXX Monthly Dividends ----
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(255, 127, 0)
    pdf.cell(0, 7, "6. VMFXX Monthly Dividends", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(230, 230, 230)
    pdf.ln(1)

    if vm_div_monthly.empty:
        pdf.cell(0, 6, "No VMFXX dividend payments detected.", ln=1)
    else:
        for _, row in vm_div_monthly.iterrows():
            pdf.cell(0, 6, f"{row['Month']}: {row['VMFXX Dividends ($)']:,.2f}", ln=1)

    # Output as bytes
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

    # Bloomberg-style orange/dark CSS
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
    st.caption("Upload your E*TRADE CSV → see realized + unrealized PnL → download a PDF report.")

    uploaded_file = st.file_uploader("Upload E*TRADE CSV", type=["csv"])

    if not uploaded_file:
        return

    df = load_etrade_csv(uploaded_file)
    if df is None:
        return

    report = compute_report(df)

    # ---- Top Summary ----
    st.subheader("Summary (Realized vs Unrealized)")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Realized Earnings ($)", f"{report['total_realized_earnings']:,.2f}")
    with col2:
        st.metric("Realized Equity PnL ($)", f"{report['totals']['Realized Equity PnL ($)']:,.2f}")
    with col3:
        st.metric("Realized Options PnL ($)", f"{report['totals']['Realized Options PnL ($)']:,.2f}")

    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("Company Dividends ($)", f"{report['totals']['Company Dividends ($)']:,.2f}")
    with col5:
        st.metric("VMFXX Dividends ($)", f"{report['totals']['VMFXX Dividends ($)']:,.2f}")
    with col6:
        st.metric("Unrealized Equity PnL ($)", f"{report['unreal_total_pnl']:,.2f}")

    st.markdown("---")

    # ---- Detailed Tables ----
    st.subheader("Details")

    c_real, c_unreal = st.columns(2)
    with c_real:
        st.markdown("**Realized Equity (PnL + Days Held)**")
        st.dataframe(report["realized_df"], use_container_width=True)
    with c_unreal:
        st.markdown("**Unrealized Equity (Open Positions)**")
        st.dataframe(report["unrealized_df"], use_container_width=True)

    st.markdown("**Options PnL by Contract**")
    st.dataframe(report["opt_pnl_by_sym"], use_container_width=True)

    st.markdown("**Company Dividends by Symbol**")
    st.dataframe(report["company_div_by_sym"], use_container_width=True)

    exp1, exp2 = st.columns(2)
    with exp1:
        st.markdown("**VMFXX Monthly Dividend Breakdown**")
        st.dataframe(report["vm_div_monthly"], use_container_width=True)
    with exp2:
        st.markdown("**Other MMF / Bank Interest Rows**")
        st.dataframe(report["mmf_interest_credits"], use_container_width=True)

    st.markdown("---")
    st.caption(
        "Unrealized PnL uses latest prices from Yahoo Finance via yfinance. "
        "If price lookup fails, Market Value / U-PnL may be blank."
    )

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

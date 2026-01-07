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

    if trades.empty:
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

    if realized_rows:
        realized_df = pd.DataFrame(realized_rows).sort_values(
            "Realized_PnL", ascending=False
        )
    else:
        realized_df = pd.DataFrame(columns=cols_real)

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

    if unreal_rows:
        unrealized_df = pd.DataFrame(unreal_rows)
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
    else:
        unrealized_df = pd.DataFrame(columns=cols_unrl)

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
        "

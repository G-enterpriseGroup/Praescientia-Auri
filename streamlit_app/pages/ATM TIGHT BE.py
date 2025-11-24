import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

# =========================
# PAGE SETUP + THEME (BLOOMBERG STYLE)
# =========================
st.set_page_config(page_title="ATM Breakeven Finder", layout="wide", page_icon="📊")

BLOOM_ORANGE = "#ff9f1c"

st.markdown(
    f"""
    <style>
    html, body, [class*="stApp"] {{
        background-color: #050608;
        color: #f4f4f4;
        font-family: "Menlo", "Consolas", "Roboto Mono", monospace;
    }}
    .main {{
        background-color: #050608;
    }}
    .metric-label {{
        font-size: 0.75rem;
        color: #9fa4ad;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}
    .metric-value {{
        font-size: 1.3rem;
        font-weight: 700;
        color: {BLOOM_ORANGE};
    }}
    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
    }}
    thead tr th {{
        background-color: #11141a !important;
        color: {BLOOM_ORANGE} !important;
        border-bottom: 1px solid #333 !important;
    }}
    tbody tr td {{
        color: #f4f4f4 !important;
        border-color: #222 !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 ATM Breakeven Finder")
st.caption("Bloomberg-style: paired call/put strangles near the money with visual breakeven bands.")


# =========================
# CORE HELPERS
# =========================
def _get_spot(ticker: str) -> float:
    tk = yf.Ticker(ticker)
    hist = tk.history(period="1d")
    if hist.empty:
        raise ValueError(f"No price history for {ticker}")
    return float(hist["Close"].iloc[-1])


def _get_chain(ticker: str, expiration: str):
    tk = yf.Ticker(ticker)
    chain = tk.option_chain(expiration)
    return chain.calls.copy(), chain.puts.copy()


# =========================
# RAW OPTIONS: CALLS / PUTS SEPARATELY (TIGHTEST DIST)
# =========================
def compute_tight_breakevens_for_exp(
    ticker: str,
    expiration: str,
    atm_window: float = 0.05,
    top_n: int = 40,
) -> pd.DataFrame:
    spot = _get_spot(ticker)
    calls_df, puts_df = _get_chain(ticker, expiration)

    rows = []
    today = pd.Timestamp.today().normalize()
    exp_date = pd.to_datetime(expiration)
    dte = (exp_date - today).days

    def process_side(df: pd.DataFrame, side: str):
        nonlocal rows
        if df.empty:
            return

        df["mid"] = (df["bid"].fillna(0) + df["ask"].fillna(0)) / 2
        df.loc[df["mid"] <= 0, "mid"] = df["lastPrice"]

        df = df[df["strike"] > 0]
        df = df[(df["strike"] - spot).abs() / spot <= atm_window]
        if df.empty:
            return

        if side == "CALL":
            df["breakeven"] = df["strike"] + df["mid"]
        else:
            df["breakeven"] = df["strike"] - df["mid"]

        df["distance"] = (df["breakeven"] - spot).abs()

        out = pd.DataFrame({
            "TCK": ticker,
            "SD": side,
            "EXP": expiration,
            "DTE": dte,
            "STK": df["strike"],
            "MID": df["mid"],
            "BE": df["breakeven"],
            "DIST": df["distance"],
            "VOL": df["volume"],
            "OI": df["openInterest"],
            "IV": df["impliedVolatility"],
            "SPOT": spot,
        })

        rows.extend(out.to_dict("records"))

    process_side(calls_df, "CALL")
    process_side(puts_df, "PUT")

    if not rows:
        raise ValueError("No ATM options found with current filters.")

    result = pd.DataFrame(rows)
    result = result.sort_values(["DIST", "DTE", "STK"]).reset_index(drop=True)
    return result.head(top_n)


# =========================
# STRANGLE VIEW: PAIR CALLS & PUTS BY STRIKE
# =========================
def compute_paired_strangles(
    ticker: str,
    expiration: str,
    atm_window: float = 0.05,
    top_n: int = 40,
) -> pd.DataFrame:
    """
    For one ticker + expiration:
    - Get calls & puts
    - Filter near-the-money
    - Compute breakeven & distance for each
    - Pair by strike
    - Return one row per strike with Call+Put metrics
    """
    spot = _get_spot(ticker)
    calls_df, puts_df = _get_chain(ticker, expiration)

    today = pd.Timestamp.today().normalize()
    exp_date = pd.to_datetime(expiration)
    dte = (exp_date - today).days

    # ---- Calls ----
    if not calls_df.empty:
        calls_df["mid"] = (calls_df["bid"].fillna(0) + calls_df["ask"].fillna(0)) / 2
        calls_df.loc[calls_df["mid"] <= 0, "mid"] = calls_df["lastPrice"]
        calls_df = calls_df[calls_df["strike"] > 0]
        calls_df = calls_df[(calls_df["strike"] - spot).abs() / spot <= atm_window]
        if not calls_df.empty:
            calls_df["breakeven"] = calls_df["strike"] + calls_df["mid"]
            calls_df["distance"] = (calls_df["breakeven"] - spot).abs()
            calls_df = calls_df.rename(columns={
                "strike": "STK",
                "mid": "MC",
                "breakeven": "BC",
                "distance": "DC",
                "volume": "VOL_C",
                "openInterest": "OI_C",
                "impliedVolatility": "IV_C",
            })[["STK", "MC", "BC", "DC", "VOL_C", "OI_C", "IV_C"]]

    # ---- Puts ----
    if not puts_df.empty:
        puts_df["mid"] = (puts_df["bid"].fillna(0) + puts_df["ask"].fillna(0)) / 2
        puts_df.loc[puts_df["mid"] <= 0, "mid"] = puts_df["lastPrice"]
        puts_df = puts_df[puts_df["strike"] > 0]
        puts_df = puts_df[(puts_df["strike"] - spot).abs() / spot <= atm_window]
        if not puts_df.empty:
            puts_df["breakeven"] = puts_df["strike"] - puts_df["mid"]
            puts_df["distance"] = (puts_df["breakeven"] - spot).abs()
            puts_df = puts_df.rename(columns={
                "strike": "STK",
                "mid": "MP",
                "breakeven": "BP",
                "distance": "DP",
                "volume": "VOL_P",
                "openInterest": "OI_P",
                "impliedVolatility": "IV_P",
            })[["STK", "MP", "BP", "DP", "VOL_P", "OI_P", "IV_P"]]

    if 'calls_df' not in locals() or calls_df.empty:
        calls_df = pd.DataFrame(columns=["STK", "MC", "BC", "DC", "VOL_C", "OI_C", "IV_C"])
    if 'puts_df' not in locals() or puts_df.empty:
        puts_df = pd.DataFrame(columns=["STK", "MP", "BP", "DP", "VOL_P", "OI_P", "IV_P"])

    merged = pd.merge(calls_df, puts_df, on="STK", how="outer")

    if merged.empty:
        raise ValueError("No ATM call/put pairs found with current filters.")

    merged["DC"] = merged["DC"].fillna(0.0)
    merged["DP"] = merged["DP"].fillna(0.0)
    merged["CD"] = merged["DC"] + merged["DP"]

    merged["EXP"] = expiration
    merged["DTE"] = dte
    merged["TCK"] = ticker
    merged["SPOT"] = spot

    merged = merged[[
        "TCK", "EXP", "DTE", "STK",
        "MC", "BC", "DC",
        "MP", "BP", "DP",
        "CD",
        "VOL_C", "OI_C", "IV_C",
        "VOL_P", "OI_P", "IV_P",
        "SPOT",
    ]]

    merged = merged.sort_values(["CD", "STK"]).reset_index(drop=True)
    return merged.head(top_n)


# =========================
# SIDEBAR CONTROLS
# =========================
st.sidebar.header("Settings")

ticker = st.sidebar.text_input("Ticker", value="SPY").upper().strip()

atm_pct = st.sidebar.slider(
    "ATM window (±% from spot)",
    min_value=1.0,
    max_value=15.0,
    value=5.0,
    step=1.0,
)
atm_window = atm_pct / 100.0

top_n = st.sidebar.slider(
    "Rows to show (top N)",
    min_value=5,
    max_value=60,
    value=30,
    step=5,
)


# =========================
# MAIN LOGIC
# =========================
if not ticker:
    st.info("Enter a ticker on the left to begin.")
else:
    try:
        tk = yf.Ticker(ticker)
        expirations = tk.options

        if not expirations:
            st.error(f"No options listed for {ticker}.")
        else:
            exp = st.sidebar.selectbox(
                "Expiration",
                options=expirations,
                index=0,
                key="exp_select",
            )

            paired_df = compute_paired_strangles(
                ticker=ticker,
                expiration=exp,
                atm_window=atm_window,
                top_n=top_n,
            )
            raw_df = compute_tight_breakevens_for_exp(
                ticker=ticker,
                expiration=exp,
                atm_window=atm_window,
                top_n=top_n,
            )

            spot_val = paired_df["SPOT"].iloc[0]
            dte_val = paired_df["DTE"].iloc[0]

            # Top metrics row
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown('<div class="metric-label">TICKER</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-value">{ticker}</div>', unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="metric-label">SPOT</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-value">${spot_val:,.2f}</div>', unsafe_allow_html=True)
            with c3:
                st.markdown('<div class="metric-label">EXP / DTE</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="metric-value">{exp} · {dte_val}d</div>',
                    unsafe_allow_html=True
                )

            tab1, tab2 = st.tabs(["Strangle View (Paired)", "Raw Options"])

            # ---- TAB 1: STRANGLE (PAIRED) ----
            with tab1:
                st.subheader("Paired Calls & Puts by Strike (Strangle Bands)")

                viz_df = paired_df.copy()

                # Band: BP → BC
                band = (
                    alt.Chart(viz_df)
                    .mark_rule(stroke=BLOOM_ORANGE, strokeWidth=3, opacity=0.9)
                    .encode(
                        x=alt.X("BP:Q", title="Price"),
                        x2="BC:Q",
                        y=alt.Y("STK:O", title="Strike"),
                        tooltip=[
                            alt.Tooltip("STK:Q", title="Strike"),
                            alt.Tooltip("BP:Q", title="Put BE"),
                            alt.Tooltip("BC:Q", title="Call BE"),
                            alt.Tooltip("CD:Q", title="CD (DC+DP)"),
                            alt.Tooltip("MC:Q", title="Call mid (MC)"),
                            alt.Tooltip("MP:Q", title="Put mid (MP)"),
                        ],
                    )
                )

                # Spot line
                spot_line = (
                    alt.Chart(pd.DataFrame({"SPOT": [spot_val]}))
                    .mark_rule(stroke="#ffffff", strokeWidth=2, strokeDash=[4, 4])
                    .encode(x="SPOT:Q")
                )

                # Label endpoints: Put BE (left) and Call BE (right)
                end_points = pd.concat(
                    [
                        viz_df.assign(Price=viz_df["BP"], Type="Put BE"),
                        viz_df.assign(Price=viz_df["BC"], Type="Call BE"),
                    ],
                    ignore_index=True,
                )

                points = (
                    alt.Chart(end_points)
                    .mark_point(size=70)
                    .encode(
                        x="Price:Q",
                        y="STK:O",
                        color=alt.Color("Type:N", title="", scale=alt.Scale(range=["#00d1ff", "#ff4b4b"])),
                        shape="Type:N",
                        tooltip=[
                            alt.Tooltip("STK:Q", title="Strike"),
                            alt.Tooltip("Type:N", title="Side"),
                            alt.Tooltip("Price:Q", title="Breakeven"),
                        ],
                    )
                )

                chart = (band + spot_line + points).properties(
                    height=400,
                    title="Strangle Breakeven Bands vs Spot",
                )

                st.altair_chart(chart, use_container_width=True)

                st.caption(
                    "Orange band = strangle range from BP (Put breakeven) to BC (Call breakeven). "
                    "Blue point = Put BE, red point = Call BE. "
                    "White dashed line = current spot. Narrower bands & smaller CD = tighter strangles."
                )

                # Table under the visual
                disp = paired_df[[
                    "STK",
                    "MC", "BC", "DC",
                    "MP", "BP", "DP",
                    "CD",
                    "VOL_C", "OI_C", "IV_C",
                    "VOL_P", "OI_P", "IV_P",
                ]].copy()

                styled = (
                    disp.style
                    .format({
                        "STK": "{:,.2f}",
                        "MC": "{:,.2f}",
                        "BC": "{:,.2f}",
                        "DC": "{:,.2f}",
                        "MP": "{:,.2f}",
                        "BP": "{:,.2f}",
                        "DP": "{:,.2f}",
                        "CD": "{:,.2f}",
                        "VOL_C": "{:,.0f}",
                        "OI_C": "{:,.0f}",
                        "IV_C": "{:.2%}",
                        "VOL_P": "{:,.0f}",
                        "OI_P": "{:,.0f}",
                        "IV_P": "{:.2%}",
                    })
                )

                st.dataframe(styled, use_container_width=True)
                st.caption(
                    "MC/MP = Call/Put mid; BC/BP = Call/Put breakeven; "
                    "DC/DP = |breakeven − spot|; CD = DC + DP (combined distance)."
                )

            # ---- TAB 2: RAW OPTIONS ----
            with tab2:
                st.subheader("Individual Options (Calls & Puts)")
                disp_raw = raw_df[[
                    "SD", "STK", "MID", "BE", "DIST", "VOL", "OI", "IV",
                ]].copy()

                styled_raw = (
                    disp_raw.style
                    .format({
                        "STK": "{:,.2f}",
                        "MID": "{:,.2f}",
                        "BE": "{:,.2f}",
                        "DIST": "{:,.2f}",
                        "VOL": "{:,.0f}",
                        "OI": "{:,.0f}",
                        "IV": "{:.2%}",
                    })
                )

                st.dataframe(styled_raw, use_container_width=True)
                st.caption("Sorted by DIST = |breakeven − spot|. Smaller DIST = tighter breakeven.")

    except Exception as e:
        st.error(f"Error: {e}")

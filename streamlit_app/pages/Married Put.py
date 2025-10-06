import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from streamlit.components.v1 import html as components_html

# ---------- Page config ----------
st.set_page_config(page_title="Married Put", layout="wide")

# ---------- Helpers ----------
def set_tab_title(title: str):
    st.markdown(
        f"""
        <script>
            document.title = {repr(title)};
        </script>
        """,
        unsafe_allow_html=True,
    )

def calculate_max_loss(stock_price, options_table):
    """
    Max Loss = (Strike × 100) - (Cost of Stock + Cost of Put)
    Uses both Ask and Last prices.
    """
    n = 100  # contract size

    # Ask path
    options_table["CPA"] = options_table["ASK"] * n                              # Cost Put Ask
    options_table["MLA"] = (options_table["STK"] * n) - (stock_price * n + options_table["CPA"])   # Max Loss Ask
    options_table["MLC-A"] = options_table.apply(
        lambda r: f"({r['STK']:.2f} × {n}) - ({stock_price * n:.2f} + {r['CPA']:.2f})", axis=1
    )

    # Last path
    options_table["CPL"] = options_table["LP"] * n                               # Cost Put Last
    options_table["MLL"] = (options_table["STK"] * n) - (stock_price * n + options_table["CPL"])   # Max Loss Last
    options_table["MLC-L"] = options_table.apply(
        lambda r: f"({r['STK']:.2f} × {n}) - ({stock_price * n:.2f} + {r['CPL']:.2f})", axis=1
    )
    return options_table

def calculate_days_left(expiration_date: str) -> int:
    today = datetime.today().date()
    return (datetime.strptime(expiration_date, "%Y-%m-%d").date() - today).days

def display_put_options_all_dates(ticker_symbol: str, stock_price: float):
    try:
        tkr = yf.Ticker(ticker_symbol)
        dates = tkr.options
        if not dates:
            st.error(f"No options data for {ticker_symbol}.")
            return

        all_data = pd.DataFrame()

        for exp in dates:
            dleft = calculate_days_left(exp)
            st.subheader(f"Expiration: {exp}  ({dleft} days left)")

            chain = tkr.option_chain(exp)
            puts = chain.puts
            if puts.empty:
                st.warning(f"No puts for {exp}.")
                continue

            tbl = puts[["contractSymbol", "strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"]].copy()
            tbl.columns = ["CN", "STK", "LP", "BID", "ASK", "VOL", "OI", "IV"]
            tbl["EXP"] = exp

            tbl = calculate_max_loss(stock_price, tbl)
            all_data = pd.concat([all_data, tbl], ignore_index=True)

            st.dataframe(
                tbl.style.highlight_max(subset=["MLA", "MLL"]),
                use_container_width=True
            )

        if not all_data.empty:
            st.download_button(
                "Download All Expirations (CSV)",
                all_data.to_csv(index=False),
                file_name=f"{ticker_symbol}_puts.csv",
                mime="text/csv",
            )
        else:
            st.warning(f"No put options to display or download for {ticker_symbol}.")
    except Exception as e:
        st.error(f"An error occurred: {e}")

# ---------- UI ----------
st.title("Options Analysis • Married Put (Max Loss)")

# Read ticker from query params (supports the Paste button below)
try:
    qp = st.query_params  # new API
    qp_ticker = qp.get("ticker", "")
    if isinstance(qp_ticker, list):  # older behavior safeguard
        qp_ticker = qp_ticker[0] if qp_ticker else ""
except Exception:
    qp_ticker = ""

row = st.columns([3, 1])

with row[0]:
    ticker_symbol = st.text_input("Ticker", value=str(qp_ticker).upper().strip(), key="ticker_input").upper().strip()

with row[1]:
    # One-click Paste from clipboard → writes ?ticker=... and reloads
    components_html(
        """
        <button id="pasteBtn" style="margin-top:28px;width:100%;padding:0.6rem;border-radius:10px;border:1px solid #444;cursor:pointer">
          📋 Paste from Clipboard
        </button>
        <script>
        const btn = document.getElementById('pasteBtn');
        btn.onclick = async () => {
          try {
            const txt = (await navigator.clipboard.readText() || '').trim().toUpperCase();
            if (!txt) return;
            const p = window.parent || window;
            const url = new URL(p.location.href);
            url.searchParams.set('ticker', txt);
            p.history.replaceState({}, '', url.toString());
            p.location.reload();
          } catch(e) {
            alert('Clipboard not accessible. Use Cmd/Ctrl+V.');
          }
        };
        </script>
        """,
        height=60,
    )

# Dynamic tab title
tab_title = f"{ticker_symbol} · Married Put" if ticker_symbol else "Married Put"
set_tab_title(tab_title)

# Company name
if ticker_symbol:
    try:
        tkr = yf.Ticker(ticker_symbol)
        long_name = tkr.info.get("longName", "N/A")
        st.write(f"**Company Name:** {long_name}")
    except Exception as e:
        st.warning(f"Unable to fetch company name: {e}")
else:
    st.warning("Enter a valid ticker.")
    st.stop()

# Current price default
try:
    tkr = yf.Ticker(ticker_symbol)
    hist = tkr.history(period="1d")
    current_price = float(hist["Close"].iloc[-1]) if not hist.empty else 0.0
except Exception:
    current_price = 0.0

stock_price = st.number_input(
    "Purchase price per share",
    min_value=0.0,
    value=float(current_price),
    step=0.01,
    help="Default = latest close."
)
if stock_price <= 0:
    st.warning("Enter a valid stock price.")
    st.stop()

if st.button("Fetch Options Data"):
    display_put_options_all_dates(ticker_symbol, stock_price)

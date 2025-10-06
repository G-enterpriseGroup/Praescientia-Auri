import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from streamlit.components.v1 import html as components_html

# ---------------- Page config ----------------
st.set_page_config(page_title="Married Put", layout="wide")

# ---------------- Helpers ----------------
def calculate_max_loss(stock_price, options_table):
    n = 100  # contract size
    options_table["CPA"] = options_table["ASK"] * n
    options_table["MLA"] = (options_table["STK"] * n) - (stock_price * n + options_table["CPA"])
    options_table["MLC-A"] = options_table.apply(
        lambda r: f"({r['STK']:.2f} × {n}) - ({stock_price * n:.2f} + {r['CPA']:.2f})", axis=1
    )
    options_table["CPL"] = options_table["LP"] * n
    options_table["MLL"] = (options_table["STK"] * n) - (stock_price * n + options_table["CPL"])
    options_table["MLC-L"] = options_table.apply(
        lambda r: f"({r['STK']:.2f} × {n}) - ({stock_price * n:.2f} + {r['CPL']:.2f})", axis=1
    )
    return options_table

def days_left(exp: str) -> int:
    return (datetime.strptime(exp, "%Y-%m-%d").date() - datetime.today().date()).days

def display_put_options_all_dates(ticker_symbol: str, stock_price: float):
    try:
        tkr = yf.Ticker(ticker_symbol)
        dates = tkr.options
        if not dates:
            st.error(f"No options data for {ticker_symbol}.")
            return
        all_data = pd.DataFrame()
        for exp in dates:
            st.subheader(f"Expiration: {exp}  ({days_left(exp)} days left)")
            puts = tkr.option_chain(exp).puts
            if puts.empty:
                st.warning(f"No puts for {exp}.")
                continue
            tbl = puts[["contractSymbol","strike","lastPrice","bid","ask","volume","openInterest","impliedVolatility"]].copy()
            tbl.columns = ["CN","STK","LP","BID","ASK","VOL","OI","IV"]
            tbl["EXP"] = exp
            tbl = calculate_max_loss(stock_price, tbl)
            all_data = pd.concat([all_data, tbl], ignore_index=True)
            st.dataframe(tbl.style.highlight_max(subset=["MLA","MLL"]), use_container_width=True)
        if not all_data.empty:
            st.download_button(
                "Download All Expirations (CSV)",
                all_data.to_csv(index=False),
                file_name=f"{ticker_symbol}_puts.csv",
                mime="text/csv",
            )
    except Exception as e:
        st.error(f"An error occurred: {e}")

# ---------------- UI ----------------
st.title("Options Analysis • Married Put (Max Loss)")

# Ticker input + seamless paste button
cols = st.columns([3,1])
with cols[0]:
    ticker_symbol = st.text_input("Ticker", key="ticker_input", value=st.session_state.get("ticker_input","")).upper().strip()
with cols[1]:
    components_html(
        """
        <button id="pasteBtn" style="margin-top:28px;width:100%;padding:.6rem;border-radius:10px;border:1px solid #444;cursor:pointer">
          📋 Paste
        </button>
        <script>
          const findTickerInput = () => {
            // find input by its label text "Ticker"
            const lbl = Array.from(parent.document.querySelectorAll('label'))
              .find(el => el.textContent.trim() === 'Ticker');
            return lbl ? lbl.parentElement.querySelector('input') : null;
          };
          // live tab title sync
          const input = findTickerInput();
          const setTitle = v => parent.document.title = (v ? v.toUpperCase() + ' · Married Put' : 'Married Put');
          if (input) {
            setTitle(input.value);
            input.addEventListener('input', e => setTitle(e.target.value));
          }
          // paste button behavior (no page reload)
          document.getElementById('pasteBtn').onclick = async () => {
            try {
              const txt = (await navigator.clipboard.readText() || '').trim().toUpperCase();
              const inp = findTickerInput();
              if (!inp || !txt) return;
              // set value and dispatch input event so Streamlit updates seamlessly
              const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
              nativeInputValueSetter.call(inp, txt);
              inp.dispatchEvent(new Event('input', { bubbles: true }));
              setTitle(txt);
            } catch (e) {
              alert('Clipboard blocked. Use Cmd/Ctrl+V.');
            }
          };
        </script>
        """,
        height=60,
    )

# Company name
if not ticker_symbol:
    st.warning("Enter a valid ticker.")
    st.stop()

try:
    tkr = yf.Ticker(ticker_symbol)
    long_name = tkr.info.get("longName", "N/A")
    st.write(f"**Company Name:** {long_name}")
except Exception as e:
    st.warning(f"Unable to fetch company name: {e}")

# Default to latest close
try:
    hist = yf.Ticker(ticker_symbol).history(period="1d")
    current_price = float(hist["Close"].iloc[-1]) if not hist.empty else 0.0
except Exception:
    current_price = 0.0

stock_price = st.number_input(
    "Purchase price per share",
    min_value=0.0, value=float(current_price), step=0.01, help="Default = latest close."
)
if stock_price <= 0:
    st.warning("Enter a valid stock price.")
    st.stop()

if st.button("Fetch Options Data"):
    display_put_options_all_dates(ticker_symbol, stock_price)

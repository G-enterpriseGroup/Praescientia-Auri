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
            st.dataframe(tbl.style.highlight_max(subset=["MLA","MLL"]), use_container_width=True)
            all_data = pd.concat([all_data, tbl], ignore_index=True)
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

# Input + better Paste button (no clipping, no reload)
cols = st.columns([5, 1.6])  # wider button column to prevent squeeze
with cols[0]:
    ticker_symbol = st.text_input("Ticker", key="ticker_input", value=st.session_state.get("ticker_input","")).upper().strip()

with cols[1]:
    components_html(
        """
        <style>
          :root {
            color-scheme: light dark;
          }
          .paste-wrap {
            display:flex; align-items:center; justify-content:center;
            height:64px;  /* enough vertical room so nothing clips */
          }
          .paste-btn {
            width:100%; height:44px; line-height:44px;
            padding:0 12px; border-radius:12px; border:1px solid;
            cursor:pointer; font:600 14px/44px system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
            transition:transform .02s ease, opacity .15s ease, background .15s ease, border-color .15s ease;
          }
          @media (prefers-color-scheme: dark) {
            .paste-btn { background:#2b2b2b; color:#eaeaea; border-color:#444; }
            .paste-btn:hover { background:#333; }
            .paste-btn:active { transform:translateY(1px); }
          }
          @media (prefers-color-scheme: light) {
            .paste-btn { background:#f4f4f4; color:#111; border-color:#cfcfcf; }
            .paste-btn:hover { background:#eee; }
            .paste-btn:active { transform:translateY(1px); }
          }
        </style>
        <div class="paste-wrap">
          <button id="pasteBtn" class="paste-btn" type="button" aria-label="Paste from clipboard">📋 Paste</button>
        </div>
        <script>
          // find the Streamlit input for label "Ticker"
          const findTickerInput = () => {
            const labels = Array.from(parent.document.querySelectorAll('label'));
            const lbl = labels.find(el => el.textContent.trim() === 'Ticker');
            return lbl ? lbl.parentElement.querySelector('input') : null;
          };
          const setTitle = v => parent.document.title = (v ? v.toUpperCase() + ' · Married Put' : 'Married Put');

          const inp = findTickerInput();
          if (inp) {
            setTitle(inp.value);
            inp.addEventListener('input', e => setTitle(e.target.value));
          }

          document.getElementById('pasteBtn').onclick = async () => {
            try {
              const txt = (await navigator.clipboard.readText() || '').trim().toUpperCase();
              const input = findTickerInput();
              if (!input || !txt) return;
              const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
              setter.call(input, txt);
              input.dispatchEvent(new Event('input', { bubbles: true }));
              setTitle(txt);
            } catch (e) {
              alert('Clipboard blocked. Use Cmd/Ctrl+V.');
            }
          };
        </script>
        """,
        height=90,   # taller iframe so the button never clips
    )

# Block until ticker present
if not ticker_symbol:
    st.warning("Enter a valid ticker.")
    st.stop()

# Long name
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

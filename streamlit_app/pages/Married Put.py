import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from streamlit.components.v1 import html as components_html

st.set_page_config(page_title="Married Put", layout="wide")

# ---------- helpers ----------
def calculate_max_loss(stock_price, df):
    n = 100
    df["CPA"] = df["ASK"] * n
    df["MLA"] = (df["STK"] * n) - (stock_price * n + df["CPA"])
    df["MLC-A"] = df.apply(lambda r: f"({r['STK']:.2f} × {n}) - ({stock_price*n:.2f} + {r['CPA']:.2f})", axis=1)
    df["CPL"] = df["LP"] * n
    df["MLL"] = (df["STK"] * n) - (stock_price * n + df["CPL"])
    df["MLC-L"] = df.apply(lambda r: f"({r['STK']:.2f} × {n}) - ({stock_price*n:.2f} + {r['CPL']:.2f})", axis=1)
    return df

def days_left(exp: str) -> int:
    return (datetime.strptime(exp, "%Y-%m-%d").date() - datetime.today().date()).days

def display_put_options_all_dates(ticker: str, stock_price: float):
    try:
        t = yf.Ticker(ticker)
        dates = t.options
        if not dates:
            st.error(f"No options data for {ticker}."); return
        all_data = pd.DataFrame()
        for exp in dates:
            st.subheader(f"Expiration: {exp} ({days_left(exp)} days left)")
            puts = t.option_chain(exp).puts
            if puts.empty:
                st.warning(f"No puts for {exp}."); continue
            tbl = puts[["contractSymbol","strike","lastPrice","bid","ask","volume","openInterest","impliedVolatility"]].copy()
            tbl.columns = ["CN","STK","LP","BID","ASK","VOL","OI","IV"]
            tbl["EXP"] = exp
            tbl = calculate_max_loss(stock_price, tbl)
            st.dataframe(tbl.style.highlight_max(subset=["MLA","MLL"]), use_container_width=True)
            all_data = pd.concat([all_data, tbl], ignore_index=True)
        if not all_data.empty:
            st.download_button("Download All Expirations (CSV)", all_data.to_csv(index=False),
                               file_name=f"{ticker}_puts.csv", mime="text/csv")
    except Exception as e:
        st.error(f"An error occurred: {e}")

# ---------- UI ----------
st.title("Options Analysis • Married Put (Max Loss)")

c1, c2 = st.columns([5, 1.6])
with c1:
    ticker_symbol = st.text_input("Ticker", key="ticker_input",
                                  placeholder="e.g., SPY").upper().strip()

with c2:
    components_html(
        """
        <style>
          .wrap{display:flex;align-items:center;justify-content:center;height:64px}
          .btn{width:100%;height:44px;border-radius:12px;border:1px solid;
               font:600 14px/44px system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
               cursor:pointer}
          @media (prefers-color-scheme: dark){
            .btn{background:#2b2b2b;color:#eaeaea;border-color:#444}
            .btn:hover{background:#333}
          }
          @media (prefers-color-scheme: light){
            .btn{background:#f4f4f4;color:#111;border-color:#cfcfcf}
            .btn:hover{background:#eee}
          }
        </style>
        <div class="wrap"><button id="pasteBtn" class="btn" type="button">📋 Paste</button></div>
        <script>
          // robustly find the ticker input
          const findTickerInput = () =>
            (parent.document.querySelector('input[placeholder="e.g., SPY"]')
              || (() => {
                   const labels=[...parent.document.querySelectorAll('label')];
                   const lbl=labels.find(el=>el.textContent.trim()==='Ticker');
                   return lbl?lbl.parentElement.querySelector('input'):null;
                 })());

          // live tab title sync
          const syncTitle = v => parent.document.title = (v && v.trim()
            ? v.trim().toUpperCase() + ' · Married Put'
            : 'Married Put');

          const inp = findTickerInput();
          if (inp) {
            syncTitle(inp.value);
            inp.addEventListener('input', e => syncTitle(e.target.value));
          }

          // single-click paste (no context menu)
          document.getElementById('pasteBtn').onclick = async () => {
            try {
              const clip = (parent.navigator && parent.navigator.clipboard)
                           ? parent.navigator.clipboard
                           : navigator.clipboard;
              const txt = (await clip.readText() || '').trim().toUpperCase();
              const input = findTickerInput();
              if (!input || !txt) return;
              input.focus();
              const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
              setter.call(input, txt);
              input.dispatchEvent(new Event('input',  {bubbles:true}));
              input.dispatchEvent(new Event('change', {bubbles:true}));
              syncTitle(txt);
            } catch(e) {
              alert('Clipboard permission blocked by the browser. Use Cmd/Ctrl+V once.');
            }
          };
        </script>
        """,
        height=90,
    )

if not ticker_symbol:
    st.warning("Enter a valid ticker.")
    st.stop()

# company name
try:
    t = yf.Ticker(ticker_symbol)
    st.write(f"**Company Name:** {t.info.get('longName','N/A')}")
except Exception as e:
    st.warning(f"Unable to fetch company name: {e}")

# default to latest close
try:
    h = yf.Ticker(ticker_symbol).history(period="1d")
    current_price = float(h["Close"].iloc[-1]) if not h.empty else 0.0
except Exception:
    current_price = 0.0

stock_price = st.number_input("Purchase price per share", min_value=0.0,
                              value=float(current_price), step=0.01, help="Default = latest close.")
if stock_price <= 0:
    st.warning("Enter a valid stock price.")
    st.stop()

if st.button("Fetch Options Data"):
    display_put_options_all_dates(ticker_symbol, stock_price)

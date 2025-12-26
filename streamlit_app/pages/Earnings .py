import re
import requests
import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime

# =========================
# CONFIG (PASTE YOUR KEY LOCALLY)
# =========================
FMP_API_KEY = "PASTE_YOUR_FMP_KEY_HERE"  # <-- paste your key here on your computer
BASE = "https://financialmodelingprep.com/stable/earnings-calendar"

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="Earnings Dates (FMP)", layout="wide")

# =========================
# BLOOMBERG-STYLE ORANGE THEME + 3D BUTTON + HTML TABLE
# =========================
CSS = """
<style>
/* Global */
html, body, [class*="css"] {
  background: #000000 !important;
  color: #ff9900 !important;
  font-family: "Courier New", Courier, monospace !important;
}

/* Reduce padding a bit */
.block-container { padding-top: 1.0rem; padding-bottom: 1.0rem; }

/* Titles */
h1, h2, h3, h4, h5, h6 {
  color: #ff9900 !important;
  letter-spacing: 0.4px;
}

/* Inputs */
textarea, input, div[data-baseweb="input"] input {
  background: #0b0b0b !important;
  color: #ff9900 !important;
  border: 2px solid #ff9900 !important;
  border-radius: 10px !important;
}

/* Slider */
div[data-baseweb="slider"] * {
  color: #ff9900 !important;
}

/* 3D Orange Button */
div.stButton > button {
  background: linear-gradient(180deg, #ffb84d 0%, #ff9900 55%, #e07f00 100%) !important;
  color: #000000 !important;
  border: 2px solid #ffcc80 !important;
  border-radius: 12px !important;
  font-weight: 900 !important;
  letter-spacing: 0.6px !important;
  padding: 0.60rem 1.00rem !important;
  box-shadow:
    0 7px 0 #a65a00,
    0 12px 22px rgba(0,0,0,0.55) !important;
  transform: translateY(0px);
}

div.stButton > button:hover {
  filter: brightness(1.03);
}

div.stButton > button:active {
  transform: translateY(6px);
  box-shadow:
    0 1px 0 #a65a00,
    0 6px 14px rgba(0,0,0,0.45) !important;
}

/* Download button matches theme */
div.stDownloadButton > button {
  ba

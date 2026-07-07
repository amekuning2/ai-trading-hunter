import streamlit as st
import pandas as pd
import MetaTrader5 as mt5
import ta
import os
import time
from datetime import datetime
import google.generativeai as genai
import json
import plotly.graph_objects as go

# ─────────────────────────────────────────────────────────────────────────────
#  1. UI OVERHAUL: MOBILE-FIRST APP STYLE
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="MT5 AI Dashboard V1.5", page_icon="⚡", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #e6edf3; font-family: sans-serif; }
    /* Card UI */
    .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 16px; margin-bottom: 15px; }
    .header-text { font-size: 24px; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .signal-card { background: #0f1614; border: 2px solid #2ea043; border-radius: 12px; padding: 20px; }
    .signal-header { color: #2ea043; font-size: 32px; font-weight: 800; text-align: center; }
    .progress-bar { background: #21262d; border-radius: 10px; height: 8px; margin: 10px 0; }
    .progress-fill { background: #2ea043; height: 100%; border-radius: 10px; width: 75%; }
    .metric-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #30363d; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  2. BACKEND LOGIC (MT5 & AI - MANTAP)
# ─────────────────────────────────────────────────────────────────────────────
if "ai_analysis" not in st.session_state: st.session_state["ai_analysis"] = None

def init_mt5(): return mt5.initialize()

# [REUSE FUNGSI ANALISIS & TRADING DARI SEBELUMNYA - LOGIC TETAP SAMA]
def fetch_and_calculate_indicators(symbol, timeframe_mt5, count=100):
    rates = mt5.copy_rates_from_pos(symbol, timeframe_mt5, 0, count)
    if rates is None: return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
    df['ema_200'] = ta.trend.ema_indicator(df['close'], window=200)
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    return df

# ─────────────────────────────────────────────────────────────────────────────
#  3. MOBILE-FIRST UI LAYOUT (KONTROL DI ATAS, BUKAN SIDEBAR)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("<div class='header-text'>📱 MT5 Dashboard</div>", unsafe_allow_html=True)

# Main Controls (Integrated)
with st.expander("⚙️ Konfigurasi Trading (Buka untuk Ubah)", expanded=False):
    symbol_input = st.text_input("Simbol", value="EURUSD").upper()
    timeframe_input = st.selectbox("Timeframe", ["M1", "M5", "M15", "H1"], index=2)
    lot_input = st.number_input("Lot Size", value=0.10, step=0.01)

# Status
mt5.initialize()
account = mt5.account_info()
if account:
    st.markdown(f"<div style='text-align:center; color:#2ea043; font-weight:bold;'>🟢 {account.name} | Bal: ${account.balance:.2f}</div>", unsafe_allow_html=True)

# AI Signal Card (REPLICA UI REFERENSI)
st.markdown("### ⚡ AI SIGNAL")
# --- Logic Mockup Signal (Ganti dengan fungsi API lo nanti) ---
signal_data = {
    "rec": "BUY",
    "desc": "Tren besar sangat selaras (MTF 15/15) dan harga bertahan di atas EMA200.",
    "conf": 75,
    "entry": 1.14420,
    "sl": 1.14340,
    "tp": 1.14460
}

st.markdown(f"""
<div class='signal-card'>
    <div class='signal-header'>{signal_data['rec']}</div>
    <p style='font-size:13px; color:#8b949e; text-align:center;'>{signal_data['desc']}</p>
    <div class='progress-bar'><div class='progress-fill' style='width:{signal_data['conf']}%'></div></div>
    <div style='text-align:center; font-size:12px;'>AI Confidence: {signal_data['conf']}%</div>
</div>
""", unsafe_allow_html=True)

# Level dari Gemini AI
st.markdown("### ✨ LEVEL DARI GEMINI AI")
st.markdown(f"""
<div class='card'>
    <div class='metric-row'><span>Posisi</span><span style='color:#2ea043;'>{signal_data['rec']}</span></div>
    <div class='metric-row'><span>Entry</span><span>{signal_data['entry']}</span></div>
    <div class='metric-row'><span>Stop Loss</span><span style='color:#da3633;'>{signal_data['sl']}</span></div>
    <div class='metric-row'><span>TP 1</span><span style='color:#2ea043;'>{signal_data['tp']}</span></div>
</div>
""", unsafe_allow_html=True)

# Action Buttons
col1, col2 = st.columns(2)
with col1: st.button("🟢 BUY", use_container_width=True)
with col2: st.button("🔴 SELL", use_container_width=True)

st.button("🔄 REFRESH", use_container_width=True)
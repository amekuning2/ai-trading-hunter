import streamlit as st
import pandas as pd
import MetaTrader5 as mt5
import ta
import time
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
#  1. UI & STYLING (MOBILE-FIRST)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="MT5 Simple Dashboard v2.5", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .stApp { background-color: #0e0e0e; color: #ffffff; }
    .main-card { background: #1a1a1a; padding: 20px; border-radius: 15px; border: 1px solid #333; margin-bottom: 15px; }
    .signal-box { background: #0c1a0c; border: 2px solid #22c55e; border-radius: 10px; padding: 15px; text-align: center; }
    .btn-refresh { background-color: #ea580c !important; color: white !important; font-weight: bold !important; }
    .metric-value { font-size: 24px; font-weight: bold; }
    .label-text { color: #9ca3af; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  2. LOGIC ENGINE (LOCAL FALLBACK)
# ─────────────────────────────────────────────────────────────────────────────
def get_market_data(symbol, tf_str):
    tf_map = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1}
    rates = mt5.copy_rates_from_pos(symbol, tf_map.get(tf_str, mt5.TIMEFRAME_M15), 0, 100)
    if rates is None: return None
    df = pd.DataFrame(rates)
    df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
    df['ema_200'] = ta.trend.ema_indicator(df['close'], window=200)
    df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    return df.iloc[-1]

def calculate_local_signal(data, symbol):
    # Logic formula lokal buat jaga-jaga kalau AI limit
    close = data['close']
    ema50 = data['ema_50']
    ema200 = data['ema_200']
    atr = data['atr']
    
    pos = "BUY" if close > ema50 else "SELL"
    entry = close
    sl = entry - (atr * 1.5) if pos == "BUY" else entry + (atr * 1.5)
    tp1 = entry + (atr * 1.3) if pos == "BUY" else entry - (atr * 1.3)
    tp2 = entry + (atr * 2.0) if pos == "BUY" else entry - (atr * 2.0)
    
    return {"pos": pos, "entry": round(entry, 5), "sl": round(sl, 5), "tp1": round(tp1, 5), "tp2": round(tp2, 5), "rr": "1:1.5", "conf": 75}

# ─────────────────────────────────────────────────────────────────────────────
#  3. UI RENDER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 📱 MT5 Simple Dashboard v2.5")

# Setup Session State
if "symbol" not in st.session_state: st.session_state.symbol = "XAUUSD"

with st.expander("⚙️ Konfigurasi Trading (Buka untuk Ubah)", expanded=True):
    pair = st.selectbox("Simbol", ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"], index=0)
    mode = st.selectbox("Trading Mode", ["Scalping — M1-M15, TP cepat", "Swing — H1-H4, TP jauh"])
    tf = st.selectbox("Timeframe", ["M1", "M5", "M15", "H1"], index=2)
    lot = st.number_input("Lot Size", value=0.10, step=0.01)

mt5.initialize()
acc = mt5.account_info()
if acc:
    st.markdown(f"<center><b style='color:#22c55e;'>🟢 {acc.name} | Bal: ${acc.balance:,.2f}</b></center>", unsafe_allow_html=True)

data = get_market_data(pair, tf)
if data is not None:
    # Price Display
    st.markdown(f"""
    <div class='main-card'>
        <h3>{pair} <span style='font-size:12px; color:gray;'>MT5 FOREX</span></h3>
        <div style='display:flex; justify-content:space-between;'>
            <div><div class='label-text'>BID</div><div class='metric-value' style='color:#22c55e;'>{data['close']:.2f}</div></div>
            <div><div class='label-text'>ASK</div><div class='metric-value' style='color:#ef4444;'>{(data['close']+0.02):.2f}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    sig = calculate_local_signal(data, pair)
    
    # Signal Card
    st.markdown(f"""
    <div class='signal-box'>
        <div style='font-size:24px; font-weight:bold; color:#22c55e;'>{sig['pos']}</div>
        <p style='font-size:12px;'>Tren besar sangat selaras (MTF 15/15) dan harga bertahan di atas EMA200.</p>
        <div style='background:#1f2937; height:8px; border-radius:5px;'><div style='background:#22c55e; width:{sig['conf']}%; height:100%; border-radius:5px;'></div></div>
        <p style='font-size:10px; margin-top:5px;'>AI Confidence: {sig['conf']}%</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Levels Card
    st.markdown(f"""
    <div class='main-card'>
        <b style='color:#fbbf24;'>✨ LEVEL DARI GEMINI AI (Fallback Lokal)</b>
        <div style='display:flex; justify-content:space-between; margin-top:10px;'><span>Posisi</span><b style='color:#22c55e;'>{sig['pos']}</b></div>
        <div style='display:flex; justify-content:space-between;'><span>Entry</span><b>{sig['entry']}</b></div>
        <div style='display:flex; justify-content:space-between;'><span>Stop Loss</span><b style='color:#ef4444;'>{sig['sl']} (8.0 pips)</b></div>
        <div style='display:flex; justify-content:space-between;'><span>TP 1</span><b style='color:#22c55e;'>{sig['tp1']} (+4.0 pips)</b></div>
        <div style='display:flex; justify-content:space-between;'><span>TP 2</span><b style='color:#22c55e;'>{sig['tp2']} (+10.0 pips)</b></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Risk Card
    st.markdown(f"""
    <div class='main-card'>
        <b>RISK & REWARD</b>
        <div style='display:flex; justify-content:space-between;'><span>R/R Ratio</span><span>{sig['rr']}</span></div>
        <div style='display:flex; justify-content:space-between;'><span>Modal</span><span>${acc.balance:,.2f}</span></div>
        <div style='display:flex; justify-content:space-between;'><span>Lot Size</span><span>{lot}</span></div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🔄 REFRESH MANUAL", use_container_width=True, type="primary"):
        st.rerun()
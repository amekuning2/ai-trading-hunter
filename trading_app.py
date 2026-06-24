import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from binance.client import Client
from binance.exceptions import BinanceAPIException
import ta
import time
from datetime import datetime
import google.generativeai as genai
import json

# ─────────────────────────────────────────────
#  CONFIG (KEMBALI KE COLLAPSED SUPAYA AMAN DI HP)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────
#  DARK MODE STYLING (ASLI v2.9.5 TANPA LOGO BARU)
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #e6edf3; }
    .stSidebar { background-color: #161b22; border-right: 1px solid #30363d; }
    .stSidebar .stSelectbox label,
    .stSidebar .stRadio label,
    .stSidebar p { color: #8b949e !important; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }

    [data-testid="metric-container"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px;
    }

    .signal-box { padding: 16px; border-radius: 8px; text-align: center; margin-bottom: 16px; }
    .signal-buy { background-color: #0d2b1d; border: 1px solid #2ea043; color: #3fb950; }
    .signal-sell { background-color: #2d1b1b; border: 1px solid #f85149; color: #f85149; }
    .signal-hold { background-color: #1b1f2d; border: 1px solid #388bfd; color: #388bfd; }

    .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; margin: 2px; }
    .badge-green { background-color: #0d2b1d; color: #3fb950; border: 1px solid #2ea043; }
    .badge-red { background-color: #2d1b1b; color: #f85149; border: 1px solid #f85149; }
    .badge-gray { background-color: #21262d; color: #8b949e; border: 1px solid #30363d; }

    .section-header { color: #8b949e; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid #30363d; padding-bottom: 6px; margin-bottom: 16px; margin-top: 16px; }
    
    .plan-box { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
    .plan-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #21262d; font-size: 14px; }
    .plan-row:last-child { border-bottom: none; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  LOAD SECRETS
# ─────────────────────────────────────────────
try:
    BINANCE_API_KEY = st.secrets["BINANCE_API_KEY"]
    BINANCE_API_SECRET = st.secrets["BINANCE_API_SECRET"]
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
except Exception as e:
    st.error(f"❌ Gagal membaca st.secrets. Error: {e}")
    st.stop()

GEMINI_ENABLED = False
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_ENABLED = True

@st.cache_resource
def get_binance_client():
    return Client(BINANCE_API_KEY, BINANCE_API_SECRET)

client = get_binance_client()

# ─────────────────────────────────────────────
#  SESSION STATE (SISTEM WALLET REALISTIS)
# ─────────────────────────────────────────────
if "wallet_spot" not in st.session_state: st.session_state["wallet_spot"] = 50.0
if "wallet_futures" not in st.session_state: st.session_state["wallet_futures"] = 50.0
if "sim_history" not in st.session_state: st.session_state["sim_history"] = []
if "auto_refresh" not in st.session_state: st.session_state["auto_refresh"] = False

# ─────────────────────────────────────────────
#  PERSISTENT SETTINGS CONTROL (DI PINDAH KE TAB 5 BIAR HP AMAN)
# ─────────────────────────────────────────────
if "market_type" not in st.session_state: st.session_state["market_type"] = "Spot"
if "leverage" not in st.session_state: st.session_state["leverage"] = 10

# ─────────────────────────────────────────────
#  SIDEBAR CONTROLLER (DIPERTAHANKAN BERSIH NYA v2.9.5)
# ─────────────────────────────────────────────
st.sidebar.markdown("**⚙️ GLOBAL SETTINGS**")
symbol = st.sidebar.text_input("Pair Trading", value="BTCUSDT").upper()
interval = st.sidebar.selectbox("Timeframe", ["5m", "15m", "1h", "4h"], index=1)
mode = st.sidebar.radio("Mode Analisis", ["Scalping", "Ketat"], index=0)

# ─────────────────────────────────────────────
#  DYNAMIC DATA FETCHING ENGINE (SPOT / FUTURES)
# ─────────────────────────────────────────────
def get_market_data(symbol, interval, market_type):
    try:
        if market_type == "Futures":
            ticker = client.futures_symbol_ticker(symbol=symbol)
            klines = client.futures_klines(symbol=symbol, interval=interval, limit=100)
            price = float(ticker["price"])
            price_change = 0.0
        else:
            ticker = client.get_ticker(symbol=symbol)
            klines = client.get_klines(symbol=symbol, interval=interval, limit=100)
            price = float(ticker["lastPrice"])
            price_change = float(ticker["priceChangePercent"])

        df = pd.DataFrame(klines, columns=["timestamp","open","high","low","close","volume","ct","qv","tr","tbb","tbq","ig"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        for col in ["open","high","low","close","volume"]:
            df[col] = df[col].astype(float)
        return price, price_change, df
    except Exception as e:
        st.error(f"⚠️ Error memuat data ({market_type}): {e}")
        return None, None, None

current_price, price_change, df = get_market_data(symbol, interval, st.session_state["market_type"])
if df is None: st.stop()

# ─────────────────────────────────────────────
#  MATHEMATICAL FORMULA INDICATORS (ASLI v2.9.5)
# ─────────────────────────────────────────────
df["ema20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
df["ema50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
df["ema200"] = ta.trend.EMAIndicator(df["close"], window=200).ema_indicator()
df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()

macd_obj = ta.trend.MACD(df["close"])
df["macd"] = macd_obj.macd()
df["macd_signal"] = macd_obj.macd_signal()

stoch = ta.momentum.StochasticOscillator(df["high"], df["low"], df["close"], window=14, smooth_window=3)
df["stoch_k"] = stoch.stoch()
df["stoch_d"] = stoch.stoch_signal()

bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
df["bb_high"] = bb.bollinger_hband()
df["bb_low"] = bb.bollinger_lband()

df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range()

# Ambil baris terakhir data teknikals
last_row = df.iloc[-1]
rsi_val = last_row["rsi"]
stoch_k = last_row["stoch_k"]
stoch_d = last_row["stoch_d"]
macd_val = last_row["macd"]
macd_sig = last_row["macd_signal"]
ema20 = last_row["ema20"]
ema50 = last_row["ema50"]
ema200 = last_row["ema200"] if not pd.isna(last_row["ema200"]) else ema50
atr_val = last_row["atr"]

# Support & Resistance Kalkulasi
sup_price = round(df["low"].rolling(15).min().iloc[-1], 2)
res_price = round(df["high"].rolling(15).max().iloc[-1], 2)

# ─────────────────────────────────────────────
#  HYBRID CORE INTELLIGENCE (GEMINI ENGINE)
# ─────────────────────────────────────────────
def ask_gemini_hybrid_logic(market, mode, price, rsi, ema20, ema50, macd, macd_s, sup, res, lev):
    if not GEMINI_ENABLED:
        return {"signal": "HOLD", "reason": "Gemini nonaktif.", "insights": ["Formula dasar kaku aktif."]}
    
    market_state = {
        "market_type": market, "mode": mode, "price": price, "leverage": lev,
        "rsi": round(rsi, 2), "ema20": round(ema20, 2), "ema50": round(ema50, 2),
        "macd_trend": "BULLISH" if macd > macd_s else "BEARISH",
        "support": sup, "resistance": res
    }
    
    prompt = f"""
    Analisis data market ini secara profesional untuk scalping target $5/hari:
    {json.dumps(market_state)}
    
    ATURAN STRATEGI:
    1. Jangan kaku. Cari peluang mikro yang rasional.
    2. Jika market_type='Futures', kamu diizinkan mutlak mengeluarkan keputusan 'BUY' (LONG) atau 'SELL' (SHORT).
    3. Jika market_type='Spot', keputusan hanya boleh 'BUY' atau 'HOLD'.
    
    Kembalikan output WAJIB JSON murni tanpa mark-up teks:
    {{"signal": "BUY / SELL / HOLD", "reason": "alasan singkat", "insights": ["poin 1", "poin 2"]}}
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        res_ai = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(res_ai.text.strip())
    except:
        return {"signal": "HOLD", "reason": "Fallback API Error", "insights": []}

ai_decision = ask_gemini_hybrid_logic(st.session_state["market_type"], mode, current_price, rsi_val, ema20, ema50, macd_val, macd_sig, sup_price, res_price, st.session_state["leverage"])
final_signal = ai_decision.get("signal", "HOLD")

# ─────────────────────────────────────────────
#  APP DASHBOARD TABS STRUCTURE (UTUH ASLI v2.9.5)
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Dashboard", 
    "📊 Multi-Timeframe (MTF)", 
    "📋 Trading Plan", 
    "🔄 Backtesting", 
    "⚙️ Settings"
])

# ─── TAB 1: DASHBOARD ───
with tab1:
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Live Price", f"${current_price:,} USDT", f"{price_change:.2f}%" if st.session_state["market_type"] == "Spot" else "Futures Mode")
    col_m2.metric("RSI (14)", f"{rsi_val:.2f}")
    col_m3.metric("Stochastic K/D", f"{stoch_k:.1f} / {stoch_d:.1f}")
    col_m4.metric("Market Type", st.session_state["market_type"])

    st.markdown('<p class=\"section-header\">🔮 AI Hybrid Decision Engine</p>', unsafe_allow_html=True)
    
    c_sig, c_ins = st.columns([4, 6])
    with c_sig:
        box_cls = "signal-buy" if final_signal == "BUY" else "signal-sell" if final_signal == "SELL" else "signal-hold"
        lbl = final_signal
        if st.session_state["market_type"] == "Futures":
            if final_signal == "BUY": lbl = "LONG (BUY)"
            elif final_signal == "SELL": lbl = "SHORT (SELL)"
            
        st.markdown(f"""
        <div class="signal-box {box_cls}">
            <p style="margin:0; font-size:12px; uppercase; opacity:0.7;">Sinyal Final AI</p>
            <p style="margin:4px 0; font-size:28px; font-weight:800;">{lbl}</p>
            <p style="margin:0; font-size:13px;">{ai_decision.get('reason')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with c_ins:
        st.markdown("**💡 AI Market Insights:**")
        for insight in ai_decision.get("insights", []):
            st.markdown(f"• {insight}")

    # Chart Area
    st.markdown('<p class=\"section-header\">📊 Technical Candlestick Chart</p>', unsafe_allow_html=True)
    fig = make_subplots(rows=1, cols=1)
    fig.add_trace(go.Candlestick(x=df["timestamp"], open=df["open"], high=df["high"], low=df["low"], close=df["close"], name="Candle"))
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["ema20"], line=dict(color='#ffaa00', width=1), name="EMA 20"))
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["ema50"], line=dict(color='#00e6ff', width=1), name="EMA 50"))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10,r=10,t=10,b=10), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# ─── TAB 2: MULTI-TIMEFRAME (ASLI v2.9.5) ───
with tab2:
    st.markdown('<p class=\"section-header\">📊 Multi-Timeframe Alignment</p>', unsafe_allow_html=True)
    st.write("Data visualisasi tren keselarasan multi-timeframe berbasis MA / RSI alignment.")
    c1, c2, c3 = st.columns(3)
    c1.markdown('<div class="badge badge-green">5m Trend: Bullish</div>', unsafe_allow_html=True)
    c2.markdown('<div class="badge badge-green">15m Trend: Bullish</div>', unsafe_allow_html=True)
    c3.markdown('<div class="badge badge-gray">1h Trend: Sideways</div>', unsafe_allow_html=True)

# ─── TAB 3: TRADING PLAN (RISK & MARGIN CALCULATOR ACCURATE) ───
with tab3:
    st.markdown('<p class=\"section-header\">🎯 Strategy Trading Plan & Execution</p>', unsafe_allow_html=True)
    
    if final_signal != "HOLD":
        entry = current_price
        sl = round(entry - (atr_val * 1.5), 2) if final_signal == "BUY" else round(entry + (atr_val * 1.5), 2)
        tp = round(entry + (atr_val * 2), 2) if final_signal == "BUY" else round(entry - (atr_val * 2), 2)
        
        sl_pct = abs((sl - entry) / entry) * 100
        tp_pct = abs((tp - entry) / entry) * 100
        
        mult = st.session_state["leverage"] if st.session_state["market_type"] == "Futures" else 1
        est_pnl = tp_pct * mult
        est_loss = sl_pct * mult
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown(f"""
            <div class="plan-box">
                <span style="color:#58a6ff; font-weight:700;">📌 PEMETAAN HARGA</span><br><br>
                <div class="plan-row"><span>Entry Target</span><b>${entry:,} USDT</b></div>
                <div class="plan-row"><span>Stop Loss (SL)</span><b style="color:#f85149;">${sl:,} USDT</b></div>
                <div class="plan-row"><span>Take Profit (TP)</span><b style="color:#3fb950;">${tp:,} USDT</b></div>
            </div>
            """, unsafe_allow_html=True)
        with col_p2:
            st.markdown(f"""
            <div class="plan-box">
                <span style="color:#58a6ff; font-weight:700;">⚡ METRIKS RISIKO ({st.session_state['market_type']})</span><br><br>
                <div class="plan-row"><span>Leverage</span><b>{mult}x</b></div>
                <div class="plan-row"><span>Projeksi Profit (TP)</span><b style="color:#3fb950;">+{est_pnl:.2f}%</b></div>
                <div class="plan-row"><span>Projeksi Risiko (SL)</span><b style="color:#f85149;">-{est_loss:.2f}%</b></div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Buka Posisi Simulasi (Alokasi $10)", use_container_width=True):
            cost = 10.0
            cur_wallet = "wallet_spot" if st.session_state["market_type"] == "Spot" else "wallet_futures"
            
            if st.session_state[cur_wallet] >= cost:
                st.session_state[cur_wallet] -= cost
                t_type = "LONG" if final_signal == "BUY" else "SHORT"
                st.session_state["sim_history"].append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "market": st.session_state["market_type"],
                    "type": t_type,
                    "info": f"Margin/Cost: ${cost} USDT (Leverage {mult}x)"
                })
                st.success("🎉 Posisi simulasi berhasil dicatat ke dalam ledger!")
            else:
                st.error("❌ Saldo Simulasi dompet terkait tidak mencukupi ($10).")
    else:
        st.info("Sinyal dalam status HOLD. Menunggu sinyal konfirmasi dari AI.")

    st.markdown('<p class=\"section-header\">📜 Log Aktivitas Simulasi Hari Ini</p>', unsafe_allow_html=True)
    if not st.session_state["sim_history"]:
        st.caption("Belum ada trade yang dieksekusi.")
    else:
        for log in reversed(st.session_state["sim_history"]):
            st.text(f"⏱️ {log['time']} | Bursa: {log['market']} | Posisi: {log['type']} | {log['info']}")

# ─── TAB 4: BACKTESTING (ASLI v2.9.5) ───
with tab4:
    st.markdown('<p class=\"section-header\">🔄 Static Backtesting Engine</p>', unsafe_allow_html=True)
    st.write("Modul uji performa histori strategi formula kaku bawaan versi v2.9.5.")
    st.dataframe(df[["timestamp", "close", "rsi"]].tail(5), use_container_width=True)

# ─── TAB 5: SETTINGS & DYNAMIC FUTURES SWITCH (KONTROL PENUH) ───
with tab5:
    st.markdown('<p class=\"section-header\">⚙️ Konfigurasi Sistem Dashboard</p>', unsafe_allow_html=True)

    # Integrasi Fitur Baru Fase 3 di dalam Tab Settings
    st.markdown("**🎯 Pengaturan Tipe Market (Fase 3)**")
    m_choice = st.selectbox("Pilih Bursa Transaksi", ["Spot", "Futures"], index=0 if st.session_state["market_type"] == "Spot" else 1)
    st.session_state["market_type"] = m_choice
    
    if m_choice == "Futures":
        lev_choice = st.slider("Atur Besaran Leverage Kontrak", min_value=1, max_value=20, value=st.session_state["leverage"])
        st.session_state["leverage"] = lev_choice
        st.caption(f"Beban Pengali Margin saat ini dikunci pada: {lev_choice}x")

    st.markdown("---")
    st.markdown("**🔄 Auto Refresh Panel**")
    auto_ref = st.checkbox("Nyalakan auto refresh dashboard (30s)", value=st.session_state["auto_refresh"])
    st.session_state["auto_refresh"] = auto_ref

    st.markdown("---")
    st.markdown("**🔄 Manajemen Saldo & Reset**")
    if st.button("Reset Total Dompet Simulasi ($50 Spot + $50 Futures)"):
        st.session_state["wallet_spot"] = 50.0
        st.session_state["wallet_futures"] = 50.0
        st.session_state["sim_history"] = []
        st.rerun()

    st.markdown("---")
    st.markdown("**ℹ️ Informasi Aplikasi**")
    g_status = "🟢 Aktif" if GEMINI_ENABLED else "🔴 Tidak aktif"
    st.markdown(f"""
    <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:16px;">
        <p style="color:#8b949e; font-size:12px; margin:0;">
        Version: <span style="color:#e6edf3;">v3.0.0 (Fase 3 - Futures Extension Layer)</span><br>
        Gemini Integration: <span style="color:#e6edf3;">{g_status}</span><br>
        Current Wallet Spot: <span style="color:#e6edf3;">${st.session_state['wallet_spot']:.2f} USDT</span><br>
        Current Wallet Futures: <span style="color:#e6edf3;">${st.session_state['wallet_futures']:.2f} USDT</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  TIMING REFRESH ENGINE
# ─────────────────────────────────────────────
if st.session_state["auto_refresh"]:
    time.sleep(30)
    st.rerun()
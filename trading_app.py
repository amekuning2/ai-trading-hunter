import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from binance.client import Client
import ta
import time
from datetime import datetime
import google.generativeai as genai
import json

# ──────────────────────────────────────────────────────────────────────────────
#  1. APP CONFIGURATION & DARK THEME CUSTOM STYLING
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🔮 AI Trading Hunter v3.0.0",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk UI bernuansa Dark Pro Cyberpunk
st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #e6edf3; }
    .stSidebar { background-color: #161b22; border-right: 1px solid #30363d; }
    
    /* Metric Styling */
    [data-testid="metric-container"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 14px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    /* Dynamic Signal Box Styling */
    .signal-container { padding: 18px; border-radius: 8px; text-align: center; margin-bottom: 15px; }
    .sig-buy { background: linear-gradient(135deg, #0d2b1d, #0f3d2a); border: 1px solid #2ea043; border-left: 5px solid #2ea043; }
    .sig-sell { background: linear-gradient(135deg, #2d1b1b, #3d1f1f); border: 1px solid #f85149; border-left: 5px solid #f85149; }
    .sig-hold { background: linear-gradient(135deg, #1b1f2d, #1e2540); border: 1px solid #388bfd; border-left: 5px solid #388bfd; }
    
    .signal-title { font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #8b949e; margin: 0 0 4px 0; }
    .signal-text { font-size: 32px; font-weight: 800; margin: 0; }
    .sig-buy .signal-text { color: #3fb950; }
    .sig-sell .signal-text { color: #f85149; }
    .sig-hold .signal-text { color: #388bfd; }
    
    /* Technical Badges */
    .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin: 4px; }
    .badge-green { background: #0d2b1d; color: #3fb950; border: 1px solid #2ea043; }
    .badge-red { background: #2d1b1b; color: #f85149; border: 1px solid #f85149; }
    .badge-neutral { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; }
    
    /* Trading Plan Dashboard Box */
    .tp-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; height: 100%; }
    .tp-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #21262d; font-size: 14px; }
    .tp-row:last-child { border-bottom: none; }
    .tp-row span { color: #8b949e; }
    .tp-row b { color: #c9d1d9; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
#  2. INITIALIZATION SECRETS & CLIENTS
# ──────────────────────────────────────────────────────────────────────────────
try:
    BINANCE_API_KEY = st.secrets["BINANCE_API_KEY"]
    BINANCE_API_SECRET = st.secrets["BINANCE_API_SECRET"]
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
except Exception as e:
    st.error(f"❌ Gagal membaca st.secrets! Pastikan konfigurasi file secrets.toml sudah benar. Error: {e}")
    st.stop()

# Konfigurasi AI Gemini
GEMINI_ACTIVE = False
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_ACTIVE = True

@st.cache_resource
def init_binance_connection():
    return Client(BINANCE_API_KEY, BINANCE_API_SECRET)

client = init_binance_connection()

# ──────────────────────────────────────────────────────────────────────────────
#  3. PERSISTENT STATE MANAGEMENT (REAL BINANCE SYSTEM SIMULATION)
# ──────────────────────────────────────────────────────────────────────────────
# Mengikuti sistem Binance asli: Dompet Spot dan Futures dipisahkan secara internal
if "wallet_spot" not in st.session_state: st.session_state["wallet_spot"] = 50.0
if "wallet_futures" not in st.session_state: st.session_state["wallet_futures"] = 50.0
if "trade_logs" not in st.session_state: st.session_state["trade_logs"] = []
if "loop_refresh" not in st.session_state: st.session_state["loop_refresh"] = False

# ──────────────────────────────────────────────────────────────────────────────
#  4. SIDEBAR PANEL CONTROLLER
# ──────────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("### 🎛️ CONTROL PANEL AI")

# Fitur Inti Fase 3: Pemilihan Pasar Tanpa Menghilangkan Fitur Spot Lama
selected_market = st.sidebar.selectbox("📊 TYPE MARKET", ["Spot", "Futures"])
crypto_asset = st.sidebar.text_input("🪙 PAIR TRADING", value="BTCUSDT").upper()
chosen_tf = st.sidebar.selectbox("⏳ TIME FRAME DATA", ["5m", "15m", "1h", "4h"])
scoring_mode = st.sidebar.radio("⚙️ RULES AGGRESSIVENESS", ["Ketat", "Scalping"])

# Dynamic Parameter Khusus Pasar Futures
leverage_factor = 1
if selected_market == "Futures":
    st.sidebar.markdown("---")
    leverage_factor = st.sidebar.slider("⚡ FUTURES LEVERAGE", min_value=1, max_value=20, value=10)
    st.sidebar.caption(f"Sistem Margin Multiplier aktif pada beban: {leverage_factor}x")

st.sidebar.markdown("---")
st.sidebar.markdown("### 💰 REALISTIC MOCK WALLET")
st.sidebar.markdown(f"**Spot Wallet:** `${st.session_state['wallet_spot']:.2f}` USDT")
st.sidebar.markdown(f"**Futures Wallet:** `${st.session_state['wallet_futures']:.2f}` USDT")
st.sidebar.caption("Target Mikro: Profit minimal $5 per hari secara konsisten.")

# ──────────────────────────────────────────────────────────────────────────────
#  5. ADVANCED DATA FETCHING PIPELINE
# ──────────────────────────────────────────────────────────────────────────────
def fetch_binance_market_data(symbol, interval, market_type):
    try:
        if market_type == "Futures":
            # Menarik data tickers & candlestick dari REST API USDS-M Futures secara publik
            ticker_data = client.futures_symbol_ticker(symbol=symbol)
            raw_klines = client.futures_klines(symbol=symbol, interval=interval, limit=120)
            current_price = float(ticker_data["price"])
            price_change = 0.0 # Placeholder default untuk data klines futures
        else:
            # Menarik data dari REST API Spot konvensional
            ticker_data = client.get_ticker(symbol=symbol)
            raw_klines = client.get_klines(symbol=symbol, interval=interval, limit=120)
            current_price = float(ticker_data["lastPrice"])
            price_change = float(ticker_data["priceChangePercent"])

        # Pemetaan struktur dataframe
        columns = ["timestamp", "open", "high", "low", "close", "volume", "close_time", 
                   "quote_av", "trades_num", "tb_base_av", "tb_quote_av", "ignore"]
        df_candles = pd.DataFrame(raw_klines, columns=columns)
        df_candles["timestamp"] = pd.to_datetime(df_candles["timestamp"], unit="ms")
        
        for numeric_col in ["open", "high", "low", "close", "volume"]:
            df_candles[numeric_col] = df_candles[numeric_col].astype(float)
            
        return current_price, price_change, df_candles
    except Exception as error:
        st.error(f"⚠️ Gagal memuat data dari market {market_type}: {error}")
        return None, None, None

live_price, live_change, df_market = fetch_binance_market_data(crypto_asset, chosen_tf, selected_market)

if df_market is None or df_market.empty:
    st.warning("Gagal menyinkronkan data bursa. Silakan periksa kembali penulisan Pair Trading Anda (Contoh: BTCUSDT).")
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
#  6. COMPLETE MATHEMATICAL MATH ENGINE (TECHNICAL INDICATORS)
# ──────────────────────────────────────────────────────────────────────────────
# Trend Indicators
df_market["ema20"] = ta.trend.EMAIndicator(df_market["close"], window=20).ema_indicator()
df_market["ema50"] = ta.trend.EMAIndicator(df_market["close"], window=50).ema_indicator()

latest_ema20 = df_market["ema20"].iloc[-1]
latest_ema50 = df_market["ema50"].iloc[-1]

# Momentum Indicators
df_market["rsi"] = ta.momentum.RSIIndicator(df_market["close"], window=14).rsi()
latest_rsi = df_market["rsi"].iloc[-1]

# MACD Lines
macd_calc = ta.trend.MACD(df_market["close"], window_fast=12, window_slow=26, window_sign=9)
df_market["macd_line"] = macd_calc.macd()
df_market["macd_signal"] = macd_calc.macd_signal()

latest_macd_line = df_market["macd_line"].iloc[-1]
latest_macd_sig = df_market["macd_signal"].iloc[-1]

# Volatility ATR
df_market["atr"] = ta.volatility.AverageTrueRange(df_market["high"], df_market["low"], df_market["close"], window=14).average_true_range()
latest_atr = df_market["atr"].iloc[-1]

# Support & Resistance Kalkulasi Lokal 10 Candlestick
local_resistance = float(df_market["high"].rolling(10).max().iloc[-1])
local_support = float(df_market["low"].rolling(10).min().iloc[-1])

# ──────────────────────────────────────────────────────────────────────────────
#  7. HYBRID INTELLIGENCE: GEMINI BRAIN ENHANCEMENT v3
# ──────────────────────────────────────────────────────────────────────────────
def request_hybrid_ai_decision(m_type, r_mode, price, rsi, ema20, ema50, macd_l, macd_s, sup, res, lev):
    if not GEMINI_ACTIVE:
        return {
            "signal": "HOLD", 
            "reason": "Kunci API Gemini tidak terdeteksi. Sistem berjalan dalam mode darurat formula kaku.",
            "insights": ["Tambahkan GEMINI_API_KEY di secrets panel Anda."]
        }
    
    # Payload data matang dari kalkulasi matematika lokal
    context_payload = {
        "market_type": m_type,
        "rule_mode": r_mode,
        "current_price": price,
        "leverage_selected": lev,
        "indicators": {
            "rsi_14": round(rsi, 2),
            "ema_20": round(ema20, 2),
            "ema_50": round(ema50, 2),
            "macd_trend": "BULLISH CROSSOVER" if macd_l > macd_s else "BEARISH CROSSOVER",
            "support": round(sup, 2),
            "resistance": round(res, 2)
        },
        "target_objective": "Mengejar target mikro minimal $5 per hari dengan aman tanpa risiko tinggi."
    }
    
    system_prompt = f"""
    Anda adalah Inti Algoritma Hibrida (Hybrid Brain Engine) untuk asisten perdagangan kuantitatif.
    Tugas Anda adalah memproses data metrik indikator matematika berikut ini dan memberikan instruksi sinyal final:
    {json.dumps(context_payload)}
    
    MANUAL INSTRUKSI OPERASIONAL:
    1. Anda tidak boleh bersikap terlalu kaku seperti rumus konvensional. Ambil peluang mikro scalping demi target harian $5.
    2. JIKA pasar yang dipilih adalah 'Futures': Anda DIIZINKAN secara mutlak mengeluarkan sinyal arah 'BUY' (untuk posisi LONG) atau 'SELL' (untuk posisi SHORT/Mencari untung dari penurunan harga).
    3. JIKA pasar yang dipilih adalah 'Spot': Anda HANYA BOLEH memberikan keputusan 'BUY' (membeli aset naik) atau 'HOLD' (menahan/tidak melakukan transaksi). Sinyal 'SELL' pada mode Spot dilarang kecuali untuk melepas aset.
    
    Berikan respon akhir WAJIB dalam bentuk struktur JSON murni yang valid tanpa format tambahan apa pun seperti berikut:
    {{"signal": "BUY / SELL / HOLD", "reason": "Alasan singkat berbasis data matematika", "insights": ["poin analisis 1", "poin analisis 2"]}}
    """
    
    try:
        ai_model = genai.GenerativeModel("gemini-1.5-flash")
        raw_response = ai_model.generate_content(system_prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(raw_response.text.strip())
    except Exception:
        # Fallback engine jika API mengalami request limit throttled
        return {
            "signal": "HOLD",
            "reason": "Sistem mendeteksi kepadatan lalu lintas API Gemini. Mengaktifkan sinyal hold preventif.",
            "insights": ["Gagal memproses keputusan hibrida."]
        }

# Eksekusi Keputusan Otak AI
ai_analysis = request_hybrid_ai_decision(
    selected_market, scoring_mode, live_price, latest_rsi, 
    latest_ema20, latest_ema50, latest_macd_line, latest_macd_sig, 
    local_support, local_resistance, leverage_factor
)
final_signal = ai_analysis.get("signal", "HOLD")

# ──────────────────────────────────────────────────────────────────────────────
#  8. AUTOMATED TRADING PLAN CALCULATOR
# ──────────────────────────────────────────────────────────────────────────────
def generate_trading_plan(sig, price, atr, m_type, lev):
    if sig == "HOLD": return None
    
    entry_level = price
    # Menggunakan pengali ATR 1.5x untuk adaptasi volatilitas micro scalping
    if sig == "BUY":
        stop_loss = entry_level - (atr * 1.5)
        take_profit = entry_level + (atr * 2.0)
    else: # Sinyal SELL (Hanya aktif di Futures)
        stop_loss = entry_level + (atr * 1.5)
        take_profit = entry_level - (atr * 2.0)
        
    raw_sl_pct = abs((stop_loss - entry_level) / entry_level) * 100
    raw_tp_pct = abs((take_profit - entry_level) / entry_level) * 100
    
    # Implementasi pengali daya ungkit jika masuk area Futures
    multiplier = lev if m_type == "Futures" else 1
    leverage_tp_pct = raw_tp_pct * multiplier
    leverage_sl_pct = raw_sl_pct * multiplier
    
    return {
        "entry": round(entry_level, 4),
        "sl": round(stop_loss, 4),
        "tp": round(take_profit, 4),
        "raw_sl_pct": round(raw_sl_pct, 2),
        "raw_tp_pct": round(raw_tp_pct, 2),
        "lev_tp_pct": round(leverage_tp_pct, 2),
        "lev_sl_pct": round(leverage_sl_pct, 2)
    }

trading_strategy = generate_trading_plan(final_signal, live_price, latest_atr, selected_market, leverage_factor)

# ──────────────────────────────────────────────────────────────────────────────
#  9. UI DASHBOARD RENDERING DESIGN
# ──────────────────────────────────────────────────────────────────────────────
st.title("🔮 AI TRADING HUNTER v3.0.0")
st.caption(f"Arsitektur Data: Hybrid Logic (Mathematical Formula + Gemini Pro Context Engine) | Bursa Terkoneksi: Binance {selected_market}")

# Row 1: Real-Time Metric Tickers
m_col1, m_col2, m_col3, m_col4 = st.columns(4)
m_col1.metric(f"Harga Live {crypto_asset}", f"${live_price:,} USDT", f"{live_change:.2f}%" if selected_market == "Spot" else "Futures Live")
m_col2.metric("Relative Strength Index (RSI)", f"{latest_rsi:.2f}", "Overbought" if latest_rsi > 70 else "Oversold" if latest_rsi < 30 else "Neutral")
m_col3.metric("Trend EMA 20/50", f"{'Bullish Cross' if latest_ema20 > latest_ema50 else 'Bearish Cross'}")
m_col4.metric("MACD Convergence", f"{latest_macd_line:.4f}", "Divergence Atas" if latest_macd_line > latest_macd_sig else "Divergence Bawah")

st.markdown("---")

# Row 2: Layout Utama Konten (Tabbed View)
tab_dashboard, tab_strategy, tab_history = st.tabs(["📊 Analytics Dashboard", "📋 Strategy Execution", "📜 Simulation Ledger"])

with tab_dashboard:
    col_graph, col_signal = st.columns([6, 4])
    
    with col_graph:
        # Pembuatan Grafik Lilin Kuantitatif Pro Komplit
        fig_candles = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_width=[0.3, 0.7])
        
        # Candlestick Trace
        fig_candles.add_trace(go.Candlestick(
            x=df_market["timestamp"], open=df_market["open"], high=df_market["high"],
            low=df_market["low"], close=df_market["close"], name="Candlestick"
        ), row=1, col=1)
        
        # Line Indicator Traces
        fig_candles.add_trace(go.Scatter(x=df_market["timestamp"], y=df_market["ema20"], line=dict(color='#ffaa00', width=1.5), name="EMA 20"), row=1, col=1)
        fig_candles.add_trace(go.Scatter(x=df_market["timestamp"], y=df_market["ema50"], line=dict(color='#00e6ff', width=1.5), name="EMA 50"), row=1, col=1)
        
        # Volume Trace
        fig_candles.add_trace(go.Bar(x=df_market["timestamp"], y=df_market["volume"], name="Volume", marker_color="#21262d"), row=2, col=1)
        
        fig_candles.update_layout(
            template="plotly_dark",
            height=420,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", ylink=1.1, y=1.05, x=0)
        )
        st.plotly_chart(fig_candles, use_container_width=True)
        
    with col_signal:
        # Penentuan Kelas Desain Kotak Sinyal
        box_style = "sig-buy" if final_signal == "BUY" else "sig-sell" if final_signal == "SELL" else "sig-hold"
        
        # Penamaan Label Sesuai Struktur Pasar
        display_label = final_signal
        if selected_market == "Futures":
            if final_signal == "BUY": display_label = "LONG (BUY)"
            elif final_signal == "SELL": display_label = "SHORT (SELL)"
            
        st.markdown(f"""
        <div class="signal-container {box_style}">
            <p class="signal-title">DIAGNOSIS OPTIMASI AI</p>
            <p class="signal-text">{display_label}</p>
            <p style="margin:8px 0 0 0; font-size:14px;">{ai_analysis.get('reason')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("#### 🧠 AI ANALYTICAL INSIGHTS:")
        for dynamic_insight in ai_analysis.get("insights", []):
            st.markdown(f"🔹 {dynamic_insight}")
            
        # Tampilkan Status Kondisi Teknikal Lokal Berupa Badgesc
        st.markdown("<br><b>Kondisi Matematika Saat Ini:</b>", unsafe_allow_html=True)
        if latest_rsi > 65: st.markdown('<span class="badge badge-red">RSI Overbought</span>', unsafe_allow_html=True)
        elif latest_rsi < 35: st.markdown('<span class="badge badge-green">RSI Oversold</span>', unsafe_allow_html=True)
        else: st.markdown('<span class="badge badge-neutral">RSI Netral</span>', unsafe_allow_html=True)
        
        if latest_ema20 > latest_ema50: st.markdown('<span class="badge badge-green">EMA Bullish Trend</span>', unsafe_allow_html=True)
        else: st.markdown('<span class="badge badge-red">EMA Bearish Trend</span>', unsafe_allow_html=True)

with tab_strategy:
    if trading_strategy:
        col_plan_left, col_plan_right = st.columns(2)
        
        with col_plan_left:
            st.markdown(f"""
            <div class="tp-card">
                <h4 style="margin:0 0 12px 0; color:#58a6ff;">🎯 TRADING TARGET EXECUTION</h4>
                <div class="tp-row"><span>Entry Price Target</span><b>${trading_strategy['entry']:,} USDT</b></div>
                <div class="tp-row"><span>Kalkulasi Batas Stop Loss</span><b style="color:#f85149;">${trading_strategy['sl']:,} USDT</b></div>
                <div class="tp-row"><span>Kalkulasi Target Take Profit</span><b style="color:#3fb950;">${trading_strategy['tp']:,} USDT</b></div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_plan_right:
            st.markdown(f"""
            <div class="tp-card">
                <h4 style="margin:0 0 12px 0; color:#58a6ff;">⚡ LEVERAGE RISK & PnL PROJECTION</h4>
                <div class="tp-row"><span>Pergerakan Harga Murni Koin</span><b>{trading_strategy['raw_tp_pct']}%</b></div>
                <div class="tp-row"><span>Beban Daya Ungkit (Leverage)</span><b>{leverage_factor}x</b></div>
                <div class="tp-row"><span>Projeksi Bersih Keuntungan (TP)</span><b style="color:#3fb950;">+{trading_strategy['lev_tp_pct']}%</b></div>
                <div class="tp-row"><span>Projeksi Risiko Kerugian (SL)</span><b style="color:#f85149;">-{trading_strategy['lev_sl_pct']}%</b></div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Tombol Eksekusi Simulasi Berdasarkan Batas Aturan Pasar
        order_action_label = f"Eksekusi Posisi Simulasi (Alokasi Modal $10)"
        if st.button(order_action_label, use_container_width=True):
            fixed_cost = 10.0
            
            if selected_market == "Spot":
                if final_signal == "BUY" and st.session_state["wallet_spot"] >= fixed_cost:
                    st.session_state["wallet_spot"] -= fixed_cost
                    st.session_state["trade_logs"].append({
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "market": "Spot Market",
                        "type": "BUY / LONG",
                        "allocated": f"${fixed_cost} USDT",
                        "note": "Aset Spot Berhasil Disimpan"
                    })
                    st.success(f"🎉 Posisi Simulasi Spot dibuka! Saldo Spot Anda dipotong sebesar ${fixed_cost}.")
                else:
                    st.error("Gagal melakukan simulasi! Saldo Spot Wallet tidak mencukupi atau Sinyal AI dalam kondisi HOLD.")
            else:
                # Mode Logika Simulasi Akurat Bursa Futures
                if st.session_state["wallet_futures"] >= fixed_cost:
                    st.session_state["wallet_futures"] -= fixed_cost
                    f_direction = "LONG" if final_signal == "BUY" else "SHORT"
                    total_size_position = fixed_cost * leverage_factor
                    
                    st.session_state["trade_logs"].append({
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "market": f"Futures ({leverage_factor}x)",
                        "type": f_direction,
                        "allocated": f"${fixed_cost} USDT Margin",
                        "note": f"Mengontrol Posisi Kontrak Senilai ${total_size_position} USDT"
                    })
                    st.success(f"🎉 Posisi Kontrak Futures {f_direction} Berhasil Dibuka! Margin Terkunci: ${fixed_cost} USDT.")
                else:
                    st.error("Gagal melakukan simulasi! Saldo Dompet Futures Anda kurang dari $10.")
    else:
        st.info("💡 Sinyal Berada di Posisi HOLD. Algoritma hibrida menilai market belum memiliki momentum mikro yang aman untuk masuk.")

with tab_history:
    col_hist_left, col_hist_right = st.columns([7, 3])
    
    with col_hist_left:
        st.markdown("#### 📜 LOG TRANSAKSI SIMULASI")
        if not st.session_state["trade_logs"]:
            st.caption("Belum ada aktivitas perdagangan hari ini.")
        else:
            for log in reversed(st.session_state["trade_logs"]):
                st.info(f"⏱️ **{log['timestamp']}** | Bursa: `{log['market']}` | Sinyal: **{log['type']}** | Dana: `{log['allocated']}` — *{log['note']}*")
                
    with col_hist_right:
        st.markdown("#### 🔄 RESET CORE ENGINE")
        if st.button("Reset Seldo Simulasi ($50+$50)", use_container_width=True):
            st.session_state["wallet_spot"] = 50.0
            st.session_state["wallet_futures"] = 50.0
            st.session_state["trade_logs"] = []
            st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
#  10. INTERACTIVE AUTOMATED REFRESH LOOP LOOP
# ──────────────────────────────────────────────────────────────────────────────
if st.sidebar.checkbox("Aktifkan Auto Refresh (30s)", value=st.session_state["loop_refresh"]):
    st.session_state["loop_refresh"] = True
    time.sleep(30)
    st.rerun()
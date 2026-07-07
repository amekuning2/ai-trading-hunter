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
#  1. CONFIG & THEME SETUP
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MT5 AI Simple Dashboard V1.0",
    page_icon="⚡",
    layout="centered", # Cocok untuk tampilan mobile maupun desktop ringkas
    initial_sidebar_state="expanded"
)

# Custom CSS untuk gaya premium dark mode, tombol trading berwarna tegas, dan metric card yang rapi
st.markdown("""
<style>
    /* Global styling */
    .stApp { background-color: #0d1117; color: #e6edf3; }
    
    /* Metric Cards */
    [data-testid="metric-container"] {
        background: #161b22; 
        border: 1px solid #30363d;
        border-radius: 10px; 
        padding: 12px 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.15);
    }
    [data-testid="metric-container"] label {
        color: #8b949e !important; 
        font-size: 11px;
        text-transform: uppercase; 
        letter-spacing: 0.8px;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #e6edf3; 
        font-size: 20px; 
        font-weight: 700;
    }
    
    /* Box Info Panel */
    .info-panel {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
    }
    
    /* AI Signal Card Style */
    .ai-card {
        background: linear-gradient(135deg, #1b223c 0%, #111827 100%);
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 15px;
    }
    
    /* Status Badge styling */
    .badge-green { background-color: #2ea043; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }
    .badge-red { background-color: #da3633; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Inisialisasi Session States
if "ai_analysis" not in st.session_state:
    st.session_state["ai_analysis"] = None
if "ai_last_update" not in st.session_state:
    st.session_state["ai_last_update"] = None
if "ai_source" not in st.session_state:
    st.session_state["ai_source"] = "NONE" # "GEMINI", "LOCAL", atau "NONE"
if "applied_sl" not in st.session_state:
    st.session_state["applied_sl"] = 0.0
if "applied_tp" not in st.session_state:
    st.session_state["applied_tp"] = 0.0

# ─────────────────────────────────────────────────────────────────────────────
#  2. KONEKSI & UTILITY METATRADER 5
# ─────────────────────────────────────────────────────────────────────────────
def init_mt5():
    """Menginisialisasi koneksi ke terminal MT5."""
    if not mt5.initialize():
        return False
    return True

def get_filling_mode(symbol):
    """Mendapatkan mode pengisian (filling mode) yang didukung broker untuk meminimalisir error 10030."""
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return mt5.ORDER_FILLING_FOK
    
    filling = symbol_info.filling_mode
    if filling & mt5.SYMBOL_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK
    elif filling & mt5.SYMBOL_FILLING_IOC:
        return mt5.ORDER_FILLING_IOC
    else:
        return mt5.ORDER_FILLING_RETURN

def check_and_add_symbol(symbol):
    """Mengecek ketersediaan simbol dan memastikan simbol aktif di Market Watch MT5."""
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        st.error(f"⚠️ Simbol **{symbol}** tidak ditemukan di broker Anda. Cek kembali penamaannya (misal: ada tambahan .m, .i, atau _c).")
        return False
    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            st.error(f"⚠️ Gagal mengaktifkan {symbol} di Market Watch MT5.")
            return False
    return True

# Map Timeframe dari Dropdown ke Konstanta MT5
TIMEFRAME_MAP = {
    "1 Menit (M1)": (mt5.TIMEFRAME_M1, "M1"),
    "5 Menit (M5)": (mt5.TIMEFRAME_M5, "M5"),
    "15 Menit (M15)": (mt5.TIMEFRAME_M15, "M15"),
    "30 Menit (M30)": (mt5.TIMEFRAME_M30, "M30"),
    "1 Jam (H1)": (mt5.TIMEFRAME_H1, "H1"),
    "4 Jam (H4)": (mt5.TIMEFRAME_H4, "H4"),
    "1 Hari (D1)": (mt5.TIMEFRAME_D1, "D1")
}

# ─────────────────────────────────────────────────────────────────────────────
#  3. FUNGSI ANALISIS DATA & AI / LOCAL FALLBACK ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def fetch_and_calculate_indicators(symbol, timeframe_mt5, count=100):
    """Mengambil harga historis dan menghitung indikator teknikal + volatilitas ATR dengan aman."""
    rates = mt5.copy_rates_from_pos(symbol, timeframe_mt5, 0, count)
    if rates is None or len(rates) < 50:
        return None
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Kalkulasi Indikator Tren & Momentum
    df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
    df['ema_200'] = ta.trend.ema_indicator(df['close'], window=200)
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    
    macd_indicator = ta.trend.MACD(df['close'])
    df['macd_line'] = macd_indicator.macd()
    df['macd_signal'] = macd_indicator.macd_signal()
    
    # Kalkulasi Volatilitas ATR untuk menentukan target SL/TP aman (Strategi khusus user)
    df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    
    return df

def calculate_local_fallback_signal(df, symbol):
    """Menghitung sinyal trading secara matematis menggunakan EMA, RSI, MACD, dan ATR saat Gemini API Limit."""
    if df is None or len(df) < 50:
        return {
            "rekomendasi": "WAIT",
            "confidence": 0,
            "entry_price": 0.0,
            "sl": 0.0,
            "tp": 0.0,
            "analisis_tren": "Data tidak cukup.",
            "analisis_rsi_macd": "-",
            "analisis_candlestick": "-",
            "kesimpulan": "Data pasar MT5 tidak memadai untuk kalkulasi lokal."
        }
    
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    atr = last_row['atr']
    close_price = last_row['close']
    
    # Aturan Tren Berdasarkan EMA Crossover & Harga
    is_bullish_trend = last_row['close'] > last_row['ema_50'] and last_row['ema_50'] > last_row['ema_200']
    is_bearish_trend = last_row['close'] < last_row['ema_50'] and last_row['ema_50'] < last_row['ema_200']
    
    # Aturan Momentum
    macd_cross_up = last_row['macd_line'] > last_row['macd_signal'] and prev_row['macd_line'] <= prev_row['macd_signal']
    macd_cross_down = last_row['macd_line'] < last_row['macd_signal'] and prev_row['macd_line'] >= prev_row['macd_signal']
    
    rsi_low = last_row['rsi'] < 42
    rsi_high = last_row['rsi'] > 58
    
    rekomendasi = "WAIT"
    confidence = 50
    sl = 0.0
    tp = 0.0
    
    # Eksekusi Sinyal BUY (Mengikuti strategi user: Tighter TP & Wider SL)
    if is_bullish_trend and (macd_cross_up or rsi_low):
        rekomendasi = "BUY"
        confidence = 78 if (macd_cross_up and rsi_low) else 68
        # SL ditaruh aman di bawah ayunan harga (1.5x ATR)
        sl = close_price - (1.5 * atr)
        # TP ditaruh lebih dekat (1.2x ATR) untuk probabilitas kena yang jauh lebih tinggi
        tp = close_price + (1.2 * atr)
        
    # Eksekusi Sinyal SELL
    elif is_bearish_trend and (macd_cross_down or rsi_high):
        rekomendasi = "SELL"
        confidence = 78 if (macd_cross_down and rsi_high) else 68
        sl = close_price + (1.5 * atr)
        tp = close_price - (1.2 * atr)
        
    # Sinyal Counter-Trend Ringan jika RSI menyentuh level ekstrem
    elif last_row['rsi'] < 30:
        rekomendasi = "BUY"
        confidence = 60
        sl = close_price - (1.2 * atr)
        tp = close_price + (1.0 * atr)
    elif last_row['rsi'] > 70:
        rekomendasi = "SELL"
        confidence = 60
        sl = close_price + (1.2 * atr)
        tp = close_price - (1.0 * atr)
        
    # Ambil presisi digit desimal dari broker agar harga akurat
    symbol_info = mt5.symbol_info(symbol)
    digits = symbol_info.digits if symbol_info else 5
    
    return {
        "rekomendasi": rekomendasi,
        "confidence": confidence,
        "entry_price": round(close_price, digits),
        "sl": round(sl, digits) if sl > 0 else 0.0,
        "tp": round(tp, digits) if tp > 0 else 0.0,
        "analisis_tren": f"EMA50 ({last_row['ema_50']:.5f}) berada {'di atas' if last_row['ema_50'] > last_row['ema_200'] else 'di bawah'} EMA200 ({last_row['ema_200']:.5f})",
        "analisis_rsi_macd": f"RSI berada di level {last_row['rsi']:.2f}. MACD Line: {last_row['macd_line']:.5f} vs Signal: {last_row['macd_signal']:.5f}",
        "analisis_candlestick": f"Volatilitas ATR (14): {atr:.5f}. Menggunakan multiplier risiko aman khusus.",
        "kesimpulan": "Kalkulator lokal mendeteksi peluang masuk aman dengan menargetkan rasio target presisi demi akurasi transaksi harian Anda."
    }

def ask_gemini_for_signal(api_key, symbol, timeframe_label, df):
    """Memanggil Gemini API untuk mendapatkan sinyal terstruktur tanpa me-refresh otomatis."""
    if not api_key:
        return {"error": "API Key Gemini kosong."}
    
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    # 5 baris terakhir untuk pola candlestick
    recent_candles = []
    for i in range(-5, 0):
        row = df.iloc[i]
        recent_candles.append({
            "time": str(row['time']),
            "open": float(row['open']),
            "high": float(row['high']),
            "low": float(row['low']),
            "close": float(row['close']),
            "vol": int(row['real_volume'])
        })
    
    prompt = f"""
    Bertindaklah sebagai analis Forex profesional senior dan sistem AI pembuat sinyal otomatis.
    Analisis data pasar saat ini untuk instrumen {symbol} pada timeframe {timeframe_label}.

    INFORMASI UTAMA SAAT INI:
    - Close Terakhir: {last_row['close']:.5f} (Sebelumnya: {prev_row['close']:.5f})
    - EMA 50: {last_row['ema_50']:.5f}
    - EMA 200: {last_row['ema_200']:.5f}
    - RSI (14): {last_row['rsi']:.2f}
    - MACD Line: {last_row['macd_line']:.5f} | Signal Line: {last_row['macd_signal']:.5f}
    - ATR (14): {last_row['atr']:.5f}

    5 LILIN TERAKHIR:
    {json.dumps(recent_candles, indent=2)}

    TUGAS ANDA:
    Berikan keputusan trading taktis yang matang (BUY, SELL, atau WAIT).
    Gunakan kalkulasi aman yang realistis untuk SL/TP. Jika keputusannya BUY atau SELL, berikan saran harga Entry, Stop Loss (SL), dan Take Profit (TP) yang logis.
    Target TP sebaiknya lebih rapat (tighter) dibanding SL untuk mempertahankan win-rate tinggi di timeframe M15/H1.

    Format keluaran HARUS berupa objek JSON murni (tanpa format markdown tambahan, tanpa tanda ```json) dengan struktur persis seperti ini:
    {{
      "rekomendasi": "BUY / SELL / WAIT",
      "confidence": 85,
      "entry_price": 1.08542,
      "sl": 1.08200,
      "tp": 1.09200,
      "analisis_tren": "Deskripsi tren berdasarkan EMA 50 dan EMA 200",
      "analisis_rsi_macd": "Deskripsi momentum berdasarkan RSI dan MACD",
      "analisis_candlestick": "Deskripsi pola harga dari candle",
      "kesimpulan": "Rangkuman taktis"
    }}
    """
    
    try:
        genai.configure(api_key=api_key)
        # Menggunakan model default yang disarankan dan hemat energi/biaya
        model = genai.GenerativeModel("gemini-3.1-flash-lite")
        
        response = model.generate_content(prompt)
        text_response = response.text.strip()
        
        if text_response.startswith("```json"):
            text_response = text_response.replace("```json", "").replace("```", "").strip()
        elif text_response.startswith("```"):
            text_response = text_response.replace("```", "").strip()
            
        result_json = json.loads(text_response)
        return result_json
    except Exception as e:
        return {"error": f"API Limit/Error: {str(e)}"}

# ─────────────────────────────────────────────────────────────────────────────
#  4. FUNGSI EKSEKUSI TRADING MT5
# ─────────────────────────────────────────────────────────────────────────────
def execute_trade(action_type, symbol, lot, sl=0.0, tp=0.0):
    """Mengirimkan perintah BUY atau SELL langsung ke MetaTrader 5 dengan pengisian instan."""
    if not init_mt5():
        return False, "MT5 tidak terhubung."
    
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return False, f"Tidak bisa mendapatkan harga terbaru untuk {symbol}"
    
    price = tick.ask if action_type == mt5.ORDER_TYPE_BUY else tick.bid
    filling_mode = get_filling_mode(symbol)
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lot),
        "type": action_type,
        "price": float(price),
        "deviation": 20,
        "magic": 998877,
        "comment": "Simple AI Trading Dashboard",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }
    
    if sl > 0:
        request["sl"] = float(sl)
    if tp > 0:
        request["tp"] = float(tp)
        
    result = mt5.order_send(request)
    if result is None:
        return False, "Order gagal dikirim. Respon MT5 kosong."
        
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return False, f"Gagal! Kode error: {result.retcode} - {result.comment}"
        
    return True, f"Berhasil membuka posisi { 'BUY' if action_type == mt5.ORDER_TYPE_BUY else 'SELL' } sebanyak {lot} Lot."

def close_active_position(position):
    """Menutup satu posisi perdagangan aktif secara instan."""
    symbol = position.symbol
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return False, "Gagal mendapatkan harga untuk penutupan."
        
    order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": position.volume,
        "type": order_type,
        "position": position.ticket,
        "price": price,
        "deviation": 20,
        "magic": 998877,
        "comment": "Tutup Posisi Manual",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": get_filling_mode(symbol)
    }
    
    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        return True, "Posisi berhasil ditutup."
    return False, f"Gagal menutup posisi: {result.comment}"

# ─────────────────────────────────────────────────────────────────────────────
#  5. USER INTERFACE (SIDEBAR CONTROLS)
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #388bfd;'>🛠️ CONFIG PANEL</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Deteksi API Key dari secrets.toml secara cerdas & aman
    api_key_env = ""
    if "GEMINI_API_SIMPLE" in st.secrets:
        api_key_env = st.secrets["GEMINI_API_SIMPLE"]
    elif "GEMINI_API_KEY" in st.secrets:
        api_key_env = st.secrets["GEMINI_API_KEY"]
    else:
        api_key_env = os.environ.get("GEMINI_API_SIMPLE", os.environ.get("GEMINI_API_KEY", ""))
        
    gemini_key = st.text_input("🔑 Gemini API Key", value=api_key_env, type="password", 
                               placeholder="Masukkan API Key Gemini Anda di sini")
    
    # Pemilihan Simbol & Timeframe
    st.subheader("📊 Instrumen & Chart")
    symbol_input = st.text_input("Simbol Trading", value="EURUSD", help="Sesuaikan dengan nama simbol di broker Anda (cth: EURUSD, GBPUSD, XAUUSD)").upper()
    timeframe_choice = st.selectbox("Timeframe Analisis", list(TIMEFRAME_MAP.keys()), index=2) # Default ke M15 seperti yang sering dipakai user
    
    # Parameter Eksekusi Trading
    st.subheader("💰 Parameter Transaksi")
    trade_lot = st.number_input("Lot Volume", min_value=0.01, max_value=10.0, value=0.10, step=0.01)
    
    st.markdown("---")
    # Manual Refresh seluruh halaman
    refresh_button = st.button("🔄 Refresh Data MT5 Manual", use_container_width=True, 
                               help="Gunakan tombol ini untuk memperbarui harga pasar, balance, dan posisi tanpa memakan kuota RPD AI.")
    
    st.markdown("""
    <div style="font-size:11px; color:#8b949e; background:#161b22; padding:10px; border-radius:6px; border:1px solid #30363d; margin-top:10px;">
        💡 <strong>Info Hemat RPD:</strong><br>
        • Untuk cek pergerakan harga atau balance, cukup klik tombol <strong>Refresh Data MT5 Manual</strong>.<br>
        • Klik <strong>Analisis AI Sekarang</strong> hanya jika Anda butuh sinyal baru dari Gemini.<br>
        • Jika kuota RPD Gemini habis, sistem otomatis beralih menggunakan kalkulasi formula lokal (ATR + EMA) tanpa macet!
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  6. MAIN DASHBOARD CONTENT
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align: center; margin-bottom: 2px;'>⚡ MT5 AI SIMPLE DASHBOARD</h1>", unsafe_allow_html=True)

# Inisialisasi MT5 & Ambil Data Akun
mt5_connected = init_mt5()
account_info = mt5.account_info() if mt5_connected else None

# Bar Status Koneksi Utama
if mt5_connected and account_info:
    status_color = "#2ea043"
    status_text = "🟢 TERHUBUNG KE MT5"
else:
    status_color = "#da3633"
    status_text = "🔴 MT5 DISCONNECTED (Buka aplikasi MT5 Anda di Windows)"

st.markdown(f"""
<div style="background:{status_color}; text-align:center; padding:6px; border-radius:6px; color:white; font-size:12px; font-weight:bold; margin-bottom:15px; letter-spacing:1px;">
    {status_text}
</div>
""", unsafe_allow_html=True)

if not mt5_connected or account_info is None:
    st.error("❌ Gagal terhubung ke terminal MetaTrader 5. Harap pastikan bahwa:")
    st.markdown("""
    1. Aplikasi **MetaTrader 5** sudah terbuka di komputer/laptop Windows Anda.
    2. Anda menjalankan skrip Python ini di komputer yang sama dengan terminal MT5 aktif.
    3. Akun trading Anda di MT5 sudah masuk (Logged In).
    """)
    st.stop()

# Tampilkan Informasi Akun di Baris Atas
col_acc1, col_acc2, col_acc3, col_acc4 = st.columns(4)
with col_acc1:
    st.metric(label="👤 Nama Akun", value=account_info.name)
with col_acc2:
    st.metric(label="💰 Balance", value=f"${account_info.balance:,.2f}")
with col_acc3:
    st.metric(label="📊 Equity", value=f"${account_info.equity:,.2f}")
with col_acc4:
    st.metric(label="📈 Floating P&L", value=f"${account_info.profit:,.2f}", 
              delta=f"${account_info.profit:,.2f}" if account_info.profit != 0 else None)

# Mempersiapkan data market
tf_mt5, tf_label = TIMEFRAME_MAP[timeframe_choice]
symbol_valid = check_and_add_symbol(symbol_input)

if symbol_valid:
    df_market = fetch_and_calculate_indicators(symbol_input, tf_mt5, 100)
    tick_info = mt5.symbol_info_tick(symbol_input)
    
    if df_market is None or tick_info is None:
        st.warning(f"⚠️ Gagal mengambil pergerakan harga untuk {symbol_input}. Tunggu beberapa saat atau coba ganti simbol.")
        df_market = pd.DataFrame()
    else:
        # Menampilkan Informasi Harga Saat Ini
        col_price1, col_price2, col_price3 = st.columns([1, 1.2, 1])
        with col_price1:
            st.metric(label=f"🔴 Bid ({symbol_input})", value=f"{tick_info.bid:.5f}")
        with col_price2:
            spread = (tick_info.ask - tick_info.bid) * (10 ** mt5.symbol_info(symbol_input).digits)
            st.metric(label="↔️ Spread (Pips / Points)", value=f"{spread:.1f}")
        with col_price3:
            st.metric(label=f"🟢 Ask ({symbol_input})", value=f"{tick_info.ask:.5f}")

        # Tampilkan Grafik Candlestick Sederhana & Ringan
        st.markdown("### 📊 Market Candlestick & EMA")
        chart_df = df_market.tail(40) # 40 Candlestick terakhir agar loading cepat
        fig = go.Figure(data=[
            go.Candlestick(
                x=chart_df['time'],
                open=chart_df['open'],
                high=chart_df['high'],
                low=chart_df['low'],
                close=chart_df['close'],
                name="Candlestick"
            ),
            go.Scatter(x=chart_df['time'], y=chart_df['ema_50'], name="EMA 50", line=dict(color='#ffc107', width=1.5)),
            go.Scatter(x=chart_df['time'], y=chart_df['ema_200'], name="EMA 200", line=dict(color='#17a2b8', width=1.5))
        ])
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=280,
            paper_bgcolor='#0d1117',
            plot_bgcolor='#0d1117',
            xaxis_rangeslider_visible=False,
            font=dict(color="#8b949e"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

        # ─────────────────────────────────────────────────────────────────────
        #  7. PANEL AI SIGNAL & ANALISIS (SISTEM CADANGAN OTOMATIS)
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("### 🧠 Gemini AI / Technical Decision Signal")
        
        # Area Tombol Picu Manual AI
        col_ai1, col_ai2 = st.columns([1.5, 1])
        with col_ai1:
            st.write("Dapatkan analisis teknikal komprehensif & rekomendasi SL/TP langsung dari Gemini AI atau Formula Lokal.")
        with col_ai2:
            trigger_ai = st.button("🧠 Analisis AI Sekarang", type="primary", use_container_width=True)
            
        if trigger_ai:
            if not gemini_key:
                # Fallback langsung ke kalkulasi formula lokal jika kunci API kosong
                st.info("ℹ️ API Key kosong. Menjalankan Kalkulasi Formula Lokal...")
                local_result = calculate_local_fallback_signal(df_market, symbol_input)
                st.session_state["ai_analysis"] = local_result
                st.session_state["ai_last_update"] = datetime.now().strftime("%H:%M:%S")
                st.session_state["ai_source"] = "LOCAL"
                
                # Set auto-populate ke state form order
                st.session_state["applied_sl"] = float(local_result.get("sl", 0.0))
                st.session_state["applied_tp"] = float(local_result.get("tp", 0.0))
                st.success("✅ Formula Teknikal Lokal Berhasil Diperbarui!")
            else:
                with st.spinner("Mengirim data pasar ke Gemini..."):
                    ai_result = ask_gemini_for_signal(gemini_key, symbol_input, tf_label, df_market)
                    
                    # Jika Gemini mengembalikan error atau terkena limit kuota RPD
                    if "error" in ai_result:
                        st.warning("⚠️ Gemini RPD Limit / Gagal Merespon. Mengalihkan ke Formula Teknikal Lokal...")
                        local_result = calculate_local_fallback_signal(df_market, symbol_input)
                        st.session_state["ai_analysis"] = local_result
                        st.session_state["ai_last_update"] = datetime.now().strftime("%H:%M:%S")
                        st.session_state["ai_source"] = "LOCAL"
                        
                        st.session_state["applied_sl"] = float(local_result.get("sl", 0.0))
                        st.session_state["applied_tp"] = float(local_result.get("tp", 0.0))
                        st.success("✅ Formula Teknikal Lokal (Fallback) Aktif!")
                    else:
                        st.session_state["ai_analysis"] = ai_result
                        st.session_state["ai_last_update"] = datetime.now().strftime("%H:%M:%S")
                        st.session_state["ai_source"] = "GEMINI"
                        
                        # Set auto-populate ke state form order
                        st.session_state["applied_sl"] = float(ai_result.get("sl", 0.0))
                        st.session_state["applied_tp"] = float(ai_result.get("tp", 0.0))
                        st.success("✅ Analisis Gemini AI Berhasil Diperbarui!")

        # Menampilkan Sinyal jika Tersedia di Session State
        if st.session_state["ai_analysis"]:
            res = st.session_state["ai_analysis"]
            rec = res.get("rekomendasi", "WAIT").upper()
            conf = res.get("confidence", 0)
            source = st.session_state["ai_source"]
            
            # Label pembeda sumber sinyal
            if source == "GEMINI":
                source_label = "🧠 GEMINI AI SIGNAL"
                border_color = "#388bfd"
                card_gradient = "linear-gradient(135deg, #1b223c 0%, #111827 100%)"
            else:
                source_label = "🧮 FORMULA CADANGAN LOKAL (Hemat RPD)"
                border_color = "#f0883e"
                card_gradient = "linear-gradient(135deg, #2b2015 0%, #111827 100%)"
            
            # Berikan warna berbeda berdasarkan rekomendasi
            if "BUY" in rec:
                color_text = "#2ea043"
            elif "SELL" in rec:
                color_text = "#da3633"
            else:
                color_text = "#8b949e"
                
            st.markdown(f"""
            <div class="ai-card" style="border: 1px solid {border_color}; background: {card_gradient};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <span style="font-size:14px; font-weight:bold; color:#e6edf3;">{source_label}</span>
                    <span style="font-size:11px; color:#8b949e;">Update: {st.session_state["ai_last_update"]}</span>
                </div>
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
                    <span style="font-size:20px; font-weight:800; color:{color_text};">{rec}</span>
                    <span style="background-color:#21262d; border:1px solid #30363d; padding:2px 8px; border-radius:6px; font-size:12px; color:#e6edf3; font-weight:bold;">
                        Confidence: {conf}%
                    </span>
                </div>
                <div style="font-size:13px; line-height:1.5; color:#c9d1d9;">
                    <p><strong>📈 Tren Pasar:</strong> {res.get('analisis_tren', '-')}</p>
                    <p><strong>⚡ RSI & MACD:</strong> {res.get('analisis_rsi_macd', '-')}</p>
                    <p><strong>🕯️ Deteksi Volatilitas:</strong> {res.get('analisis_candlestick', '-')}</p>
                    <p style="border-top: 1px solid #30363d; padding-top: 10px; margin-top: 10px; color:#8b949e;">
                        <strong>🎯 Rekomendasi Target:</strong><br>
                        Entry: <span style="color:#e6edf3; font-weight:bold;">{res.get('entry_price', 0.0)}</span> | 
                        SL: <span style="color:#da3633; font-weight:bold;">{res.get('sl', 0.0)}</span> | 
                        TP: <span style="color:#2ea043; font-weight:bold;">{res.get('tp', 0.0)}</span>
                    </p>
                    <p style="background:rgba(56,139,253,0.1); border-left:3px solid #388bfd; padding:8px; border-radius:4px; font-style:italic; font-size:12px; color:#58a6ff; margin-top:10px;">
                        "{res.get('kesimpulan', '-')}"
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Tombol Terapan Otomatis Nilai Sinyal ke Form Order
            if res.get('sl', 0.0) > 0 or res.get('tp', 0.0) > 0:
                if st.button("📥 Terapkan SL/TP dari Sinyal ke Form Order", use_container_width=True):
                    st.session_state["applied_sl"] = float(res.get("sl", 0.0))
                    st.session_state["applied_tp"] = float(res.get("tp", 0.0))
                    st.success("Target SL dan TP berhasil diterapkan ke form di bawah.")
        else:
            st.info("ℹ️ Belum ada analisis pasar aktif. Tekan tombol 'Analisis AI Sekarang' untuk menghitung sinyal.")

        # ─────────────────────────────────────────────────────────────────────
        #  8. ORDER EXECUTION PANEL
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("### 🛒 Panel Transaksi Pasar")
        
        # Grid Form Pengisian SL / TP
        col_ord1, col_ord2, col_ord3 = st.columns(3)
        with col_ord1:
            lot_input = st.number_input("Volume Transaksi (Lot)", min_value=0.01, max_value=10.0, value=trade_lot, key="execute_lot")
        with col_ord2:
            sl_input = st.number_input("Stop Loss (SL)", value=st.session_state["applied_sl"], format="%.5f")
        with col_ord3:
            tp_input = st.number_input("Take Profit (TP)", value=st.session_state["applied_tp"], format="%.5f")

        # Tombol Eksekusi BUY / SELL Gede Berwarna
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            buy_triggered = st.button("🟢 BUY MARKET", use_container_width=True, type="secondary")
            if buy_triggered:
                with st.spinner("Mengeksekusi Buy Order..."):
                    success, msg = execute_trade(mt5.ORDER_TYPE_BUY, symbol_input, lot_input, sl_input, tp_input)
                    if success:
                        st.success(msg)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)
        with col_act2:
            sell_triggered = st.button("🔴 SELL MARKET", use_container_width=True, type="secondary")
            if sell_triggered:
                with st.spinner("Mengeksekusi Sell Order..."):
                    success, msg = execute_trade(mt5.ORDER_TYPE_SELL, symbol_input, lot_input, sl_input, tp_input)
                    if success:
                        st.success(msg)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)

        # ─────────────────────────────────────────────────────────────────────
        #  9. DAFTAR POSISI AKTIF & MANAGEMENT
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("### 💼 Posisi Aktif Saat Ini")
        
        positions = mt5.positions_get()
        if positions is None or len(positions) == 0:
            st.info("Tidak ada transaksi aktif yang sedang berjalan di akun Anda.")
        else:
            # Konversi daftar posisi ke DataFrame untuk representasi yang rapi
            pos_data = []
            for pos in positions:
                pos_type = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
                pos_data.append({
                    "Ticket": pos.ticket,
                    "Simbol": pos.symbol,
                    "Tipe": pos_type,
                    "Lot": pos.volume,
                    "Entry Price": pos.price_open,
                    "Current Price": pos.price_current,
                    "S/L": pos.sl,
                    "T/P": pos.tp,
                    "Profit ($)": pos.profit,
                    "obj": pos # Menyimpan referensi objek posisi asli untuk fungsi close manual
                })
                
            pos_df = pd.DataFrame(pos_data)
            
            # Tampilkan Ringkasan Tabel Posisi
            st.dataframe(
                pos_df.drop(columns=["obj"]), 
                use_container_width=True,
                hide_index=True
            )
            
            # Aksi Penutupan Posisi Satuan / Masal
            col_manage1, col_manage2 = st.columns([1, 1])
            with col_manage1:
                # Menutup Posisi Berdasarkan Pilihan Ticket
                tickets = [p["Ticket"] for p in pos_data]
                selected_ticket = st.selectbox("Pilih No. Ticket untuk Ditutup Manual:", tickets)
                if st.button("🛑 Tutup Posisi Terpilih", use_container_width=True):
                    # Cari objek posisi berdasarkan ticket terpilih
                    target_pos = next((p["obj"] for p in pos_data if p["Ticket"] == selected_ticket), None)
                    if target_pos:
                        with st.spinner(f"Menutup posisi #{selected_ticket}..."):
                            success, msg = close_active_position(target_pos)
                            if success:
                                st.success(msg)
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(msg)
            with col_manage2:
                # Tombol Tutup Semua Posisi jika darurat
                st.write("") # Spacer agar sejajar dengan selectbox
                st.write("")
                if st.button("⚠️ TUTUP SEMUA TRANSAKSI SEKARANG", use_container_width=True, type="primary"):
                    closed_count = 0
                    errors = []
                    with st.spinner("Menutup semua posisi aktif..."):
                        for pos in positions:
                            success, msg = close_active_position(pos)
                            if success:
                                closed_count += 1
                            else:
                                errors.append(f"Ticket #{pos.ticket}: {msg}")
                    if closed_count > 0:
                        st.success(f"Berhasil menutup {closed_count} transaksi.")
                    if errors:
                        st.error("\n".join(errors))
                    time.sleep(1)
                    st.rerun()

else:
    st.error("Masukkan simbol terlebih dahulu untuk memulai pemantauan dashboard.")

# ─────────────────────────────────────────────────────────────────────────────
#  10. FOOTER & COPYRIGHT INFO
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align: center; font-size: 11px; color: #8b949e;'>"
    "⚡ MT5 Simple AI Dashboard &copy; 2026. Trade responsibly & manage your risks."
    "</p>", 
    unsafe_allow_html=True
)
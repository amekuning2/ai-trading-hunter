import streamlit as st
import pandas as pd
import MetaTrader5 as mt5
import ta
from datetime import datetime
from google import genai
import json

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="MT5 Lite v4.0",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp { background-color: #0e0e0e; color: #ffffff; }

    /* Hide default streamlit */
    #MainMenu, footer, header { visibility: hidden; }

    /* Price card */
    .price-card {
        background: #1a1a1a; border: 1px solid #2a2a2a;
        border-radius: 14px; padding: 16px 20px; margin: 8px 0;
    }
    .symbol-name { font-size: 16px; font-weight: 800; color: #fff; }
    .price-big-green { font-size: 30px; font-weight: 900; color: #22c55e; }
    .price-big-red   { font-size: 30px; font-weight: 900; color: #ef4444; }
    .price-label { font-size: 10px; color: #6b7280; text-transform: uppercase; letter-spacing: 1px; }
    .spread-val { font-size: 14px; font-weight: 700; color: #f97316; }

    /* Signal box */
    .sig-buy  { background:#0c1f0c; border:2px solid #22c55e; border-radius:14px; padding:20px; text-align:center; margin:8px 0; }
    .sig-sell { background:#1f0c0c; border:2px solid #ef4444; border-radius:14px; padding:20px; text-align:center; margin:8px 0; }
    .sig-hold { background:#0c0f1f; border:2px solid #3b82f6; border-radius:14px; padding:20px; text-align:center; margin:8px 0; }
    .sig-action-buy  { font-size: 40px; font-weight: 900; color: #22c55e; letter-spacing: 4px; margin: 6px 0; }
    .sig-action-sell { font-size: 40px; font-weight: 900; color: #ef4444; letter-spacing: 4px; margin: 6px 0; }
    .sig-action-hold { font-size: 40px; font-weight: 900; color: #3b82f6; letter-spacing: 4px; margin: 6px 0; }
    .sig-reason { color: #d1d5db; font-size: 13px; line-height: 1.5; margin-top: 6px; }
    .sig-conf   { color: #6b7280; font-size: 11px; margin-top: 6px; }
    .ai-badge   { font-size: 10px; color: #a78bfa; text-transform: uppercase; letter-spacing: 2px; }
    .formula-badge { font-size: 10px; color: #f97316; text-transform: uppercase; letter-spacing: 2px; }

    /* Level card */
    .lv-card {
        background: #1a1a1a; border: 1px solid #2a2a2a;
        border-radius: 12px; padding: 14px 16px; margin: 8px 0;
    }
    .lv-title { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
    .lv-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 7px 0; border-bottom: 1px solid #2a2a2a; font-size: 14px;
    }
    .lv-row:last-child { border-bottom: none; }
    .lv-label { color: #6b7280; }
    .lv-val   { color: #fff; font-weight: 700; }
    .c-green  { color: #22c55e !important; }
    .c-red    { color: #ef4444 !important; }
    .c-orange { color: #f97316 !important; }
    .c-yellow { color: #eab308 !important; }
    .c-purple { color: #a78bfa !important; }

    /* Bar */
    .bar-bg   { background:#2a2a2a; border-radius:20px; height:8px; margin:8px 0; overflow:hidden; }
    .bar-fill { height:100%; border-radius:20px; }

    /* Info */
    .info-bar {
        background:#1a1a1a; border:1px solid #2a2a2a;
        border-radius:8px; padding:10px 14px; font-size:12px; color:#6b7280; margin:6px 0;
    }

    /* Insight */
    .insight-card {
        background: linear-gradient(135deg,#1a1a2e,#16213e);
        border:1px solid #1e3a5f; border-left:4px solid #a78bfa;
        border-radius:12px; padding:16px; margin:8px 0;
    }
    .insight-item { color:#d1d5db; font-size:13px; margin-bottom:8px; line-height:1.6; }

    /* Empty state */
    .empty-state {
        background:#1a1a1a; border:1px solid #2a2a2a;
        border-radius:14px; padding:32px 20px; text-align:center; margin:16px 0;
    }

    /* Button */
    .stButton > button {
        background: linear-gradient(135deg,#ea580c,#f97316) !important;
        color: #fff !important; font-size: 17px !important; font-weight: 800 !important;
        height: 54px !important; border-radius: 12px !important;
        border: none !important; width: 100% !important; letter-spacing: 1px !important;
    }

    /* Metric */
    [data-testid="metric-container"] {
        background:#1a1a1a; border:1px solid #2a2a2a; border-radius:10px; padding:12px;
    }
    [data-testid="metric-container"] label { color:#6b7280 !important; font-size:11px !important; text-transform:uppercase; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { color:#fff; font-size:20px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  API SETUP
# ─────────────────────────────────────────────
try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_SIMPLE", "")
except Exception:
    GEMINI_API_KEY = ""

GEMINI_ENABLED = bool(GEMINI_API_KEY)
if GEMINI_ENABLED:
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

GEMINI_MODEL = "gemini-3.1-flash-lite"

# ─────────────────────────────────────────────
#  MT5 INIT
# ─────────────────────────────────────────────

def init_mt5():
    # Coba initialize beberapa kali kalau gagal pertama
    for attempt in range(3):
        if mt5.initialize():
            return True, None
        mt5.shutdown()
        import time; time.sleep(1)
    return False, mt5.last_error()

# Panggil TANPA cache_resource, atau kasih retry logic
if "mt5_connected" not in st.session_state:
    ok, err = init_mt5()
    st.session_state.mt5_connected = ok
    if not ok:
        st.error(f"Gagal konek MT5: {err}")
        if st.button("🔄 Retry Koneksi"):
            st.session_state.mt5_connected = False
            st.rerun()
        st.stop()

TIMEFRAME_MAP = {
    "1m":  mt5.TIMEFRAME_M1,
    "5m":  mt5.TIMEFRAME_M5,
    "15m": mt5.TIMEFRAME_M15,
    "1h":  mt5.TIMEFRAME_H1,
    "4h":  mt5.TIMEFRAME_H4,
}

if not init_mt5():
    st.error("❌ MT5 tidak terkoneksi. Pastikan MetaTrader5 berjalan di VPS.")
    st.stop()

# ─────────────────────────────────────────────
#  DATA FUNCTIONS
# ─────────────────────────────────────────────
def get_price(symbol):
    try:
        mt5.symbol_select(symbol, True)
        tick = mt5.symbol_info_tick(symbol)
        info = mt5.symbol_info(symbol)
        if not tick or not info:
            return None
        return {
            "bid":    round(tick.bid, info.digits),
            "ask":    round(tick.ask, info.digits),
            "spread": round((tick.ask - tick.bid) / info.point, 1),
            "digits": info.digits,
            "point":  info.point,
        }
    except:
        return None

def get_klines(symbol, interval, limit=200):
    try:
        tf    = TIMEFRAME_MAP.get(interval, mt5.TIMEFRAME_M15)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, limit)
        if rates is None or len(rates) == 0:
            return None
        df = pd.DataFrame(rates)
        df["timestamp"] = pd.to_datetime(df["time"], unit="s")
        df = df.rename(columns={"tick_volume": "volume"})
        for c in ["open","high","low","close","volume"]:
            df[c] = df[c].astype(float)
        return df
    except:
        return None

def get_sr(df, n=2):
    if df is None or len(df) < 20:
        return [], []
    price = df["close"].iloc[-1]
    highs = df["high"].rolling(5, center=True).max()
    lows  = df["low"].rolling(5, center=True).min()
    res, sup = [], []
    for i in range(len(df)):
        if df["high"].iloc[i] == highs.iloc[i]:
            res.append(df["high"].iloc[i])
        if df["low"].iloc[i] == lows.iloc[i]:
            sup.append(df["low"].iloc[i])
    res = sorted(set([round(r, 5) for r in res if r > price]))[:n]
    sup = sorted(set([round(s, 5) for s in sup if s < price]), reverse=True)[:n]
    return res, sup

# ─────────────────────────────────────────────
#  FORMULA FALLBACK ENGINE
#  Berdasarkan strategi demo trading lo:
#  XAUUSD: TP = entry + 1.5~2.0, SL = entry - 15~16
#  Pair lain: ATR-based
# ─────────────────────────────────────────────
def formula_signal(df, symbol, bid, digits):
    if df is None or len(df) < 50:
        return None
    close = df["close"]
    rsi   = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]
    macd  = ta.trend.MACD(close)
    mv    = macd.macd().iloc[-1]
    ms    = macd.macd_signal().iloc[-1]
    ema20 = ta.trend.EMAIndicator(close, window=20).ema_indicator().iloc[-1]
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]
    atr   = ta.volatility.AverageTrueRange(df["high"], df["low"], close, window=14).average_true_range().iloc[-1]

    # Tentukan arah
    bull = sum([bid > ema20, bid > ema50, mv > ms, rsi < 60])
    bear = sum([bid < ema20, bid < ema50, mv < ms, rsi > 40])

    is_xau = "XAU" in symbol or "GOL" in symbol
    is_jpy = "JPY" in symbol

    if bull >= 3:
        action = "BUY"
        entry  = round(bid, digits)
        if is_xau:
            # Strategi lo: TP kecil ~1.5-2.0, SL jauh ~15-16
            tp1 = round(entry + 1.5, digits)
            tp2 = round(entry + 2.5, digits)
            sl  = round(entry - 16.0, digits)
        elif is_jpy:
            tp1 = round(entry + (atr * 0.8), digits)
            tp2 = round(entry + (atr * 1.3), digits)
            sl  = round(entry - (atr * 1.5), digits)
        else:
            tp1 = round(entry + (atr * 0.8), digits)
            tp2 = round(entry + (atr * 1.3), digits)
            sl  = round(entry - (atr * 1.5), digits)
    elif bear >= 3:
        action = "SELL"
        entry  = round(bid, digits)
        if is_xau:
            tp1 = round(entry - 1.5, digits)
            tp2 = round(entry - 2.5, digits)
            sl  = round(entry + 16.0, digits)
        elif is_jpy:
            tp1 = round(entry - (atr * 0.8), digits)
            tp2 = round(entry - (atr * 1.3), digits)
            sl  = round(entry + (atr * 1.5), digits)
        else:
            tp1 = round(entry - (atr * 0.8), digits)
            tp2 = round(entry - (atr * 1.3), digits)
            sl  = round(entry + (atr * 1.5), digits)
    else:
        return {
            "action": "HOLD", "entry": bid, "tp1": 0, "tp2": 0, "sl": 0,
            "reason": "Market sideways — tidak ada setup yang cukup jelas saat ini.",
            "insights": [], "source": "formula", "confidence": 40,
        }

    pip_m = 1.0 if is_xau else 100 if is_jpy else 10000
    rsi_note = "RSI oversold" if rsi < 35 else "RSI overbought" if rsi > 65 else f"RSI {rsi:.0f}"

    return {
        "action":     action,
        "entry":      entry,
        "tp1":        tp1,
        "tp2":        tp2,
        "sl":         sl,
        "confidence": min(int((max(bull, bear) / 4) * 80 + 20), 85),
        "reason":     f"{'Bullish' if action=='BUY' else 'Bearish'} — EMA + MACD + {rsi_note} konfirmasi arah.",
        "insights":   [
            f"EMA20={ema20:.{digits}f} EMA50={ema50:.{digits}f} — {'price above' if bid > ema50 else 'price below'} EMA",
            f"MACD {'bullish cross' if mv > ms else 'bearish cross'}, RSI {rsi:.1f}",
            f"ATR={atr:.{digits}f} — SL/TP dihitung dari pola scalping {'XAUUSD' if is_xau else 'forex'}",
        ],
        "source":     "formula",
        "pair_reco":  "",
    }

# ─────────────────────────────────────────────
#  GEMINI AI ANALYSIS — dipanggil manual saja
# ─────────────────────────────────────────────
def call_gemini(symbol, interval, trading_mode, df, bid, ask, spread, digits, res, sup):
    close  = df["close"]
    fmt    = f".{digits}f"
    rsi    = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]
    macd_i = ta.trend.MACD(close)
    mv, ms = macd_i.macd().iloc[-1], macd_i.macd_signal().iloc[-1]
    ema20  = ta.trend.EMAIndicator(close, window=20).ema_indicator().iloc[-1]
    ema50  = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]
    ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator().iloc[-1] if len(close)>=200 else ema50
    bb     = ta.volatility.BollingerBands(close, window=20)
    bb_pos = ((bid - bb.bollinger_lband().iloc[-1]) / max(bb.bollinger_hband().iloc[-1] - bb.bollinger_lband().iloc[-1], 0.0001)) * 100
    atr    = ta.volatility.AverageTrueRange(df["high"], df["low"], close, window=14).average_true_range().iloc[-1]
    vol_r  = df["volume"].iloc[-1] / max(df["volume"].rolling(20).mean().iloc[-1], 0.0001)
    ohlcv  = "\n".join([f"[{i}] O={r.open:{fmt}} H={r.high:{fmt}} L={r.low:{fmt}} C={r.close:{fmt}}"
                         for i, r in enumerate(df.tail(5).itertuples())])

    is_xau = "XAU" in symbol or "GOL" in symbol
    xau_note = """
PENTING untuk XAUUSD: 
- TP kecil sangat efektif: +1.5 sampai +2.5 dari entry sudah bagus
- SL jauh dari entry: minimal -15 dari entry agar tidak kena noise
- Strategi terbukti: BUY 4187 → TP 4189 (+2) sudah dapat $197 profit per lot
""" if is_xau else ""

    mode_ctx = {
        "Aggressive": "AGGRESSIVE: entry sering, profit kecil tapi rutin. Ada momentum minimal → BUY/SELL.",
        "Scalping":   "SCALPING M15: cari setup clean, TP cepat, SL anti-noise.",
        "Intraday":   "INTRADAY: balance kualitas dan frekuensi, butuh 2+ konfirmasi.",
    }.get(trading_mode, "")

    prompt = f"""
Kamu adalah AI Trading Analyst untuk Forex MT5.
Analisis data berikut dan beri keputusan trading actionable.

PAIR: {symbol} | TF: {interval}
HARGA: Bid={bid:{fmt}} Ask={ask:{fmt}} Spread={spread:.0f} pts

INDIKATOR:
RSI={rsi:.1f} | MACD={mv:.{digits}f} vs Signal={ms:.{digits}f}
EMA20={ema20:.{digits}f} EMA50={ema50:.{digits}f} EMA200={ema200:.{digits}f}
BB={bb_pos:.0f}% | Volume={vol_r:.2f}x | ATR={atr:.{digits}f}
Support={sup} | Resistance={res}

5 CANDLE TERAKHIR:
{ohlcv}

MODE: {mode_ctx}
{xau_note}

Beri keputusan trading. Ada peluang → BUY/SELL. Tidak ada → HOLD.

BALAS HANYA JSON:
{{
  "action": "BUY"/"SELL"/"HOLD",
  "confidence": 0-100,
  "entry": angka,
  "tp1": angka,
  "tp2": angka,
  "sl": angka,
  "reason": "1-2 kalimat santai bahasa Indonesia",
  "insights": ["poin1","poin2","poin3"],
  "pair_reco": "rekomendasikan pair lain kalau pair ini tidak menarik, atau kosong"
}}
"""
    try:
        model    = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt, generation_config={"response_mime_type":"application/json"})
        data     = json.loads(response.text.strip())
        return {
            "action":     data.get("action","HOLD"),
            "confidence": int(data.get("confidence", 0)),
            "entry":      float(data.get("entry", bid)),
            "tp1":        float(data.get("tp1", 0)),
            "tp2":        float(data.get("tp2", 0)),
            "sl":         float(data.get("sl", 0)),
            "reason":     data.get("reason",""),
            "insights":   data.get("insights",[]),
            "pair_reco":  data.get("pair_reco",""),
            "source":     "gemini",
            "timestamp":  datetime.now().strftime("%H:%M:%S"),
        }
    except Exception as e:
        return None

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
for k, v in {
    "result": None,
    "last_symbol": "XAUUSD",
    "last_mode": "Aggressive",
    "last_tf": "15m",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────
st.markdown("## 📊 MT5 Lite v4.0")

# ─────────────────────────────────────────────
#  CONTROLS
# ─────────────────────────────────────────────
PAIRS = ["XAUUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","NZDUSD","GBPJPY","EURJPY"]

col1, col2 = st.columns(2)
with col1:
    symbol = st.selectbox("🪙 Pair", PAIRS,
        index=PAIRS.index(st.session_state["last_symbol"])
        if st.session_state["last_symbol"] in PAIRS else 0)
with col2:
    trading_mode = st.selectbox("⚙️ Mode", ["Aggressive","Scalping","Intraday"],
        format_func=lambda m: {"Aggressive":"🔥 Aggressive","Scalping":"⚡ Scalping","Intraday":"🎯 Intraday"}.get(m,m))

tf_default_map = {"Aggressive": 2, "Scalping": 2, "Intraday": 3}
interval = st.selectbox("⏱ Timeframe",
    [("1m","1 Min"),("5m","5 Min"),("15m","15 Min"),("1h","1 Hour"),("4h","4 Hour")],
    format_func=lambda x: x[1],
    index=tf_default_map.get(trading_mode, 2))
interval_val = interval[0]

col3, col4 = st.columns(2)
with col3:
    modal = st.number_input("💵 Modal (USD)", min_value=10.0, value=100.0, step=10.0)
with col4:
    leverage = st.selectbox("⚡ Leverage", [1,10,50,100,200,500], index=3)

st.session_state["last_symbol"] = symbol
st.session_state["last_mode"]   = trading_mode
st.session_state["last_tf"]     = interval_val

# ─────────────────────────────────────────────
#  LIVE PRICE
# ─────────────────────────────────────────────
pd_data = get_price(symbol)
if pd_data:
    bid    = pd_data["bid"]
    ask    = pd_data["ask"]
    spread = pd_data["spread"]
    digits = pd_data["digits"]
    fmt    = f".{digits}f"
    st.markdown(f"""
    <div class="price-card">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <span class="symbol-name">{symbol}</span>
                <span style="color:#6b7280;font-size:11px;margin-left:8px;">MT5 FOREX</span>
                <div style="margin-top:6px;">
                    <span class="price-label">BID </span>
                    <span class="price-big-green">{bid:{fmt}}</span>
                    &nbsp;&nbsp;
                    <span class="price-label">ASK </span>
                    <span class="price-big-red">{ask:{fmt}}</span>
                </div>
            </div>
            <div style="text-align:right;">
                <div class="price-label">Spread</div>
                <div class="spread-val">{spread:.0f} pts</div>
                <div class="price-label" style="margin-top:4px;">{datetime.now().strftime('%H:%M:%S')}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.warning(f"⚠️ Gagal ambil harga {symbol}")
    bid = ask = spread = 0
    digits = 5
    fmt = ".5f"

# ─────────────────────────────────────────────
#  TOGGLE GEMINI + TOMBOL REFRESH
# ─────────────────────────────────────────────
col_tog1, col_tog2 = st.columns([1, 2])
with col_tog1:
    use_gemini = st.checkbox(
        "✨ Pakai Gemini AI",
        value=GEMINI_ENABLED,
        disabled=not GEMINI_ENABLED,
        help="Uncheck untuk pakai Formula Engine saja (hemat RPD)"
    )
    if not GEMINI_ENABLED:
        st.caption("🔴 Gemini key tidak aktif")
with col_tog2:
    if use_gemini and GEMINI_ENABLED:
        st.caption(f"🟢 Gemini aktif — 1 klik = 1 RPD")
    else:
        st.caption("📐 Formula Engine aktif — 0 RPD")

do_refresh = st.button("🔄 Refresh Analisis", use_container_width=True)

# ─────────────────────────────────────────────
#  LOGIC — jalankan saat tombol diklik
# ─────────────────────────────────────────────
if do_refresh and bid > 0:
    df = get_klines(symbol, interval_val, 200)
    res, sup = get_sr(df) if df is not None else ([], [])

    if use_gemini and GEMINI_ENABLED:
        with st.status("🤖 Gemini menganalisis...", expanded=False):
            result = call_gemini(symbol, interval_val, trading_mode,
                                  df, bid, ask, spread, digits, res, sup)
        if result is None:
            # Gemini error/limit → fallback formula otomatis
            st.warning("⚠️ Gemini tidak merespons / limit — Formula Engine aktif sebagai fallback.")
            result = formula_signal(df, symbol, bid, digits)
    else:
        # Gemini di-toggle off atau tidak aktif → langsung formula
        result = formula_signal(df, symbol, bid, digits)

    if result:
        result["timestamp"] = datetime.now().strftime("%H:%M:%S")
    st.session_state["result"] = result

elif do_refresh and bid == 0:
    st.error("❌ Harga tidak tersedia. Cek koneksi MT5.")

# ─────────────────────────────────────────────
#  RENDER HASIL
# ─────────────────────────────────────────────
result = st.session_state["result"]

if result:
    action = result["action"]
    conf   = result["confidence"]
    reason = result["reason"]
    source = result.get("source","formula")
    ts     = result.get("timestamp","")

    # Badge source
    if source == "gemini":
        badge_html = f'<div class="ai-badge">🤖 Gemini AI — {ts}</div>'
    else:
        badge_html = f'<div class="formula-badge">📐 Formula Engine — {ts}</div>'

    # Signal card
    if action == "BUY":
        sig_cls = "sig-buy";  act_cls = "sig-action-buy"
        sig_ico = "🟢"
    elif action == "SELL":
        sig_cls = "sig-sell"; act_cls = "sig-action-sell"
        sig_ico = "🔴"
    else:
        sig_cls = "sig-hold"; act_cls = "sig-action-hold"
        sig_ico = "🔵"

    conf_color = "#22c55e" if conf>=70 else "#f97316" if conf>=50 else "#ef4444"

    st.markdown(f"""
    <div class="{sig_cls}">
        {badge_html}
        <div class="{act_cls}">{sig_ico} {action}</div>
        <div class="sig-reason">{reason}</div>
        <div class="bar-bg" style="margin:10px 30px 0 30px;">
            <div class="bar-fill" style="width:{conf}%;background:{conf_color};"></div>
        </div>
        <div class="sig-conf">Confidence: {conf}%</div>
    </div>
    """, unsafe_allow_html=True)

    # Pair reco
    if result.get("pair_reco"):
        st.markdown(f"""
        <div class="info-bar">💡 <strong style="color:#3b82f6;">Coba pair lain:</strong> {result["pair_reco"]}</div>
        """, unsafe_allow_html=True)

    # Level card
    if action != "HOLD" and result.get("tp1", 0) > 0:
        entry = result["entry"]
        tp1   = result["tp1"]
        tp2   = result["tp2"]
        sl    = result["sl"]

        is_xau = "XAU" in symbol
        is_jpy = "JPY" in symbol
        pip_m  = 1.0 if is_xau else 100 if is_jpy else 10000
        pip_v  = 1.0 if is_xau else 10.0

        sl_pip  = round(abs(entry - sl)    * pip_m, 1)
        tp1_pip = round(abs(tp1   - entry) * pip_m, 1)
        tp2_pip = round(abs(tp2   - entry) * pip_m, 1) if tp2 > 0 else 0
        rr      = round(tp1_pip / sl_pip, 2) if sl_pip > 0 else 0

        lot     = round(modal * 0.01 / max(sl_pip * pip_v, 0.01), 2)
        lot     = max(0.01, min(lot, 5.0))
        pnl_tp1 = round(tp1_pip * pip_v * lot, 2)
        pnl_tp2 = round(tp2_pip * pip_v * lot, 2) if tp2_pip > 0 else 0
        pnl_sl  = round(sl_pip  * pip_v * lot, 2)
        rr_col  = "#22c55e" if rr >= 1.0 else "#f97316" if rr >= 0.5 else "#ef4444"

        tp_c = "c-green" if action=="BUY" else "c-red"
        sl_c = "c-red"   if action=="BUY" else "c-green"
        src_label = "✨ Level dari Gemini AI" if source=="gemini" else "📐 Level dari Formula"
        src_color = "c-purple" if source=="gemini" else "c-orange"

        tp2_row = f'<div class="lv-row"><span class="lv-label">TP 2</span><span class="lv-val {tp_c}">{tp2:{fmt}} (+{tp2_pip:.0f} pips)</span></div>' if tp2 > 0 else ""
        pnl2_row = f'<div class="lv-row"><span class="lv-label">Est. Profit TP2</span><span class="lv-val c-green">+${pnl_tp2}</span></div>' if pnl_tp2 > 0 else ""

        st.markdown(f"""
        <div class="lv-card">
            <div class="lv-title {src_color}">{src_label}</div>
            <div class="lv-row"><span class="lv-label">Posisi</span><span class="lv-val {tp_c}">{action}</span></div>
            <div class="lv-row"><span class="lv-label">Entry</span><span class="lv-val c-orange">{entry:{fmt}}</span></div>
            <div class="lv-row"><span class="lv-label">Stop Loss</span><span class="lv-val {sl_c}">{sl:{fmt}} ({sl_pip:.0f} pips)</span></div>
            <div class="lv-row"><span class="lv-label">TP 1</span><span class="lv-val {tp_c}">{tp1:{fmt}} (+{tp1_pip:.0f} pips)</span></div>
            {tp2_row}
        </div>

        <div class="lv-card">
            <div class="lv-title" style="color:#6b7280;">RISK & REWARD</div>
            <div class="lv-row"><span class="lv-label">R/R Ratio</span><span class="lv-val" style="color:{rr_col};">1 : {rr}</span></div>
            <div class="lv-row"><span class="lv-label">Modal</span><span class="lv-val">${modal:,.0f}</span></div>
            <div class="lv-row"><span class="lv-label">Lot Size</span><span class="lv-val">{lot}</span></div>
            <div class="lv-row"><span class="lv-label">Leverage</span><span class="lv-val">1:{leverage}</span></div>
            <div class="lv-row"><span class="lv-label">Est. Profit TP1</span><span class="lv-val c-green">+${pnl_tp1}</span></div>
            {pnl2_row}
            <div class="lv-row"><span class="lv-label">Max Loss (SL)</span><span class="lv-val c-red">-${pnl_sl}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # Quick note
        dir_w = "BUY" if action=="BUY" else "SELL"
        st.markdown(f"""
        <div class="info-bar">
        ⚡ <b style="color:#fff;">{dir_w}</b> di
        <b style="color:#f97316;">{entry:{fmt}}</b> →
        SL <b style="color:#ef4444;">{sl:{fmt}}</b> →
        TP1 <b style="color:#22c55e;">{tp1:{fmt}}</b>
        &nbsp;|&nbsp; Est. +${pnl_tp1}
        </div>
        """, unsafe_allow_html=True)

    # Insights
    if result.get("insights"):
        st.markdown('<div class="insight-card">', unsafe_allow_html=True)
        for ins in result["insights"]:
            st.markdown(f'<div class="insight-item">• {ins}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # Empty state
    if use_gemini and GEMINI_ENABLED:
        gem_hint = f"Gemini AI aktif ({GEMINI_MODEL})"
    elif GEMINI_ENABLED:
        gem_hint = "Formula Engine aktif (Gemini di-toggle off)"
    else:
        gem_hint = "Formula Engine aktif (Gemini key tidak ada)"
    st.markdown(f"""
    <div class="empty-state">
        <div style="font-size:48px;">🤖</div>
        <div style="font-size:16px;font-weight:700;color:#fff;margin:10px 0 6px;">Siap Menganalisis</div>
        <div style="color:#6b7280;font-size:13px;line-height:1.6;">
            Pilih pair, mode, dan timeframe di atas<br>
            lalu klik <b style="color:#f97316;">Refresh Analisis</b>
        </div>
        <div style="margin-top:14px;padding:10px;background:#111;border-radius:8px;">
            <div style="color:#f97316;font-size:12px;font-weight:700;">⚡ {gem_hint}</div>
            <div style="color:#6b7280;font-size:11px;margin-top:4px;">
                1 klik = 1 request Gemini<br>
                Kalau Gemini limit → Formula Engine otomatis aktif
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  FOOTER
# ─────────────────────────────────────────────
account    = mt5.account_info()
gem_status = f"🟢 {GEMINI_MODEL}" if GEMINI_ENABLED else "🔴 Gemini off → Formula aktif"

st.markdown("---")
if account:
    st.markdown(f"""
    <div class="info-bar">
    👤 <b>{account.name}</b> &nbsp;|&nbsp;
    💰 <b style="color:#22c55e;">${account.balance:,.2f}</b> &nbsp;|&nbsp;
    📊 1:{account.leverage} &nbsp;|&nbsp;
    ✨ {gem_status}
    </div>
    """, unsafe_allow_html=True)
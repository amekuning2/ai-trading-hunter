import streamlit as st
import pandas as pd
import MetaTrader5 as mt5
import ta
from datetime import datetime
import google.generativeai as genai
import json

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="MT5 AI Signal",
    page_icon="⚡",
    layout="centered",          # centered = lebih enak di HP
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────
#  STYLING — Mobile-first, clean, minimal
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #e6edf3; }

    /* Metric */
    [data-testid="metric-container"] {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 10px; padding: 14px;
    }
    [data-testid="metric-container"] label {
        color: #8b949e !important; font-size: 11px;
        text-transform: uppercase; letter-spacing: 1px;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #e6edf3; font-size: 22px; font-weight: 700;
    }

    /* Signal card */
    .sig-card {
        border-radius: 14px; padding: 24px 20px;
        text-align: center; margin: 12px 0;
    }
    .sig-buy  { background: linear-gradient(135deg,#0d2b1d,#0f3d2a); border: 2px solid #2ea043; }
    .sig-sell { background: linear-gradient(135deg,#2d1b1b,#3d1f1f); border: 2px solid #f85149; }
    .sig-hold { background: linear-gradient(135deg,#1b1f2d,#1e2540); border: 2px solid #388bfd; }
    .sig-action { font-size: 42px; font-weight: 900; letter-spacing: 4px; margin: 6px 0; }
    .sig-buy  .sig-action { color: #3fb950; }
    .sig-sell .sig-action { color: #f85149; }
    .sig-hold .sig-action { color: #388bfd; }
    .sig-reason { color: #c9d1d9; font-size: 13px; line-height: 1.5; margin-top: 8px; }
    .sig-conf { color: #8b949e; font-size: 11px; margin-top: 6px; }

    /* Level card */
    .lv-card {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 12px; padding: 16px; margin: 8px 0;
    }
    .lv-row {
        display: flex; justify-content: space-between;
        padding: 7px 0; border-bottom: 1px solid #21262d;
        font-size: 14px;
    }
    .lv-row:last-child { border-bottom: none; }
    .lv-label { color: #8b949e; }
    .lv-val   { color: #e6edf3; font-weight: 700; }
    .lv-buy   { color: #3fb950 !important; }
    .lv-sell  { color: #f85149 !important; }
    .lv-entry { color: #f0883e !important; }

    /* Refresh button besar */
    .stButton > button {
        width: 100%; height: 56px;
        background: linear-gradient(135deg,#1f6feb,#388bfd);
        color: #fff; font-size: 18px; font-weight: 800;
        border: none; border-radius: 12px;
        letter-spacing: 1px; cursor: pointer;
        margin-top: 8px;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg,#388bfd,#1f6feb);
    }

    /* Price header */
    .price-header {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 12px; padding: 16px 20px; margin: 12px 0;
    }
    .price-symbol { font-size: 18px; font-weight: 800; color: #e6edf3; }
    .price-bid    { font-size: 32px; font-weight: 900; color: #3fb950; }
    .price-ask    { font-size: 32px; font-weight: 900; color: #f85149; }
    .price-sub    { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }

    /* Info bar */
    .info-bar {
        background: #1b1f2d; border: 1px solid #30363d;
        border-radius: 8px; padding: 10px 14px;
        font-size: 12px; color: #8b949e; margin: 6px 0;
    }

    /* Bar confidence */
    .bar-bg { background: #21262d; border-radius: 20px; height: 8px; margin: 8px 0; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 20px; }

    /* Insight list */
    .insight-card {
        background: linear-gradient(135deg,#1a1a2e,#16213e);
        border: 1px solid #0f3460; border-left: 4px solid #d2a8ff;
        border-radius: 10px; padding: 16px; margin: 10px 0;
    }
    .insight-item {
        color: #c9d1d9; font-size: 13px;
        margin-bottom: 8px; line-height: 1.6;
        padding-left: 8px;
    }

    /* Hide streamlit default */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  API SETUP
# ─────────────────────────────────────────────
try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_SIMPLE", "")
except Exception:
    GEMINI_API_KEY = ""

GEMINI_ENABLED = bool(GEMINI_API_SIMPLE)
if GEMINI_ENABLED:
    genai.configure(api_key=GEMINI_API_SIMPLE)

GEMINI_MODEL = "gemini-3.1-flash-lite"   # ganti di sini kalau mau model lain

# ─────────────────────────────────────────────
#  MT5 CONNECTION
# ─────────────────────────────────────────────
@st.cache_resource
def init_mt5():
    return mt5.initialize()

TIMEFRAME_MAP = {
    "1m":  mt5.TIMEFRAME_M1,
    "5m":  mt5.TIMEFRAME_M5,
    "15m": mt5.TIMEFRAME_M15,
    "1h":  mt5.TIMEFRAME_H1,
    "4h":  mt5.TIMEFRAME_H4,
    "1d":  mt5.TIMEFRAME_D1,
}

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
        digits = info.digits
        return {
            "bid": round(tick.bid, digits),
            "ask": round(tick.ask, digits),
            "spread": round((tick.ask - tick.bid) / info.point, 1),
            "digits": digits,
            "point": info.point,
        }
    except:
        return None

def get_klines(symbol, interval, limit=150):
    try:
        tf = TIMEFRAME_MAP.get(interval, mt5.TIMEFRAME_M15)
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

# ─────────────────────────────────────────────
#  SUPPORT & RESISTANCE
# ─────────────────────────────────────────────
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
#  GEMINI AI — MANUAL CALL (tidak di-cache page load)
#  Dipanggil HANYA saat user klik tombol Refresh
# ─────────────────────────────────────────────
def call_gemini_analysis(symbol, interval, trading_mode,
                          rsi, macd_val, macd_sig, ema20, ema50, ema200,
                          bb_pos, vol_ratio, atr,
                          bid, ask, spread,
                          supports, resistances, ohlcv_txt):
    if not GEMINI_ENABLED:
        return None

    if trading_mode == "Aggressive":
        mode_ctx = "AGGRESSIVE: entry sering, profit kecil rutin. Rekomendasikan BUY/SELL kalau ada momentum minimal."
    elif trading_mode == "Scalping":
        mode_ctx = "SCALPING M15: cari peluang clean di M15, TP cepat, SL anti-noise."
    else:
        mode_ctx = "INTRADAY: balance kualitas & frekuensi, butuh 2+ konfirmasi."

    prompt = f"""
Kamu adalah AI Trading Analyst untuk Forex MT5.
Analisis data berikut dan beri keputusan trading yang actionable.

PAIR: {symbol} | TF: {interval}
HARGA: Bid={bid} Ask={ask} Spread={spread:.0f} pts

INDIKATOR:
RSI={rsi:.1f} | MACD={macd_val:.5f} vs Signal={macd_sig:.5f}
EMA20={ema20:.5f} EMA50={ema50:.5f} EMA200={ema200:.5f}
BB Position={bb_pos:.0f}% | Volume Ratio={vol_ratio:.2f}x | ATR={atr:.5f}
Support={supports} | Resistance={resistances}

OHLCV 5 CANDLE TERAKHIR:
{ohlcv_txt}

MODE: {mode_ctx}

Analisis sekarang — apakah ada peluang trading?
- Ada peluang (meski tidak sempurna) → BUY atau SELL dengan entry/TP/SL yang konkret
- Tidak ada setup → HOLD
- SL untuk XAUUSD minimal 150 pips dari entry, untuk forex pair minimal 20 pips

BALAS HANYA JSON:
{{
  "action": "BUY" atau "SELL" atau "HOLD",
  "confidence": 0-100,
  "entry": angka,
  "tp1": angka,
  "tp2": angka,
  "sl": angka,
  "reason": "alasan 1-2 kalimat santai bahasa Indonesia",
  "insights": ["poin 1", "poin 2", "poin 3"],
  "pair_reco": "kalau pair ini tidak menarik sekarang, rekomendasikan pair lain atau kosongkan"
}}
"""
    try:
        model    = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text.strip())
        return {
            "action":     data.get("action", "HOLD"),
            "confidence": int(data.get("confidence", 0)),
            "entry":      float(data.get("entry", bid)),
            "tp1":        float(data.get("tp1", 0)),
            "tp2":        float(data.get("tp2", 0)),
            "sl":         float(data.get("sl", 0)),
            "reason":     data.get("reason", ""),
            "insights":   data.get("insights", []),
            "pair_reco":  data.get("pair_reco", ""),
            "timestamp":  datetime.now().strftime("%H:%M:%S"),
            "ok":         True,
        }
    except Exception as e:
        return {"ok": False, "reason": str(e), "action": "HOLD"}

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
if "ai_result"    not in st.session_state: st.session_state["ai_result"]    = None
if "last_symbol"  not in st.session_state: st.session_state["last_symbol"]  = "XAUUSD"
if "last_mode"    not in st.session_state: st.session_state["last_mode"]    = "Aggressive"
if "last_tf"      not in st.session_state: st.session_state["last_tf"]      = "15m"

# ─────────────────────────────────────────────
#  INIT MT5
# ─────────────────────────────────────────────
if not init_mt5():
    st.error("❌ MT5 tidak terkoneksi. Pastikan MetaTrader5 sudah berjalan di VPS.")
    st.stop()

# ─────────────────────────────────────────────
#  CONTROLS — Compact, mobile-friendly
# ─────────────────────────────────────────────
st.markdown("## 📊 MT5 AI Signal")

PAIRS = ["XAUUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","NZDUSD","GBPJPY","EURJPY"]

col1, col2 = st.columns(2)
with col1:
    symbol = st.selectbox("🪙 Pair", PAIRS,
                          index=PAIRS.index(st.session_state["last_symbol"])
                          if st.session_state["last_symbol"] in PAIRS else 0)
with col2:
    def mode_lbl(m):
        return {"Aggressive":"🔥 Aggressive","Scalping":"⚡ Scalping","Intraday":"🎯 Intraday"}.get(m, m)
    trading_mode = st.selectbox("⚙️ Mode", ["Aggressive","Scalping","Intraday"], format_func=mode_lbl)

col3, col4 = st.columns(2)
with col3:
    tf_default = {"Aggressive":2,"Scalping":2,"Intraday":3}
    interval   = st.selectbox("⏱ Timeframe",
                               [("1m","1 Min"),("5m","5 Min"),("15m","15 Min"),("1h","1 Hour"),("4h","4 Hour")],
                               format_func=lambda x: x[1],
                               index=tf_default.get(trading_mode, 2))
    interval_val = interval[0]
with col4:
    modal = st.number_input("💵 Modal (USD)", min_value=10.0, value=100.0, step=10.0)

st.session_state["last_symbol"] = symbol
st.session_state["last_mode"]   = trading_mode
st.session_state["last_tf"]     = interval_val

# ─────────────────────────────────────────────
#  LIVE PRICE — selalu update
# ─────────────────────────────────────────────
price_data = get_price(symbol)
if price_data:
    bid    = price_data["bid"]
    ask    = price_data["ask"]
    spread = price_data["spread"]
    digits = price_data["digits"]
    fmt    = f".{digits}f"
    st.markdown(f"""
    <div class="price-header">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div class="price-symbol">{symbol} <span style="color:#8b949e;font-size:12px;font-weight:400;">MT5 FOREX</span></div>
                <div style="margin-top:4px;">
                    <span class="price-sub">BID </span><span class="price-bid">{bid:{fmt}}</span>
                    &nbsp;&nbsp;
                    <span class="price-sub">ASK </span><span class="price-ask">{ask:{fmt}}</span>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="color:#8b949e;font-size:11px;">Spread</div>
                <div style="font-size:18px;font-weight:700;color:#f0883e;">{spread:.0f} pts</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.warning(f"⚠️ Gagal ambil harga {symbol}. Pastikan pair ada di Market Watch MT5.")
    bid = ask = spread = 0
    digits = 5
    fmt = ".5f"

# ─────────────────────────────────────────────
#  TOMBOL REFRESH — satu-satunya trigger Gemini
# ─────────────────────────────────────────────
do_refresh = st.button("🤖 Analisis AI Sekarang", use_container_width=True)

# ─────────────────────────────────────────────
#  LOGIC: Jalankan analisis kalau tombol diklik
# ─────────────────────────────────────────────
if do_refresh and bid > 0:
    df = get_klines(symbol, interval_val, 150)
    if df is None or len(df) < 30:
        st.error("Data candlestick tidak cukup. Cek koneksi MT5.")
    else:
        close  = df["close"]
        rsi    = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]
        macd_i = ta.trend.MACD(close)
        macd_v = macd_i.macd().iloc[-1]
        macd_s = macd_i.macd_signal().iloc[-1]
        ema20  = ta.trend.EMAIndicator(close, window=20).ema_indicator().iloc[-1]
        ema50  = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]
        ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator().iloc[-1] if len(close) >= 200 else ema50
        bb     = ta.volatility.BollingerBands(close, window=20)
        bb_pos = ((bid - bb.bollinger_lband().iloc[-1]) / max(bb.bollinger_hband().iloc[-1] - bb.bollinger_lband().iloc[-1], 0.0001)) * 100
        atr    = ta.volatility.AverageTrueRange(df["high"], df["low"], close, window=14).average_true_range().iloc[-1]
        vol_r  = df["volume"].iloc[-1] / max(df["volume"].rolling(20).mean().iloc[-1], 0.0001)
        res, sup = get_sr(df)

        ohlcv_txt = "\n".join([
            f"[{i}] O={r.open:{fmt}} H={r.high:{fmt}} L={r.low:{fmt}} C={r.close:{fmt}}"
            for i, r in enumerate(df.tail(5).itertuples())
        ])

        if GEMINI_ENABLED:
            with st.status("🤖 Gemini sedang menganalisis...", expanded=False):
                result = call_gemini_analysis(
                    symbol=symbol, interval=interval_val, trading_mode=trading_mode,
                    rsi=rsi, macd_val=macd_v, macd_sig=macd_s,
                    ema20=ema20, ema50=ema50, ema200=ema200,
                    bb_pos=bb_pos, vol_ratio=vol_r, atr=atr,
                    bid=bid, ask=ask, spread=spread,
                    supports=res, resistances=sup,
                    ohlcv_txt=ohlcv_txt
                )
            st.session_state["ai_result"] = result
        else:
            st.session_state["ai_result"] = {
                "ok": False,
                "reason": "GEMINI_API_SIMPLE belum diset di secrets.toml",
                "action": "HOLD"
            }

elif do_refresh and bid == 0:
    st.error("Harga tidak tersedia. Cek koneksi MT5 dan pair.")

# ─────────────────────────────────────────────
#  TAMPILAN HASIL AI
# ─────────────────────────────────────────────
result = st.session_state["ai_result"]

if result:
    if not result.get("ok", True):
        st.error(f"❌ Gemini error: {result.get('reason','unknown')}")
    else:
        action = result["action"]
        conf   = result["confidence"]
        reason = result["reason"]
        ts     = result.get("timestamp","")

        # Signal Card
        sig_class = "sig-buy" if action=="BUY" else "sig-sell" if action=="SELL" else "sig-hold"
        sig_emoji = "🟢" if action=="BUY" else "🔴" if action=="SELL" else "🔵"
        sig_color = "#3fb950" if action=="BUY" else "#f85149" if action=="SELL" else "#388bfd"
        conf_color= "#3fb950" if conf>=70 else "#f0883e" if conf>=50 else "#f85149"

        st.markdown(f"""
        <div class="sig-card {sig_class}">
            <div style="color:#8b949e;font-size:10px;text-transform:uppercase;letter-spacing:2px;">🤖 Gemini AI — {ts}</div>
            <div class="sig-action">{sig_emoji} {action}</div>
            <div class="sig-reason">{reason}</div>
            <div class="bar-bg" style="margin:10px 20px 0 20px;">
                <div class="bar-fill" style="width:{conf}%;background:{conf_color};"></div>
            </div>
            <div class="sig-conf">AI Confidence: {conf}%</div>
        </div>
        """, unsafe_allow_html=True)

        # Pair recommendation
        if result.get("pair_reco"):
            st.markdown(f"""
            <div class="info-bar">
            💡 <strong style="color:#388bfd;">Rekomendasi:</strong> {result["pair_reco"]}
            </div>
            """, unsafe_allow_html=True)

        # Level dari AI
        if action != "HOLD" and result["tp1"] > 0:
            entry  = result["entry"]
            tp1    = result["tp1"]
            tp2    = result["tp2"]
            sl     = result["sl"]
            pip_m  = 1.0 if "XAU" in symbol or "GOL" in symbol else 100 if "JPY" in symbol else 10000
            sl_pip = round(abs(entry - sl) * pip_m, 1)
            t1_pip = round(abs(tp1 - entry) * pip_m, 1)
            t2_pip = round(abs(tp2 - entry) * pip_m, 1) if tp2 > 0 else 0
            rr     = round(t1_pip / sl_pip, 2) if sl_pip > 0 else 0

            tp_c = "lv-buy" if action=="BUY" else "lv-sell"
            sl_c = "lv-sell" if action=="BUY" else "lv-buy"

            # Hitung lot & PnL
            pip_val  = 1.0 if "XAU" in symbol else 10.0
            lot      = round(modal * 0.01 / max(sl_pip * pip_val, 0.01), 2)
            lot      = max(0.01, min(lot, 5.0))
            pnl_tp1  = round(t1_pip * pip_val * lot, 2)
            pnl_tp2  = round(t2_pip * pip_val * lot, 2) if t2_pip > 0 else 0
            pnl_sl   = round(sl_pip * pip_val * lot, 2)
            rr_color = "#3fb950" if rr >= 1.0 else "#f0883e" if rr >= 0.5 else "#f85149"

            st.markdown(f"""
            <div class="lv-card">
                <div style="color:#d2a8ff;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">✨ Level dari Gemini AI</div>
                <div class="lv-row"><span class="lv-label">Posisi</span><span class="lv-val {tp_c}">{action}</span></div>
                <div class="lv-row"><span class="lv-label">Entry</span><span class="lv-val lv-entry">{entry:{fmt}}</span></div>
                <div class="lv-row"><span class="lv-label">Stop Loss</span><span class="lv-val {sl_c}">{sl:{fmt}} ({sl_pip:.0f} pips)</span></div>
                <div class="lv-row"><span class="lv-label">TP 1</span><span class="lv-val {tp_c}">{tp1:{fmt}} (+{t1_pip:.0f} pips)</span></div>
                {'<div class="lv-row"><span class="lv-label">TP 2</span><span class="lv-val ' + tp_c + '">' + f"{tp2:{fmt}} (+{t2_pip:.0f} pips)" + '</span></div>' if tp2 > 0 else ""}
            </div>

            <div class="lv-card">
                <div style="color:#8b949e;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">💰 Risk & Reward</div>
                <div class="lv-row"><span class="lv-label">R/R Ratio</span><span class="lv-val" style="color:{rr_color};">1 : {rr}</span></div>
                <div class="lv-row"><span class="lv-label">Lot Size</span><span class="lv-val">{lot}</span></div>
                <div class="lv-row"><span class="lv-label">Est. Profit TP1</span><span class="lv-val lv-buy">+${pnl_tp1}</span></div>
                {'<div class="lv-row"><span class="lv-label">Est. Profit TP2</span><span class="lv-val lv-buy">+$' + str(pnl_tp2) + '</span></div>' if pnl_tp2 > 0 else ""}
                <div class="lv-row"><span class="lv-label">Max Loss (SL)</span><span class="lv-val lv-sell">-${pnl_sl}</span></div>
            </div>
            """, unsafe_allow_html=True)

            # Quick action note
            dir_w = "BUY di" if action == "BUY" else "SELL di"
            st.markdown(f"""
            <div class="info-bar">
            ⚡ <strong style="color:#e6edf3;">Quick:</strong>
            {dir_w} <strong style="color:#f0883e;">{entry:{fmt}}</strong> →
            SL <strong style="color:#f85149;">{sl:{fmt}}</strong> →
            TP1 <strong style="color:#3fb950;">{tp1:{fmt}}</strong>
            </div>
            """, unsafe_allow_html=True)

        # Insights
        if result.get("insights"):
            st.markdown('<div class="insight-card">', unsafe_allow_html=True)
            for ins in result["insights"]:
                st.markdown(f'<div class="insight-item">• {ins}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

else:
    # Belum ada hasil — tampilkan instruksi
    st.markdown(f"""
    <div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
         padding:32px 20px;text-align:center;margin:20px 0;">
        <div style="font-size:48px;margin-bottom:12px;">🤖</div>
        <div style="color:#e6edf3;font-size:16px;font-weight:700;margin-bottom:8px;">
            Siap Menganalisis
        </div>
        <div style="color:#8b949e;font-size:13px;line-height:1.6;">
            Pilih pair dan mode di atas,<br>
            lalu klik <strong style="color:#388bfd;">Analisis AI Sekarang</strong><br>
            untuk mendapatkan sinyal dari Gemini.
        </div>
        <div style="margin-top:16px;padding:10px;background:#1b1f2d;border-radius:8px;">
            <div style="color:#f0883e;font-size:12px;font-weight:700;">💡 Tips Hemat RPD</div>
            <div style="color:#8b949e;font-size:11px;margin-top:4px;">
                1 klik = 1 request Gemini.<br>
                Tunggu minimal 5 menit antar refresh biar efisien.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  FOOTER INFO
# ─────────────────────────────────────────────
mt5_connected = init_mt5()
account = mt5.account_info() if mt5_connected else None
gem_status = f"🟢 {GEMINI_MODEL}" if GEMINI_ENABLED else "🔴 Tidak aktif"

st.markdown("---")
if account:
    st.markdown(f"""
    <div class="info-bar">
    👤 <strong>{account.name}</strong> &nbsp;|&nbsp;
    💰 Balance: <strong style="color:#3fb950;">${account.balance:,.2f}</strong> &nbsp;|&nbsp;
    📊 Leverage: 1:{account.leverage} &nbsp;|&nbsp;
    ✨ Gemini: {gem_status}
    ⚙️ Version: <span style="color:#e6edf3;">v4.2 (3-Mode + Gemini Decision Engine)</span>;
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="info-bar">
    ⚠️ MT5 tidak terkoneksi &nbsp;|&nbsp; ✨ Gemini: {gem_status}
    </div>
    """, unsafe_allow_html=True)
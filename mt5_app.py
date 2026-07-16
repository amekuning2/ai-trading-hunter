import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import MetaTrader5 as mt5
import ta
import time
from datetime import datetime
from google import genai
import json

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="MT5 Forex Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────
#  DARK MODE STYLING
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #e6edf3; }
    .stSidebar { background-color: #161b22; border-right: 1px solid #30363d; }

    [data-testid="metric-container"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
    }
    [data-testid="metric-container"] label { color: #8b949e !important; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #e6edf3; font-size: 22px; font-weight: 700; }

    .signal-buy { background: linear-gradient(135deg, #0d2b1d, #0f3d2a); border: 1px solid #2ea043; border-left: 4px solid #2ea043; border-radius: 8px; padding: 20px; text-align: center; }
    .signal-sell { background: linear-gradient(135deg, #2d1b1b, #3d1f1f); border: 1px solid #f85149; border-left: 4px solid #f85149; border-radius: 8px; padding: 20px; text-align: center; }
    .signal-hold { background: linear-gradient(135deg, #1b1f2d, #1e2540); border: 1px solid #388bfd; border-left: 4px solid #388bfd; border-radius: 8px; padding: 20px; text-align: center; }
    .signal-text { font-size: 28px; font-weight: 800; margin: 0; letter-spacing: 2px; }
    .signal-buy .signal-text { color: #3fb950; }
    .signal-sell .signal-text { color: #f85149; }
    .signal-hold .signal-text { color: #388bfd; }
    .signal-reason { color: #8b949e; font-size: 12px; margin-top: 8px; }

    .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; margin: 2px; }
    .badge-green { background: #0d2b1d; color: #3fb950; border: 1px solid #2ea043; }
    .badge-red { background: #2d1b1b; color: #f85149; border: 1px solid #f85149; }
    .badge-neutral { background: #1b1f2d; color: #8b949e; border: 1px solid #30363d; }

    .section-header { color: #8b949e; font-size: 11px; text-transform: uppercase; letter-spacing: 2px; border-bottom: 1px solid #30363d; padding-bottom: 8px; margin-bottom: 16px; }

    .pair-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px; margin: 4px 0; display: flex; justify-content: space-between; align-items: center; }

    .mtf-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px; text-align: center; margin: 4px 0; }
    .mtf-buy { border-left: 3px solid #3fb950; }
    .mtf-sell { border-left: 3px solid #f85149; }
    .mtf-hold { border-left: 3px solid #388bfd; }

    .strength-bar-container { background: #21262d; border-radius: 20px; height: 8px; margin: 8px 0; overflow: hidden; }
    .strength-bar-fill { height: 100%; border-radius: 20px; }

    .sr-level { display: flex; justify-content: space-between; padding: 6px 10px; border-radius: 6px; margin: 3px 0; font-size: 12px; }
    .sr-resistance { background: #2d1b1b; border-left: 3px solid #f85149; }
    .sr-support { background: #0d2b1d; border-left: 3px solid #3fb950; }

    .tp-card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 16px; margin: 8px 0; }
    .tp-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #21262d; font-size: 13px; }
    .tp-row:last-child { border-bottom: none; }
    .tp-label { color: #8b949e; }
    .tp-value { color: #e6edf3; font-weight: 600; }
    .tp-green { color: #3fb950 !important; }
    .tp-red { color: #f85149 !important; }
    .tp-yellow { color: #f0883e !important; }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  MT5 CONNECTION & GEMINI SETUP
# ─────────────────────────────────────────────
def init_mt5():
    if not mt5.initialize():
        return False, mt5.last_error()
    return True, None

# Pembongkaran (unpacking) tuple yang benar agar evaluasi boolean tidak salah bias
if "mt5_connected" not in st.session_state:
    ok, err = init_mt5()
    st.session_state.mt5_connected = ok
    if not ok:
        st.error(f"Gagal konek MT5: {err}")
        if st.button("🔄 Retry Koneksi"):
            st.session_state.mt5_connected = False
            st.rerun()
        st.stop()

connected, conn_err = init_mt5()
if not connected:
    st.error(f"❌ Gagal konek ke MT5! Error: {conn_err}. Pastiin MetaTrader 5 sedang running di VPS.")
    st.stop()

try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
except Exception:
    GEMINI_API_KEY = ""

GEMINI_ENABLED = bool(GEMINI_API_KEY)
GEMINI_MODEL = "gemini-3.1-flash-lite"
if GEMINI_ENABLED:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ─────────────────────────────────────────────
#  FORMULA FALLBACK ENGINE
# ─────────────────────────────────────────────
def formula_signal_engine(df, symbol, bid, digits):
    if df is None or df.empty or len(df) < 50:
        return None
    close = df["close"]
    rsi   = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]
    macd_i= ta.trend.MACD(close)
    mv    = macd_i.macd().iloc[-1]
    ms    = macd_i.macd_signal().iloc[-1]
    ema20 = ta.trend.EMAIndicator(close, window=20).ema_indicator().iloc[-1]
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]
    atr   = ta.volatility.AverageTrueRange(df["high"], df["low"], close, window=14).average_true_range().iloc[-1]
    is_xau = "XAU" in symbol or "GOL" in symbol
    is_jpy = "JPY" in symbol
    bull = sum([bid > ema20, bid > ema50, mv > ms, rsi < 60])
    bear = sum([bid < ema20, bid < ema50, mv < ms, rsi > 40])
    if bull >= 3:
        action = "BUY"
        entry  = round(bid, digits)
        if is_xau:
            tp1,tp2,sl = round(entry+1.5,digits),round(entry+2.5,digits),round(entry-16.0,digits)
        elif is_jpy:
            tp1,tp2,sl = round(entry+(atr*0.8),digits),round(entry+(atr*1.3),digits),round(entry-(atr*1.5),digits)
        else:
            tp1,tp2,sl = round(entry+(atr*0.8),digits),round(entry+(atr*1.3),digits),round(entry-(atr*1.5),digits)
    elif bear >= 3:
        action = "SELL"
        entry  = round(bid, digits)
        if is_xau:
            tp1,tp2,sl = round(entry-1.5,digits),round(entry-2.5,digits),round(entry+16.0,digits)
        elif is_jpy:
            tp1,tp2,sl = round(entry-(atr*0.8),digits),round(entry-(atr*1.3),digits),round(entry+(atr*1.5),digits)
        else:
            tp1,tp2,sl = round(entry-(atr*0.8),digits),round(entry-(atr*1.3),digits),round(entry+(atr*1.5),digits)
    else:
        return {"action":"HOLD","entry":bid,"tp1":0,"tp2":0,"sl":0,
                "confidence":40,"reason":"Market sideways — tidak ada setup jelas.",
                "insights":[],"ai_active":True,"source":"formula","market_reco":""}
    rsi_note = f"RSI {rsi:.0f} {'oversold' if rsi<35 else 'overbought' if rsi>65 else 'neutral'}"
    return {
        "action":action,"entry":entry,"tp1":tp1,"tp2":tp2,"sl":sl,
        "confidence":min(int((max(bull,bear)/4)*80+20),85),
        "reason":f"{'Bullish' if action=='BUY' else 'Bearish'} — EMA+MACD+{rsi_note} konfirmasi.",
        "insights":[
            f"EMA20={ema20:.{digits}f} EMA50={ema50:.{digits}f} — price {'above' if bid>ema50 else 'below'} EMA50",
            f"MACD {'bullish' if mv>ms else 'bearish'} cross, RSI={rsi:.1f}, ATR={atr:.{digits}f}",
            f"Level {'XAUUSD scalping (TP kecil realistis)' if is_xau else 'ATR-based forex'}",
        ],
        "ai_active":True,"source":"formula","market_reco":"",
    }

@st.cache_data(ttl=60)
def get_gemini_full_analysis(symbol, interval, trading_mode,
                              ohlcv_summary, rsi, macd_val, macd_sig,
                              ema20, ema50, ema200,
                              bb_pos, vol_ratio, atr,
                              current_price, bid, ask, spread,
                              supports_str, resistances_str,
                              mtf_score, formula_signal, formula_score,
                              GEMINI_API_KEY):
    empty = {
        "action": "HOLD", "entry": current_price,
        "tp1": 0, "tp2": 0, "sl": 0,
        "reason": "Gemini tidak aktif", "insights": [],
        "market_reco": "", "confidence": 0,
        "ai_active": False
    }
    if not GEMINI_API_KEY:
        return empty

    try:
        if atr > current_price * 0.015:
            empty["reason"] = "Market terlalu volatile saat ini, tunggu sebentar"
            return empty
    except:
        pass

    if trading_mode == "Scalping":
        mode_instruction = """MODE: AGGRESSIVE SCALPING
- Prioritas UTAMA: frekuensi entry tinggi, profit kecil tapi sering
- Target per trade: $5-$25 profit
- Jangan terlalu selektif — kalau ada momentum minimal, langsung rekomendasikan BUY atau SELL
- SL ketat tapi realistis
- Kalau tidak ada setup sama sekali, baru kasih HOLD"""
    elif trading_mode == "Scalping":
        mode_instruction = """MODE: SCALPING M15
- Cari peluang entry yang cukup bagus di timeframe M15
- Target per trade: $10-$30, TP cepat
- Lebih longgar dari Intraday, tapi tetap ada konfirmasi minimal"""
    elif trading_mode == "Intraday":
        mode_instruction = """MODE: INTRADAY
- Balance antara kualitas dan frekuensi
- Target per trade: $20-$50
- Butuh 2+ konfirmasi sebelum entry"""
    else:
        mode_instruction = """MODE: SWING
- Selektif, setup harus matang
- Target per trade: $50+"""

    prompt = f"""
Kamu adalah AI Trading Analyst profesional untuk Forex MT5.
Analisis semua data berikut dan berikan keputusan trading yang actionable.

PAIR: {symbol} | TIMEFRAME: {interval}
HARGA SEKARANG: Bid={bid} | Ask={ask} | Spread={spread:.1f} pts

INDIKATOR TEKNIKAL:
- RSI(14): {rsi:.1f}
- MACD: {macd_val:.5f} vs Signal {macd_sig:.5f}
- EMA20: {ema20:.5f} | EMA50: {ema50:.5f} | EMA200: {ema200:.5f}
- Bollinger Band position: {bb_pos:.1f}%
- Volume ratio vs avg: {vol_ratio:.2f}x
- ATR(14): {atr:.5f}

STRUKTUR HARGA:
- Support: {supports_str}
- Resistance: {resistances_str}
- MTF Alignment Score: {mtf_score}/15

{mode_instruction}

WAJIB BALAS HANYA FORMAT JSON INI:
{{
    "action": "BUY" atau "SELL" atau "HOLD",
    "confidence": 0-100,
    "entry": angka_harga_entry,
    "tp1": angka_harga_tp1,
    "tp2": angka_harga_tp2,
    "sl": angka_harga_sl,
    "reason": "alasan singkat kenapa BUY/SELL/HOLD (1-2 kalimat, bahasa Indonesia santai)",
    "insights": [
        "analisis momentum",
        "analisis struktur harga",
        "analisis risiko"
    ],
    "market_reco": "rekomendasikan pair lain (atau kosongkan string)"
}}
"""
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text.strip())
        return {
            "action":       data.get("action", "HOLD"),
            "confidence":   int(data.get("confidence", 0)),
            "entry":        float(data.get("entry", current_price)),
            "tp1":          float(data.get("tp1", 0)),
            "tp2":          float(data.get("tp2", 0)),
            "sl":           float(data.get("sl", 0)),
            "reason":       data.get("reason", ""),
            "insights":     data.get("insights", []),
            "market_reco":  data.get("market_reco", ""),
            "ai_active":    True
        }
    except Exception as e:
        empty["reason"] = f"Gemini error: {str(e)}"
        return empty

# ─────────────────────────────────────────────
#  DATA FUNCTIONS
# ─────────────────────────────────────────────
TIMEFRAME_MAP = {
    "1m": mt5.TIMEFRAME_M1,
    "5m": mt5.TIMEFRAME_M5,
    "15m": mt5.TIMEFRAME_M15,
    "1h": mt5.TIMEFRAME_H1,
    "4h": mt5.TIMEFRAME_H4,
    "1d": mt5.TIMEFRAME_D1,
}

@st.cache_data(ttl=30)
def get_mt5_price(symbol):
    try:
        mt5.symbol_select(symbol, True)
        tick = mt5.symbol_info_tick(symbol)
        info = mt5.symbol_info(symbol)
        if tick is None or info is None:
            return None
        if tick.bid == 0.0 and tick.ask == 0.0:
            return None
        return {
            "bid": tick.bid,
            "ask": tick.ask,
            "spread": round((tick.ask - tick.bid) / info.point * info.trade_tick_size / info.point, 1),
            "digits": info.digits,
        }
    except:
        return None

@st.cache_data(ttl=15)
def get_mt5_klines(symbol, timeframe_str, limit):
    try:
        if not mt5.symbol_select(symbol, True):
            st.session_state["_last_chart_error"] = f"symbol_select gagal: {mt5.last_error()}"
            return None
        tf = TIMEFRAME_MAP.get(timeframe_str, mt5.TIMEFRAME_H1)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, limit)
        
        retry_delays = [1, 2, 3]
        for delay in retry_delays:
            if rates is not None and len(rates) > 0:
                break
            time.sleep(delay)
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, limit)
            
        if rates is None or len(rates) == 0:
            st.session_state["_last_chart_error"] = f"copy_rates_from_pos kosong: {mt5.last_error()}"
            return None
            
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.rename(columns={"time": "timestamp", "tick_volume": "volume"})
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        st.session_state["_last_chart_error"] = None
        return df
    except Exception as e:
        st.session_state["_last_chart_error"] = f"Exception: {e}"
        return None

@st.cache_data(ttl=60)
def get_all_prices(pairs):
    result = []
    for symbol in pairs:
        tick = mt5.symbol_info_tick(symbol)
        info = mt5.symbol_info(symbol)
        if tick and info:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 2)
            if rates is not None and len(rates) >= 2:
                prev_close = rates[-2]["close"]
                curr_price = tick.bid
                change_pct = round((curr_price - prev_close) / prev_close * 100, 4)
            else:
                change_pct = 0
            result.append({
                "symbol": symbol,
                "bid": tick.bid,
                "ask": tick.ask,
                "change": change_pct,
                "digits": info.digits,
            })
    return result

# ─────────────────────────────────────────────
#  AI SIGNAL ENGINE v2
# ─────────────────────────────────────────────
def calculate_signal(df, mtf_score_override=None):
    if df is None or df.empty or len(df) < 50:
        empty_detail = {
            "trend": 0, "trend_max": 35,
            "momentum": 0, "momentum_max": 25,
            "structure": 0, "structure_max": 20,
            "mtf": 0, "mtf_max": 15,
            "volume": 0, "volume_max": 5,
            "total": 0, "bias": "HOLD"
        }
        return "HOLD", "Data tidak cukup", {}, {}, 0, empty_detail

    close   = df["close"]
    high    = df["high"]
    low     = df["low"]
    volume  = df["volume"]
    current_price = close.iloc[-1]

    ema20  = ta.trend.EMAIndicator(close, window=20).ema_indicator()
    ema50  = ta.trend.EMAIndicator(close, window=50).ema_indicator()
    ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator() if len(close) >= 200 else ema50

    ema20_val  = ema20.iloc[-1]
    ema50_val  = ema50.iloc[-1]
    ema200_val = ema200.iloc[-1]

    rsi        = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]
    macd_ind   = ta.trend.MACD(close)
    macd_val   = macd_ind.macd().iloc[-1]
    macd_sig   = macd_ind.macd_signal().iloc[-1]
    macd_hist  = macd_ind.macd_diff().iloc[-1]

    stoch      = ta.momentum.StochasticOscillator(high, low, close)
    stoch_k    = stoch.stoch().iloc[-1]
    stoch_d    = stoch.stoch_signal().iloc[-1]

    bb         = ta.volatility.BollingerBands(close, window=20)
    bb_upper   = bb.bollinger_hband().iloc[-1]
    bb_lower   = bb.bollinger_lband().iloc[-1]
    bb_pos     = (current_price - bb_lower) / max(bb_upper - bb_lower, 0.0000001) * 100

    avg_vol    = volume.rolling(20).mean().iloc[-1]
    curr_vol   = volume.iloc[-1]
    vol_ratio  = curr_vol / max(avg_vol, 0.0000001)

    highs = high.rolling(10).max()
    lows  = low.rolling(10).min()
    nearest_resistance = highs.iloc[-1]
    nearest_support    = lows.iloc[-1]
    dist_to_resistance = (nearest_resistance - current_price) / max(current_price, 0.0000001) * 100
    dist_to_support    = (current_price - nearest_support)    / max(current_price, 0.0000001) * 100

    # Trend Score
    trend_score = 0
    trend_bias  = 0
    if ema20_val > ema50_val > ema200_val: trend_score += 20; trend_bias += 1
    elif ema20_val < ema50_val < ema200_val: trend_score += 0; trend_bias -= 1
    elif ema20_val > ema50_val: trend_score += 12; trend_bias += 1
    else: trend_score += 5

    if current_price > ema50_val: trend_score += 10; trend_bias += 1
    else: trend_score += 0; trend_bias -= 1

    if current_price > ema200_val: trend_score += 5; trend_bias += 1
    else: trend_score += 0; trend_bias -= 1

    # Momentum Score
    momentum_score = 0
    momentum_bias  = 0
    if rsi < 30: momentum_score += 10; momentum_bias += 1
    elif rsi > 70: momentum_score += 0; momentum_bias -= 1
    else: momentum_score += 5

    if macd_val > macd_sig: momentum_score += 10; momentum_bias += 1
    else: momentum_score += 0; momentum_bias -= 1

    if stoch_k < 20: momentum_score += 5; momentum_bias += 1
    else: momentum_score += 0

    # Structure Score
    structure_score = 0
    if bb_pos < 20: structure_score += 10
    elif bb_pos > 80: structure_score += 0
    else: structure_score += 5

    if dist_to_support < dist_to_resistance: structure_score += 10
    else: structure_score += 0

    # MTF Score
    mtf_score = mtf_score_override if mtf_score_override is not None else 7

    # Volume Score
    volume_score = 5 if vol_ratio >= 1.5 else 3

    total_score = trend_score + momentum_score + structure_score + mtf_score + volume_score
    
    if trend_bias > 0 and total_score >= 55: signal = "BUY"
    elif trend_bias < 0 and total_score <= 45: signal = "SELL"
    else: signal = "HOLD"

    confidence = total_score if signal == "BUY" else (100 - total_score) if signal == "SELL" else 50
    reason = f"Market Bias: {signal} ({confidence}/100)"

    signals = {
        "RSI": ("OVERSOLD" if rsi<30 else "OVERBOUGHT" if rsi>70 else "NEUTRAL", "green" if rsi<30 else "red" if rsi>70 else "neutral"),
        "MACD": ("BULLISH" if macd_val > macd_sig else "BEARISH", "green" if macd_val > macd_sig else "red")
    }

    indicators = {"RSI": round(rsi, 2), "MACD": round(macd_val, 6)}
    score_detail = {
        "trend": trend_score, "trend_max": 35,
        "momentum": momentum_score, "momentum_max": 25,
        "structure": structure_score, "structure_max": 20,
        "mtf": mtf_score, "mtf_max": 15,
        "volume": volume_score, "volume_max": 5,
        "total": total_score, "confidence": confidence
    }

    return signal, reason, signals, indicators, confidence, score_detail

# ─────────────────────────────────────────────
#  DECISION & PLANS
# ─────────────────────────────────────────────
def calculate_trade_decision(signal, score_detail, df, supports, resistances, trading_mode="Intraday"):
    if df is None or df.empty or signal == "HOLD":
        return "SKIP", "Sinyal HOLD — tidak ada setup", "#8b949e"
    return "ENTER", "Setup siap dieksekusi", "#3fb950"

def calculate_mtf_score(symbol, current_tf, trading_mode="Ketat"):
    tf_config = [("15m","15M",2),("1h","1H",5),("4h","4H",8)]
    total_score, total_weight = 0, 0
    for interval, label, weight in tf_config:
        df_tf = get_mt5_klines(symbol, interval, 100)
        if df_tf is None or df_tf.empty: continue
        close_tf = df_tf["close"]
        price_tf = close_tf.iloc[-1]
        ema50_tf = ta.trend.EMAIndicator(close_tf, window=50).ema_indicator().iloc[-1]
        tf_score = 1.0 if price_tf > ema50_tf else 0.0
        total_score  += tf_score * weight
        total_weight += weight
    return round((total_score / max(total_weight, 1)) * 15)

def get_support_resistance(df, n=3):
    if df is None or df.empty or len(df) < 20:
        return [], []
    price = df["close"].iloc[-1]
    highs = df["high"].rolling(5, center=True).max()
    lows  = df["low"].rolling(5, center=True).min()
    res, sup = [], []
    for i in range(len(df)):
        if df["high"].iloc[i] == highs.iloc[i]: res.append(df["high"].iloc[i])
        if df["low"].iloc[i] == lows.iloc[i]: sup.append(df["low"].iloc[i])
    res = sorted(set([round(r, 5) for r in res if r > price]))[:n]
    sup = sorted(set([round(s, 5) for s in sup if s < price]), reverse=True)[:n]
    return res, sup

def generate_ai_reasoning(signal, decision, decision_reason, score_detail, indicators, supports, resistances, trading_mode="Ketat"):
    points = ["Kombinasi analisis indikator MT5."]
    return points, "Kesimpulan trading terhitung dari data historis.", "#3fb950"

def build_chart(df, symbol, resistances=[], supports=[]):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2])
    fig.add_trace(go.Candlestick(x=df["timestamp"], open=df["open"], high=df["high"], low=df["low"], close=df["close"]), row=1, col=1)
    fig.update_layout(plot_bgcolor="#0d1117", paper_bgcolor="#0d1117", height=450)
    return fig

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
if "auto_refresh_mt5"   not in st.session_state: st.session_state["auto_refresh_mt5"]   = False
if "use_gemini_mt5"     not in st.session_state: st.session_state["use_gemini_mt5"]     = True
if "gemini_result_mt5"  not in st.session_state: st.session_state["gemini_result_mt5"]  = None

# ─────────────────────────────────────────────
#  DASHBOARD RENDER
# ─────────────────────────────────────────────
DEFAULT_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "XAUUSD"]

col_sel1, col_sel2 = st.columns([2, 1])
with col_sel1:
    symbol = st.selectbox("🌍 Select Pair", DEFAULT_PAIRS)
with col_sel2:
    custom = st.text_input("Custom pair", placeholder="e.g. NZDUSD")
    if custom: symbol = custom.upper()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🕐 Multi-Timeframe", "🌍 Market Watch", "🧪 Backtesting", "⚙️ Settings"])

with tab1:
    trading_mode = st.selectbox("🎯 Trading Mode", ["Scalping","Intraday","Swing"])
    interval = st.selectbox("⏱ Timeframe", [("15 Minutes","15m"), ("1 Hour","1h")])
    interval_val = interval[1]
    candles = st.slider("Candles", 50, 500, 200)

    price_data = get_mt5_price(symbol)
    if price_data is None:
        st.error(f"Gagal ambil data {symbol}. Pastiin MT5 running & pair tersedia di Market Watch.")
        st.stop()

    bid, ask, digits = price_data["bid"], price_data["ask"], price_data["digits"]
    fmt = f",.{digits}f"

    st.write(f"**Bid:** {bid} | **Ask:** {ask} | **Spread:** {price_data['spread']} pts")

    df = get_mt5_klines(symbol, interval_val, candles)
    
    if df is None or df.empty:
        st.error("Gagal memuat data chart dari terminal.")
        st.info("💡 Solusi: Silakan buka MT5 Anda dan pastikan chart pair ini terunduh di timeframe yang dipilih.")
        st.stop()

    resistances, supports = get_support_resistance(df)

    col_tog, col_btn = st.columns([1, 2])
    with col_tog:
        use_gemini = st.checkbox("✨ Pakai Gemini AI", value=st.session_state["use_gemini_mt5"] and GEMINI_ENABLED)
    with col_btn:
        do_refresh = st.button("🔄 Refresh Analisis", use_container_width=True)

    col_chart, col_signal = st.columns([3, 1])
    with col_chart:
        fig = build_chart(df, symbol, resistances, supports)
        st.plotly_chart(fig, use_container_width=True)

    with col_signal:
        mtf_real = calculate_mtf_score(symbol, "15M", trading_mode)
        signal, reason, signals, indicators, confidence, score_detail = calculate_signal(df, mtf_score_override=mtf_real)
        
        gemini_data = formula_signal_engine(df, symbol, bid, digits)
        if gemini_data:
            st.success(f"Analisis Selesai: {gemini_data['action']} - Conf: {gemini_data['confidence']}%")
            st.write(gemini_data["reason"])
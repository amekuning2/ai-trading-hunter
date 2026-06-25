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
from binance_helper import fetch_ticker_price, fetch_klines_data

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Trading Dashboard",
    page_icon="📈",
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
    .stSidebar .stSelectbox label,
    .stSidebar .stRadio label,
    .stSidebar p { color: #8b949e !important; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }

    [data-testid="metric-container"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
    }
    [data-testid="metric-container"] label { color: #8b949e !important; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #e6edf3; font-size: 24px; font-weight: 700; }
    [data-testid="metric-container"] [data-testid="stMetricDelta"] { font-size: 13px; }

    .signal-buy {
        background: linear-gradient(135deg, #0d2b1d, #0f3d2a);
        border: 1px solid #2ea043;
        border-left: 4px solid #2ea043;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
    }
    .signal-sell {
        background: linear-gradient(135deg, #2d1b1b, #3d1f1f);
        border: 1px solid #f85149;
        border-left: 4px solid #f85149;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
    }
    .signal-hold {
        background: linear-gradient(135deg, #1b1f2d, #1e2540);
        border: 1px solid #388bfd;
        border-left: 4px solid #388bfd;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
    }
    .signal-text { font-size: 32px; font-weight: 800; margin: 0; letter-spacing: 2px; }
    .signal-buy .signal-text { color: #3fb950; }
    .signal-sell .signal-text { color: #f85149; }
    .signal-hold .signal-text { color: #388bfd; }
    .signal-reason { color: #8b949e; font-size: 13px; margin-top: 8px; }

    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin: 3px;
    }
    .badge-green { background: #0d2b1d; color: #3fb950; border: 1px solid #2ea043; }
    .badge-red { background: #2d1b1b; color: #f85149; border: 1px solid #f85149; }
    .badge-neutral { background: #1b1f2d; color: #8b949e; border: 1px solid #30363d; }

    .section-header {
        color: #8b949e;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 2px;
        border-bottom: 1px solid #30363d;
        padding-bottom: 8px;
        margin-bottom: 16px;
    }

    .gainer-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 12px;
        border-radius: 6px;
        margin: 4px 0;
        background: #161b22;
        border: 1px solid #30363d;
    }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    .js-plotly-plot { border-radius: 8px; }

    .mtf-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        margin: 4px 0;
    }
    .mtf-buy { border-left: 3px solid #3fb950; }
    .mtf-sell { border-left: 3px solid #f85149; }
    .mtf-hold { border-left: 3px solid #388bfd; }

    .strength-bar-container {
        background: #21262d;
        border-radius: 20px;
        height: 8px;
        margin: 8px 0;
        overflow: hidden;
    }
    .strength-bar-fill {
        height: 100%;
        border-radius: 20px;
    }

    .sr-level { display: flex; justify-content: space-between; padding: 6px 10px; border-radius: 6px; margin: 3px 0; font-size: 12px; }
    .sr-resistance { background: #2d1b1b; border-left: 3px solid #f85149; }
    .sr-support { background: #0d2b1d; border-left: 3px solid #3fb950; }

    .tp-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 16px;
        margin: 8px 0;
    }
    .tp-row {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px solid #21262d;
        font-size: 13px;
    }
    .tp-row:last-child { border-bottom: none; }
    .tp-label { color: #8b949e; }
    .tp-value { color: #e6edf3; font-weight: 600; }
    .tp-green { color: #3fb950 !important; }
    .tp-red { color: #f85149 !important; }
    .tp-yellow { color: #f0883e !important; }

    .gemini-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid #0f3460;
        border-left: 4px solid #d2a8ff;
        border-radius: 8px;
        padding: 16px;
        margin-top: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  LOAD API CREDENTIALS
# ─────────────────────────────────────────────
try:
    BINANCE_API_KEY    = st.secrets["BINANCE_API_KEY"]
    BINANCE_API_SECRET = st.secrets["BINANCE_API_SECRET"]
    GEMINI_API_KEY     = st.secrets.get("GEMINI_API_KEY", "")
except Exception as e:
    st.error(f"Secrets error: {e}")
    st.stop()

if not BINANCE_API_KEY or not BINANCE_API_SECRET:
    st.error("❌ Binance API credentials not found!")
    st.stop()

GEMINI_ENABLED = bool(GEMINI_API_KEY)
if GEMINI_ENABLED:
    genai.configure(api_key=GEMINI_API_KEY)

# ─────────────────────────────────────────────
#  BINANCE CLIENT
# ─────────────────────────────────────────────
@st.cache_resource
def get_client(BINANCE_API_KEY, BINANCE_API_SECRET):
    return Client(BINANCE_API_KEY, BINANCE_API_SECRET)

# ─────────────────────────────────────────────
#  DATA FUNCTIONS — DUAL MARKET (SPOT & FUTURES)
# ─────────────────────────────────────────────
@st.cache_data(ttl=30)
def get_price(symbol, BINANCE_API_KEY, BINANCE_API_SECRET, market_type="Spot"):
    try:
        client = get_client(BINANCE_API_KEY, BINANCE_API_SECRET)
        if market_type == "Futures":
            ticker = client.futures_ticker(symbol=symbol)
            return {
                "price":       float(ticker["lastPrice"]),
                "change":      float(ticker["priceChangePercent"]),
                "high":        float(ticker["highPrice"]),
                "low":         float(ticker["lowPrice"]),
                "volume":      float(ticker["volume"]),
                "quoteVolume": float(ticker["quoteVolume"]),
            }
        else:
            ticker = client.get_ticker(symbol=symbol)
            return {
                "price":       float(ticker["lastPrice"]),
                "change":      float(ticker["priceChangePercent"]),
                "high":        float(ticker["highPrice"]),
                "low":         float(ticker["lowPrice"]),
                "volume":      float(ticker["volume"]),
                "quoteVolume": float(ticker["quoteVolume"]),
            }
    except Exception as e:
        st.error(f"BINANCE ERROR: {type(e).__name__}")
        st.error(str(e))
        raise

@st.cache_data(ttl=60)
def get_klines(symbol, interval, limit, BINANCE_API_KEY, BINANCE_API_SECRET, market_type="Spot"):
    try:
        client = get_client(BINANCE_API_KEY, BINANCE_API_SECRET)
        if market_type == "Futures":
            klines = client.futures_klines(symbol=symbol, interval=interval, limit=limit)
        else:
            klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=[
            "timestamp","open","high","low","close","volume",
            "close_time","quote_volume","trades","taker_buy_base",
            "taker_buy_quote","ignore"
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        for col in ["open","high","low","close","volume"]:
            df[col] = df[col].astype(float)
        return df
    except Exception as e:
        return None

@st.cache_data(ttl=60)
def get_top_gainers(BINANCE_API_KEY, BINANCE_API_SECRET, n=10):
    try:
        client = get_client(BINANCE_API_KEY, BINANCE_API_SECRET)
        tickers = client.get_ticker()
        usdt_pairs = [t for t in tickers if t["symbol"].endswith("USDT") and float(t["quoteVolume"]) > 1_000_000]
        sorted_gainers = sorted(usdt_pairs, key=lambda x: float(x["priceChangePercent"]), reverse=True)
        return sorted_gainers[:n]
    except:
        return []

# ─────────────────────────────────────────────
#  AI SIGNAL ENGINE v2 — 5-CATEGORY SCORING
#  Trend=35, Momentum=25, Structure=20, MTF=15, Volume=5
# ─────────────────────────────────────────────
def calculate_signal(df, mtf_score_override=None):
    if df is None or len(df) < 50:
        empty_detail = {
            "trend": 0, "trend_max": 35, "momentum": 0, "momentum_max": 25,
            "structure": 0, "structure_max": 20, "mtf": 0, "mtf_max": 15,
            "volume": 0, "volume_max": 5, "total": 0, "bias": "HOLD"
        }
        return "HOLD", "Data tidak cukup", {}, {}, 0, empty_detail

    close         = df["close"]
    high          = df["high"]
    low           = df["low"]
    volume        = df["volume"]
    current_price = close.iloc[-1]

    ema20  = ta.trend.EMAIndicator(close, window=20).ema_indicator()
    ema50  = ta.trend.EMAIndicator(close, window=50).ema_indicator()
    ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator() if len(close) >= 200 else ema50

    ema20_val  = ema20.iloc[-1]
    ema50_val  = ema50.iloc[-1]
    ema200_val = ema200.iloc[-1]

    rsi       = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]
    macd_ind  = ta.trend.MACD(close)
    macd_val  = macd_ind.macd().iloc[-1]
    macd_sig  = macd_ind.macd_signal().iloc[-1]
    macd_hist = macd_ind.macd_diff().iloc[-1]

    stoch   = ta.momentum.StochasticOscillator(high, low, close)
    stoch_k = stoch.stoch().iloc[-1]
    stoch_d = stoch.stoch_signal().iloc[-1]

    bb        = ta.volatility.BollingerBands(close, window=20)
    bb_upper  = bb.bollinger_hband().iloc[-1]
    bb_lower  = bb.bollinger_lband().iloc[-1]
    bb_pos    = (current_price - bb_lower) / max(bb_upper - bb_lower, 0.0001) * 100

    avg_vol   = volume.rolling(20).mean().iloc[-1]
    curr_vol  = volume.iloc[-1]
    vol_ratio = curr_vol / max(avg_vol, 0.0001)

    highs              = high.rolling(10).max()
    lows               = low.rolling(10).min()
    nearest_resistance = highs.iloc[-1]
    nearest_support    = lows.iloc[-1]
    dist_to_resistance = (nearest_resistance - current_price) / max(current_price, 0.0001) * 100
    dist_to_support    = (current_price - nearest_support)    / max(current_price, 0.0001) * 100

    # ── 1. TREND SCORE (0-35) ──
    trend_score = 0
    trend_bias  = 0
    if ema20_val > ema50_val > ema200_val:
        trend_score += 20; trend_bias += 1
    elif ema20_val < ema50_val < ema200_val:
        trend_score += 0;  trend_bias -= 1
    elif ema20_val > ema50_val:
        trend_score += 12; trend_bias += 1
    elif ema20_val < ema50_val:
        trend_score += 5;  trend_bias -= 1
    else:
        trend_score += 8

    if current_price > ema50_val:
        trend_score += 10; trend_bias += 1
    elif current_price < ema50_val:
        trend_score += 0;  trend_bias -= 1
    else:
        trend_score += 5

    if current_price > ema200_val:
        trend_score += 5;  trend_bias += 1
    else:
        trend_score += 0;  trend_bias -= 1

    trend_score = min(trend_score, 35)

    # ── 2. MOMENTUM SCORE (0-25) ──
    momentum_score = 0
    momentum_bias  = 0
    if rsi < 30:
        momentum_score += 10; momentum_bias += 1
    elif rsi < 45:
        momentum_score += 8;  momentum_bias += 1
    elif rsi > 70:
        momentum_score += 0;  momentum_bias -= 1
    elif rsi > 55:
        momentum_score += 3;  momentum_bias -= 1
    else:
        momentum_score += 5

    if macd_val > macd_sig and macd_hist > 0:
        momentum_score += 10; momentum_bias += 1
    elif macd_val < macd_sig and macd_hist < 0:
        momentum_score += 0;  momentum_bias -= 1
    elif macd_val > macd_sig:
        momentum_score += 6;  momentum_bias += 1
    elif macd_val < macd_sig:
        momentum_score += 3;  momentum_bias -= 1
    else:
        momentum_score += 5

    if stoch_k < 20 and stoch_k > stoch_d:
        momentum_score += 5;  momentum_bias += 1
    elif stoch_k > 80 and stoch_k < stoch_d:
        momentum_score += 0;  momentum_bias -= 1
    elif stoch_k < 40:
        momentum_score += 3;  momentum_bias += 1
    elif stoch_k > 60:
        momentum_score += 2;  momentum_bias -= 1
    else:
        momentum_score += 2

    momentum_score = min(momentum_score, 25)

    # ── 3. STRUCTURE SCORE (0-20) ──
    structure_score = 0
    structure_bias  = 0
    if dist_to_support < dist_to_resistance:
        structure_score += 10; structure_bias += 1
    else:
        structure_score += 5;  structure_bias -= 1

    if dist_to_support <= 1.5:
        structure_score += 10; structure_bias += 1
    elif dist_to_resistance <= 1.0:
        structure_score += 2;  structure_bias -= 1
    else:
        structure_score += 5

    structure_score = min(structure_score, 20)

    # ── 4. MTF SCORE (0-15) ──
    if mtf_score_override is not None:
        mtf_score = mtf_score_override
        mtf_bias  = 1 if mtf_score >= 8 else -1 if mtf_score <= 5 else 0
    else:
        mtf_score = 7
        mtf_bias  = 0

    # ── 5. VOLUME SCORE (0-5) ──
    volume_score = 0
    if vol_ratio >= 2.0:
        volume_score = 5
    elif vol_ratio >= 1.5:
        volume_score = 4
    elif vol_ratio >= 1.2:
        volume_score = 2
    elif vol_ratio < 0.5:
        volume_score = 0
    else:
        volume_score = 1

    total_score = trend_score + momentum_score + structure_score + mtf_score + volume_score

    # ── SIGNAL DETERMINATION ──
    net_bias = trend_bias + momentum_bias + structure_bias + mtf_bias
    if total_score >= 60 and net_bias >= 2:
        signal = "BUY"
        confidence = min(100, int(
            total_score + trend_score * 0.3 + momentum_score * 0.2
        ))
    elif total_score <= 40 or net_bias <= -3:
        signal = "SELL"
        confidence = min(100, int(
            (100 - total_score) + (35 - trend_score) * 0.3 + (25 - momentum_score) * 0.2
        ))
    else:
        signal = "HOLD"
        confidence = 50

    if signal == "HOLD":
        reason = "Market Bias: NETRAL — tunggu arah yang lebih jelas"
    else:
        strength = "STRONG" if confidence >= 75 else "MODERATE" if confidence >= 60 else "WEAK"
        reason = f"Market Bias: {signal} — {strength} ({confidence}/100)"

    # ── BADGES ──
    signals = {}
    if rsi < 30:       signals["RSI"]   = ("OVERSOLD", "green")
    elif rsi < 45:     signals["RSI"]   = ("BULLISH", "green")
    elif rsi > 70:     signals["RSI"]   = ("OVERBOUGHT", "red")
    elif rsi > 55:     signals["RSI"]   = ("BEARISH", "red")
    else:              signals["RSI"]   = ("NEUTRAL", "neutral")

    if macd_val > macd_sig and macd_hist > 0:    signals["MACD"] = ("BULLISH CROSS", "green")
    elif macd_val < macd_sig and macd_hist < 0:  signals["MACD"] = ("BEARISH CROSS", "red")
    else:                                         signals["MACD"] = ("NEUTRAL", "neutral")

    if ema20_val > ema50_val > ema200_val:   signals["EMA"] = ("STRONG UPTREND", "green")
    elif ema20_val < ema50_val < ema200_val: signals["EMA"] = ("STRONG DOWNTREND", "red")
    elif ema20_val > ema50_val:              signals["EMA"] = ("UPTREND", "green")
    else:                                    signals["EMA"] = ("DOWNTREND", "red")

    if stoch_k < 20 and stoch_k > stoch_d:  signals["STOCH"] = ("OVERSOLD CROSS", "green")
    elif stoch_k > 80 and stoch_k < stoch_d: signals["STOCH"] = ("OVERBOUGHT CROSS", "red")
    else:                                    signals["STOCH"] = ("NEUTRAL", "neutral")

    if bb_pos < 20:   signals["BB"] = ("BELOW LOWER", "green")
    elif bb_pos > 80: signals["BB"] = ("ABOVE UPPER", "red")
    else:             signals["BB"] = ("WITHIN BAND", "neutral")

    if vol_ratio >= 1.5: signals["VOL"] = ("SURGE ⚡", "green")
    else:                signals["VOL"] = ("NORMAL", "neutral")

    indicators = {
        "RSI":      round(rsi, 2),
        "MACD":     round(macd_val, 6),
        "Stoch %K": round(stoch_k, 2),
        "BB_pos":   round(bb_pos, 1),
        "EMA20":    round(ema20_val, 4),
        "EMA50":    round(ema50_val, 4),
        "EMA200":   round(ema200_val, 4),
    }

    score_detail = {
        "trend": trend_score, "trend_max": 35,
        "momentum": momentum_score, "momentum_max": 25,
        "structure": structure_score, "structure_max": 20,
        "mtf": mtf_score, "mtf_max": 15,
        "volume": volume_score, "volume_max": 5,
        "total": total_score, "confidence": confidence, "bias": signal,
    }

    return signal, reason, signals, indicators, confidence, score_detail

# ─────────────────────────────────────────────
#  TRADE DECISION ENGINE
# ─────────────────────────────────────────────
def calculate_trade_decision(signal, score_detail, df, supports, resistances, trading_mode="Ketat"):
    if signal == "HOLD":
        return "SKIP", "Sinyal HOLD — tidak ada setup", "#8b949e"

    is_buy      = signal == "BUY"
    total       = score_detail.get("confidence", score_detail["total"])
    trend       = score_detail["trend"] if is_buy else score_detail["trend_max"] - score_detail["trend"]
    momentum    = score_detail["momentum"] if is_buy else score_detail["momentum_max"] - score_detail["momentum"]
    structure   = score_detail["structure"] if is_buy else score_detail["structure_max"] - score_detail["structure"]
    mtf         = score_detail["mtf"] if is_buy else score_detail["mtf_max"] - score_detail["mtf"]

    is_scalping = trading_mode == "Scalping"
    sl_mult = 0.8 if is_scalping else 1.5
    tp_mult = 0.7 if is_scalping else 2.0

    try:
        atr           = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range().iloc[-1]
        current_price = df["close"].iloc[-1]
        sl_price      = current_price - (atr * sl_mult) if signal == "BUY" else current_price + (atr * sl_mult)
        tp1_price     = current_price + (atr * tp_mult) if signal == "BUY" else current_price - (atr * tp_mult)
        sl_dist       = abs(current_price - sl_price)
        tp_dist       = abs(tp1_price - current_price)
        rr_ratio      = tp_dist / sl_dist if sl_dist > 0 else 0
    except Exception:
        rr_ratio = 0

    structure_ok = False
    if signal == "BUY" and supports:
        structure_ok = abs(current_price - supports[0]) / current_price * 100 <= 1.5
    elif signal == "SELL" and resistances:
        structure_ok = abs(resistances[0] - current_price) / current_price * 100 <= 1.5
    else:
        structure_ok = structure >= 12

    reasons_wait = []
    min_score    = 52 if is_scalping else 50
    min_rr       = 0.70 if is_scalping else 1.0
    trend_min    = 10 if is_scalping else 15
    momentum_min = 8  if is_scalping else 12
    mtf_min      = 4  if is_scalping else 6

    if total < min_score:
        return "SKIP", f"Score terlalu rendah ({total}/100) — jangan masuk", "#f85149"
    if rr_ratio < min_rr:
        return "SKIP", f"RR {rr_ratio:.2f} — reward tidak sepadan risiko", "#f85149"
    if trend < trend_min:
        reasons_wait.append("trend lemah")
    if momentum < momentum_min:
        reasons_wait.append("momentum belum konfirmasi")
    if not is_scalping and rr_ratio < 1.5:
        reasons_wait.append(f"RR {rr_ratio:.2f} masih marginal")
    if mtf < mtf_min:
        reasons_wait.append("MTF belum searah")
    if not structure_ok and (not is_scalping or structure < 7):
        reasons_wait.append("belum di zona S/R ideal")

    enter_score = 55 if is_scalping else 60
    enter_rr    = 0.70 if is_scalping else 1.5

    if not reasons_wait and total >= enter_score and rr_ratio >= enter_rr:
        mode_note = "Scalp aktif" if is_scalping else "Setup solid"
        return "ENTER", f"{mode_note} — Score {total}/100, RR 1:{rr_ratio:.2f}", "#3fb950"

    if reasons_wait:
        return "WAIT", f"Tunggu: {', '.join(reasons_wait[:2])}", "#f0883e"

    return "ENTER", f"Setup cukup — Score {total}/100, RR 1:{rr_ratio:.1f}", "#3fb950"

# ─────────────────────────────────────────────
#  REAL MTF SCORE ENGINE
# ─────────────────────────────────────────────
def calculate_mtf_score(symbol, current_tf, BINANCE_API_KEY, BINANCE_API_SECRET, trading_mode="Ketat"):
    tf_config = (
        [("5m", "5M", 3), ("15m", "15M", 5), ("1h", "1H", 7)]
        if trading_mode == "Scalping"
        else [("1h", "1H", 3), ("4h", "4H", 5), ("1d", "1D", 7)]
    )
    total_weight = 0
    total_score  = 0

    for interval, label, weight in tf_config:
        if label == current_tf:
            continue
        df_tf = get_klines(symbol, interval, 200, BINANCE_API_KEY, BINANCE_API_SECRET)
        if df_tf is None or len(df_tf) < 50:
            continue

        close_tf  = df_tf["close"]
        ema20_tf  = ta.trend.EMAIndicator(close_tf, window=20).ema_indicator().iloc[-1]
        ema50_tf  = ta.trend.EMAIndicator(close_tf, window=50).ema_indicator().iloc[-1]
        ema200_tf = ta.trend.EMAIndicator(close_tf, window=200).ema_indicator().iloc[-1] if len(close_tf) >= 200 else ema50_tf
        price_tf  = close_tf.iloc[-1]

        if ema20_tf > ema50_tf > ema200_tf and price_tf > ema50_tf:      tf_score = 1.0
        elif ema20_tf < ema50_tf < ema200_tf and price_tf < ema50_tf:    tf_score = 0.0
        elif ema20_tf > ema50_tf and price_tf > ema50_tf:                tf_score = 0.75
        elif ema20_tf < ema50_tf and price_tf < ema50_tf:                tf_score = 0.25
        else:                                                              tf_score = 0.5

        total_score  += tf_score * weight
        total_weight += weight

    if total_weight == 0:
        return 7

    return round((total_score / total_weight) * 15)

def multi_timeframe_analysis(symbol, BINANCE_API_KEY, BINANCE_API_SECRET):
    timeframes = [("1H", "1h", 100), ("4H", "4h", 100), ("1D", "1d", 200)]
    results = []
    for label, interval, limit in timeframes:
        df = get_klines(symbol, interval, limit, BINANCE_API_KEY, BINANCE_API_SECRET)
        sig, reason, _, _, confidence, _ = calculate_signal(df)
        results.append((label, sig, reason, confidence))
    return results

# ─────────────────────────────────────────────
#  SUPPORT & RESISTANCE
# ─────────────────────────────────────────────
def get_support_resistance(df, n=3):
    if df is None or len(df) < 20:
        return [], []
    highs         = df["high"].rolling(5, center=True).max()
    lows          = df["low"].rolling(5, center=True).min()
    resistance_levels = []
    support_levels    = []
    current_price = df["close"].iloc[-1]
    for i in range(len(df)):
        if df["high"].iloc[i] == highs.iloc[i]:
            resistance_levels.append(df["high"].iloc[i])
        if df["low"].iloc[i] == lows.iloc[i]:
            support_levels.append(df["low"].iloc[i])
    resistance_levels = sorted(set([round(r, 4) for r in resistance_levels if r > current_price]))[:n]
    support_levels    = sorted(set([round(s, 4) for s in support_levels if s < current_price]), reverse=True)[:n]
    return resistance_levels, support_levels

# ─────────────────────────────────────────────
#  TRADING PLAN GENERATOR
# ─────────────────────────────────────────────
def generate_trading_plan(df, price_data, signal, supports, resistances, modal_usdt=100, trading_mode="Ketat"):
    current_price = price_data["price"]
    if df is None or len(df) < 20:
        return None

    atr = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range().iloc[-1]

    if trading_mode == "Scalping":
        sl_mult, tp1_mult, tp2_mult, tp3_mult = 0.8, 0.7, 1.0, 1.4
        min_tp_pct, tp_step_pct, min_sl_pct   = 0.0005, 0.0005, 0.0015
    else:
        sl_mult, tp1_mult, tp2_mult, tp3_mult = 1.5, 2.0, 3.5, 5.0
        min_tp_pct, tp_step_pct, min_sl_pct   = 0.001, 0.002, 0.005

    if signal == "BUY":
        entry   = round(current_price, 4)
        sl_atr  = round(entry - (atr * sl_mult), 4)
        sl_sr   = round(supports[0] * 0.998, 4) if supports else sl_atr
        sl      = sl_atr if trading_mode == "Scalping" else min(sl_atr, sl_sr)
        tp1_atr = round(entry + (atr * tp1_mult), 4)
        tp2_atr = round(entry + (atr * tp2_mult), 4)
        tp3_atr = round(entry + (atr * tp3_mult), 4)
        if resistances:
            r1  = round(resistances[0] * 0.999, 4)
            tp1 = min(tp1_atr, r1) if r1 > entry else tp1_atr
        else:
            tp1 = tp1_atr
        tp2 = tp2_atr
        tp3 = tp3_atr
        tp1 = max(tp1, round(entry * (1 + min_tp_pct), 4))
        tp2 = max(tp2, round(tp1  * (1 + tp_step_pct), 4))
        tp3 = max(tp3, round(tp2  * (1 + tp_step_pct), 4))
        sl  = min(sl,  round(entry * (1 - min_sl_pct), 4))

    elif signal == "SELL":
        entry   = round(current_price, 4)
        sl_atr  = round(entry + (atr * sl_mult), 4)
        sl_sr   = round(resistances[0] * 1.002, 4) if resistances else sl_atr
        sl      = sl_atr if trading_mode == "Scalping" else max(sl_atr, sl_sr)
        tp1_atr = round(entry - (atr * tp1_mult), 4)
        tp2_atr = round(entry - (atr * tp2_mult), 4)
        tp3_atr = round(entry - (atr * tp3_mult), 4)
        if supports:
            s1  = round(supports[0] * 1.001, 4)
            tp1 = max(tp1_atr, s1) if s1 < entry else tp1_atr
        else:
            tp1 = tp1_atr
        tp2 = tp2_atr
        tp3 = tp3_atr
        tp1 = min(tp1, round(entry * (1 - min_tp_pct), 4))
        tp2 = min(tp2, round(tp1  * (1 - tp_step_pct), 4))
        tp3 = min(tp3, round(tp2  * (1 - tp_step_pct), 4))
        sl  = max(sl,  round(entry * (1 + min_sl_pct), 4))
    else:
        return None

    sl_pct   = abs((sl  - entry) / entry * 100)
    tp1_pct  = abs((tp1 - entry) / entry * 100)
    tp2_pct  = abs((tp2 - entry) / entry * 100)
    tp3_pct  = abs((tp3 - entry) / entry * 100)
    rr_ratio = round(tp1_pct / sl_pct, 2) if sl_pct > 0 else 0
    qty      = round(modal_usdt / entry, 6)

    profit_tp1 = round((tp1 - entry) * qty, 2) if signal == "BUY" else round((entry - tp1) * qty, 2)
    profit_tp2 = round((tp2 - entry) * qty, 2) if signal == "BUY" else round((entry - tp2) * qty, 2)
    profit_tp3 = round((tp3 - entry) * qty, 2) if signal == "BUY" else round((entry - tp3) * qty, 2)
    loss_sl    = round(abs((sl - entry) * qty), 2)

    return {
        "signal": signal, "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3,
        "sl_pct": round(sl_pct, 2), "tp1_pct": round(tp1_pct, 2),
        "tp2_pct": round(tp2_pct, 2), "tp3_pct": round(tp3_pct, 2),
        "rr_ratio": rr_ratio, "qty": qty, "modal": modal_usdt,
        "profit_tp1": profit_tp1, "profit_tp2": profit_tp2, "profit_tp3": profit_tp3,
        "loss_sl": loss_sl, "atr": round(atr, 4),
    }

# ─────────────────────────────────────────────
#  AI REASONING ENGINE (Original Rule-based)
# ─────────────────────────────────────────────
def generate_ai_reasoning(signal, decision, decision_reason, score_detail, indicators, supports, resistances, trading_mode="Ketat"):
    if signal == "HOLD":
        points     = [
            "Tidak ada bias arah yang cukup jelas dari kombinasi Trend, Momentum, dan Structure saat ini.",
            "Total score belum cukup tinggi maupun cukup rendah untuk memicu sinyal BUY atau SELL.",
        ]
        conclusion = "Kesimpulan: Market belum menunjukkan arah yang jelas. Lebih baik tunggu konfirmasi candle berikutnya."
        return points, conclusion, "#388bfd"

    is_buy         = signal == "BUY"
    direction_word = "bullish" if is_buy else "bearish"

    def strength_label(pct):
        if pct >= 80: return "sangat kuat"
        if pct >= 60: return "kuat"
        if pct >= 45: return "cukup mendukung"
        if pct >= 25: return "masih lemah"
        return "berlawanan arah dengan sinyal"

    def cat_pct(score, max_score):
        raw_pct = (score / max_score * 100) if max_score else 0
        return raw_pct if is_buy else (100 - raw_pct)

    trend_pct     = cat_pct(score_detail["trend"],     score_detail["trend_max"])
    momentum_pct  = cat_pct(score_detail["momentum"],  score_detail["momentum_max"])
    structure_pct = cat_pct(score_detail["structure"], score_detail["structure_max"])
    mtf_pct       = cat_pct(score_detail["mtf"],       score_detail["mtf_max"])
    volume_score  = score_detail["volume"]

    points = []
    ema_note = "EMA20/EMA50/EMA200 align mendukung arah ini" if trend_pct >= 60 else "EMA belum sepenuhnya align"
    points.append(f"Trend {direction_word} {strength_label(trend_pct)} — {ema_note}.")
    rsi_val  = indicators.get("RSI", "-")
    macd_note = "MACD searah dengan sinyal" if momentum_pct >= 60 else "MACD belum konfirmasi penuh"
    points.append(f"Momentum {strength_label(momentum_pct)} — RSI di level {rsi_val}, {macd_note}.")
    sr_note = "harga berada di zona Support/Resistance yang ideal" if structure_pct >= 60 else "harga belum berada di zona S/R yang ideal"
    points.append(f"Struktur harga {strength_label(structure_pct)} — {sr_note}.")
    if mtf_pct >= 70:
        mtf_label = "5M/15M/1H" if trading_mode == "Scalping" else "1H/4H/1D"
        points.append(f"Multi-timeframe ({mtf_label}) searah penuh, konfirmasi cukup kuat.")
    elif mtf_pct >= 45:
        points.append("Multi-timeframe sebagian searah, masih ada timeframe yang belum konfirmasi.")
    else:
        points.append("Multi-timeframe belum align — ada risiko pergerakan choppy/whipsaw.")
    if volume_score >= 4:   points.append("Volume sedang surge, menandakan minat pasar yang kuat di balik pergerakan ini.")
    elif volume_score >= 2: points.append("Volume dalam kondisi normal, tidak ada lonjakan minat pasar yang signifikan.")
    else:                   points.append("Volume tergolong lemah — waspada potensi pergerakan palsu (false move).")

    if decision == "ENTER":
        conclusion = f"Kesimpulan: Setup layak untuk {signal} sekarang. {decision_reason}."
        color = "#3fb950"
    elif decision == "WAIT":
        conclusion = f"Kesimpulan: Ada potensi {signal}, tapi belum ideal untuk masuk sekarang. {decision_reason}."
        color = "#f0883e"
    else:
        conclusion = f"Kesimpulan: Tidak disarankan masuk saat ini. {decision_reason}."
        color = "#f85149"

    return points, conclusion, color

# ─────────────────────────────────────────────
#  GEMINI AI LAYER (Enhancement, bukan pengganti)
# ─────────────────────────────────────────────
@st.cache_data(ttl=120)
def get_gemini_insights(symbol, interval, trading_mode, signal, decision, score_total,
                        rsi, macd_val, ema20, ema50, current_price,
                        supports_str, resistances_str, mtf_context_str, GEMINI_API_KEY,
                        market_type="Spot", leverage=1):
    if not GEMINI_API_KEY:
        return None
    try:
        futures_note = f"""
- Market Type: FUTURES (Leverage {leverage}x)
- Di Futures, sinyal BUY = posisi LONG, sinyal SELL = posisi SHORT (keduanya valid)
- Hitung potensi profit/loss dengan pengali leverage {leverage}x
""" if market_type == "Futures" else "- Market Type: SPOT (hanya BUY/HOLD yang valid)"

        prompt = f"""
Kamu adalah analis trading profesional yang membantu trader retail Indonesia.
Berikan 3 poin insight singkat dan 1 kesimpulan dalam Bahasa Indonesia yang santai tapi informatif.

Data market:
- Symbol: {symbol}, Timeframe: {interval}, Mode: {trading_mode}
- Signal Engine: {signal}, Decision: {decision}, Score: {score_total}/100
- RSI: {rsi}, MACD: {macd_val}, EMA20: {ema20}, EMA50: {ema50}
- Harga saat ini: {current_price}
- Support levels: {supports_str}
- Resistance levels: {resistances_str}
- MTF bias: {mtf_context_str}
{futures_note}

Fokus pada: apakah setup ini worth it untuk diambil trader dengan modal kecil?
Target: konsisten profit kecil, bukan FOMO besar.

Balas HANYA dalam format JSON:
{{"insights": ["poin1", "poin2", "poin3"], "kesimpulan": "teks kesimpulan singkat"}}
"""
        model    = genai.GenerativeModel("gemini-3.1-flash-lite")
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        data     = json.loads(response.text.strip())
        return data
    except Exception as e:
        return {"insights": [f"Gemini tidak tersedia: {str(e)}"], "kesimpulan": ""}

# ─────────────────────────────────────────────
#  CHART GENERATOR
# ─────────────────────────────────────────────
def build_chart(df, symbol, resistances=[], supports=[]):
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2]
    )

    fig.add_trace(go.Candlestick(
        x=df["timestamp"],
        open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="Price",
        increasing_line_color="#3fb950", decreasing_line_color="#f85149",
        increasing_fillcolor="#0d2b1d",  decreasing_fillcolor="#2d1b1b",
    ), row=1, col=1)

    ema20 = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    ema50 = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    fig.add_trace(go.Scatter(x=df["timestamp"], y=ema20, name="EMA20",
        line=dict(color="#f0883e", width=1.5, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=ema50, name="EMA50",
        line=dict(color="#388bfd", width=1.5, dash="dot")), row=1, col=1)

    bb = ta.volatility.BollingerBands(df["close"], window=20)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=bb.bollinger_hband(),
        name="BB Upper", line=dict(color="#8b949e", width=1, dash="dash"), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=bb.bollinger_lband(),
        name="BB Lower", line=dict(color="#8b949e", width=1, dash="dash"),
        fill="tonexty", fillcolor="rgba(139,148,158,0.05)", showlegend=False), row=1, col=1)

    for r in resistances:
        fig.add_hline(y=r, line_dash="dash", line_color="#f85149", opacity=0.6, row=1, col=1,
                      annotation_text=f"R {r:,.4f}", annotation_position="right")
    for s in supports:
        fig.add_hline(y=s, line_dash="dash", line_color="#3fb950", opacity=0.6, row=1, col=1,
                      annotation_text=f"S {s:,.4f}", annotation_position="right")

    colors = ["#3fb950" if df["close"].iloc[i] >= df["open"].iloc[i] else "#f85149" for i in range(len(df))]
    fig.add_trace(go.Bar(x=df["timestamp"], y=df["volume"], name="Volume",
        marker_color=colors, opacity=0.7), row=2, col=1)

    rsi_series = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    fig.add_trace(go.Scatter(x=df["timestamp"], y=rsi_series, name="RSI",
        line=dict(color="#d2a8ff", width=1.5)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#f85149", opacity=0.5, row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#3fb950", opacity=0.5, row=3, col=1)

    fig.update_layout(
        plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
        font=dict(color="#8b949e", size=11),
        height=600, margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        xaxis_rangeslider_visible=False,
    )
    fig.update_yaxes(gridcolor="#21262d", zerolinecolor="#21262d")
    fig.update_xaxes(gridcolor="#21262d", zerolinecolor="#21262d")
    return fig

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
if "symbol"         not in st.session_state: st.session_state["symbol"]         = "BTCUSDT"
if "interval_val"   not in st.session_state: st.session_state["interval_val"]   = "1h"
if "candles"        not in st.session_state: st.session_state["candles"]        = 200
if "auto_refresh"   not in st.session_state: st.session_state["auto_refresh"]   = False
# ── Fase 3: Futures State ──
if "market_type"    not in st.session_state: st.session_state["market_type"]    = "Spot"
if "leverage"       not in st.session_state: st.session_state["leverage"]       = 10
if "wallet_spot"    not in st.session_state: st.session_state["wallet_spot"]    = 50.0
if "wallet_futures" not in st.session_state: st.session_state["wallet_futures"] = 50.0
if "sim_history"    not in st.session_state: st.session_state["sim_history"]    = []

# ─────────────────────────────────────────────
#  MAIN CONTENT
# ─────────────────────────────────────────────
DEFAULT_PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
col_sel1, col_sel2 = st.columns([2, 1])
with col_sel1:
    symbol = st.selectbox("🪙 Select Pair", DEFAULT_PAIRS,
                          index=DEFAULT_PAIRS.index(st.session_state["symbol"]) if st.session_state["symbol"] in DEFAULT_PAIRS else 0)
with col_sel2:
    custom = st.text_input("Custom pair", placeholder="e.g. ADAUSDT")
    if custom:
        symbol = custom.upper()
st.session_state["symbol"] = symbol

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🕐 Multi-Timeframe", "🔥 Top Gainers", "🧪 Backtesting", "⚙️ Settings"])

# ─── TAB 1: DASHBOARD ───
with tab1:
    trading_mode = st.selectbox(
        "🎯 Trading Mode",
        ["Scalping", "Ketat"],
        format_func=lambda mode: "⚡ Scalping — entry & TP cepat" if mode == "Scalping" else "🛡️ Ketat — seleksi maksimum",
    )

    col_mode, col_lev = st.columns([1, 1])
    with col_mode:
        market_type = st.selectbox(
            "🏦 Market Type",
            ["Spot", "Futures"],
            index=0 if st.session_state["market_type"] == "Spot" else 1,
            format_func=lambda x: "🔵 Spot — Hanya BUY/HOLD" if x == "Spot" else "🟡 Futures — LONG & SHORT"
        )
        st.session_state["market_type"] = market_type
    with col_lev:
        if market_type == "Futures":
            leverage = st.slider("⚡ Leverage", min_value=1, max_value=20, value=st.session_state["leverage"])
            st.session_state["leverage"] = leverage
        else:
            leverage = 1
            st.session_state["leverage"] = 1
            st.markdown(f"""<div style="padding:10px; color:#8b949e; font-size:12px; margin-top:8px;">Leverage: 1x (Spot mode)</div>""", unsafe_allow_html=True)

    col_tf, col_candle = st.columns([2, 1])
    with col_tf:
        interval = st.selectbox("⏱ Timeframe", [
            ("1 Minute","1m"),("5 Minutes","5m"),("15 Minutes","15m"),
            ("1 Hour","1h"),("4 Hours","4h"),("1 Day","1d")
        ], format_func=lambda x: x[0], index=2 if trading_mode == "Scalping" else 3)
        interval_val = interval[1]
    with col_candle:
        candles = st.slider("Candles", 50, 500, 200)

    price_data = get_price(symbol, BINANCE_API_KEY, BINANCE_API_SECRET, market_type=market_type)
    if price_data is None:
        st.error(f"Gagal ambil data {symbol}. Cek API key atau nama pair.")
        st.stop()

    price        = price_data["price"]
    change       = price_data["change"]
    change_color = "#3fb950" if change >= 0 else "#f85149"

    # Header harga
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"""
        <div style="margin-bottom:8px;">
            <span style="font-size:28px; font-weight:800; color:#e6edf3;">{symbol}</span>
            <span style="font-size:13px; color:#8b949e; margin-left:12px;">BINANCE {market_type.upper()}</span>
            {f'<span style="font-size:12px; color:#f0883e; margin-left:8px; font-weight:700;">⚡ {leverage}x</span>' if market_type == "Futures" else ""}
        </div>
        <div>
            <span style="font-size:36px; font-weight:700; color:#e6edf3;">${price:,.4f}</span>
            <span style="font-size:16px; color:{change_color}; margin-left:12px;">
                {'▲' if change >= 0 else '▼'} {abs(change):.2f}%
            </span>
        </div>
        """, unsafe_allow_html=True)
    with col_h2:
        st.markdown(f"""
        <div style="text-align:right; padding-top:12px; color:#8b949e; font-size:12px;">
            Last update<br>
            <span style="color:#e6edf3;">{datetime.now().strftime('%H:%M:%S')}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("24h High", f"${price_data['high']:,.4f}")
    with col2: st.metric("24h Low",  f"${price_data['low']:,.4f}")
    with col3:
        vol_m = price_data["quoteVolume"] / 1_000_000
        st.metric("Volume (USDT)", f"${vol_m:,.1f}M")
    with col4: st.metric("24h Change", f"{change:+.2f}%", delta=f"{'Up' if change >= 0 else 'Down'}")

    st.markdown("---")

    col_chart, col_signal = st.columns([3, 1])

    with col_chart:
        st.markdown('<p class="section-header">Price Chart</p>', unsafe_allow_html=True)
        df          = get_klines(symbol, interval_val, candles, BINANCE_API_KEY, BINANCE_API_SECRET, market_type=market_type)
        resistances, supports = get_support_resistance(df)
        if df is not None:
            fig = build_chart(df, symbol, resistances, supports)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Gagal load chart data")

        trading_plan_container = st.container()

    with col_signal:
        st.markdown('<p class="section-header">AI Signal</p>', unsafe_allow_html=True)

        if df is not None:
            tf_label_map    = {"1m":"1M","5m":"5M","15m":"15M","1h":"1H","4h":"4H","1d":"1D"}
            current_tf_label = tf_label_map.get(interval_val, "1H")
            mtf_real        = calculate_mtf_score(symbol, current_tf_label, BINANCE_API_KEY, BINANCE_API_SECRET, trading_mode)
            signal, reason, signals, indicators, confidence, score_detail = calculate_signal(df, mtf_score_override=mtf_real)
            decision, decision_reason, decision_color = calculate_trade_decision(
                signal, score_detail, df, supports, resistances, trading_mode
            )

            signal_class   = f"signal-{signal.lower()}"
            signal_emoji   = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🔵"
            strength_color = "#3fb950" if signal == "BUY" else "#f85149" if signal == "SELL" else "#388bfd"
            decision_emoji = "🟢" if decision == "ENTER" else "🟡" if decision == "WAIT" else "🔴"
            decision_bg    = "rgba(63,185,80,0.12)"  if decision == "ENTER" else \
                             "rgba(240,136,62,0.12)" if decision == "WAIT"  else "rgba(248,81,73,0.08)"

            st.markdown(f"""
            <div class="{signal_class}">
                <p class="signal-text">{signal_emoji} {signal}</p>
                <p class="signal-reason">{reason}</p>
                <div class="strength-bar-container">
                    <div class="strength-bar-fill" style="width:{confidence}%; background:{strength_color};"></div>
                </div>
                <p style="color:#8b949e; font-size:11px;">Confidence: {confidence}%</p>
                <div style="margin-top:14px; background:{decision_bg}; border:1px solid {decision_color};
                     border-radius:6px; padding:10px 12px; text-align:center;">
                    <p style="font-size:18px; font-weight:900; color:{decision_color}; margin:0; letter-spacing:3px;">
                        {decision_emoji} {decision}
                    </p>
                    <p style="color:#8b949e; font-size:11px; margin:4px 0 0 0;">{decision_reason}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

            reasoning_container = st.container()

            # Score Breakdown
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<p class="section-header">Score Breakdown</p>', unsafe_allow_html=True)
            score_direction = 1 if signal != "SELL" else -1
            score_rows = [
                ("Trend",     score_detail["trend"] if score_direction > 0 else score_detail["trend_max"] - score_detail["trend"],               score_detail["trend_max"],     "#388bfd"),
                ("Momentum",  score_detail["momentum"] if score_direction > 0 else score_detail["momentum_max"] - score_detail["momentum"],       score_detail["momentum_max"],  "#d2a8ff"),
                ("Structure", score_detail["structure"] if score_direction > 0 else score_detail["structure_max"] - score_detail["structure"],     score_detail["structure_max"], "#f0883e"),
                ("MTF",       score_detail["mtf"] if score_direction > 0 else score_detail["mtf_max"] - score_detail["mtf"],                     score_detail["mtf_max"],       "#79c0ff"),
                ("Volume",    score_detail["volume"], score_detail["volume_max"], "#56d364"),
            ]
            for label_s, val, max_val, bar_color in score_rows:
                pct = int(val / max_val * 100)
                st.markdown(f"""
                <div style="margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
                        <span style="color:#8b949e; font-size:11px;">{label_s}</span>
                        <span style="color:#e6edf3; font-size:11px; font-weight:700;">{val}/{max_val}</span>
                    </div>
                    <div class="strength-bar-container">
                        <div class="strength-bar-fill" style="width:{pct}%; background:{bar_color};"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; padding:6px 0; border-top:1px solid #30363d; margin-top:4px;">
                <span style="color:#e6edf3; font-size:12px; font-weight:700;">TOTAL</span>
                <span style="color:{strength_color}; font-size:14px; font-weight:800;">{confidence}/100</span>
            </div>
            """, unsafe_allow_html=True)

            # Indicators & Values
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<p class="section-header">Indicators</p>', unsafe_allow_html=True)
            for ind_name, (ind_val, ind_color) in signals.items():
                badge_class = f"badge-{'green' if ind_color == 'green' else 'red' if ind_color == 'red' else 'neutral'}"
                st.markdown(f"""
                <span style="color:#8b949e; font-size:12px;">{ind_name}</span>
                <span class="badge {badge_class}">{ind_val}</span><br>
                """, unsafe_allow_html=True)

            if indicators:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<p class="section-header">Values</p>', unsafe_allow_html=True)
                for k, v in indicators.items():
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid #21262d;">
                        <span style="color:#8b949e; font-size:12px;">{k}</span>
                        <span style="color:#e6edf3; font-size:12px; font-weight:600;">{v}</span>
                    </div>
                    """, unsafe_allow_html=True)

            # Support & Resistance
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<p class="section-header">Support & Resistance</p>', unsafe_allow_html=True)
            for r in resistances:
                st.markdown(f'<div class="sr-level sr-resistance"><span style="color:#8b949e;">Resistance</span><span style="color:#f85149; font-weight:700;">${r:,.4f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="text-align:center; padding:4px; color:#e6edf3; font-size:12px; font-weight:700;">── Now: ${price:,.4f} ──</div>', unsafe_allow_html=True)
            for s in supports:
                st.markdown(f'<div class="sr-level sr-support"><span style="color:#8b949e;">Support</span><span style="color:#3fb950; font-weight:700;">${s:,.4f}</span></div>', unsafe_allow_html=True)

    # ── Trading Plan (di bawah chart, kiri) ──
    with trading_plan_container:
        st.markdown("---")
        st.markdown('<p class="section-header">📋 Trading Plan</p>', unsafe_allow_html=True)
        modal = st.number_input("💵 Modal (USDT)", min_value=1.0, value=10.0, step=5.0, format="%.2f")

        if df is not None and price_data is not None and decision == "ENTER":
            plan = generate_trading_plan(df, price_data, signal, supports, resistances, modal_usdt=modal, trading_mode=trading_mode)

            if plan:
                rr_target   = 0.7 if trading_mode == "Scalping" else 1.5
                rr_marginal = 0.6 if trading_mode == "Scalping" else 1.0
                rr_color    = "#3fb950" if plan["rr_ratio"] >= rr_target else "#f0883e" if plan["rr_ratio"] >= rr_marginal else "#f85149"

                # Label aksi: Futures pakai LONG/SHORT, Spot pakai BUY/SELL
                if market_type == "Futures":
                    action_label = "🟡 LONG (BUY)" if plan["signal"] == "BUY" else "🔴 SHORT (SELL)"
                    action_color = "#f0883e" if plan["signal"] == "BUY" else "#f85149"
                else:
                    action_label = f"🟢 {plan['signal']}" if plan["signal"] == "BUY" else f"🔴 {plan['signal']}"
                    action_color = "#3fb950" if plan["signal"] == "BUY" else "#f85149"

                # P&L dengan leverage
                lev_profit_tp1 = round(plan["profit_tp1"] * leverage, 2)
                lev_profit_tp2 = round(plan["profit_tp2"] * leverage, 2)
                lev_profit_tp3 = round(plan["profit_tp3"] * leverage, 2)
                lev_loss_sl    = round(plan["loss_sl"]    * leverage, 2)

                col_p1, col_p2, col_p3 = st.columns(3)
                with col_p1:
                    st.markdown(f"""
                    <div class="tp-card">
                        <p style="color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin:0 0 12px 0;">Entry & Exit</p>
                        <div class="tp-row"><span class="tp-label">Posisi</span><span class="tp-value" style="color:{action_color};">{action_label}</span></div>
                        <div class="tp-row"><span class="tp-label">Entry Price</span><span class="tp-value tp-yellow">${plan["entry"]:,.4f}</span></div>
                        <div class="tp-row"><span class="tp-label">Stop Loss</span><span class="tp-value tp-red">${plan["sl"]:,.4f} (-{plan["sl_pct"]}%)</span></div>
                        <div class="tp-row"><span class="tp-label">TP 1</span><span class="tp-value tp-green">${plan["tp1"]:,.4f} (+{plan["tp1_pct"]}%)</span></div>
                        <div class="tp-row"><span class="tp-label">TP 2</span><span class="tp-value tp-green">${plan["tp2"]:,.4f} (+{plan["tp2_pct"]}%)</span></div>
                        <div class="tp-row"><span class="tp-label">TP 3</span><span class="tp-value tp-green">${plan["tp3"]:,.4f} (+{plan["tp3_pct"]}%)</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_p2:
                    lev_label = f"{leverage}x" if market_type == "Futures" else "1x (Spot)"
                    st.markdown(f"""
                    <div class="tp-card">
                        <p style="color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin:0 0 12px 0;">Risk & Reward</p>
                        <div class="tp-row"><span class="tp-label">R/R Ratio</span><span class="tp-value" style="color:{rr_color};">1 : {plan["rr_ratio"]}</span></div>
                        <div class="tp-row"><span class="tp-label">ATR</span><span class="tp-value">${plan["atr"]:,.4f}</span></div>
                        <div class="tp-row"><span class="tp-label">Modal / Margin</span><span class="tp-value">${plan["modal"]:,.2f} USDT</span></div>
                        <div class="tp-row"><span class="tp-label">Leverage</span><span class="tp-value" style="color:#f0883e;">{lev_label}</span></div>
                        <div class="tp-row"><span class="tp-label">Qty</span><span class="tp-value">{plan["qty"]} {symbol.replace("USDT","")}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_p3:
                    pnl_note = f" (x{leverage})" if market_type == "Futures" else ""
                    st.markdown(f"""
                    <div class="tp-card">
                        <p style="color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin:0 0 12px 0;">Estimasi P&L{pnl_note}</p>
                        <div class="tp-row"><span class="tp-label">Profit TP1</span><span class="tp-value tp-green">+${lev_profit_tp1}</span></div>
                        <div class="tp-row"><span class="tp-label">Profit TP2</span><span class="tp-value tp-green">+${lev_profit_tp2}</span></div>
                        <div class="tp-row"><span class="tp-label">Profit TP3</span><span class="tp-value tp-green">+${lev_profit_tp3}</span></div>
                        <div class="tp-row"><span class="tp-label">Max Loss</span><span class="tp-value tp-red">-${lev_loss_sl}</span></div>
                        <div class="tp-row"><span class="tp-label">Worth it?</span><span class="tp-value" style="color:{rr_color};">{"✅ YES" if plan["rr_ratio"] >= rr_target else "⚠️ MARGINAL" if plan["rr_ratio"] >= rr_marginal else "❌ NO"}</span></div>
                    </div>
                    """, unsafe_allow_html=True)

                # Sim button
                cur_wallet_key  = "wallet_futures" if market_type == "Futures" else "wallet_spot"
                cur_wallet_bal  = st.session_state[cur_wallet_key]
                pos_type        = ("LONG" if plan["signal"] == "BUY" else "SHORT") if market_type == "Futures" else plan["signal"]
                btn_label       = f"🚀 Buka Posisi Simulasi ({pos_type}) — Alokasi ${modal:.0f} USDT"
                st.markdown("<br>", unsafe_allow_html=True)
                col_btn, col_bal = st.columns([2, 1])
                with col_btn:
                    if st.button(btn_label, use_container_width=True):
                        if cur_wallet_bal >= modal:
                            st.session_state[cur_wallet_key] -= modal
                            st.session_state["sim_history"].append({
                                "time":   datetime.now().strftime("%H:%M:%S"),
                                "market": market_type,
                                "type":   pos_type,
                                "entry":  plan["entry"],
                                "tp1":    plan["tp1"],
                                "sl":     plan["sl"],
                                "modal":  modal,
                                "lev":    leverage,
                            })
                            st.success(f"✅ Posisi simulasi {pos_type} dicatat! Sisa saldo {market_type}: ${st.session_state[cur_wallet_key]:.2f}")
                        else:
                            st.error(f"❌ Saldo simulasi {market_type} tidak cukup (${cur_wallet_bal:.2f} < ${modal:.0f})")
                with col_bal:
                    st.markdown(f"""
                    <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:10px; text-align:center; margin-top:4px;">
                        <p style="color:#8b949e; font-size:10px; margin:0 0 4px 0;">SALDO SIM {market_type.upper()}</p>
                        <p style="color:#3fb950; font-size:16px; font-weight:800; margin:0;">${cur_wallet_bal:.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown(f"""
                <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:12px; margin-top:8px;">
                    <p style="color:#8b949e; font-size:12px; margin:0;">
                    💡 <strong style="color:#e6edf3;">Cara pakai:</strong>
                    {"Buka posisi " + pos_type + " di" if market_type == "Futures" else "Entry di"} <strong style="color:#f0883e;">${plan["entry"]:,.4f}</strong> →
                    Pasang SL di <strong style="color:#f85149;">${plan["sl"]:,.4f}</strong> →
                    TP sebagian di <strong style="color:#3fb950;">${plan["tp1"]:,.4f}</strong>.
                    R/R <strong style="color:{rr_color};">1:{plan["rr_ratio"]}</strong>
                    {"| Leverage " + str(leverage) + "x → Efektif profit TP1: +$" + str(lev_profit_tp1) if market_type == "Futures" else ""}
                    {"— worth it! ✅" if plan["rr_ratio"] >= rr_target else "— pertimbangkan ⚠️" if plan["rr_ratio"] >= rr_marginal else "— skip ❌"}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("⏳ Sinyal HOLD — Trading plan tidak tersedia.")
        elif df is not None and price_data is not None:
            st.warning(f"Trading Plan dikunci — keputusan AI: {decision}. {decision_reason}")

    # ── AI Reasoning (di bawah signal, kanan) ──
    if df is not None and price_data is not None:
        with reasoning_container:
            reasoning_points, reasoning_conclusion, reasoning_color = generate_ai_reasoning(
                signal, decision, decision_reason, score_detail, indicators, supports, resistances, trading_mode
            )
            st.markdown("---")
            st.markdown('<p class="section-header">🧠 AI Reasoning</p>', unsafe_allow_html=True)
            points_html = "".join([
                f'<li style="color:#c9d1d9; font-size:13px; margin-bottom:6px; line-height:1.6;">{p}</li>'
                for p in reasoning_points
            ])
            st.markdown(f"""
            <div style="background:#161b22; border:1px solid #30363d; border-left:4px solid {reasoning_color}; border-radius:8px; padding:18px;">
                <ul style="margin:0 0 12px 0; padding-left:18px;">{points_html}</ul>
                <p style="color:{reasoning_color}; font-size:14px; font-weight:700; margin:0; padding-top:10px; border-top:1px solid #21262d;">
                    {reasoning_conclusion}
                </p>
            </div>
            """, unsafe_allow_html=True)

            # ── Gemini AI Insights (enhancement layer) ──
            if GEMINI_ENABLED and df is not None:
                st.markdown("---")
                st.markdown('<p class="section-header">✨ Gemini AI Insights</p>', unsafe_allow_html=True)
                gemini_data = get_gemini_insights(
                        symbol=symbol,
                        interval=interval_val,
                        trading_mode=trading_mode,
                        signal=signal,
                        decision=decision,
                        score_total=score_detail["total"],
                        rsi=indicators.get("RSI", 0),
                        macd_val=indicators.get("MACD", 0),
                        ema20=indicators.get("EMA20", 0),
                        ema50=indicators.get("EMA50", 0),
                        current_price=price,
                        supports_str=str(supports),
                        resistances_str=str(resistances),
                        mtf_context_str=f"MTF Score {mtf_real}/15",
                        GEMINI_API_KEY=GEMINI_API_KEY,
                        market_type=market_type,
                        leverage=leverage
                    )
                if gemini_data:
                    insights_html = "".join([
                        f'<li style="color:#c9d1d9; font-size:13px; margin-bottom:6px; line-height:1.6;">{p}</li>'
                        for p in gemini_data.get("insights", [])
                    ])
                    kesimpulan = gemini_data.get("kesimpulan", "")
                    st.markdown(f"""
                    <div class="gemini-card">
                        <ul style="margin:0 0 12px 0; padding-left:18px;">{insights_html}</ul>
                        {"<p style='color:#d2a8ff; font-size:14px; font-weight:700; margin:0; padding-top:10px; border-top:1px solid #0f3460;'>" + kesimpulan + "</p>" if kesimpulan else ""}
                    </div>
                    """, unsafe_allow_html=True)

# ─── TAB 2: MULTI TIMEFRAME ───
with tab2:
    st.markdown('<p class="section-header">🕐 Multi-Timeframe Analysis</p>', unsafe_allow_html=True)
    st.markdown(f"<p style='color:#8b949e; font-size:13px;'>Analisis {symbol} dari 3 timeframe sekaligus</p>", unsafe_allow_html=True)

    mtf_results = multi_timeframe_analysis(symbol, BINANCE_API_KEY, BINANCE_API_SECRET)

    buy_count  = sum(1 for _, s, _, _ in mtf_results if s == "BUY")
    sell_count = sum(1 for _, s, _, _ in mtf_results if s == "SELL")
    hold_count = sum(1 for _, s, _, _ in mtf_results if s == "HOLD")

    if buy_count >= 2:
        consensus_color = "#3fb950"; consensus_emoji = "🟢"
        consensus_text  = "STRONG BUY" if buy_count == 3 else "BUY"
    elif sell_count >= 2:
        consensus_color = "#f85149"; consensus_emoji = "🔴"
        consensus_text  = "STRONG SELL" if sell_count == 3 else "SELL"
    else:
        consensus_color = "#388bfd"; consensus_emoji = "🔵"
        consensus_text  = "MIXED / HOLD"

    st.markdown(f"""
    <div style="background:#161b22; border:1px solid #30363d; border-radius:12px; padding:24px; text-align:center; margin-bottom:24px;">
        <p style="color:#8b949e; font-size:12px; text-transform:uppercase; letter-spacing:2px; margin:0;">MTF Consensus</p>
        <p style="font-size:36px; font-weight:800; color:{consensus_color}; margin:8px 0;">{consensus_emoji} {consensus_text}</p>
        <p style="color:#8b949e; font-size:12px;">{buy_count} BUY · {sell_count} SELL · {hold_count} HOLD</p>
    </div>
    """, unsafe_allow_html=True)

    col_mtf1, col_mtf2, col_mtf3 = st.columns(3)
    cols = [col_mtf1, col_mtf2, col_mtf3]
    for i, (label, sig, reason_mtf, conf) in enumerate(mtf_results):
        color = "#3fb950" if sig == "BUY" else "#f85149" if sig == "SELL" else "#388bfd"
        emoji = "🟢" if sig == "BUY" else "🔴" if sig == "SELL" else "🔵"
        with cols[i]:
            st.markdown(f"""
            <div class="mtf-card mtf-{sig.lower()}">
                <p style="color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin:0;">{label}</p>
                <p style="font-size:22px; font-weight:800; color:{color}; margin:8px 0;">{emoji} {sig}</p>
                <div class="strength-bar-container">
                    <div class="strength-bar-fill" style="width:{conf}%; background:{color};"></div>
                </div>
                <p style="color:#8b949e; font-size:11px; margin:4px 0;">Confidence: {conf}%</p>
                <p style="color:#8b949e; font-size:11px; margin:0;">{reason_mtf}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:16px;">
        <p style="color:#8b949e; font-size:12px; margin:0;">
        💡 <strong style="color:#e6edf3;">Cara baca MTF:</strong> Kalau 1H + 4H + 1D semua BUY → sinyal sangat kuat.
        Kalau 1H BUY tapi 4H/1D SELL → hati-hati, bisa false signal.
        Konfirmasi minimal 2 dari 3 timeframe sebelum entry.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ─── TAB 3: TOP GAINERS ───
with tab3:
    st.markdown('<p class="section-header">🔥 Top 10 Gainers Today</p>', unsafe_allow_html=True)
    gainers = get_top_gainers(BINANCE_API_KEY, BINANCE_API_SECRET, n=10)
    if gainers:
        col_g1, col_g2 = st.columns(2)
        for i, g in enumerate(gainers):
            sym  = g["symbol"]
            pct  = float(g["priceChangePercent"])
            pr   = float(g["lastPrice"])
            vol  = float(g["quoteVolume"]) / 1_000_000
            color = "#3fb950" if pct >= 0 else "#f85149"
            card  = f"""
            <div class="gainer-row">
                <div>
                    <span style="color:#e6edf3; font-weight:700; font-size:14px;">{sym}</span>
                    <span style="color:#8b949e; font-size:11px; margin-left:8px;">Vol ${vol:.1f}M</span>
                </div>
                <div style="text-align:right;">
                    <span style="color:#e6edf3; font-size:13px;">${pr:,.4f}</span><br>
                    <span style="color:{color}; font-size:13px; font-weight:700;">{'▲' if pct >= 0 else '▼'} {abs(pct):.2f}%</span>
                </div>
            </div>
            """
            if i % 2 == 0:
                with col_g1: st.markdown(card, unsafe_allow_html=True)
            else:
                with col_g2: st.markdown(card, unsafe_allow_html=True)
    else:
        st.info("Gagal load data gainers. Cek koneksi API.")

# ─── TAB 4: BACKTESTING ───
with tab4:
    st.markdown('<p class="section-header">🧪 Backtesting Engine</p>', unsafe_allow_html=True)
    st.markdown("<p style='color:#8b949e; font-size:13px;'>Simulasi signal engine di data historis — lihat win rate, profit/loss, dan RR ratio.</p>", unsafe_allow_html=True)

    col_bt1, col_bt2, col_bt3 = st.columns(3)
    with col_bt1: bt_symbol = st.text_input("Symbol", value=symbol)
    with col_bt2:
        bt_interval = st.selectbox("Backtest Timeframe", [
            ("1 Hour", "1h"), ("4 Hours", "4h"), ("1 Day", "1d")
        ], format_func=lambda x: x[0], index=0)
        bt_interval_val = bt_interval[1]
    with col_bt3:
        bt_candles = st.slider("Candles (data historis)", 100, 1000, 500)

    bt_modal = st.number_input("💵 Modal per Trade (USDT)", min_value=1.0, value=10.0, step=5.0)

    if st.button("▶️ Jalankan Backtest", use_container_width=True):
        df_bt = get_klines(bt_symbol, bt_interval_val, bt_candles, BINANCE_API_KEY, BINANCE_API_SECRET, market_type="Spot")

        if df_bt is None or len(df_bt) < 100:
            st.error("Data tidak cukup untuk backtest. Coba tambah jumlah candles.")
        else:
            trades     = []
            min_window = 50

            for i in range(min_window, len(df_bt) - 1):
                df_slice = df_bt.iloc[:i+1].copy()
                signal_bt, _, _, _, confidence_bt, score_bt = calculate_signal(df_slice)
                if signal_bt == "HOLD": continue
                if score_bt["total"] < 55: continue

                entry_price = df_bt["close"].iloc[i]
                atr_bt = ta.volatility.AverageTrueRange(
                    df_slice["high"], df_slice["low"], df_slice["close"], window=14
                ).average_true_range().iloc[-1]

                if signal_bt == "BUY":
                    sl_bt  = entry_price - (atr_bt * 1.5)
                    tp1_bt = entry_price + (atr_bt * 2.0)
                else:
                    sl_bt  = entry_price + (atr_bt * 1.5)
                    tp1_bt = entry_price - (atr_bt * 2.0)

                outcome = "OPEN"; exit_price = None; exit_candle = None
                lookahead = min(10, len(df_bt) - i - 1)

                for j in range(1, lookahead + 1):
                    future_high = df_bt["high"].iloc[i + j]
                    future_low  = df_bt["low"].iloc[i + j]
                    if signal_bt == "BUY":
                        if future_low <= sl_bt:  outcome = "LOSS"; exit_price = sl_bt;  exit_candle = j; break
                        elif future_high >= tp1_bt: outcome = "WIN";  exit_price = tp1_bt; exit_candle = j; break
                    else:
                        if future_high >= sl_bt: outcome = "LOSS"; exit_price = sl_bt;  exit_candle = j; break
                        elif future_low <= tp1_bt:  outcome = "WIN";  exit_price = tp1_bt; exit_candle = j; break

                if outcome == "OPEN": continue

                qty = bt_modal / entry_price
                pnl = (exit_price - entry_price) * qty if signal_bt == "BUY" else (entry_price - exit_price) * qty
                sl_dist  = abs(entry_price - sl_bt)
                tp_dist  = abs(tp1_bt - entry_price)
                rr_actual = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 0

                trades.append({
                    "candle":      i,
                    "timestamp":   df_bt["timestamp"].iloc[i].strftime("%Y-%m-%d %H:%M") if hasattr(df_bt["timestamp"].iloc[i], "strftime") else str(df_bt["timestamp"].iloc[i]),
                    "signal":      signal_bt,
                    "entry":       round(entry_price, 4),
                    "exit":        round(exit_price, 4),
                    "outcome":     outcome,
                    "pnl":         round(pnl, 2),
                    "rr":          rr_actual,
                    "score":       score_bt["total"],
                    "exit_candle": exit_candle,
                })

            if not trades:
                st.warning("Tidak ada trade yang tereksekusi. Coba kurangi threshold score atau tambah candles.")
            else:
                total_trades = len(trades)
                wins         = [t for t in trades if t["outcome"] == "WIN"]
                losses       = [t for t in trades if t["outcome"] == "LOSS"]
                win_rate     = round(len(wins) / total_trades * 100, 1)
                total_pnl    = round(sum(t["pnl"] for t in trades), 2)
                avg_win      = round(sum(t["pnl"] for t in wins) / len(wins), 2) if wins else 0
                avg_loss     = round(sum(t["pnl"] for t in losses) / len(losses), 2) if losses else 0
                avg_rr       = round(sum(t["rr"] for t in trades) / total_trades, 2)
                avg_score    = round(sum(t["score"] for t in trades) / total_trades, 1)

                pnl_color = "#3fb950" if total_pnl >= 0 else "#f85149"
                wr_color  = "#3fb950" if win_rate >= 55 else "#f0883e" if win_rate >= 45 else "#f85149"

                st.markdown("<br>", unsafe_allow_html=True)
                c1, c2, c3, c4, c5 = st.columns(5)
                for col, label, val, color in [
                    (c1, "Total Trade", str(total_trades),                                                    "#e6edf3"),
                    (c2, "Win Rate",    f"{win_rate}%",                                                       wr_color),
                    (c3, "Total P&L",   f"{'+'if total_pnl>=0 else ''}{total_pnl} USDT",                     pnl_color),
                    (c4, "Avg RR",      f"1:{avg_rr}",                                                        "#388bfd"),
                    (c5, "Avg Score",   f"{avg_score}/100",                                                   "#d2a8ff"),
                ]:
                    with col:
                        st.markdown(f"""
                        <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:14px; text-align:center;">
                            <p style="color:#8b949e; font-size:11px; margin:0 0 6px 0; text-transform:uppercase;">{label}</p>
                            <p style="color:{color}; font-size:22px; font-weight:800; margin:0;">{val}</p>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                col_wl1, col_wl2 = st.columns(2)
                with col_wl1:
                    st.markdown(f"""
                    <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:14px;">
                        <p style="color:#8b949e; font-size:11px; text-transform:uppercase; margin:0 0 10px 0;">Win Summary</p>
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Total Win</span><span style="color:#3fb950; font-weight:700;">{len(wins)} trade</span></div>
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Avg Profit</span><span style="color:#3fb950; font-weight:700;">+{avg_win} USDT</span></div>
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Total Profit</span><span style="color:#3fb950; font-weight:700;">+{round(sum(t["pnl"] for t in wins),2)} USDT</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_wl2:
                    st.markdown(f"""
                    <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:14px;">
                        <p style="color:#8b949e; font-size:11px; text-transform:uppercase; margin:0 0 10px 0;">Loss Summary</p>
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Total Loss</span><span style="color:#f85149; font-weight:700;">{len(losses)} trade</span></div>
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Avg Loss</span><span style="color:#f85149; font-weight:700;">{avg_loss} USDT</span></div>
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Total Loss</span><span style="color:#f85149; font-weight:700;">{round(sum(t["pnl"] for t in losses),2)} USDT</span></div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<p class="section-header">Trade History</p>', unsafe_allow_html=True)
                for t in reversed(trades[-30:]):
                    outcome_color = "#3fb950" if t["outcome"] == "WIN" else "#f85149"
                    signal_color  = "#3fb950" if t["signal"] == "BUY" else "#f85149"
                    pnl_sign      = "+" if t["pnl"] >= 0 else ""
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center;
                         padding:8px 12px; margin:3px 0; background:#161b22;
                         border:1px solid #30363d; border-radius:6px; font-size:12px;">
                        <span style="color:#8b949e; width:130px;">{t["timestamp"]}</span>
                        <span style="color:{signal_color}; font-weight:700; width:45px;">{t["signal"]}</span>
                        <span style="color:#e6edf3; width:90px;">Entry: ${t["entry"]}</span>
                        <span style="color:#e6edf3; width:90px;">Exit: ${t["exit"]}</span>
                        <span style="color:#8b949e; width:60px;">RR 1:{t["rr"]}</span>
                        <span style="color:#8b949e; width:70px;">Score: {t["score"]}</span>
                        <span style="color:{outcome_color}; font-weight:700; width:55px;">{t["outcome"]}</span>
                        <span style="color:{outcome_color}; font-weight:700;">{pnl_sign}{t["pnl"]} USDT</span>
                    </div>
                    """, unsafe_allow_html=True)

# ─── TAB 5: SETTINGS ───
with tab5:
    st.markdown('<p class="section-header">⚙️ Settings & Simulasi Wallet</p>', unsafe_allow_html=True)

    # Sim history log
    st.markdown("**📜 Log Simulasi Posisi**")
    if not st.session_state["sim_history"]:
        st.caption("Belum ada posisi simulasi yang dicatat.")
    else:
        for log in reversed(st.session_state["sim_history"][-20:]):
            pos_color = "#f0883e" if log["type"] in ("LONG","BUY") else "#f85149"
            mkt_badge = "🟡 Futures" if log["market"] == "Futures" else "🔵 Spot"
            lev_str = f" | {log['lev']}x" if log.get("lev", 1) > 1 else ""
            st.markdown(f"""
            <div style="padding:8px 12px; margin:3px 0; background:#161b22; border:1px solid #30363d;
                 border-left:3px solid {pos_color}; border-radius:6px; font-size:12px;">
                <span style="color:#8b949e;">{log["time"]}</span>
                <span style="color:#e6edf3; margin:0 8px;">{mkt_badge}{lev_str}</span>
                <span style="color:{pos_color}; font-weight:700;">{log["type"]}</span>
                <span style="color:#8b949e; margin-left:8px;">Entry: ${log.get("entry", "-")} | TP1: ${log.get("tp1", "-")} | SL: ${log.get("sl", "-")} | Modal: ${log.get("modal", "-")}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**💰 Manajemen Saldo Simulasi**")
    col_ws, col_wf = st.columns(2)
    with col_ws:
        st.metric("Saldo Spot", f"${st.session_state['wallet_spot']:.2f} USDT")
    with col_wf:
        st.metric("Saldo Futures", f"${st.session_state['wallet_futures']:.2f} USDT")
    if st.button("🔄 Reset Saldo ($50 Spot + $50 Futures)", use_container_width=True):
        st.session_state["wallet_spot"] = 50.0
        st.session_state["wallet_futures"] = 50.0
        st.session_state["sim_history"] = []
        st.rerun()

    st.markdown("---")
    st.markdown("**🔄 Auto Refresh**")
    auto_refresh = st.checkbox("Auto Refresh setiap 30 detik", value=st.session_state["auto_refresh"])
    st.session_state["auto_refresh"] = auto_refresh
    if auto_refresh:
        st.success("✅ Auto refresh aktif — data update tiap 30 detik")
    else:
        st.info("ℹ️ Auto refresh nonaktif")

    st.markdown("---")
    st.markdown("**ℹ️ App Info**")
    gemini_status = "🟢 Aktif" if GEMINI_ENABLED else "🔴 Tidak aktif (tambahkan GEMINI_API_KEY di secrets)"
    st.markdown(f"""
    <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:16px;">
        <p style="color:#8b949e; font-size:12px; margin:0;">
        Version: <span style="color:#e6edf3;">v3.5 (Fase 3 — Spot + Futures Dual Market)</span><br>
        Exchange: <span style="color:#e6edf3;">Binance Spot & Futures (USDS-M)</span><br>
        Features: <span style="color:#e6edf3;">Dual Mode · Futures LONG/SHORT · Leverage Calc · Real MTF · S&R · Stochastic · EMA200 · Trading Plan · Backtest · Top Gainers</span><br>
        Gemini AI: <span style="color:#e6edf3;">{gemini_status}</span><br>
        Status: <span style="color:#3fb950;">🟢 Running</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  AUTO REFRESH
# ─────────────────────────────────────────────
if st.session_state.get("auto_refresh"):
    time.sleep(30)
    st.rerun()
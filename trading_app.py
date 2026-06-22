import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from binance.client import Client
from binance.exceptions import BinanceAPIException
import ta
import time
from datetime import datetime

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
    /* Base dark theme */
    .stApp { background-color: #0d1117; color: #e6edf3; }
    .stSidebar { background-color: #161b22; border-right: 1px solid #30363d; }
    .stSidebar .stSelectbox label,
    .stSidebar .stRadio label,
    .stSidebar p { color: #8b949e !important; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
    }
    [data-testid="metric-container"] label { color: #8b949e !important; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #e6edf3; font-size: 24px; font-weight: 700; }
    [data-testid="metric-container"] [data-testid="stMetricDelta"] { font-size: 13px; }

    /* Signal box */
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

    /* Indicator badges */
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

    /* Section headers */
    .section-header {
        color: #8b949e;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 2px;
        border-bottom: 1px solid #30363d;
        padding-bottom: 8px;
        margin-bottom: 16px;
    }

    /* Gainers table */
    .gainer-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 12px;
        border-radius: 6px;
        margin: 4px 0;
        background: #161b22;
        border: 1px solid #30363d;
    }

    /* Hide streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* Plotly chart background */
    .js-plotly-plot { border-radius: 8px; }

    /* MTF Cards */
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

    /* Strength bar */
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

    /* Support Resistance */
    .sr-level { display: flex; justify-content: space-between; padding: 6px 10px; border-radius: 6px; margin: 3px 0; font-size: 12px; }
    .sr-resistance { background: #2d1b1b; border-left: 3px solid #f85149; }
    .sr-support { background: #0d2b1d; border-left: 3px solid #3fb950; }

    /* Trading Plan */
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
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  LOAD API CREDENTIALS FROM ENVIRONMENT
# ─────────────────────────────────────────────
try:
    BINANCE_API_KEY = st.secrets["BINANCE_API_KEY"]
    BINANCE_API_SECRET = st.secrets["BINANCE_API_SECRET"]
except Exception as e:
    st.error(f"Secrets error: {e}")
    st.stop()

# Validate credentials
if not BINANCE_API_KEY or not BINANCE_API_SECRET:
    st.error("❌ Binance API credentials not found!")
    st.info("""
    Please setup your `.env` file with:
    ```
    BINANCE_API_KEY=your_key_here
    BINANCE_API_SECRET=your_secret_here
    ```
    """)
    st.stop()

# ─────────────────────────────────────────────
#  BINANCE CLIENT
# ─────────────────────────────────────────────
@st.cache_resource
def get_client(BINANCE_API_KEY, BINANCE_API_SECRET):
    return Client(BINANCE_API_KEY, BINANCE_API_SECRET)

# ─────────────────────────────────────────────
#  DATA FUNCTIONS
# ─────────────────────────────────────────────
@st.cache_data(ttl=30)
def get_price(symbol, BINANCE_API_KEY, BINANCE_API_SECRET):
    try:
        client = get_client(BINANCE_API_KEY, BINANCE_API_SECRET)
        ticker = client.get_ticker(symbol=symbol)

        return {
            "price": float(ticker["lastPrice"]),
            "change": float(ticker["priceChangePercent"]),
            "high": float(ticker["highPrice"]),
            "low": float(ticker["lowPrice"]),
            "volume": float(ticker["volume"]),
            "quoteVolume": float(ticker["quoteVolume"]),
        }
    except Exception as e:
        st.error(f"BINANCE ERROR: {type(e).__name__}")
        st.error(str(e))
        raise

@st.cache_data(ttl=60)
def get_klines(symbol, interval, limit, BINANCE_API_KEY, BINANCE_API_SECRET):
    try:
        client = get_client(BINANCE_API_KEY, BINANCE_API_SECRET)
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
#  AI SIGNAL ENGINE v2 — SCORING ENGINE
#  Bobot: Trend=35, Momentum=25, Structure=20,
#         MTF=15, Volume=5  → Total=100
# ─────────────────────────────────────────────
def calculate_signal(df, mtf_score_override=None):
    """
    Returns:
        signal       : "BUY" | "SELL" | "HOLD"
        reason       : string deskripsi
        signals      : dict badge indikator (kompatibel UI lama)
        indicators   : dict nilai mentah indikator
        confidence   : int 0-100 (pengganti strength)
        score_detail : dict breakdown per kategori
    """
    if df is None or len(df) < 50:
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

    # ── Hitung semua indikator ──────────────────
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
    bb_mid     = bb.bollinger_mavg().iloc[-1]
    bb_pos     = (current_price - bb_lower) / max(bb_upper - bb_lower, 0.0001) * 100

    avg_vol    = volume.rolling(20).mean().iloc[-1]
    curr_vol   = volume.iloc[-1]
    vol_ratio  = curr_vol / max(avg_vol, 0.0001)

    # Support & Resistance sederhana untuk Structure
    highs = high.rolling(10).max()
    lows  = low.rolling(10).min()
    nearest_resistance = highs.iloc[-1]
    nearest_support    = lows.iloc[-1]
    dist_to_resistance = (nearest_resistance - current_price) / max(current_price, 0.0001) * 100
    dist_to_support    = (current_price - nearest_support)    / max(current_price, 0.0001) * 100

    # ── 1. TREND SCORE (0-35) ──────────────────
    trend_score = 0
    trend_bias  = 0  # +1 bullish, -1 bearish

    # EMA alignment (max 20)
    if ema20_val > ema50_val > ema200_val:
        trend_score += 20
        trend_bias  += 1
    elif ema20_val < ema50_val < ema200_val:
        trend_score += 0
        trend_bias  -= 1
    elif ema20_val > ema50_val:
        trend_score += 12
        trend_bias  += 1
    elif ema20_val < ema50_val:
        trend_score += 5
        trend_bias  -= 1
    else:
        trend_score += 8

    # Price vs EMA50 (max 10)
    if current_price > ema50_val:
        trend_score += 10
        trend_bias  += 1
    elif current_price < ema50_val:
        trend_score += 0
        trend_bias  -= 1
    else:
        trend_score += 5

    # Price vs EMA200 (max 5)
    if current_price > ema200_val:
        trend_score += 5
        trend_bias  += 1
    else:
        trend_score += 0
        trend_bias  -= 1

    trend_score = min(trend_score, 35)

    # ── 2. MOMENTUM SCORE (0-25) ───────────────
    momentum_score = 0
    momentum_bias  = 0

    # RSI (max 10)
    if rsi < 30:
        momentum_score += 10; momentum_bias += 1   # oversold → reversal buy
    elif rsi < 45:
        momentum_score += 8;  momentum_bias += 1   # bullish momentum
    elif rsi > 70:
        momentum_score += 0;  momentum_bias -= 1   # overbought → reversal sell
    elif rsi > 55:
        momentum_score += 3;  momentum_bias -= 1   # bearish momentum
    else:
        momentum_score += 5                        # neutral

    # MACD (max 10)
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

    # Stochastic (max 5)
    if stoch_k < 20 and stoch_k > stoch_d:
        momentum_score += 5;  momentum_bias += 1   # oversold cross
    elif stoch_k > 80 and stoch_k < stoch_d:
        momentum_score += 0;  momentum_bias -= 1   # overbought cross
    elif stoch_k < 40:
        momentum_score += 3;  momentum_bias += 1
    elif stoch_k > 60:
        momentum_score += 1;  momentum_bias -= 1
    else:
        momentum_score += 2

    momentum_score = min(momentum_score, 25)

    # ── 3. STRUCTURE SCORE (0-20) ──────────────
    structure_score = 0
    structure_bias  = 0

    # Posisi BB (max 10)
    if bb_pos < 20:
        structure_score += 10; structure_bias += 1  # dekat lower band → buy zone
    elif bb_pos > 80:
        structure_score += 0;  structure_bias -= 1  # dekat upper band → sell zone
    elif bb_pos < 40:
        structure_score += 7;  structure_bias += 1
    elif bb_pos > 60:
        structure_score += 3;  structure_bias -= 1
    else:
        structure_score += 5                        # mid BB

    # Jarak ke Support vs Resistance (max 10)
    if dist_to_support < dist_to_resistance:
        structure_score += 8; structure_bias += 1
    elif dist_to_resistance < dist_to_support:
        structure_score += 2; structure_bias -= 1
    else:
        structure_score += 5

    structure_score = min(structure_score, 20)

    # ── 4. MTF SCORE (0-15) ────────────────────
    if mtf_score_override is not None:
        mtf_score = max(0, min(mtf_score_override, 15))
    else:
        ema20_series = ema20.dropna()
        if len(ema20_series) >= 10:
            slope_short = ema20_series.iloc[-1] - ema20_series.iloc[-5]
            slope_long  = ema20_series.iloc[-1] - ema20_series.iloc[-10]
            if slope_short > 0 and slope_long > 0:
                mtf_score = 12
            elif slope_short > 0 or slope_long > 0:
                mtf_score = 8
            elif slope_short < 0 and slope_long < 0:
                mtf_score = 3
            else:
                mtf_score = 6
        else:
            mtf_score = 7

    # ── 5. VOLUME SCORE (0-5) ──────────────────
    volume_score = 0
    if vol_ratio >= 2.0:
        volume_score = 5
    elif vol_ratio >= 1.5:
        volume_score = 4
    elif vol_ratio >= 1.0:
        volume_score = 3
    elif vol_ratio >= 0.7:
        volume_score = 2
    else:
        volume_score = 1

    # ── TOTAL SCORE ────────────────────────────
    total_score = trend_score + momentum_score + structure_score + mtf_score + volume_score

    # ── BIAS FINAL ─────────────────────────────
    weighted_bias = (trend_bias * 35) + (momentum_bias * 25) + (structure_bias * 20)

    # ── SIGNAL DECISION ────────────────────────
    if weighted_bias > 0 and total_score >= 60:
        signal = "BUY"
    elif weighted_bias < 0 and total_score <= 45:
        signal = "SELL"
    elif weighted_bias > 0 and total_score >= 50:
        signal = "BUY"
    elif weighted_bias < 0 and total_score <= 50:
        signal = "SELL"
    else:
        signal = "HOLD"

    if signal == "BUY":
        confidence = total_score
    elif signal == "SELL":
        confidence = (
            (35 - trend_score) + (25 - momentum_score) +
            (20 - structure_score) + (15 - mtf_score) + volume_score
        )
    else:
        confidence = 50

    if signal == "HOLD":
        reason = "Market Bias: NETRAL — tunggu arah yang lebih jelas"
    else:
        strength = "STRONG" if confidence >= 75 else "MODERATE" if confidence >= 60 else "WEAK"
        reason = f"Market Bias: {signal} — {strength} ({confidence}/100)"

    # ── BADGES ─────────────────────────────────
    signals = {}

    # RSI badge
    if rsi < 30:
        signals["RSI"] = ("OVERSOLD", "green")
    elif rsi < 45:
        signals["RSI"] = ("BULLISH", "green")
    elif rsi > 70:
        signals["RSI"] = ("OVERBOUGHT", "red")
    elif rsi > 55:
        signals["RSI"] = ("BEARISH", "red")
    else:
        signals["RSI"] = ("NEUTRAL", "neutral")

    # MACD badge
    if macd_val > macd_sig and macd_hist > 0:
        signals["MACD"] = ("BULLISH CROSS", "green")
    elif macd_val < macd_sig and macd_hist < 0:
        signals["MACD"] = ("BEARISH CROSS", "red")
    else:
        signals["MACD"] = ("NEUTRAL", "neutral")

    # EMA badge
    if ema20_val > ema50_val > ema200_val:
        signals["EMA"] = ("STRONG UPTREND", "green")
    elif ema20_val < ema50_val < ema200_val:
        signals["EMA"] = ("STRONG DOWNTREND", "red")
    elif ema20_val > ema50_val:
        signals["EMA"] = ("UPTREND", "green")
    else:
        signals["EMA"] = ("DOWNTREND", "red")

    # Stoch badge
    if stoch_k < 20 and stoch_k > stoch_d:
        signals["STOCH"] = ("OVERSOLD CROSS", "green")
    elif stoch_k > 80 and stoch_k < stoch_d:
        signals["STOCH"] = ("OVERBOUGHT CROSS", "red")
    else:
        signals["STOCH"] = ("NEUTRAL", "neutral")

    # BB badge
    if bb_pos < 20:
        signals["BB"] = ("BELOW LOWER", "green")
    elif bb_pos > 80:
        signals["BB"] = ("ABOVE UPPER", "red")
    else:
        signals["BB"] = ("WITHIN BAND", "neutral")

    # Volume badge
    if vol_ratio >= 1.5:
        signals["VOL"] = ("SURGE ⚡", "green")
    else:
        signals["VOL"] = ("NORMAL", "neutral")

    # ── RAW VALUES ─────────────────────────────
    indicators = {
        "RSI": round(rsi, 2),
        "MACD": round(macd_val, 6),
        "Stoch %K": round(stoch_k, 2),
        "BB_pos": round(bb_pos, 1),
        "EMA20": round(ema20_val, 4),
        "EMA50": round(ema50_val, 4),
        "EMA200": round(ema200_val, 4),
    }

    # ── SCORE BREAKDOWN ────────────────────────
    score_detail = {
        "trend":          trend_score,
        "trend_max":      35,
        "momentum":       momentum_score,
        "momentum_max":   25,
        "structure":      structure_score,
        "structure_max":  20,
        "mtf":            mtf_score,
        "mtf_max":        15,
        "volume":         volume_score,
        "volume_max":     5,
        "total":          total_score,
        "confidence":     confidence,
        "bias":           signal,
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

    # ── ATR & RR check ─────────────────────────
    try:
        atr = ta.volatility.AverageTrueRange(
            df["high"], df["low"], df["close"], window=14
        ).average_true_range().iloc[-1]
        current_price = df["close"].iloc[-1]

        if signal == "BUY":
            sl_price  = current_price - (atr * sl_mult)
            tp1_price = current_price + (atr * tp_mult)
        else:
            sl_price  = current_price + (atr * sl_mult)
            tp1_price = current_price - (atr * tp_mult)

        sl_dist  = abs(current_price - sl_price)
        tp_dist  = abs(tp1_price - current_price)
        rr_ratio = tp_dist / sl_dist if sl_dist > 0 else 0
    except Exception:
        rr_ratio = 0

    # ── Structure S/R Check ───────────────────
    structure_ok = False
    if signal == "BUY" and supports:
        dist_pct = abs(current_price - supports[0]) / current_price * 100
        structure_ok = dist_pct <= 1.5
    elif signal == "SELL" and resistances:
        dist_pct = abs(resistances[0] - current_price) / current_price * 100
        structure_ok = dist_pct <= 1.5
    else:
        structure_ok = structure >= 12

    # ── Decision Logic ─────────────────────────
    reasons_wait = []

    min_score = 52 if is_scalping else 50
    min_rr = 0.70 if is_scalping else 1.0
    trend_min = 10 if is_scalping else 15
    momentum_min = 8 if is_scalping else 12
    mtf_min = 4 if is_scalping else 6

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
    enter_rr = 0.70 if is_scalping else 1.5

    if not reasons_wait and total >= enter_score and rr_ratio >= enter_rr:
        mode_note = "Scalp aktif" if is_scalping else "Setup solid"
        return "ENTER", f"{mode_note} — Score {total}/100, RR 1:{rr_ratio:.2f}", "#3fb950"

    if reasons_wait:
        note = ", ".join(reasons_wait[:2])
        return "WAIT", f"Tunggu: {note}", "#f0883e"

    return "ENTER", f"Setup cukup — Score {total}/100, RR 1:{rr_ratio:.1f}", "#3fb950"

# ─────────────────────────────────────────────
#  REAL MTF SCORE ENGINE
# ─────────────────────────────────────────────
def calculate_mtf_score(symbol, current_tf, BINANCE_API_KEY, BINANCE_API_SECRET, trading_mode="Ketat"):
    """
    Hitung MTF score berdasarkan EMA trend alignment di 3 timeframe.
    current_tf dikecualikan dari scoring supaya tidak double-count.
    """
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

        close_tf = df_tf["close"]
        ema20_tf = ta.trend.EMAIndicator(close_tf, window=20).ema_indicator().iloc[-1]
        ema50_tf = ta.trend.EMAIndicator(close_tf, window=50).ema_indicator().iloc[-1]
        ema200_tf = ta.trend.EMAIndicator(close_tf, window=200).ema_indicator().iloc[-1] \
                    if len(close_tf) >= 200 else ema50_tf
        price_tf = close_tf.iloc[-1]

        if ema20_tf > ema50_tf > ema200_tf and price_tf > ema50_tf:
            tf_score = 1.0
        elif ema20_tf < ema50_tf < ema200_tf and price_tf < ema50_tf:
            tf_score = 0.0
        elif ema20_tf > ema50_tf and price_tf > ema50_tf:
            tf_score = 0.75
        elif ema20_tf < ema50_tf and price_tf < ema50_tf:
            tf_score = 0.25
        else:
            tf_score = 0.5

        total_score  += tf_score * weight
        total_weight += weight

    if total_weight == 0:
        return 7

    normalized = (total_score / total_weight) * 15
    return round(normalized)

def multi_timeframe_analysis(symbol, BINANCE_API_KEY, BINANCE_API_SECRET):
    timeframes = [("1H", "1h", 100), ("4H", "4h", 100), ("1D", "1d", 200)]
    results = []
    for label, interval, limit in timeframes:
        df = get_klines(symbol, interval, limit, BINANCE_API_KEY, BINANCE_API_SECRET)
        signal, reason, _, _, confidence, score_detail = calculate_signal(df)
        results.append((label, signal, reason, confidence))
    return results

# ─────────────────────────────────────────────
#  SUPPORT & RESISTANCE
# ─────────────────────────────────────────────
def get_support_resistance(df, n=3):
    if df is None or len(df) < 20:
        return [], []
    highs = df["high"].rolling(5, center=True).max()
    lows = df["low"].rolling(5, center=True).min()
    resistance_levels = []
    support_levels = []
    current_price = df["close"].iloc[-1]
    for i in range(len(df)):
        if df["high"].iloc[i] == highs.iloc[i]:
            resistance_levels.append(df["high"].iloc[i])
        if df["low"].iloc[i] == lows.iloc[i]:
            support_levels.append(df["low"].iloc[i])
    resistance_levels = sorted(set([round(r, 4) for r in resistance_levels if r > current_price]))[:n]
    support_levels = sorted(set([round(s, 4) for s in support_levels if s < current_price]), reverse=True)[:n]
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
        min_tp_pct, tp_step_pct, min_sl_pct = 0.0005, 0.0005, 0.0015
    else:
        sl_mult, tp1_mult, tp2_mult, tp3_mult = 1.5, 2.0, 3.5, 5.0
        min_tp_pct, tp_step_pct, min_sl_pct = 0.001, 0.002, 0.005

    if signal == "BUY":
        entry = round(current_price, 4)
        sl_atr  = round(entry - (atr * sl_mult), 4)
        sl_sr   = round(supports[0] * 0.998, 4) if supports else sl_atr
        sl      = sl_atr if trading_mode == "Scalping" else min(sl_atr, sl_sr)
        tp1_atr = round(entry + (atr * tp1_mult), 4)
        tp2_atr = round(entry + (atr * tp2_mult), 4)
        tp3_atr = round(entry + (atr * tp3_mult), 4)
        if resistances:
            r1 = round(resistances[0] * 0.999, 4)
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
        entry = round(current_price, 4)
        sl_atr  = round(entry + (atr * sl_mult), 4)
        sl_sr   = round(resistances[0] * 1.002, 4) if resistances else sl_atr
        sl      = sl_atr if trading_mode == "Scalping" else max(sl_atr, sl_sr)
        tp1_atr = round(entry - (atr * tp1_mult), 4)
        tp2_atr = round(entry - (atr * tp2_mult), 4)
        tp3_atr = round(entry - (atr * tp3_mult), 4)
        if supports:
            s1 = round(supports[0] * 1.001, 4)
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

    sl_pct = abs((sl - entry) / entry * 100)
    tp1_pct = abs((tp1 - entry) / entry * 100)
    tp2_pct = abs((tp2 - entry) / entry * 100)
    tp3_pct = abs((tp3 - entry) / entry * 100)
    rr_ratio = round(tp1_pct / sl_pct, 2) if sl_pct > 0 else 0
    
    qty = round(modal_usdt / entry, 6)
    
    if signal == "BUY":
        profit_tp1 = round((tp1 - entry) * qty, 2)
        profit_tp2 = round((tp2 - entry) * qty, 2)
        profit_tp3 = round((tp3 - entry) * qty, 2)
    else:
        profit_tp1 = round((entry - tp1) * qty, 2)
        profit_tp2 = round((entry - tp2) * qty, 2)
        profit_tp3 = round((entry - tp3) * qty, 2)
        
    loss_sl = round(abs((sl - entry) * qty), 2)
    
    return {
        "signal": signal,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "sl_pct": round(sl_pct, 2),
        "tp1_pct": round(tp1_pct, 2),
        "tp2_pct": round(tp2_pct, 2),
        "tp3_pct": round(tp3_pct, 2),
        "rr_ratio": rr_ratio,
        "qty": qty,
        "modal": modal_usdt,
        "profit_tp1": profit_tp1,
        "profit_tp2": profit_tp2,
        "profit_tp3": profit_tp3,
        "loss_sl": loss_sl,
        "atr": round(atr, 4),
    }

# ─────────────────────────────────────────────
#  AI REASONING ENGINE
# ─────────────────────────────────────────────
def generate_ai_reasoning(signal, decision, decision_reason, score_detail, indicators, supports, resistances, trading_mode="Ketat"):
    if signal == "HOLD":
        points = [
            "Tidak ada bias arah yang cukup jelas dari kombinasi Trend, Momentum, dan Structure saat ini.",
            "Total score belum cukup tinggi maupun cukup rendah untuk memicu sinyal BUY atau SELL."
        ]
        conclusion = "Kesimpulan: Market belum menunjukkan arah yang jelas. Lebih baik tunggu konfirmasi candle berikutnya."
        return points, conclusion, "#388bfd"

    is_buy = signal == "BUY"
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

    trend_pct    = cat_pct(score_detail["trend"], score_detail["trend_max"])
    momentum_pct = cat_pct(score_detail["momentum"], score_detail["momentum_max"])
    structure_pct= cat_pct(score_detail["structure"], score_detail["structure_max"])
    mtf_pct      = cat_pct(score_detail["mtf"], score_detail["mtf_max"])
    volume_score = score_detail["volume"]

    points = []

    # Trend
    ema_note = "EMA20/EMA50/EMA200 align mendukung arah ini" if trend_pct >= 60 else "EMA belum sepenuhnya align"
    points.append(f"Trend {direction_word} {strength_label(trend_pct)} — {ema_note}.")

    # Momentum
    rsi_val = indicators.get("RSI", "-")
    macd_note = "MACD searah dengan sinyal" if momentum_pct >= 60 else "MACD belum konfirmasi penuh"
    points.append(f"Momentum {strength_label(momentum_pct)} — RSI di level {rsi_val}, {macd_note}.")

    # Structure
    sr_note = "harga berada di zona Support/Resistance yang ideal" if structure_pct >= 60 else "harga belum berada di zona S/R yang ideal"
    points.append(f"Struktur harga {strength_label(structure_pct)} — {sr_note}.")

    # MTF
    if mtf_pct >= 70:
        mtf_label = "5M/15M/1H" if trading_mode == "Scalping" else "1H/4H/1D"
        mtf_text = f"Multi-timeframe ({mtf_label}) searah penuh, jadi konfirmasi cukup kuat."
    elif mtf_pct >= 45:
        mtf_text = "Multi-timeframe sebagian searah, masih ada timeframe yang belum konfirmasi."
    else:
        mtf_text = "Multi-timeframe belum align — ada risiko pergerakan choppy/whipsaw."
    points.append(mtf_text)

    # Volume
    if volume_score >= 4:
        points.append("Volume sedang surge, menandakan minat pasar yang kuat di balik pergerakan ini.")
    elif volume_score >= 2:
        points.append("Volume dalam kondisi normal, tidak ada lonjakan minat pasar yang signifikan.")
    else:
        points.append("Volume tergolong lemah — waspada potensi pergerakan palsu (false move).")

    # Conclusion
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
#  CHART GENERATOR
# ─────────────────────────────────────────────
def build_chart(df, symbol, resistances=[], supports=[]):
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=[0.6, 0.2, 0.2]
    )
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df["timestamp"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="Price", increasing_line_color="#3fb950", decreasing_line_color="#f85149",
        increasing_fillcolor="#0d2b1d", decreasing_fillcolor="#2d1b1b"
    ), row=1, col=1)
    
    # EMA Lines
    ema20 = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    ema50 = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    fig.add_trace(go.Scatter(x=df["timestamp"], y=ema20, name="EMA20", line=dict(color="#f0883e", width=1.5, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=ema50, name="EMA50", line=dict(color="#388bfd", width=1.5, dash="dot")), row=1, col=1)
    
    # Bollinger Bands
    bb = ta.volatility.BollingerBands(df["close"], window=20)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=bb.bollinger_hband(), name="BB Upper", line=dict(color="#8b949e", width=1, dash="dash"), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=bb.bollinger_lband(), name="BB Lower", line=dict(color="#8b949e", width=1, dash="dash"), fill="tonexty", fillcolor="rgba(139,148,158,0.05)", showlegend=False), row=1, col=1)
    
    # Support & Resistance Lines
    for r in resistances:
        fig.add_hline(y=r, line_dash="dash", line_color="#f85149", opacity=0.6, row=1, col=1, annotation_text=f"R {r:,.4f}", annotation_position="right")
    for s in supports:
        fig.add_hline(y=s, line_dash="dash", line_color="#3fb950", opacity=0.6, row=1, col=1, annotation_text=f"S {s:,.4f}", annotation_position="right")
        
    # Volume Chart
    colors = ["#3fb950" if df["close"].iloc[i] >= df["open"].iloc[i] else "#f85149" for i in range(len(df))]
    fig.add_trace(go.Bar(x=df["timestamp"], y=df["volume"], name="Volume", marker_color=colors, opacity=0.5), row=2, col=1)
    
    # MACD Chart
    macd_ind = ta.trend.MACD(df["close"])
    fig.add_trace(go.Scatter(x=df["timestamp"], y=macd_ind.macd(), name="MACD", line=dict(color="#388bfd", width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=macd_ind.macd_signal(), name="Signal", line=dict(color="#f0883e", width=1.5)), row=3, col=1)
    
    hist_colors = ["#3fb950" if val >= 0 else "#f85149" for val in macd_ind.macd_diff()]
    fig.add_trace(go.Bar(x=df["timestamp"], y=macd_ind.macd_diff(), name="Histogram", marker_color=hist_colors, opacity=0.7), row=3, col=1)
    
    # Layout Adjustment
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=30, b=10),
        height=600,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(gridcolor="#21262d", zerolinecolor="#21262d")
    fig.update_xaxes(gridcolor="#21262d", zerolinecolor="#21262d")
    
    return fig

# ─────────────────────────────────────────────
#  APP STATE COLD START
# ─────────────────────────────────────────────
if "auto_refresh" not in st.session_state:
    st.session_state["auto_refresh"] = True
if "trading_mode" not in st.session_state:
    st.session_state["trading_mode"] = "Ketat"
if "trade_history" not in st.session_state:
    st.session_state["trade_history"] = [
        {"timestamp": "2023-10-24 14:32", "pair": "BTCUSDT", "type": "BUY", "entry": 34200.0, "exit": 34850.0, "pnl": 65.0, "status": "TP1"},
        {"timestamp": "2023-10-24 11:15", "pair": "ETHUSDT", "type": "SELL", "entry": 1785.5, "exit": 1802.0, "pnl": -16.5, "status": "SL"},
        {"timestamp": "2023-10-23 18:40", "pair": "SOLUSDT", "type": "BUY", "entry": 31.20, "exit": 33.40, "pnl": 22.0, "status": "TP2"}
    ]

# ─────────────────────────────────────────────
#  SIDEBAR CONTROL PANEL
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(f'<div style="text-align:center; padding:10px 0;"><h2 style="margin:0; color:#388bfd;">Scoring Engine</h2><p style="color:#8b949e; font-size:11px; margin:0;">v2.6.0 • DUAL MODE</p></div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Mode selector
    trading_mode = st.radio(
        "🎯 TRADING MODE ENGINE",
        ["Ketat", "Scalping"],
        index=0 if st.session_state["trading_mode"] == "Ketat" else 1,
        help="Ketat: TF besar (1H/4H/1D), target RR lebar. Scalping: TF kecil (5M/15M/1H), toleransi RR longgar."
    )
    st.session_state["trading_mode"] = trading_mode
    
    # Set default timeframe based on mode
    default_tf = "1H" if trading_mode == "Ketat" else "15M"
    tf_options = ["1M", "3M", "5M", "15M", "30M", "1H", "2H", "4H", "6H", "8H", "12H", "1D", "1W", "1M_gap"]
    
    # Clean UI options mapping to Binance intervals
    tf_map = {
        "1M": "1m", "3M": "3m", "5M": "5m", "15M": "15m", "30M": "30m",
        "1H": "1h", "2H": "2h", "4H": "4h", "6H": "6h", "8H": "8h",
        "12H": "12h", "1D": "1d", "1W": "1w"
    }
    
    # Exclude 1M_gap logic just map to standard option safely
    ui_tf_options = [k for k in tf_map.keys()]
    
    selected_ui_tf = st.selectbox(
        "⏱️ BASE TIMEFRAME", 
        ui_tf_options, 
        index=ui_tf_options.index(default_tf)
    )
    interval = tf_map[selected_ui_tf]
    
    symbol = st.text_input("🪙 CRYPTO PAIR", value="BTCUSDT").upper().strip()
    modal = st.number_input("💵 RISK CAPITAL (USDT)", min_value=10, max_value=100000, value=100, step=50)
    
    st.markdown("---")
    if st.button("🔄 FORCE REFRESH DATA", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ─────────────────────────────────────────────
#  DATA FETCHING & RUN ENGINE
# ─────────────────────────────────────────────
try:
    price_data = get_price(symbol, BINANCE_API_KEY, BINANCE_API_SECRET)
    df = get_klines(symbol, interval, 200, BINANCE_API_KEY, BINANCE_API_SECRET)
except Exception:
    st.stop()

if df is None:
    st.error("❌ Gagal memuat data chart klines dari Binance API. Periksa kembali simbol koin Anda.")
    st.stop()

# Run Calculation
resistances, supports = get_support_resistance(df, n=3)
mtf_calculated = calculate_mtf_score(symbol, selected_ui_tf, BINANCE_API_KEY, BINANCE_API_SECRET, trading_mode)
signal, reason, badges, indicators, confidence, score_detail = calculate_signal(df, mtf_score_override=mtf_calculated)
decision, decision_reason, decision_color = calculate_trade_decision(signal, score_detail, df, supports, resistances, trading_mode)
plan = generate_trading_plan(df, price_data, signal, supports, resistances, modal, trading_mode)

# ─────────────────────────────────────────────
#  MAIN DASHBOARD LAYOUT
# ─────────────────────────────────────────────
# Header ticker row
c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
with c1:
    st.markdown(f'<h1 style="margin:0; font-size:32px;">{symbol} <span style="font-size:16px; color:#8b949e; font-weight:normal;">({selected_ui_tf} - {trading_mode} Mode)</span></h1>', unsafe_allow_html=True)
with c2:
    change_color = "#3fb950" if price_data["change"] >= 0 else "#f85149"
    sign = "+" if price_data["change"] >= 0 else ""
    st.markdown(f'<p style="color:#8b949e; font-size:11px; margin:0; text-transform:uppercase;">Live Price</p><h2 style="margin:0; font-size:28px;">{price_data["price"]:,.4f} <span style="font-size:14px; color:{change_color}; font-weight:500;">{sign}{price_data["change"]}%</span></h2>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<p style="color:#8b949e; font-size:11px; margin:0; text-transform:uppercase;">24h Vol</p><h2 style="margin:0; font-size:24px; color:#e6edf3;">{price_data["quoteVolume"]/1_000_000:.2f}M <span style="font-size:12px; color:#8b949e; font-weight:normal;">USDT</span></h2>', unsafe_allow_html=True)
with c4:
    # Live engine decision badge
    st.markdown(f"""
    <div style="background:{decision_color}15; border:1px solid {decision_color}; border-radius:6px; padding:8px 16px; text-align:right;">
        <span style="color:#8b949e; font-size:10px; text-transform:uppercase; display:block; margin-bottom:2px;">Engine Action v2</span>
        <strong style="color:{decision_color}; font-size:18px; letter-spacing:1px;">{decision}</strong>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Tabs Navigation
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Technical Dashboard", "🎯 AI Trading Plan", "🔮 Multi-Timeframe", "📜 Signal Logs", "⚙️ Settings"])

# ─── TAB 1: TECHNICAL DASHBOARD ───
with tab1:
    col_left, col_right = st.columns([7, 3])
    
    with col_left:
        # Chart display
        fig = build_chart(df, symbol, resistances, supports)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        
    with col_right:
        # Signal Box Dynamic
        sig_class = "signal-buy" if signal == "BUY" else "signal-sell" if signal == "SELL" else "signal-hold"
        st.markdown(f"""
        <div class="{sig_class}">
            <p style="color:#8b949e; font-size:11px; margin:0; text-transform:uppercase; letter-spacing:1px;">Scoring Output</p>
            <p class="signal-text">{signal}</p>
            <p class="signal-reason">{reason}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p class="section-header">📊 Category Weight Matrix</p>', unsafe_allow_html=True)
        
        # Breakdown Weight Scoring Engine v2
        categories = [
            ("📈 Trend Alignment", score_detail["trend"], score_detail["trend_max"], "#388bfd"),
            ("⏱️ Momentum Oscillators", score_detail["momentum"], score_detail["momentum_max"], "#f0883e"),
            ("🧱 Price Structure & S/R", score_detail["structure"], score_detail["structure_max"], "#58a6ff"),
            ("🌍 Multi-Timeframe Score", score_detail["mtf"], score_detail["mtf_max"], "#bc8cff"),
            ("📊 Volume Confirmation", score_detail["volume"], score_detail["volume_max"], "#ff7b72"),
        ]
        
        for name, val, max_val, color_bar in categories:
            pct = (val / max_val * 100) if max_val else 0
            st.markdown(f"""
            <div style="display:flex; justify-content:between; font-size:12px; margin-bottom:2px;">
                <span style="flex-grow:1; color:#e6edf3;">{name}</span>
                <span style="color:#8b949e; font-weight:600;">{val}/{max_val}</span>
            </div>
            <div class="strength-bar-container">
                <div class="strength-bar-fill" style="width: {pct}%; background-color: {color_bar};"></div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown(f"""
        <div style="background:#161b22; border:1px solid #30363d; border-radius:6px; padding:10px; margin-top:12px; text-align:center;">
            <span style="font-size:11px; color:#8b949e; display:block;">TOTAL ACCUMULATED SCORE</span>
            <span style="font-size:20px; font-weight:700; color:#e6edf3;">{score_detail["total"]} / 100</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p class="section-header">🏷️ Indicator Badges</p>', unsafe_allow_html=True)
        
        # Grid badges indicator list
        badge_html = '<div style="margin:-3px;">'
        for k, (name, style) in badges.items():
            b_class = "badge-green" if style == "green" else "badge-red" if style == "red" else "badge-neutral"
            badge_html += f'<span class="badge {b_class}">{k}: {name}</span>'
        badge_html += '</div>'
        st.markdown(badge_html, unsafe_allow_html=True)

# ─── TAB 2: AI TRADING PLAN ───
with tab2:
    if plan:
        col_p1, col_p2 = st.columns([4, 6])
        
        with col_p1:
            st.markdown('<p class="section-header">🎯 Risk & Money Management</p>', unsafe_allow_html=True)
            
            p_green  = "tp-green" if signal == "BUY" else "tp-red"
            p_red    = "tp-red" if signal == "BUY" else "tp-green"
            
            st.markdown(f"""
            <div class="tp-card">
                <div class="tp-row"><span class="tp-label">Signal Bias</span><span class="tp-value {p_green}">{plan["signal"]}</span></div>
                <div class="tp-row"><span class="tp-label">Entry Trigger Price</span><span class="tp-value" style="color:#388bfd;">{plan["entry"]:,.4f} USDT</span></div>
                <div class="tp-row"><span class="tp-label">Position Size (Qty)</span><span class="tp-value">{plan["qty"]}</span></div>
                <div class="tp-row"><span class="tp-label">Allocated Capital</span><span class="tp-value">{plan["modal"]} USDT</span></div>
                <div class="tp-row"><span class="tp-label">Invalidation Line (SL)</span><span class="tp-value {p_red}">{plan["sl"]:,.4f} ({plan["sl_pct"]}%)</span></div>
                <div class="tp-row"><span class="tp-label">Risk RR Ratio</span><span class="tp-value tp-yellow">1 : {plan["rr_ratio"]}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<p class="section-header">💰 Target Take Profit Scenarios</p>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="tp-card">
                <div class="tp-row"><span class="tp-label">🎯 Take Profit 1 (Conservative)</span><span class="tp-value {p_green}">{plan["tp1"]:,.4f} ({plan["tp1_pct"]}%)</span></div>
                <div class="tp-row"><span class="tp-label">🎯 Take Profit 2 (Moderate)</span><span class="tp-value {p_green}">{plan["tp2"]:,.4f} ({plan["tp2_pct"]}%)</span></div>
                <div class="tp-row"><span class="tp-label">🎯 Take Profit 3 (Aggressive)</span><span class="tp-value {p_green}">{plan["tp3"]:,.4f} ({plan["tp3_pct"]}%)</span></div>
                <div class="tp-row" style="margin-top:10px;"><span class="tp-label">Estimated Profit (TP1 / TP2 / TP3)</span><span class="tp-value tp-green">+{plan["profit_tp1"]} / +{plan["profit_tp2"]} / +{plan["profit_tp3"]} USDT</span></div>
                <div class="tp-row"><span class="tp-label">Max Risk Loss (SL hit)</span><span class="tp-value tp-red">-{plan["loss_sl"]} USDT</span></div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_p2:
            st.markdown('<p class="section-header">🧠 Engine Deep Reasoning Analysis</p>', unsafe_allow_html=True)
            
            points, conclusion, ai_color = generate_ai_reasoning(
                signal, decision, decision_reason, score_detail, indicators, supports, resistances, trading_mode
            )
            
            for pt in points:
                st.markdown(f"• {pt}")
                
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:{ai_color}10; border:1px solid {ai_color}; border-radius:8px; padding:16px;">
                <p style="color:{ai_color}; font-weight:600; margin:0; font-size:14px;">{conclusion}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<p class="section-header">🧱 Local Structural Key Levels</p>', unsafe_allow_html=True)
            
            st.write("⚓ Resistance Levels:")
            if resistances:
                for r in resistances:
                    st.markdown(f'<div class="sr-level sr-resistance"><span style="color:#ff7b72; font-weight:600;">Resistance</span><span>{r:,.4f} USDT</span></div>', unsafe_allow_html=True)
            else:
                st.info("Tidak ada level resistance terdekat terdeteksi.")
                
            st.write("⚓ Support Levels:")
            if supports:
                for s in supports:
                    st.markdown(f'<div class="sr-level sr-support"><span style="color:#7ee787; font-weight:600;">Support</span><span>{s:,.4f} USDT</span></div>', unsafe_allow_html=True)
            else:
                st.info("Tidak ada level support terdekat terdeteksi.")
    else:
        st.info("Sinyal HOLD tidak menghasilkan rencana trading aktif. Silakan tunggu update bias tren selanjutnya.")

# ─── TAB 3: MULTI-TIMEFRAME ANALYSIS ───
with tab3:
    st.markdown('<p class="section-header">🌍 Contextual Multi-Timeframe Trend Analysis</p>', unsafe_allow_html=True)
    mtf_data = multi_timeframe_analysis(symbol, BINANCE_API_KEY, BINANCE_API_SECRET)
    
    c_mtf1, c_mtf2, c_mtf3 = st.columns(3)
    cols_mtf = [c_mtf1, c_mtf2, c_mtf3]
    
    for idx, (tf_lbl, tf_sig, tf_reason, tf_conf) in enumerate(mtf_data):
        with cols_mtf[idx]:
            m_class = "mtf-buy" if tf_sig == "BUY" else "mtf-sell" if tf_sig == "SELL" else "mtf-hold"
            m_color = "#3fb950" if tf_sig == "BUY" else "#f85149" if tf_sig == "SELL" else "#388bfd"
            
            cols_mtf[idx].markdown(f"""
            <div class="mtf-card {m_class}">
                <p style="color:#8b949e; font-size:11px; margin:0; text-transform:uppercase;">Timeframe Profile</p>
                <h3 style="margin:4px 0 0 0; font-size:24px;">{tf_lbl}</h3>
                <span style="color:{m_color}; font-weight:700; font-size:16px; display:block; margin:6px 0;">{tf_sig} ({tf_conf}/100)</span>
                <p style="color:#8b949e; font-size:12px; margin:0; min-height:36px;">{tf_reason}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="section-header">🔥 24h Market Top Gainers Volume Spike</p>', unsafe_allow_html=True)
    gainers = get_top_gainers(BINANCE_API_KEY, BINANCE_API_SECRET, n=5)
    
    if gainers:
        for g in gainers:
            g_color = "#3fb950" if float(g["priceChangePercent"]) >= 0 else "#f85149"
            st.markdown(f"""
            <div class="gainer-row">
                <span style="font-weight:600; color:#e6edf3;">🪙 {g["symbol"]}</span>
                <div>
                    <span style="color:#8b949e; margin-right:16px;">Price: {float(g["lastPrice"]):,.4f}</span>
                    <span style="color:{g_color}; font-weight:600;">{float(g["priceChangePercent"]):+.2f}%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Tidak ada data gainers atau koneksi timeout.")

# ─── TAB 4: SIGNAL LOGS ───
with tab4:
    st.markdown('<p class="section-header">📜 Historic Mock/Live Trade Logs</p>', unsafe_allow_html=True)
    
    for t in st.session_state["trade_history"]:
        outcome_color = "#3fb950" if t["pnl"] >= 0 else "#f85149"
        pnl_sign = "+" if t["pnl"] >= 0 else ""
        type_color = "#3fb950" if t["type"] == "BUY" else "#f85149"
        
        st.markdown(f"""
        <div style="background:#161b22; border:1px solid #30363d; border-radius:6px; padding:12px 16px; margin:6px 0; display:flex; justify-content:between; align-items:center;">
            <div>
                <span style="color:#8b949e; font-size:11px; display:block;">{t["timestamp"]}</span>
                <strong style="font-size:16px; color:#e6edf3;">{t["pair"]}</strong>
                <span style="background:{type_color}15; color:{type_color}; font-size:11px; padding:2px 6px; border-radius:4px; font-weight:600; margin-left:8px;">{t["type"]}</span>
            </div>
            <div style="text-align:right;">
                <span style="font-size:12px; color:#8b949e; display:block;">Status: <span style="color:#e6edf3; font-weight:600;">{t["status"]}</span></span>
                <span style="color:{outcome_color}; font-weight:700;">{pnl_sign}{t["pnl"]} USDT</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ─── TAB 5: SETTINGS ───
with tab5:
    st.markdown('<p class="section-header">⚙️ Settings</p>', unsafe_allow_html=True)

    st.markdown("**🔄 Auto Refresh**")
    auto_refresh = st.checkbox("Auto Refresh setiap 30 detik", value=st.session_state["auto_refresh"])
    st.session_state["auto_refresh"] = auto_refresh
    if auto_refresh:
        st.success("✅ Auto refresh aktif — data update tiap 30 detik")
    else:
        st.info("ℹ️ Auto refresh nonaktif")

    st.markdown("---")
    st.markdown("**ℹ️ App Info**")
    st.markdown(f"""
    <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:16px;">
        <p style="color:#8b949e; font-size:12px; margin:0;">
        Version: <span style="color:#e6edf3;">v2.7.0 (Dual Mode Integration)</span><br>
        Exchange: <span style="color:#e6edf3;">Binance Spot</span><br>
        Features: <span style="color:#e6edf3;">Dual Mode Engine, Multi-Timeframe Scoring, Risk Matrix</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  AUTO REFRESH LOOP TRIGGER
# ─────────────────────────────────────────────
if st.session_state["auto_refresh"]:
    time.sleep(30)
    st.rerun()
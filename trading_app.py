import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import MetaTrader5 as mt5
import ta
import time
from datetime import datetime

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
#  MT5 CONNECTION
# ─────────────────────────────────────────────
@st.cache_resource
def init_mt5():
    if not mt5.initialize():
        return False
    return True

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

@st.cache_data(ttl=60)
def get_mt5_klines(symbol, timeframe_str, limit):
    try:
        mt5.symbol_select(symbol, True)
        tf = TIMEFRAME_MAP.get(timeframe_str, mt5.TIMEFRAME_H1)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, limit)
        if rates is None:
            return None
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.rename(columns={"time": "timestamp", "tick_volume": "volume"})
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df
    except:
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

    # ── 1. TREND SCORE (0-35) ──────────────────
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
        trend_score += 5; trend_bias += 1
    else:
        trend_score += 0; trend_bias -= 1

    trend_score = min(trend_score, 35)

    # ── 2. MOMENTUM SCORE (0-25) ───────────────
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
        momentum_score += 1;  momentum_bias -= 1
    else:
        momentum_score += 2

    momentum_score = min(momentum_score, 25)

    # ── 3. STRUCTURE SCORE (0-20) ──────────────
    structure_score = 0
    structure_bias  = 0

    if bb_pos < 20:
        structure_score += 10; structure_bias += 1
    elif bb_pos > 80:
        structure_score += 0;  structure_bias -= 1
    elif bb_pos < 40:
        structure_score += 7;  structure_bias += 1
    elif bb_pos > 60:
        structure_score += 3;  structure_bias -= 1
    else:
        structure_score += 5

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

    # ── TOTAL ──────────────────────────────────
    total_score = trend_score + momentum_score + structure_score + mtf_score + volume_score
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

    # Score mentah memakai skala bullish (tinggi = BUY, rendah = SELL).
    # Ubah menjadi kekuatan searah bias agar BUY dan SELL dinilai simetris.
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

    # ── BADGES (kompatibel UI lama) ─────────────
    signals = {}

    if rsi < 30:   signals["RSI"] = ("OVERSOLD", "green")
    elif rsi < 45: signals["RSI"] = ("BULLISH", "green")
    elif rsi > 70: signals["RSI"] = ("OVERBOUGHT", "red")
    elif rsi > 55: signals["RSI"] = ("BEARISH", "red")
    else:          signals["RSI"] = ("NEUTRAL", "neutral")

    if macd_val > macd_sig and macd_hist > 0:   signals["MACD"] = ("BULLISH CROSS", "green")
    elif macd_val < macd_sig and macd_hist < 0: signals["MACD"] = ("BEARISH CROSS", "red")
    else:                                        signals["MACD"] = ("NEUTRAL", "neutral")

    if ema20_val > ema50_val > ema200_val:   signals["EMA"] = ("STRONG UPTREND", "green")
    elif ema20_val < ema50_val < ema200_val: signals["EMA"] = ("STRONG DOWNTREND", "red")
    elif ema20_val > ema50_val:              signals["EMA"] = ("UPTREND", "green")
    else:                                    signals["EMA"] = ("DOWNTREND", "red")

    if stoch_k < 20 and stoch_k > stoch_d:   signals["STOCH"] = ("OVERSOLD CROSS", "green")
    elif stoch_k > 80 and stoch_k < stoch_d: signals["STOCH"] = ("OVERBOUGHT CROSS", "red")
    else:                                     signals["STOCH"] = ("NEUTRAL", "neutral")

    if bb_pos < 20:   signals["BB"] = ("BELOW LOWER", "green")
    elif bb_pos > 80: signals["BB"] = ("ABOVE UPPER", "red")
    else:             signals["BB"] = ("WITHIN BAND", "neutral")

    if vol_ratio >= 1.5: signals["VOL"] = ("SURGE ⚡", "green")
    else:                signals["VOL"] = ("NORMAL", "neutral")

    # ── RAW VALUES ─────────────────────────────
    indicators = {
        "RSI": round(rsi, 2),
        "MACD": round(macd_val, 6),
        "Stoch %K": round(stoch_k, 2),
        "BB_pos": round(bb_pos, 1),
        "EMA20": round(ema20_val, 5),
        "EMA50": round(ema50_val, 5),
        "EMA200": round(ema200_val, 5),
    }

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
#  Input  : signal, score_detail, df, supports, resistances
#  Output : decision ("ENTER"|"WAIT"|"SKIP"), reason, color
# ─────────────────────────────────────────────
def calculate_trade_decision(signal, score_detail, df, supports, resistances):
    """
    ENTER : semua syarat terpenuhi, setup bagus, masuk sekarang
    WAIT  : sinyal ada tapi salah satu syarat belum ideal
    SKIP  : kondisi jelek / RR buruk / sinyal HOLD
    """
    if signal == "HOLD":
        return "SKIP", "Sinyal HOLD — tidak ada setup", "#8b949e"

    is_buy      = signal == "BUY"
    total       = score_detail.get("confidence", score_detail["total"])
    trend       = score_detail["trend"] if is_buy else score_detail["trend_max"] - score_detail["trend"]
    momentum    = score_detail["momentum"] if is_buy else score_detail["momentum_max"] - score_detail["momentum"]
    structure   = score_detail["structure"] if is_buy else score_detail["structure_max"] - score_detail["structure"]
    mtf         = score_detail["mtf"] if is_buy else score_detail["mtf_max"] - score_detail["mtf"]

    # ── ATR & RR check ─────────────────────────
    try:
        atr = ta.volatility.AverageTrueRange(
            df["high"], df["low"], df["close"], window=14
        ).average_true_range().iloc[-1]
        current_price = df["close"].iloc[-1]

        if signal == "BUY":
            sl_price  = current_price - (atr * 1.5)
            tp1_price = current_price + (atr * 2.0)
        else:
            sl_price  = current_price + (atr * 1.5)
            tp1_price = current_price - (atr * 2.0)

        sl_dist  = abs(current_price - sl_price)
        tp_dist  = abs(tp1_price - current_price)
        rr_ratio = tp_dist / sl_dist if sl_dist > 0 else 0

    except Exception:
        rr_ratio = 0

    # ── Structure: harga dekat S/R yang tepat? ─
    structure_ok = False
    if signal == "BUY" and supports:
        dist_pct = abs(current_price - supports[0]) / current_price * 100
        structure_ok = dist_pct <= 1.5
    elif signal == "SELL" and resistances:
        dist_pct = abs(resistances[0] - current_price) / current_price * 100
        structure_ok = dist_pct <= 1.5
    else:
        structure_ok = structure >= 12

    # ── Decision logic ─────────────────────────
    reasons_wait = []

    if total < 50:
        return "SKIP", f"Score terlalu rendah ({total}/100) — jangan masuk", "#f85149"

    if rr_ratio < 1.0:
        return "SKIP", f"RR {rr_ratio:.2f} — reward tidak sepadan risiko", "#f85149"

    if trend < 15:
        reasons_wait.append("trend lemah")

    if momentum < 12:
        reasons_wait.append("momentum belum konfirmasi")

    if rr_ratio < 1.5:
        reasons_wait.append(f"RR {rr_ratio:.2f} masih marginal")

    if mtf < 6:
        reasons_wait.append("MTF belum searah")

    if not structure_ok:
        reasons_wait.append("belum di zona S/R ideal")

    if not reasons_wait and total >= 60 and rr_ratio >= 1.5:
        return "ENTER", f"Setup solid — Score {total}/100, RR 1:{rr_ratio:.1f}", "#3fb950"

    if reasons_wait:
        note = ", ".join(reasons_wait[:2])
        return "WAIT", f"Tunggu: {note}", "#f0883e"

    return "ENTER", f"Setup cukup — Score {total}/100, RR 1:{rr_ratio:.1f}", "#3fb950"

# ─────────────────────────────────────────────
#  MULTI TIMEFRAME
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
#  REAL MTF SCORE ENGINE
#  Fetch 1H / 4H / 1D → score per TF → total 0-15
#  Bobot: 1D=7, 4H=5, 1H=3
# ─────────────────────────────────────────────
def calculate_mtf_score(symbol, current_tf):
    """
    Hitung MTF score berdasarkan EMA trend alignment di 3 timeframe.
    current_tf dikecualikan supaya tidak double-count.
    Returns: int 0-15
    """
    tf_config = [
        ("1h",  "1H", 3),
        ("4h",  "4H", 5),
        ("1d",  "1D", 7),
    ]
    total_weight = 0
    total_score  = 0

    for interval, label, weight in tf_config:
        if label == current_tf:
            continue

        df_tf = get_mt5_klines(symbol, interval, 200)
        if df_tf is None or len(df_tf) < 50:
            continue

        close_tf  = df_tf["close"]
        ema20_tf  = ta.trend.EMAIndicator(close_tf, window=20).ema_indicator().iloc[-1]
        ema50_tf  = ta.trend.EMAIndicator(close_tf, window=50).ema_indicator().iloc[-1]
        ema200_tf = ta.trend.EMAIndicator(close_tf, window=200).ema_indicator().iloc[-1] \
                    if len(close_tf) >= 200 else ema50_tf
        price_tf  = close_tf.iloc[-1]

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


def multi_timeframe_analysis(symbol):
    timeframes = [("1H", "1h", 100), ("4H", "4h", 100), ("1D", "1d", 200)]
    results = []
    for label, tf, limit in timeframes:
        df = get_mt5_klines(symbol, tf, limit)
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
    resistance_levels = sorted(set([round(r, 5) for r in resistance_levels if r > current_price]))[:n]
    support_levels = sorted(set([round(s, 5) for s in support_levels if s < current_price]), reverse=True)[:n]
    return resistance_levels, support_levels

# ─────────────────────────────────────────────
#  TRADING PLAN
# ─────────────────────────────────────────────
def generate_trading_plan(df, current_price, signal, supports, resistances, modal_usd=100, leverage=100):
    if df is None or len(df) < 20 or signal == "HOLD":
        return None

    atr   = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range().iloc[-1]
    entry = round(current_price, 5)

    if signal == "BUY":
        sl_atr  = round(entry - (atr * 1.5), 5)
        sl_sr   = round(supports[0] * 0.9998, 5) if supports else sl_atr
        sl      = min(sl_atr, sl_sr)
        tp1_atr = round(entry + (atr * 2.0), 5)
        tp2_atr = round(entry + (atr * 3.5), 5)
        tp3_atr = round(entry + (atr * 5.0), 5)
        if resistances:
            r1  = round(resistances[0] * 0.9999, 5)
            tp1 = min(tp1_atr, r1) if r1 > entry else tp1_atr
        else:
            tp1 = tp1_atr
        tp2 = tp2_atr
        tp3 = tp3_atr
        tp1 = max(tp1, round(entry * 1.0001, 5))
        tp2 = max(tp2, round(tp1  * 1.0002, 5))
        tp3 = max(tp3, round(tp2  * 1.0002, 5))
        sl  = min(sl,  round(entry * 0.9950, 5))

    else:  # SELL
        sl_atr  = round(entry + (atr * 1.5), 5)
        sl_sr   = round(resistances[0] * 1.0002, 5) if resistances else sl_atr
        sl      = max(sl_atr, sl_sr)
        tp1_atr = round(entry - (atr * 2.0), 5)
        tp2_atr = round(entry - (atr * 3.5), 5)
        tp3_atr = round(entry - (atr * 5.0), 5)
        if supports:
            s1  = round(supports[0] * 1.0001, 5)
            tp1 = max(tp1_atr, s1) if s1 < entry else tp1_atr
        else:
            tp1 = tp1_atr
        tp2 = tp2_atr
        tp3 = tp3_atr
        tp1 = min(tp1, round(entry * 0.9999, 5))
        tp2 = min(tp2, round(tp1  * 0.9998, 5))
        tp3 = min(tp3, round(tp2  * 0.9998, 5))
        sl  = max(sl,  round(entry * 1.0050, 5))

    sl_pct  = abs((sl  - entry) / entry * 100)
    tp1_pct = abs((tp1 - entry) / entry * 100)
    tp2_pct = abs((tp2 - entry) / entry * 100)
    tp3_pct = abs((tp3 - entry) / entry * 100)
    rr_ratio = round(tp1_pct / sl_pct, 2) if sl_pct > 0 else 0

    # Auto-detect pip size & lot size berdasarkan harga
    # Forex (< 100): pip = 0.00010, lot dari 100k unit
    # Gold/Indices (>= 100): pip = 0.10, lot dari 10 unit
    if entry >= 100:
        pip_size = 0.10
        lot_size = round(modal_usd / (entry * 10), 4)
    else:
        pip_size = 0.00010
        lot_size = round(modal_usd / (entry * 1000), 4)

    sl_pips   = round(abs(sl  - entry) / pip_size, 1)
    tp1_pips  = round(abs(tp1 - entry) / pip_size, 1)
    tp2_pips  = round(abs(tp2 - entry) / pip_size, 1)
    tp3_pips  = round(abs(tp3 - entry) / pip_size, 1)
    profit_tp1  = round(tp1_pips * lot_size * 1.0, 2)
    profit_tp2  = round(tp2_pips * lot_size * 1.0, 2)
    profit_tp3  = round(tp3_pips * lot_size * 1.0, 2)
    loss_sl     = round(sl_pips  * lot_size * 1.0, 2)

    return {
        "signal":     signal,
        "entry":      entry,
        "sl":         sl,
        "tp1":        tp1,
        "tp2":        tp2,
        "tp3":        tp3,
        "sl_pct":     round(sl_pct,  4),
        "tp1_pct":    round(tp1_pct, 4),
        "tp2_pct":    round(tp2_pct, 4),
        "tp3_pct":    round(tp3_pct, 4),
        "sl_pips":    sl_pips,
        "tp1_pips":   tp1_pips,
        "tp2_pips":   tp2_pips,
        "tp3_pips":   tp3_pips,
        "rr_ratio":   rr_ratio,
        "lot_size":   lot_size,
        "modal":      modal_usd,
        "leverage":   leverage,
        "profit_tp1": profit_tp1,
        "profit_tp2": profit_tp2,
        "profit_tp3": profit_tp3,
        "loss_sl":    loss_sl,
        "atr":        round(atr, 5),
    }

# ─────────────────────────────────────────────
#  AI REASONING ENGINE — Phase 4A.6
#  Mengubah score_detail + decision jadi narasi penjelasan
#  Input  : signal, decision, decision_reason, score_detail, indicators, supports, resistances
#  Output : (points: list[str], conclusion: str, conclusion_color: str)
# ─────────────────────────────────────────────
def generate_ai_reasoning(signal, decision, decision_reason, score_detail, indicators, supports, resistances):
    if signal == "HOLD":
        points = [
            "Tidak ada bias arah yang cukup jelas dari kombinasi Trend, Momentum, dan Structure saat ini.",
            "Total score belum cukup tinggi maupun cukup rendah untuk memicu sinyal BUY atau SELL.",
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
        # Score tinggi = bullish, score rendah = bearish (sesuai desain Signal Engine v2)
        return raw_pct if is_buy else (100 - raw_pct)

    trend_pct     = cat_pct(score_detail["trend"],     score_detail["trend_max"])
    momentum_pct  = cat_pct(score_detail["momentum"],  score_detail["momentum_max"])
    structure_pct = cat_pct(score_detail["structure"], score_detail["structure_max"])
    mtf_pct       = cat_pct(score_detail["mtf"],       score_detail["mtf_max"])
    volume_score  = score_detail["volume"]

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
        mtf_text = "Multi-timeframe (1H/4H/1D) searah penuh, jadi konfirmasi cukup kuat."
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
#  CHART
# ─────────────────────────────────────────────
def build_chart(df, symbol, resistances=[], supports=[]):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])

    fig.add_trace(go.Candlestick(
        x=df["timestamp"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="Price", increasing_line_color="#3fb950", decreasing_line_color="#f85149",
        increasing_fillcolor="#0d2b1d", decreasing_fillcolor="#2d1b1b",
    ), row=1, col=1)

    ema20 = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    ema50 = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    fig.add_trace(go.Scatter(x=df["timestamp"], y=ema20, name="EMA20", line=dict(color="#f0883e", width=1.5, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=ema50, name="EMA50", line=dict(color="#388bfd", width=1.5, dash="dot")), row=1, col=1)

    bb = ta.volatility.BollingerBands(df["close"], window=20)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=bb.bollinger_hband(), name="BB Upper", line=dict(color="#8b949e", width=1, dash="dash"), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=bb.bollinger_lband(), name="BB Lower", line=dict(color="#8b949e", width=1, dash="dash"), fill="tonexty", fillcolor="rgba(139,148,158,0.05)", showlegend=False), row=1, col=1)

    for r in resistances:
        fig.add_hline(y=r, line_dash="dash", line_color="#f85149", opacity=0.6, row=1, col=1, annotation_text=f"R {r:.5f}", annotation_position="right")
    for s in supports:
        fig.add_hline(y=s, line_dash="dash", line_color="#3fb950", opacity=0.6, row=1, col=1, annotation_text=f"S {s:.5f}", annotation_position="right")

    colors = ["#3fb950" if df["close"].iloc[i] >= df["open"].iloc[i] else "#f85149" for i in range(len(df))]
    fig.add_trace(go.Bar(x=df["timestamp"], y=df["volume"], name="Volume", marker_color=colors, opacity=0.7), row=2, col=1)

    rsi = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    fig.add_trace(go.Scatter(x=df["timestamp"], y=rsi, name="RSI", line=dict(color="#d2a8ff", width=1.5)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#f85149", opacity=0.5, row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#3fb950", opacity=0.5, row=3, col=1)

    fig.update_layout(
        plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
        font=dict(color="#8b949e", size=11), height=580,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        xaxis_rangeslider_visible=False,
    )
    fig.update_yaxes(gridcolor="#21262d", zerolinecolor="#21262d")
    fig.update_xaxes(gridcolor="#21262d", zerolinecolor="#21262d")
    return fig

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
if "auto_refresh_mt5" not in st.session_state:
    st.session_state["auto_refresh_mt5"] = False

# ─────────────────────────────────────────────
#  MT5 INIT CHECK
# ─────────────────────────────────────────────
connected = init_mt5()
if not connected:
    st.error("❌ Gagal konek ke MT5! Pastiin MetaTrader 5 sedang running di VPS.")
    st.stop()

# ─────────────────────────────────────────────
#  MAIN CONTENT
# ─────────────────────────────────────────────
DEFAULT_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "XAUUSD"]

col_sel1, col_sel2 = st.columns([2, 1])
with col_sel1:
    symbol = st.selectbox("🌍 Select Pair", DEFAULT_PAIRS)
with col_sel2:
    custom = st.text_input("Custom pair", placeholder="e.g. NZDUSD")
    if custom:
        symbol = custom.upper()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🕐 Multi-Timeframe", "🌍 Market Watch", "🧪 Backtesting", "⚙️ Settings"])

# ─── TAB 1: DASHBOARD ───
with tab1:
    col_tf, col_candle = st.columns([2, 1])
    with col_tf:
        interval = st.selectbox("⏱ Timeframe", [
            ("1 Minute","1m"),("5 Minutes","5m"),("15 Minutes","15m"),
            ("1 Hour","1h"),("4 Hours","4h"),("1 Day","1d")
        ], format_func=lambda x: x[0], index=3)
        interval_val = interval[1]
    with col_candle:
        candles = st.slider("Candles", 50, 500, 200)

    price_data = get_mt5_price(symbol)
    if price_data is None:
        st.error(f"Gagal ambil data {symbol}. Pastiin MT5 running & pair tersedia.")
        st.stop()

    bid = price_data["bid"]
    ask = price_data["ask"]
    digits = price_data["digits"]
    fmt = f",.{digits}f"

    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"""
        <div style="margin-bottom:8px;">
            <span style="font-size:26px; font-weight:800; color:#e6edf3;">{symbol}</span>
            <span style="font-size:12px; color:#8b949e; margin-left:12px;">MT5 FOREX</span>
        </div>
        <div>
            <span style="font-size:14px; color:#8b949e;">BID </span>
            <span style="font-size:32px; font-weight:700; color:#3fb950;">{bid:{fmt}}</span>
            <span style="font-size:14px; color:#8b949e; margin-left:16px;">ASK </span>
            <span style="font-size:32px; font-weight:700; color:#f85149;">{ask:{fmt}}</span>
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

    df = get_mt5_klines(symbol, interval_val, candles)
    resistances, supports = get_support_resistance(df)

    if df is not None:
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Open", f"{df['open'].iloc[-1]:{fmt}}")
        with col2: st.metric("High", f"{df['high'].iloc[-1]:{fmt}}")
        with col3: st.metric("Low", f"{df['low'].iloc[-1]:{fmt}}")
        with col4: st.metric("Volume", f"{int(df['volume'].iloc[-1]):,}")

    st.markdown("---")

    col_chart, col_signal = st.columns([3, 1])

    with col_chart:
        st.markdown('<p class="section-header">Price Chart</p>', unsafe_allow_html=True)
        if df is not None:
            fig = build_chart(df, symbol, resistances, supports)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Gagal load chart data")

        # Filled after signal calculation, but rendered directly below the chart.
        trading_plan_container = st.container()

    with col_signal:
        st.markdown('<p class="section-header">AI Signal</p>', unsafe_allow_html=True)
        if df is not None:
            # Map interval_val ke label TF untuk exclude dari MTF scoring
            tf_label_map = {"1m":"1M","5m":"5M","15m":"15M","1h":"1H","4h":"4H","1d":"1D"}
            current_tf_label = tf_label_map.get(interval_val, "1H")

            # Hitung MTF score real dari TF lain (1H/4H/1D)
            mtf_real = calculate_mtf_score(symbol, current_tf_label)

            signal, reason, signals, indicators, confidence, score_detail = calculate_signal(df, mtf_score_override=mtf_real)
            decision, decision_reason, decision_color = calculate_trade_decision(
                signal, score_detail, df, supports, resistances
            )
            signal_class = f"signal-{signal.lower()}"
            signal_emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🔵"
            strength_color = "#3fb950" if signal == "BUY" else "#f85149" if signal == "SELL" else "#388bfd"

            decision_emoji = "🟢" if decision == "ENTER" else "🟡" if decision == "WAIT" else "🔴"
            decision_bg    = "rgba(63,185,80,0.12)"  if decision == "ENTER" else \
                             "rgba(240,136,62,0.12)" if decision == "WAIT"  else \
                             "rgba(248,81,73,0.08)"

            st.markdown(f"""
            <div class="{signal_class}">
                <p class="signal-text">{signal_emoji} {signal}</p>
                <p class="signal-reason">{reason}</p>
                <div class="strength-bar-container">
                    <div class="strength-bar-fill" style="width:{confidence}%; background:{strength_color};"></div>
                </div>
                <p style="color:#8b949e; font-size:11px;">Confidence: {confidence}%</p>
                <div style="
                    margin-top:14px;
                    background:{decision_bg};
                    border:1px solid {decision_color};
                    border-radius:6px;
                    padding:10px 12px;
                    text-align:center;
                ">
                    <p style="font-size:18px; font-weight:900; color:{decision_color}; margin:0; letter-spacing:3px;">
                        {decision_emoji} {decision}
                    </p>
                    <p style="color:#8b949e; font-size:11px; margin:4px 0 0 0;">{decision_reason}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Filled later, but rendered here so the explanation stays directly
            # below the signal card and before the score breakdown.
            reasoning_container = st.container()

            # ── Score Breakdown ──────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<p class="section-header">Score Breakdown</p>', unsafe_allow_html=True)

            score_direction = 1 if signal != "SELL" else -1
            score_rows = [
                ("Trend",     score_detail["trend"] if score_direction > 0 else score_detail["trend_max"] - score_detail["trend"],             score_detail["trend_max"],     "#388bfd"),
                ("Momentum",  score_detail["momentum"] if score_direction > 0 else score_detail["momentum_max"] - score_detail["momentum"], score_detail["momentum_max"],  "#d2a8ff"),
                ("Structure", score_detail["structure"] if score_direction > 0 else score_detail["structure_max"] - score_detail["structure"], score_detail["structure_max"], "#f0883e"),
                ("MTF",       score_detail["mtf"] if score_direction > 0 else score_detail["mtf_max"] - score_detail["mtf"],                 score_detail["mtf_max"],       "#79c0ff"),
                ("Volume",    score_detail["volume"],    score_detail["volume_max"],    "#56d364"),
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

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<p class="section-header">Indicators</p>', unsafe_allow_html=True)
            for ind_name, (ind_val, ind_color) in signals.items():
                badge_class = f"badge-{'green' if ind_color == 'green' else 'red' if ind_color == 'red' else 'neutral'}"
                st.markdown(f'<span style="color:#8b949e; font-size:12px;">{ind_name}</span> <span class="badge {badge_class}">{ind_val}</span><br>', unsafe_allow_html=True)

            if indicators:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<p class="section-header">Values</p>', unsafe_allow_html=True)
                for k, v in indicators.items():
                    st.markdown(f'<div style="display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid #21262d;"><span style="color:#8b949e; font-size:12px;">{k}</span><span style="color:#e6edf3; font-size:12px; font-weight:600;">{v}</span></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<p class="section-header">Support & Resistance</p>', unsafe_allow_html=True)
            for r in resistances:
                st.markdown(f'<div class="sr-level sr-resistance"><span style="color:#8b949e;">Resistance</span><span style="color:#f85149; font-weight:700;">{r:.5f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="text-align:center; padding:4px; color:#e6edf3; font-size:12px; font-weight:700;">── Now: {bid:{fmt}} ──</div>', unsafe_allow_html=True)
            for s in supports:
                st.markdown(f'<div class="sr-level sr-support"><span style="color:#8b949e;">Support</span><span style="color:#3fb950; font-weight:700;">{s:.5f}</span></div>', unsafe_allow_html=True)

    # Trading Plan — rendered in the left column below Price Chart
    with trading_plan_container:
        st.markdown("---")
        st.markdown('<p class="section-header">📋 Trading Plan</p>', unsafe_allow_html=True)

        col_m1, col_m2 = st.columns([1, 1])
        with col_m1:
            modal = st.number_input("💵 Modal (USD)", min_value=1.0, value=100.0, step=10.0, format="%.2f")
        with col_m2:
            leverage = st.selectbox("⚡ Leverage", [1, 10, 50, 100, 200, 500], index=3)
    
        if df is not None and decision == "ENTER":
            plan = generate_trading_plan(df, bid, signal, supports, resistances, modal_usd=modal, leverage=leverage)
    
            if plan:
                rr_color = "#3fb950" if plan["rr_ratio"] >= 1.5 else "#f0883e" if plan["rr_ratio"] >= 1 else "#f85149"
                action_color = "#3fb950" if plan["signal"] == "BUY" else "#f85149"
                action_emoji = "🟢" if plan["signal"] == "BUY" else "🔴"
    
                col_p1, col_p2, col_p3 = st.columns(3)
                with col_p1:
                    st.markdown(f"""
                    <div class="tp-card">
                        <p style="color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin:0 0 12px 0;">Entry & Exit</p>
                        <div class="tp-row"><span class="tp-label">Action</span><span class="tp-value" style="color:{action_color};">{action_emoji} {plan["signal"]}</span></div>
                        <div class="tp-row"><span class="tp-label">Entry</span><span class="tp-value tp-yellow">{plan["entry"]:.5f}</span></div>
                        <div class="tp-row"><span class="tp-label">Stop Loss</span><span class="tp-value tp-red">{plan["sl"]:.5f} ({plan["sl_pips"]} pips)</span></div>
                        <div class="tp-row"><span class="tp-label">TP 1</span><span class="tp-value tp-green">{plan["tp1"]:.5f} ({plan["tp1_pips"]} pips)</span></div>
                        <div class="tp-row"><span class="tp-label">TP 2</span><span class="tp-value tp-green">{plan["tp2"]:.5f} ({plan["tp2_pips"]} pips)</span></div>
                        <div class="tp-row"><span class="tp-label">TP 3</span><span class="tp-value tp-green">{plan["tp3"]:.5f} ({plan["tp3_pips"]} pips)</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_p2:
                    st.markdown(f"""
                    <div class="tp-card">
                        <p style="color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin:0 0 12px 0;">Risk & Reward</p>
                        <div class="tp-row"><span class="tp-label">R/R Ratio</span><span class="tp-value" style="color:{rr_color};">1 : {plan["rr_ratio"]}</span></div>
                        <div class="tp-row"><span class="tp-label">ATR</span><span class="tp-value">{plan["atr"]:.5f}</span></div>
                        <div class="tp-row"><span class="tp-label">Modal</span><span class="tp-value">${plan["modal"]:,.2f}</span></div>
                        <div class="tp-row"><span class="tp-label">Lot Size</span><span class="tp-value">{plan["lot_size"]}</span></div>
                        <div class="tp-row"><span class="tp-label">Leverage</span><span class="tp-value">1:{plan["leverage"]}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_p3:
                    st.markdown(f"""
                    <div class="tp-card">
                        <p style="color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin:0 0 12px 0;">Estimasi P&L</p>
                        <div class="tp-row"><span class="tp-label">Profit TP1</span><span class="tp-value tp-green">+${plan["profit_tp1"]}</span></div>
                        <div class="tp-row"><span class="tp-label">Profit TP2</span><span class="tp-value tp-green">+${plan["profit_tp2"]}</span></div>
                        <div class="tp-row"><span class="tp-label">Profit TP3</span><span class="tp-value tp-green">+${plan["profit_tp3"]}</span></div>
                        <div class="tp-row"><span class="tp-label">Max Loss</span><span class="tp-value tp-red">-${plan["loss_sl"]}</span></div>
                        <div class="tp-row"><span class="tp-label">Worth it?</span><span class="tp-value" style="color:{rr_color};">{"✅ YES" if plan["rr_ratio"] >= 1.5 else "⚠️ MARGINAL" if plan["rr_ratio"] >= 1 else "❌ NO"}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("⏳ Sinyal HOLD — Tunggu sinyal BUY/SELL yang lebih jelas.")
        elif df is not None:
            st.warning(f"Trading Plan dikunci — keputusan AI: {decision}. {decision_reason}")
    
    # AI Reasoning — rendered in the right column below AI Signal
    if df is not None:
        with reasoning_container:
            reasoning_points, reasoning_conclusion, reasoning_color = generate_ai_reasoning(
                signal, decision, decision_reason, score_detail, indicators, supports, resistances
            )
    
            st.markdown("---")
            st.markdown('<p class="section-header">🧠 AI Reasoning</p>', unsafe_allow_html=True)
    
            points_html = "".join([
                f'<li style="color:#c9d1d9; font-size:13px; margin-bottom:6px; line-height:1.6;">{p}</li>'
                for p in reasoning_points
            ])
    
            st.markdown(f"""
            <div style="background:#161b22; border:1px solid #30363d; border-left:4px solid {reasoning_color}; border-radius:8px; padding:18px;">
                <ul style="margin:0 0 12px 0; padding-left:18px;">
                    {points_html}
                </ul>
                <p style="color:{reasoning_color}; font-size:14px; font-weight:700; margin:0; padding-top:10px; border-top:1px solid #21262d;">
                    {reasoning_conclusion}
                </p>
            </div>
            """, unsafe_allow_html=True)
    
# ─── TAB 2: MULTI TIMEFRAME ───
with tab2:
    st.markdown('<p class="section-header">🕐 Multi-Timeframe Analysis</p>', unsafe_allow_html=True)
    st.markdown(f"<p style='color:#8b949e; font-size:13px;'>Analisis {symbol} dari 3 timeframe sekaligus</p>", unsafe_allow_html=True)

    with st.spinner("Menganalisis semua timeframe..."):
        mtf_results = multi_timeframe_analysis(symbol)

    buy_count = sum(1 for _, s, _, _ in mtf_results if s == "BUY")
    sell_count = sum(1 for _, s, _, _ in mtf_results if s == "SELL")
    hold_count = sum(1 for _, s, _, _ in mtf_results if s == "HOLD")

    if buy_count >= 2: consensus_color = "#3fb950"; consensus_emoji = "🟢"; consensus_text = "STRONG BUY" if buy_count == 3 else "BUY"
    elif sell_count >= 2: consensus_color = "#f85149"; consensus_emoji = "🔴"; consensus_text = "STRONG SELL" if sell_count == 3 else "SELL"
    else: consensus_color = "#388bfd"; consensus_emoji = "🔵"; consensus_text = "MIXED / HOLD"

    st.markdown(f"""
    <div style="background:#161b22; border:1px solid #30363d; border-radius:12px; padding:24px; text-align:center; margin-bottom:24px;">
        <p style="color:#8b949e; font-size:12px; text-transform:uppercase; letter-spacing:2px; margin:0;">MTF Consensus</p>
        <p style="font-size:36px; font-weight:800; color:{consensus_color}; margin:8px 0;">{consensus_emoji} {consensus_text}</p>
        <p style="color:#8b949e; font-size:12px;">{buy_count} BUY · {sell_count} SELL · {hold_count} HOLD</p>
    </div>
    """, unsafe_allow_html=True)

    col_mtf1, col_mtf2, col_mtf3 = st.columns(3)
    cols = [col_mtf1, col_mtf2, col_mtf3]
    for i, (label, sig, reason, confidence) in enumerate(mtf_results):
        color = "#3fb950" if sig == "BUY" else "#f85149" if sig == "SELL" else "#388bfd"
        emoji = "🟢" if sig == "BUY" else "🔴" if sig == "SELL" else "🔵"
        with cols[i]:
            st.markdown(f"""
            <div class="mtf-card mtf-{sig.lower()}">
                <p style="color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin:0;">{label}</p>
                <p style="font-size:22px; font-weight:800; color:{color}; margin:8px 0;">{emoji} {sig}</p>
                <div class="strength-bar-container"><div class="strength-bar-fill" style="width:{confidence}%; background:{color};"></div></div>
                <p style="color:#8b949e; font-size:11px; margin:4px 0;">Confidence: {confidence}%</p>
                <p style="color:#8b949e; font-size:11px; margin:0;">{reason}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:16px;">
        <p style="color:#8b949e; font-size:12px; margin:0;">
        💡 <strong style="color:#e6edf3;">Cara baca MTF:</strong> Kalau 1H + 4H + 1D semua searah → sinyal sangat kuat.
        Konfirmasi minimal 2 dari 3 timeframe sebelum entry.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ─── TAB 3: MARKET WATCH ───
with tab3:
    st.markdown('<p class="section-header">🌍 Market Watch — Forex & Gold</p>', unsafe_allow_html=True)

    with st.spinner("Loading market data..."):
        all_prices = get_all_prices(DEFAULT_PAIRS)

    if all_prices:
        col_mw1, col_mw2 = st.columns(2)
        for i, p in enumerate(all_prices):
            change_color = "#3fb950" if p["change"] >= 0 else "#f85149"
            arrow = "▲" if p["change"] >= 0 else "▼"
            fmt = f",.{p['digits']}f"
            card = f"""
            <div class="pair-card">
                <div>
                    <span style="color:#e6edf3; font-weight:700; font-size:15px;">{p["symbol"]}</span>
                </div>
                <div style="text-align:center;">
                    <span style="color:#3fb950; font-size:13px;">{p["bid"]:{fmt}}</span>
                    <span style="color:#8b949e; font-size:11px;"> / </span>
                    <span style="color:#f85149; font-size:13px;">{p["ask"]:{fmt}}</span>
                </div>
                <div style="text-align:right;">
                    <span style="color:{change_color}; font-size:13px; font-weight:700;">{arrow} {abs(p["change"]):.4f}%</span>
                </div>
            </div>
            """
            if i % 2 == 0:
                with col_mw1:
                    st.markdown(card, unsafe_allow_html=True)
            else:
                with col_mw2:
                    st.markdown(card, unsafe_allow_html=True)

# ─── TAB 4: BACKTESTING ───
with tab4:
    st.markdown('<p class="section-header">🧪 Backtesting Engine</p>', unsafe_allow_html=True)
    st.markdown("<p style='color:#8b949e; font-size:13px;'>Simulasi signal engine di data historis — lihat win rate, profit/loss, dan RR ratio.</p>", unsafe_allow_html=True)

    col_bt1, col_bt2, col_bt3 = st.columns(3)
    with col_bt1:
        bt_symbol = st.text_input("Symbol", value=symbol)
    with col_bt2:
        bt_interval = st.selectbox("Timeframe", [
            ("1 Hour", "1h"), ("4 Hours", "4h"), ("1 Day", "1d")
        ], format_func=lambda x: x[0], index=0)
        bt_interval_val = bt_interval[1]
    with col_bt3:
        bt_candles = st.slider("Candles (data historis)", 100, 1000, 500)

    bt_modal = st.number_input("💵 Modal per Trade (USD)", min_value=1.0, value=100.0, step=10.0)

    if st.button("▶️ Jalankan Backtest", use_container_width=True):
        with st.spinner("Mengambil data historis dan menjalankan simulasi..."):
            df_bt = get_mt5_klines(bt_symbol, bt_interval_val, bt_candles)

        if df_bt is None or len(df_bt) < 100:
            st.error("Data tidak cukup untuk backtest. Coba tambah jumlah candles.")
        else:
            trades     = []
            min_window = 50

            for i in range(min_window, len(df_bt) - 1):
                df_slice = df_bt.iloc[:i+1].copy()
                signal_bt, _, _, _, confidence_bt, score_bt = calculate_signal(df_slice)

                if signal_bt == "HOLD":
                    continue
                if score_bt["total"] < 55:
                    continue

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

                outcome    = "OPEN"
                exit_price = None
                exit_candle = None
                lookahead  = min(10, len(df_bt) - i - 1)

                for j in range(1, lookahead + 1):
                    future_high = df_bt["high"].iloc[i + j]
                    future_low  = df_bt["low"].iloc[i + j]

                    if signal_bt == "BUY":
                        if future_low <= sl_bt:
                            outcome = "LOSS"; exit_price = sl_bt; exit_candle = j; break
                        elif future_high >= tp1_bt:
                            outcome = "WIN";  exit_price = tp1_bt; exit_candle = j; break
                    else:
                        if future_high >= sl_bt:
                            outcome = "LOSS"; exit_price = sl_bt; exit_candle = j; break
                        elif future_low <= tp1_bt:
                            outcome = "WIN";  exit_price = tp1_bt; exit_candle = j; break

                if outcome == "OPEN":
                    continue

                # Auto-detect pip size berdasarkan harga
                # Forex (EURUSD dll): harga < 100 → pip = 0.00010
                # Gold (XAUUSD):      harga > 100 → pip = 0.10
                # Indices/Oil:        fallback ke persentase
                if entry_price < 10:
                    pip_size  = 0.00010   # JPY pairs & crypto-like
                elif entry_price < 100:
                    pip_size  = 0.00010   # Forex majors
                else:
                    pip_size  = 0.10      # Gold, Silver, Indices

                sl_pips  = abs(entry_price - sl_bt) / pip_size
                tp_pips  = abs(tp1_bt - entry_price) / pip_size

                # Lot size: untuk gold, 1 lot = 100 oz, mini lot = 10 oz
                # Estimasi lot dari modal: modal / (entry * 10) untuk gold
                if entry_price > 100:
                    lot_size = round(bt_modal / (entry_price * 10), 4)
                else:
                    lot_size = round(bt_modal / (entry_price * 1000), 4)

                if outcome == "WIN":
                    pnl = round(tp_pips * lot_size, 2)
                else:
                    pnl = round(-sl_pips * lot_size, 2)

                rr_actual = round(tp_pips / sl_pips, 2) if sl_pips > 0 else 0

                trades.append({
                    "timestamp":   str(df_bt["timestamp"].iloc[i])[:16],
                    "signal":      signal_bt,
                    "entry":       round(entry_price, 5),
                    "exit":        round(exit_price, 5),
                    "outcome":     outcome,
                    "pnl":         pnl,
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
                avg_win      = round(sum(t["pnl"] for t in wins)   / len(wins),   2) if wins   else 0
                avg_loss     = round(sum(t["pnl"] for t in losses) / len(losses), 2) if losses else 0
                avg_rr       = round(sum(t["rr"]  for t in trades) / total_trades, 2)
                avg_score    = round(sum(t["score"] for t in trades) / total_trades, 1)

                pnl_color = "#3fb950" if total_pnl >= 0 else "#f85149"
                wr_color  = "#3fb950" if win_rate >= 55 else "#f0883e" if win_rate >= 45 else "#f85149"

                st.markdown("<br>", unsafe_allow_html=True)
                c1, c2, c3, c4, c5 = st.columns(5)
                for col, label, val, color in [
                    (c1, "Total Trade", str(total_trades), "#e6edf3"),
                    (c2, "Win Rate",    f"{win_rate}%",    wr_color),
                    (c3, "Total P&L",   f"{'+'if total_pnl>=0 else ''}{total_pnl}$", pnl_color),
                    (c4, "Avg RR",      f"1:{avg_rr}",     "#388bfd"),
                    (c5, "Avg Score",   f"{avg_score}/100","#d2a8ff"),
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
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Avg Profit</span><span style="color:#3fb950; font-weight:700;">+${avg_win}</span></div>
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Total Profit</span><span style="color:#3fb950; font-weight:700;">+${round(sum(t["pnl"] for t in wins),2)}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_wl2:
                    st.markdown(f"""
                    <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:14px;">
                        <p style="color:#8b949e; font-size:11px; text-transform:uppercase; margin:0 0 10px 0;">Loss Summary</p>
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Total Loss</span><span style="color:#f85149; font-weight:700;">{len(losses)} trade</span></div>
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Avg Loss</span><span style="color:#f85149; font-weight:700;">${avg_loss}</span></div>
                        <div style="display:flex; justify-content:space-between; padding:4px 0;"><span style="color:#8b949e; font-size:12px;">Total Loss</span><span style="color:#f85149; font-weight:700;">${round(sum(t["pnl"] for t in losses),2)}</span></div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<p class="section-header">Trade History</p>', unsafe_allow_html=True)
                for t in reversed(trades[-30:]):
                    oc = "#3fb950" if t["outcome"] == "WIN" else "#f85149"
                    sc = "#3fb950" if t["signal"]  == "BUY" else "#f85149"
                    ps = "+" if t["pnl"] >= 0 else ""
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center;
                         padding:8px 12px; margin:3px 0; background:#161b22;
                         border:1px solid #30363d; border-radius:6px; font-size:12px;">
                        <span style="color:#8b949e; width:130px;">{t["timestamp"]}</span>
                        <span style="color:{sc}; font-weight:700; width:45px;">{t["signal"]}</span>
                        <span style="color:#e6edf3; width:90px;">Entry: {t["entry"]:.5f}</span>
                        <span style="color:#e6edf3; width:90px;">Exit: {t["exit"]:.5f}</span>
                        <span style="color:#8b949e; width:60px;">RR 1:{t["rr"]}</span>
                        <span style="color:#8b949e; width:60px;">Score: {t["score"]}</span>
                        <span style="color:{oc}; font-weight:700; width:60px;">{t["outcome"]}</span>
                        <span style="color:{oc}; font-weight:700;">{ps}{t["pnl"]}$</span>
                    </div>
                    """, unsafe_allow_html=True)

# ─── TAB 5: SETTINGS ───
with tab5:
    st.markdown('<p class="section-header">⚙️ Settings</p>', unsafe_allow_html=True)
    auto_refresh = st.checkbox("🔄 Auto Refresh setiap 30 detik", value=st.session_state["auto_refresh_mt5"])
    st.session_state["auto_refresh_mt5"] = auto_refresh
    if auto_refresh:
        st.success("✅ Auto refresh aktif")
    else:
        st.info("ℹ️ Auto refresh nonaktif")

    st.markdown("---")
    account = mt5.account_info()
    if account:
        st.markdown(f"""
        <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:16px;">
            <p style="color:#8b949e; font-size:12px; margin:0;">
            👤 <strong style="color:#e6edf3;">{account.name}</strong><br>
            🏦 Server: <span style="color:#e6edf3;">{account.server}</span><br>
            💰 Balance: <span style="color:#3fb950;">${account.balance:,.2f} {account.currency}</span><br>
            📊 Leverage: <span style="color:#e6edf3;">1:{account.leverage}</span><br>
            🔗 Status: <span style="color:#3fb950;">🟢 Connected</span><br>
            Ⓥ Version: <span style="color:#e6edf3;">v2.4.3 (AI Reasoning)</span><br>
            </p>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  AUTO REFRESH
# ─────────────────────────────────────────────
if st.session_state.get("auto_refresh_mt5"):
    time.sleep(30)
    st.rerun()

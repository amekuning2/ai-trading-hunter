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
        tick = mt5.symbol_info_tick(symbol)
        info = mt5.symbol_info(symbol)
        if tick is None or info is None:
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
#  AI SIGNAL ENGINE
# ─────────────────────────────────────────────
def calculate_signal(df):
    if df is None or len(df) < 50:
        return "HOLD", "Data tidak cukup", {}, {}, 0

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    rsi = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]
    macd_ind = ta.trend.MACD(close)
    macd = macd_ind.macd().iloc[-1]
    macd_signal_val = macd_ind.macd_signal().iloc[-1]
    macd_hist = macd_ind.macd_diff().iloc[-1]
    bb = ta.volatility.BollingerBands(close, window=20)
    bb_upper = bb.bollinger_hband().iloc[-1]
    bb_lower = bb.bollinger_lband().iloc[-1]
    current_price = close.iloc[-1]
    ema20 = ta.trend.EMAIndicator(close, window=20).ema_indicator().iloc[-1]
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]
    ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator().iloc[-1] if len(close) >= 200 else ema50
    stoch = ta.momentum.StochasticOscillator(high, low, close)
    stoch_k = stoch.stoch().iloc[-1]
    stoch_d = stoch.stoch_signal().iloc[-1]
    avg_vol = volume.rolling(20).mean().iloc[-1]
    curr_vol = volume.iloc[-1]
    vol_surge = curr_vol > avg_vol * 1.5

    buy_score = 0
    sell_score = 0
    signals = {}

    if rsi < 30: buy_score += 2; signals["RSI"] = ("OVERSOLD", "green")
    elif rsi < 45: buy_score += 1; signals["RSI"] = ("BULLISH", "green")
    elif rsi > 70: sell_score += 2; signals["RSI"] = ("OVERBOUGHT", "red")
    elif rsi > 55: sell_score += 1; signals["RSI"] = ("BEARISH", "red")
    else: signals["RSI"] = ("NEUTRAL", "neutral")

    if macd > macd_signal_val and macd_hist > 0: buy_score += 2; signals["MACD"] = ("BULLISH CROSS", "green")
    elif macd < macd_signal_val and macd_hist < 0: sell_score += 2; signals["MACD"] = ("BEARISH CROSS", "red")
    else: signals["MACD"] = ("NEUTRAL", "neutral")

    if current_price < bb_lower: buy_score += 2; signals["BB"] = ("BELOW LOWER", "green")
    elif current_price > bb_upper: sell_score += 2; signals["BB"] = ("ABOVE UPPER", "red")
    else: signals["BB"] = ("WITHIN BAND", "neutral")

    if ema20 > ema50 > ema200: buy_score += 2; signals["EMA"] = ("STRONG UPTREND", "green")
    elif ema20 > ema50: buy_score += 1; signals["EMA"] = ("UPTREND", "green")
    elif ema20 < ema50 < ema200: sell_score += 2; signals["EMA"] = ("STRONG DOWNTREND", "red")
    else: sell_score += 1; signals["EMA"] = ("DOWNTREND", "red")

    if stoch_k < 20 and stoch_k > stoch_d: buy_score += 2; signals["STOCH"] = ("OVERSOLD CROSS", "green")
    elif stoch_k > 80 and stoch_k < stoch_d: sell_score += 2; signals["STOCH"] = ("OVERBOUGHT CROSS", "red")
    else: signals["STOCH"] = ("NEUTRAL", "neutral")

    if vol_surge:
        signals["VOL"] = ("SURGE ⚡", "green")
        if buy_score > sell_score: buy_score += 1
        else: sell_score += 1
    else: signals["VOL"] = ("NORMAL", "neutral")

    total_score = buy_score + sell_score
    strength = int((max(buy_score, sell_score) / max(total_score, 1)) * 100)

    indicators = {
        "RSI": round(rsi, 2),
        "MACD": round(macd, 6),
        "Stoch %K": round(stoch_k, 2),
        "EMA20": round(ema20, 5),
        "EMA50": round(ema50, 5),
        "EMA200": round(ema200, 5),
    }

    if buy_score >= 5: return "BUY", f"Strong buy — {buy_score} bullish indicators", signals, indicators, strength
    elif sell_score >= 5: return "SELL", f"Strong sell — {sell_score} bearish indicators", signals, indicators, strength
    elif buy_score > sell_score: return "BUY", f"Weak buy — {buy_score} vs {sell_score} indicators", signals, indicators, strength
    elif sell_score > buy_score: return "SELL", f"Weak sell — {sell_score} vs {buy_score} indicators", signals, indicators, strength
    else: return "HOLD", "Mixed signals — market indecisive", signals, indicators, strength

# ─────────────────────────────────────────────
#  MULTI TIMEFRAME
# ─────────────────────────────────────────────
def multi_timeframe_analysis(symbol):
    timeframes = [("1H", "1h", 100), ("4H", "4h", 100), ("1D", "1d", 200)]
    results = []
    for label, tf, limit in timeframes:
        df = get_mt5_klines(symbol, tf, limit)
        signal, reason, _, _, strength = calculate_signal(df)
        results.append((label, signal, reason, strength))
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
    atr = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range().iloc[-1]

    if signal == "BUY":
        entry = round(current_price, 5)
        sl = round(entry - (atr * 1.5), 5)
        tp1 = round(entry + (atr * 2), 5)
        tp2 = round(entry + (atr * 3.5), 5)
        if supports: sl = min(sl, round(supports[0] * 0.9998, 5))
        if resistances: tp1 = min(tp1, round(resistances[0] * 0.9999, 5))
    else:
        entry = round(current_price, 5)
        sl = round(entry + (atr * 1.5), 5)
        tp1 = round(entry - (atr * 2), 5)
        tp2 = round(entry - (atr * 3.5), 5)
        if resistances: sl = max(sl, round(resistances[0] * 1.0002, 5))
        if supports: tp1 = max(tp1, round(supports[0] * 1.0001, 5))

    sl_pct = abs((sl - entry) / entry * 100)
    tp1_pct = abs((tp1 - entry) / entry * 100)
    tp2_pct = abs((tp2 - entry) / entry * 100)
    rr_ratio = round(tp1_pct / sl_pct, 2) if sl_pct > 0 else 0

    modal_leveraged = modal_usd * leverage
    pip_value = atr * 10
    profit_tp1 = round(tp1_pct / 100 * modal_leveraged, 2)
    profit_tp2 = round(tp2_pct / 100 * modal_leveraged, 2)
    loss_sl = round(sl_pct / 100 * modal_leveraged, 2)

    return {
        "signal": signal, "entry": entry, "sl": sl,
        "tp1": tp1, "tp2": tp2,
        "sl_pct": round(sl_pct, 4), "tp1_pct": round(tp1_pct, 4), "tp2_pct": round(tp2_pct, 4),
        "rr_ratio": rr_ratio, "modal": modal_usd, "leverage": leverage,
        "profit_tp1": profit_tp1, "profit_tp2": profit_tp2, "loss_sl": loss_sl,
        "atr": round(atr, 5),
    }

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

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🕐 Multi-Timeframe", "🌍 Market Watch", "⚙️ Settings"])

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

    with col_signal:
        st.markdown('<p class="section-header">AI Signal</p>', unsafe_allow_html=True)
        if df is not None:
            signal, reason, signals, indicators, strength = calculate_signal(df)
            signal_class = f"signal-{signal.lower()}"
            signal_emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🔵"
            strength_color = "#3fb950" if signal == "BUY" else "#f85149" if signal == "SELL" else "#388bfd"

            st.markdown(f"""
            <div class="{signal_class}">
                <p class="signal-text">{signal_emoji} {signal}</p>
                <p class="signal-reason">{reason}</p>
                <div class="strength-bar-container">
                    <div class="strength-bar-fill" style="width:{strength}%; background:{strength_color};"></div>
                </div>
                <p style="color:#8b949e; font-size:11px;">Strength: {strength}%</p>
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

    # Trading Plan
    st.markdown("---")
    st.markdown('<p class="section-header">📋 Trading Plan</p>', unsafe_allow_html=True)

    col_m1, col_m2 = st.columns([1, 1])
    with col_m1:
        modal = st.number_input("💵 Modal (USD)", min_value=1.0, value=100.0, step=10.0, format="%.2f")
    with col_m2:
        leverage = st.selectbox("⚡ Leverage", [1, 10, 50, 100, 200, 500], index=3)

    if df is not None:
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
                    <div class="tp-row"><span class="tp-label">Stop Loss</span><span class="tp-value tp-red">{plan["sl"]:.5f} (-{plan["sl_pct"]}%)</span></div>
                    <div class="tp-row"><span class="tp-label">TP 1</span><span class="tp-value tp-green">{plan["tp1"]:.5f} (+{plan["tp1_pct"]}%)</span></div>
                    <div class="tp-row"><span class="tp-label">TP 2</span><span class="tp-value tp-green">{plan["tp2"]:.5f} (+{plan["tp2_pct"]}%)</span></div>
                </div>
                """, unsafe_allow_html=True)
            with col_p2:
                st.markdown(f"""
                <div class="tp-card">
                    <p style="color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin:0 0 12px 0;">Risk & Reward</p>
                    <div class="tp-row"><span class="tp-label">R/R Ratio</span><span class="tp-value" style="color:{rr_color};">1 : {plan["rr_ratio"]}</span></div>
                    <div class="tp-row"><span class="tp-label">ATR</span><span class="tp-value">{plan["atr"]:.5f}</span></div>
                    <div class="tp-row"><span class="tp-label">Modal</span><span class="tp-value">${plan["modal"]:,.2f}</span></div>
                    <div class="tp-row"><span class="tp-label">Leverage</span><span class="tp-value">1:{plan["leverage"]}</span></div>
                </div>
                """, unsafe_allow_html=True)
            with col_p3:
                st.markdown(f"""
                <div class="tp-card">
                    <p style="color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin:0 0 12px 0;">Estimasi P&L</p>
                    <div class="tp-row"><span class="tp-label">Profit TP1</span><span class="tp-value tp-green">+${plan["profit_tp1"]}</span></div>
                    <div class="tp-row"><span class="tp-label">Profit TP2</span><span class="tp-value tp-green">+${plan["profit_tp2"]}</span></div>
                    <div class="tp-row"><span class="tp-label">Max Loss</span><span class="tp-value tp-red">-${plan["loss_sl"]}</span></div>
                    <div class="tp-row"><span class="tp-label">Worth it?</span><span class="tp-value" style="color:{rr_color};">{"✅ YES" if plan["rr_ratio"] >= 1.5 else "⚠️ MARGINAL" if plan["rr_ratio"] >= 1 else "❌ NO"}</span></div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("⏳ Sinyal HOLD — Tunggu sinyal BUY/SELL yang lebih jelas.")

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
    for i, (label, sig, reason, strength) in enumerate(mtf_results):
        color = "#3fb950" if sig == "BUY" else "#f85149" if sig == "SELL" else "#388bfd"
        emoji = "🟢" if sig == "BUY" else "🔴" if sig == "SELL" else "🔵"
        with cols[i]:
            st.markdown(f"""
            <div class="mtf-card mtf-{sig.lower()}">
                <p style="color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin:0;">{label}</p>
                <p style="font-size:22px; font-weight:800; color:{color}; margin:8px 0;">{emoji} {sig}</p>
                <div class="strength-bar-container"><div class="strength-bar-fill" style="width:{strength}%; background:{color};"></div></div>
                <p style="color:#8b949e; font-size:11px; margin:4px 0;">Strength: {strength}%</p>
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

# ─── TAB 4: SETTINGS ───
with tab4:
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
            Ⓥ Version: <span style="color:#e6edf3;">v2.3.5 (Secure)</span><br>
            </p>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  AUTO REFRESH
# ─────────────────────────────────────────────
if st.session_state.get("auto_refresh_mt5"):
    time.sleep(30)
    st.rerun()
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from binance.client import Client
from binance.exceptions import BinanceAPIException
import ta
import time
from datetime import datetime
import os

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
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
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  BINANCE CLIENT
# ─────────────────────────────────────────────
@st.cache_resource
def get_client(api_key, api_secret):
    return Client(api_key, api_secret)

# ─────────────────────────────────────────────
#  DATA FUNCTIONS
# ─────────────────────────────────────────────
@st.cache_data(ttl=30)
def get_price(symbol, api_key, api_secret):
    try:
        client = get_client(api_key, api_secret)
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
        return None

@st.cache_data(ttl=60)
def get_klines(symbol, interval, limit, api_key, api_secret):
    try:
        client = get_client(api_key, api_secret)
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
def get_top_gainers(api_key, api_secret, n=10):
    try:
        client = get_client(api_key, api_secret)
        tickers = client.get_ticker()
        usdt_pairs = [t for t in tickers if t["symbol"].endswith("USDT") and float(t["quoteVolume"]) > 1_000_000]
        sorted_gainers = sorted(usdt_pairs, key=lambda x: float(x["priceChangePercent"]), reverse=True)
        return sorted_gainers[:n]
    except:
        return []

# ─────────────────────────────────────────────
#  AI SIGNAL ENGINE
# ─────────────────────────────────────────────
def calculate_signal(df):
    if df is None or len(df) < 50:
        return "HOLD", "Data tidak cukup", {}

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # RSI
    rsi = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]

    # MACD
    macd_ind = ta.trend.MACD(close)
    macd = macd_ind.macd().iloc[-1]
    macd_signal = macd_ind.macd_signal().iloc[-1]
    macd_hist = macd_ind.macd_diff().iloc[-1]

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close, window=20)
    bb_upper = bb.bollinger_hband().iloc[-1]
    bb_lower = bb.bollinger_lband().iloc[-1]
    bb_mid = bb.bollinger_mavg().iloc[-1]
    current_price = close.iloc[-1]

    # EMA
    ema20 = ta.trend.EMAIndicator(close, window=20).ema_indicator().iloc[-1]
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]

    # Volume trend
    avg_vol = volume.rolling(20).mean().iloc[-1]
    curr_vol = volume.iloc[-1]
    vol_surge = curr_vol > avg_vol * 1.5

    # Scoring system
    buy_score = 0
    sell_score = 0
    signals = {}

    # RSI
    if rsi < 30:
        buy_score += 2
        signals["RSI"] = ("OVERSOLD", "green")
    elif rsi < 45:
        buy_score += 1
        signals["RSI"] = ("BULLISH", "green")
    elif rsi > 70:
        sell_score += 2
        signals["RSI"] = ("OVERBOUGHT", "red")
    elif rsi > 55:
        sell_score += 1
        signals["RSI"] = ("BEARISH", "red")
    else:
        signals["RSI"] = ("NEUTRAL", "neutral")

    # MACD
    if macd > macd_signal and macd_hist > 0:
        buy_score += 2
        signals["MACD"] = ("BULLISH CROSS", "green")
    elif macd < macd_signal and macd_hist < 0:
        sell_score += 2
        signals["MACD"] = ("BEARISH CROSS", "red")
    else:
        signals["MACD"] = ("NEUTRAL", "neutral")

    # Bollinger
    if current_price < bb_lower:
        buy_score += 2
        signals["BB"] = ("BELOW LOWER", "green")
    elif current_price > bb_upper:
        sell_score += 2
        signals["BB"] = ("ABOVE UPPER", "red")
    else:
        signals["BB"] = ("WITHIN BAND", "neutral")

    # EMA trend
    if ema20 > ema50:
        buy_score += 1
        signals["EMA"] = ("UPTREND", "green")
    else:
        sell_score += 1
        signals["EMA"] = ("DOWNTREND", "red")

    # Stochastic
    stoch = ta.momentum.StochasticOscillator(high, low, close)
    stoch_k = stoch.stoch().iloc[-1]
    stoch_d = stoch.stoch_signal().iloc[-1]
    if stoch_k < 20 and stoch_k > stoch_d:
        buy_score += 2
        signals["STOCH"] = ("OVERSOLD CROSS", "green")
    elif stoch_k > 80 and stoch_k < stoch_d:
        sell_score += 2
        signals["STOCH"] = ("OVERBOUGHT CROSS", "red")
    else:
        signals["STOCH"] = ("NEUTRAL", "neutral")

    # EMA200
    if len(close) >= 200:
        ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator().iloc[-1]
        if ema20 > ema50 > ema200:
            buy_score += 1
            signals["EMA"] = ("STRONG UPTREND", "green")
        elif ema20 < ema50 < ema200:
            sell_score += 1
            signals["EMA"] = ("STRONG DOWNTREND", "red")
    else:
        ema200 = ema50

    # Volume surge boosts signal
    if vol_surge:
        signals["VOL"] = ("SURGE ⚡", "green")
        if buy_score > sell_score:
            buy_score += 1
        else:
            sell_score += 1
    else:
        signals["VOL"] = ("NORMAL", "neutral")

    # Strength
    total_score = buy_score + sell_score
    strength = int((max(buy_score, sell_score) / max(total_score, 1)) * 100)

    # Decision
    indicators = {
        "RSI": round(rsi, 2),
        "MACD": round(macd, 6),
        "Stoch %K": round(stoch_k, 2),
        "BB_pos": round((current_price - bb_lower) / max(bb_upper - bb_lower, 0.0001) * 100, 1),
        "EMA20": round(ema20, 4),
        "EMA50": round(ema50, 4),
        "EMA200": round(ema200, 4),
    }

    if buy_score >= 5:
        reason = f"Strong buy signal — {buy_score} bullish indicators"
        return "BUY", reason, signals, indicators, strength
    elif sell_score >= 5:
        reason = f"Strong sell signal — {sell_score} bearish indicators"
        return "SELL", reason, signals, indicators, strength
    elif buy_score > sell_score:
        reason = f"Weak buy signal — {buy_score} vs {sell_score} indicators"
        return "BUY", reason, signals, indicators, strength
    elif sell_score > buy_score:
        reason = f"Weak sell signal — {sell_score} vs {buy_score} indicators"
        return "SELL", reason, signals, indicators, strength
    else:
        reason = "Mixed signals — market indecisive"
        return "HOLD", reason, signals, indicators, strength

# ─────────────────────────────────────────────
#  MULTI TIMEFRAME ANALYSIS
# ─────────────────────────────────────────────
def multi_timeframe_analysis(symbol, api_key, api_secret):
    timeframes = [("1H", "1h", 100), ("4H", "4h", 100), ("1D", "1d", 200)]
    results = []
    for label, interval, limit in timeframes:
        df = get_klines(symbol, interval, limit, api_key, api_secret)
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
    resistance_levels = sorted(set([round(r, 4) for r in resistance_levels if r > current_price]))[:n]
    support_levels = sorted(set([round(s, 4) for s in support_levels if s < current_price]), reverse=True)[:n]
    return resistance_levels, support_levels

# ─────────────────────────────────────────────
#  CHART
# ─────────────────────────────────────────────
def build_chart(df, symbol, resistances=[], supports=[]):
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2]
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df["timestamp"],
        open=df["open"], high=df["high"],
        low=df["low"], close=df["close"],
        name="Price",
        increasing_line_color="#3fb950",
        decreasing_line_color="#f85149",
        increasing_fillcolor="#0d2b1d",
        decreasing_fillcolor="#2d1b1b",
    ), row=1, col=1)

    # EMA lines
    ema20 = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    ema50 = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    fig.add_trace(go.Scatter(x=df["timestamp"], y=ema20, name="EMA20",
        line=dict(color="#f0883e", width=1.5, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=ema50, name="EMA50",
        line=dict(color="#388bfd", width=1.5, dash="dot")), row=1, col=1)

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(df["close"], window=20)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=bb.bollinger_hband(),
        name="BB Upper", line=dict(color="#8b949e", width=1, dash="dash"), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=bb.bollinger_lband(),
        name="BB Lower", line=dict(color="#8b949e", width=1, dash="dash"),
        fill="tonexty", fillcolor="rgba(139,148,158,0.05)", showlegend=False), row=1, col=1)

    # Support & Resistance lines
    for r in resistances:
        fig.add_hline(y=r, line_dash="dash", line_color="#f85149", opacity=0.6, row=1, col=1,
                      annotation_text=f"R {r:,.4f}", annotation_position="right")
    for s in supports:
        fig.add_hline(y=s, line_dash="dash", line_color="#3fb950", opacity=0.6, row=1, col=1,
                      annotation_text=f"S {s:,.4f}", annotation_position="right")

    # Volume
    colors = ["#3fb950" if df["close"].iloc[i] >= df["open"].iloc[i] else "#f85149"
              for i in range(len(df))]
    fig.add_trace(go.Bar(x=df["timestamp"], y=df["volume"], name="Volume",
        marker_color=colors, opacity=0.7), row=2, col=1)

    # RSI
    rsi = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    fig.add_trace(go.Scatter(x=df["timestamp"], y=rsi, name="RSI",
        line=dict(color="#d2a8ff", width=1.5)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#f85149", opacity=0.5, row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#3fb950", opacity=0.5, row=3, col=1)

    fig.update_layout(
        plot_bgcolor="#0d1117",
        paper_bgcolor="#0d1117",
        font=dict(color="#8b949e", size=11),
        height=600,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        xaxis_rangeslider_visible=False,
    )
    fig.update_yaxes(gridcolor="#21262d", zerolinecolor="#21262d")
    fig.update_xaxes(gridcolor="#21262d", zerolinecolor="#21262d")

    return fig

# ─────────────────────────────────────────────
#  PRICE ALERT
# ─────────────────────────────────────────────
def send_ntfy(topic, title, message, priority="high"):
    try:
        import requests
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode("utf-8"),
            headers={"Title": title, "Priority": priority, "Tags": "chart_increasing"}
        )
    except:
        pass

def check_alert(current_price, alert_price, alert_type, alert_symbol, ntfy_topic):
    if alert_price <= 0 or not ntfy_topic:
        return
    if alert_type == "Above" and current_price >= alert_price:
        send_ntfy(ntfy_topic, f"🚨 {alert_symbol} Price Alert!", f"{alert_symbol} udah tembus ${current_price:,.4f} (target: ${alert_price:,.4f})")
    elif alert_type == "Below" and current_price <= alert_price:
        send_ntfy(ntfy_topic, f"🚨 {alert_symbol} Price Alert!", f"{alert_symbol} udah turun ke ${current_price:,.4f} (target: ${alert_price:,.4f})")

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ AI Trading Dashboard")
    st.markdown("---")

    st.markdown('<p class="section-header">API Configuration</p>', unsafe_allow_html=True)
    api_key = "gXdeG9XPTBWlgG61uQxgMPojWqFTiQo9pCBQlvIqt1cKDVC9WlTlxlc1D1sJHHLt"
    api_secret = "SWpV7Y77IhF0Da4plubMVOMILnpWY9Qd2AOLi2D1Qp4oBe3tuguXUkjPdQ527UkS"
    
    st.markdown("---")
    st.markdown('<p class="section-header">Trading Pair</p>', unsafe_allow_html=True)

    DEFAULT_PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
    symbol = st.selectbox("Select Pair", DEFAULT_PAIRS)

    custom = st.text_input("Or custom pair", placeholder="e.g. ADAUSDT")
    if custom:
        symbol = custom.upper()

    st.markdown("---")
    st.markdown('<p class="section-header">Chart Settings</p>', unsafe_allow_html=True)

    interval = st.selectbox("Timeframe", [
        ("1 Minute", "1m"), ("5 Minutes", "5m"), ("15 Minutes", "15m"),
        ("1 Hour", "1h"), ("4 Hours", "4h"), ("1 Day", "1d")
    ], format_func=lambda x: x[0], index=3)
    interval_val = interval[1]

    candles = st.slider("Candles", 50, 500, 200)

    auto_refresh = st.checkbox("Auto Refresh (30s)", value=False)

    st.markdown("---")
    st.markdown('<p class="section-header">Price Alert</p>', unsafe_allow_html=True)
    ntfy_topic = st.text_input("ntfy Topic", placeholder="trading-amekuning")
    alert_symbol = st.selectbox("Alert Pair", ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"])
    alert_price = st.number_input("Target Price (USD)", min_value=0.0, value=0.0, format="%.4f")
    alert_type = st.radio("Alert Type", ["Above", "Below"])
    alert_active = st.checkbox("Activate Alert", value=False)

    st.markdown("---")
    st.caption("v2.0 · Binance · Multi-TF")

# ─────────────────────────────────────────────
#  MAIN CONTENT
# ─────────────────────────────────────────────
if not api_key or not api_secret:
    st.markdown("""
    <div style="text-align:center; padding: 80px 20px;">
        <div style="font-size:48px; margin-bottom:16px;">📈</div>
        <h2 style="color:#e6edf3; margin-bottom:8px;">AI Trading Dashboard</h2>
        <p style="color:#8b949e;">Masukkan Binance API Key di sidebar untuk mulai</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Mobile-friendly pair selector
col_sel1, col_sel2 = st.columns([2,1])
with col_sel1:
    DEFAULT_PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
    symbol = st.selectbox("🪙 Select Pair", DEFAULT_PAIRS)
with col_sel2:
    custom = st.text_input("Custom pair", placeholder="e.g. ADAUSDT")
    if custom:
        symbol = custom.upper()

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🕐 Multi-Timeframe", "🔥 Top Gainers"])

# ─── TAB 1: DASHBOARD ───
with tab1:
    price_data = get_price(symbol, api_key, api_secret)

    if price_data is None:
        st.error(f"Gagal ambil data {symbol}. Cek API key atau nama pair.")
        st.stop()

    price = price_data["price"]
    change = price_data["change"]
    change_color = "#3fb950" if change >= 0 else "#f85149"

    # Header
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"""
        <div style="margin-bottom:8px;">
            <span style="font-size:28px; font-weight:800; color:#e6edf3;">{symbol}</span>
            <span style="font-size:13px; color:#8b949e; margin-left:12px;">BINANCE SPOT</span>
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

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("24h High", f"${price_data['high']:,.4f}")
    with col2:
        st.metric("24h Low", f"${price_data['low']:,.4f}")
    with col3:
        vol_m = price_data["quoteVolume"] / 1_000_000
        st.metric("Volume (USDT)", f"${vol_m:,.1f}M")
    with col4:
        st.metric("24h Change", f"{change:+.2f}%",
                  delta=f"{'Up' if change >= 0 else 'Down'}")

    st.markdown("---")

    # Chart + Signal
    col_chart, col_signal = st.columns([3, 1])

    with col_chart:
        st.markdown('<p class="section-header">Price Chart</p>', unsafe_allow_html=True)
        df = get_klines(symbol, interval_val, candles, api_key, api_secret)
        resistances, supports = get_support_resistance(df)
        if df is not None:
            fig = build_chart(df, symbol, resistances, supports)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Gagal load chart data")

    with col_signal:
        st.markdown('<p class="section-header">AI Signal</p>', unsafe_allow_html=True)

        if df is not None:
            result = calculate_signal(df)
            signal = result[0]
            reason = result[1]
            signals = result[2]
            indicators = result[3] if len(result) > 3 else {}
            strength = result[4] if len(result) > 4 else 50

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
            price = price_data["price"]
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<p class="section-header">Support & Resistance</p>', unsafe_allow_html=True)
            for r in resistances:
                st.markdown(f'<div class="sr-level sr-resistance"><span style="color:#8b949e;">Resistance</span><span style="color:#f85149; font-weight:700;">${r:,.4f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="text-align:center; padding:4px; color:#e6edf3; font-size:12px; font-weight:700;">── Now: ${price:,.4f} ──</div>', unsafe_allow_html=True)
            for s in supports:
                st.markdown(f'<div class="sr-level sr-support"><span style="color:#8b949e;">Support</span><span style="color:#3fb950; font-weight:700;">${s:,.4f}</span></div>', unsafe_allow_html=True)

# ─── TAB 2: MULTI TIMEFRAME ───
with tab2:
    st.markdown('<p class="section-header">🕐 Multi-Timeframe Analysis</p>', unsafe_allow_html=True)
    st.markdown(f"<p style='color:#8b949e; font-size:13px;'>Analisis {symbol} dari 3 timeframe sekaligus</p>", unsafe_allow_html=True)

    with st.spinner("Menganalisis semua timeframe..."):
        mtf_results = multi_timeframe_analysis(symbol, api_key, api_secret)

    buy_count = sum(1 for _, s, _, _ in mtf_results if s == "BUY")
    sell_count = sum(1 for _, s, _, _ in mtf_results if s == "SELL")
    hold_count = sum(1 for _, s, _, _ in mtf_results if s == "HOLD")

    if buy_count >= 2:
        consensus_color = "#3fb950"; consensus_emoji = "🟢"
        consensus_text = "STRONG BUY" if buy_count == 3 else "BUY"
    elif sell_count >= 2:
        consensus_color = "#f85149"; consensus_emoji = "🔴"
        consensus_text = "STRONG SELL" if sell_count == 3 else "SELL"
    else:
        consensus_color = "#388bfd"; consensus_emoji = "🔵"
        consensus_text = "MIXED / HOLD"

    st.markdown(f"""
    <div style="background:#161b22; border:1px solid #30363d; border-radius:12px; padding:24px; text-align:center; margin-bottom:24px;">
        <p style="color:#8b949e; font-size:12px; text-transform:uppercase; letter-spacing:2px; margin:0;">MTF Consensus</p>
        <p style="font-size:36px; font-weight:800; color:{consensus_color}; margin:8px 0;">{consensus_emoji} {consensus_text}</p>
        <p style="color:#8b949e; font-size:12px;">{buy_count} BUY · {sell_count} SELL · {hold_count} HOLD</p>
    </div>
    """, unsafe_allow_html=True)

    col_mtf1, col_mtf2, col_mtf3 = st.columns(3)
    cols = [col_mtf1, col_mtf2, col_mtf3]
    for i, (label, signal, reason, strength) in enumerate(mtf_results):
        color = "#3fb950" if signal == "BUY" else "#f85149" if signal == "SELL" else "#388bfd"
        emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🔵"
        with cols[i]:
            st.markdown(f"""
            <div class="mtf-card mtf-{signal.lower()}">
                <p style="color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin:0;">{label}</p>
                <p style="font-size:22px; font-weight:800; color:{color}; margin:8px 0;">{emoji} {signal}</p>
                <div class="strength-bar-container">
                    <div class="strength-bar-fill" style="width:{strength}%; background:{color};"></div>
                </div>
                <p style="color:#8b949e; font-size:11px; margin:4px 0;">Strength: {strength}%</p>
                <p style="color:#8b949e; font-size:11px; margin:0;">{reason}</p>
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

    gainers = get_top_gainers(api_key, api_secret, n=10)

    if gainers:
        col_g1, col_g2 = st.columns(2)
        for i, g in enumerate(gainers):
            sym = g["symbol"]
            pct = float(g["priceChangePercent"])
            pr = float(g["lastPrice"])
            vol = float(g["quoteVolume"]) / 1_000_000
            color = "#3fb950" if pct >= 0 else "#f85149"

            card = f"""
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
                with col_g1:
                    st.markdown(card, unsafe_allow_html=True)
            else:
                with col_g2:
                    st.markdown(card, unsafe_allow_html=True)
    else:
        st.info("Gagal load data gainers. Cek koneksi API.")

# ─────────────────────────────────────────────
#  AUTO REFRESH
# ─────────────────────────────────────────────
# Save alert to session state
if alert_active:
    st.session_state["alert_active"] = True
    st.session_state["alert_price"] = alert_price
    st.session_state["alert_type"] = alert_type
    st.session_state["alert_symbol"] = alert_symbol
    st.session_state["ntfy_topic"] = ntfy_topic

if auto_refresh:
    time.sleep(30)
    if st.session_state.get("alert_active") and st.session_state.get("ntfy_topic") and st.session_state.get("alert_price", 0) > 0:
        price_now = get_price(st.session_state["alert_symbol"], api_key, api_secret)
        if price_now:
            current = price_now["price"]
            a_type = st.session_state["alert_type"]
            a_price = st.session_state["alert_price"]
            a_symbol = st.session_state["alert_symbol"]
            a_topic = st.session_state["ntfy_topic"]
            if a_type == "Above" and current >= a_price:
                send_ntfy(a_topic, f"🚨 {a_symbol} ALERT!", f"{a_symbol} tembus ${current:,.4f} (target: ${a_price:,.4f})")
            elif a_type == "Below" and current <= a_price:
                send_ntfy(a_topic, f"🚨 {a_symbol} ALERT!", f"{a_symbol} turun ke ${current:,.4f} (target: ${a_price:,.4f})")
    st.rerun()
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

    # Volume surge boosts signal
    if vol_surge:
        signals["VOL"] = ("SURGE ⚡", "green")
        if buy_score > sell_score:
            buy_score += 1
        else:
            sell_score += 1
    else:
        signals["VOL"] = ("NORMAL", "neutral")

    # Decision
    indicators = {
        "RSI": round(rsi, 2),
        "MACD": round(macd, 6),
        "BB_pos": round((current_price - bb_lower) / (bb_upper - bb_lower) * 100, 1),
        "EMA20": round(ema20, 4),
        "EMA50": round(ema50, 4),
    }

    if buy_score >= 5:
        reason = f"Strong buy signal — {buy_score} bullish indicators"
        return "BUY", reason, signals, indicators
    elif sell_score >= 5:
        reason = f"Strong sell signal — {sell_score} bearish indicators"
        return "SELL", reason, signals, indicators
    elif buy_score > sell_score:
        reason = f"Weak buy signal — {buy_score} vs {sell_score} indicators"
        return "BUY", reason, signals, indicators
    elif sell_score > buy_score:
        reason = f"Weak sell signal — {sell_score} vs {buy_score} indicators"
        return "SELL", reason, signals, indicators
    else:
        reason = "Mixed signals — market indecisive"
        return "HOLD", reason, signals, indicators

# ─────────────────────────────────────────────
#  CHART
# ─────────────────────────────────────────────
def build_chart(df, symbol):
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
    st.caption("v1.0 · Binance · Read Only")

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
tab1, tab2 = st.tabs(["📊 Dashboard", "🔥 Top Gainers"])

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
        if df is not None:
            fig = build_chart(df, symbol)
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

            signal_class = f"signal-{signal.lower()}"
            signal_emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🔵"

            st.markdown(f"""
            <div class="{signal_class}">
                <p class="signal-text">{signal_emoji} {signal}</p>
                <p class="signal-reason">{reason}</p>
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

# ─── TAB 2: TOP GAINERS ───
with tab2:
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
if auto_refresh:
    time.sleep(30)
    st.rerun()
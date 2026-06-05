import streamlit as st
import requests
import pandas as pd
import ta

# ==================================================
# CONFIG
# ==================================================

st.set_page_config(
    page_title="AI Trading Engine",
    layout="wide"
)

st.title("🤖 AI Trading Engine")

# ==================================================
# SETTINGS
# ==================================================

ASSETS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "TRXUSDT",
    "AVAXUSDT",
    "LINKUSDT"
]

TIMEFRAME = "5m"

# ==================================================
# FUNCTIONS
# ==================================================

def get_market_data(symbol):

    url = (
        f"https://api.binance.com/api/v3/klines"
        f"?symbol={symbol}"
        f"&interval={TIMEFRAME}"
        f"&limit=250"
    )

    response = requests.get(url, timeout=10)

    data = response.json()

    df = pd.DataFrame(data)

    df = df.iloc[:, :6]

    df.columns = [
        "time",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]

    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)

    return df


def analyze_asset(df):

    price = df["close"].iloc[-1]

    # ====================================
    # RSI
    # ====================================

    rsi = ta.momentum.RSIIndicator(
        close=df["close"],
        window=14
    ).rsi().iloc[-1]

    # ====================================
    # EMA
    # ====================================

    ema20 = ta.trend.EMAIndicator(
        close=df["close"],
        window=20
    ).ema_indicator().iloc[-1]

    ema50 = ta.trend.EMAIndicator(
        close=df["close"],
        window=50
    ).ema_indicator().iloc[-1]

    ema200 = ta.trend.EMAIndicator(
        close=df["close"],
        window=200
    ).ema_indicator().iloc[-1]

    # ====================================
    # MACD
    # ====================================

    macd = ta.trend.MACD(df["close"])

    macd_line = macd.macd().iloc[-1]
    signal_line = macd.macd_signal().iloc[-1]

    # ====================================
    # VOLUME
    # ====================================

    current_volume = df["volume"].iloc[-1]

    avg_volume = (
        df["volume"]
        .rolling(20)
        .mean()
        .iloc[-1]
    )

    volume_ratio = current_volume / avg_volume

    # ====================================
    # TREND
    # ====================================

    if ema20 > ema50 > ema200:
        trend = "Bullish"

    elif ema20 < ema50 < ema200:
        trend = "Bearish"

    else:
        trend = "Sideways"

    # ====================================
    # SCORE ENGINE
    # ====================================

    score = 0

    # TREND

    if trend == "Bullish":
        score += 30

    elif trend == "Sideways":
        score += 15

    # RSI

    if 55 <= rsi <= 70:
        score += 25

    elif 45 <= rsi < 55:
        score += 15

    elif rsi > 70:
        score += 5

    # MACD

    if macd_line > signal_line:
        score += 25

    # VOLUME

    if volume_ratio > 1.5:
        score += 20

    elif volume_ratio > 1.2:
        score += 10

    # ====================================
    # SIGNAL
    # ====================================

    if score >= 70:
        signal = "BUY"

    elif score >= 45:
        signal = "HOLD"

    else:
        signal = "SELL"

    confidence = min(score, 100)

    return {
        "Price": round(price, 4),
        "RSI": round(rsi, 2),
        "Trend": trend,
        "MACD": round(macd_line, 4),
        "VolumeX": round(volume_ratio, 2),
        "Score": score,
        "Confidence": f"{confidence}%",
        "Signal": signal
    }


# ==================================================
# SCAN
# ==================================================

rows = []

for symbol in ASSETS:

    try:

        df = get_market_data(symbol)

        result = analyze_asset(df)

        rows.append({
            "Asset": symbol,
            **result
        })

    except Exception as e:

        rows.append({
            "Asset": symbol,
            "Price": 0,
            "RSI": 0,
            "Trend": "ERROR",
            "MACD": 0,
            "VolumeX": 0,
            "Score": 0,
            "Confidence": "0%",
            "Signal": str(e)
        })

# ==================================================
# DATAFRAME
# ==================================================

table = pd.DataFrame(rows)

table = table.sort_values(
    by="Score",
    ascending=False
)

# ==================================================
# TOP OPPORTUNITY
# ==================================================

top = table.iloc[0]

st.success(
    f"""
🔥 TOP OPPORTUNITY

Asset: {top['Asset']}

Signal: {top['Signal']}

Score: {top['Score']}

Confidence: {top['Confidence']}
"""
)

# ==================================================
# TABLE
# ==================================================

st.subheader("📈 Market Scanner")

st.dataframe(
    table,
    use_container_width=True
)

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

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Trading Hunter",
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

    /* Hide streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

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
#  LOAD API CREDENTIALS FROM SECRETS
# ─────────────────────────────────────────────
try:
    BINANCE_API_KEY = st.secrets["BINANCE_API_KEY"]
    BINANCE_API_SECRET = st.secrets["BINANCE_API_SECRET"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception as e:
    st.error(f"Secrets error: {e}")
    st.stop()

if not BINANCE_API_KEY or not BINANCE_API_SECRET or not GEMINI_API_KEY:
    st.error("❌ API Credentials (Binance/Gemini) belum lengkap di secrets!")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

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
        st.error(f"BINANCE ERROR: {str(e)}")
        st.stop()

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
#  MULTI TIMEFRAME ANALYSIS (Full Version)
# ─────────────────────────────────────────────
def multi_timeframe_analysis(symbol, api_key, api_secret, trading_mode="Ketat"):
    tf_list = ["5m", "15m", "1h"] if trading_mode == "Scalping" else ["1h", "4h", "1d"]
    results = []
    for tf in tf_list:
        df_tf = get_klines(symbol, tf, 100, api_key, api_secret)
        if df_tf is not None and len(df_tf) >= 50:
            close = df_tf["close"]
            price_tf = close.iloc[-1]
            ema20 = ta.trend.EMAIndicator(close, window=20).ema_indicator().iloc[-1]
            ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]
            rsi_tf = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]
            macd_ind = ta.trend.MACD(close)
            macd_val = macd_ind.macd().iloc[-1]
            macd_sig = macd_ind.macd_signal().iloc[-1]

            bull_pts = sum([
                price_tf > ema20,
                price_tf > ema50,
                rsi_tf < 60,
                macd_val > macd_sig
            ])
            bear_pts = sum([
                price_tf < ema20,
                price_tf < ema50,
                rsi_tf > 40,
                macd_val < macd_sig
            ])

            if bull_pts >= 3:
                sig, reason_tf = "BUY", f"EMA bullish, RSI {rsi_tf:.0f}, MACD positif"
                conf = 60 + (bull_pts * 10)
            elif bear_pts >= 3:
                sig, reason_tf = "SELL", f"EMA bearish, RSI {rsi_tf:.0f}, MACD negatif"
                conf = 60 + (bear_pts * 10)
            else:
                sig, reason_tf = "HOLD", f"Konflik sinyal, RSI {rsi_tf:.0f}"
                conf = 50

            results.append((tf.upper(), sig, reason_tf, min(conf, 95)))
    return results

def get_mtf_context_data(symbol, interval, api_key, api_secret, trading_mode="Ketat"):
    """Ringkasan MTF untuk dimasukkan ke prompt Gemini."""
    tf_list = ["5m", "15m", "1h"] if trading_mode == "Scalping" else ["1h", "4h", "1d"]
    context = {}
    for tf in tf_list:
        if tf == interval:
            continue
        df_tf = get_klines(symbol, tf, 50, api_key, api_secret)
        if df_tf is not None and len(df_tf) >= 20:
            price_tf = df_tf["close"].iloc[-1]
            ema50_tf = ta.trend.EMAIndicator(df_tf["close"], window=20).ema_indicator().iloc[-1]
            context[tf] = "BULLISH" if price_tf > ema50_tf else "BEARISH"
    return context

# ─────────────────────────────────────────────
#  HYBRID AI ENGINE — GEMINI POWERED
# ─────────────────────────────────────────────
def execute_hybrid_engine(df, symbol, interval, trading_mode, resistances, supports, mtf_context):
    if df is None or len(df) < 50:
        return "HOLD", "Data tidak cukup", {}, {}, 50, "SKIP", "Data tidak mencukupi", "#8b949e", [], {}

    current_price = df["close"].iloc[-1]

    # Hitung indikator teknikal
    close = df["close"]
    ema20 = ta.trend.EMAIndicator(close, window=20).ema_indicator().iloc[-1]
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]
    ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator().iloc[-1] if len(df) >= 200 else ema50
    rsi = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]

    macd_ind = ta.trend.MACD(close)
    macd_val = macd_ind.macd().iloc[-1]
    macd_sig = macd_ind.macd_signal().iloc[-1]

    bb = ta.volatility.BollingerBands(close, window=20)
    bb_upper = bb.bollinger_hband().iloc[-1]
    bb_lower = bb.bollinger_lband().iloc[-1]
    bb_pos = ((current_price - bb_lower) / max(bb_upper - bb_lower, 0.0001)) * 100

    atr = ta.volatility.AverageTrueRange(df["high"], df["low"], close, window=14).average_true_range().iloc[-1]
    vol_ratio = df["volume"].iloc[-1] / max(df["volume"].rolling(20).mean().iloc[-1], 0.0001)

    # Hitung score breakdown (5 kategori)
    trend_score = 0
    trend_max = 25
    if current_price > ema20: trend_score += 8
    if current_price > ema50: trend_score += 9
    if current_price > ema200: trend_score += 8

    momentum_score = 0
    momentum_max = 25
    if rsi < 45: momentum_score += 12
    elif rsi < 55: momentum_score += 6
    if macd_val > macd_sig: momentum_score += 13

    structure_score = 0
    structure_max = 20
    if supports and abs(current_price - supports[0]) / current_price < 0.01:
        structure_score += 10
    if resistances and abs(resistances[0] - current_price) / current_price > 0.005:
        structure_score += 10

    mtf_score = 0
    mtf_max = 20
    bullish_tf = sum(1 for v in mtf_context.values() if v == "BULLISH")
    mtf_score = round((bullish_tf / max(len(mtf_context), 1)) * mtf_max)

    volume_score = 0
    volume_max = 10
    if vol_ratio >= 1.5: volume_score = 10
    elif vol_ratio >= 1.2: volume_score = 5

    total_score = trend_score + momentum_score + structure_score + mtf_score + volume_score

    score_detail = {
        "trend": trend_score, "trend_max": trend_max,
        "momentum": momentum_score, "momentum_max": momentum_max,
        "structure": structure_score, "structure_max": structure_max,
        "mtf": mtf_score, "mtf_max": mtf_max,
        "volume": volume_score, "volume_max": volume_max,
        "total": total_score
    }

    # Susun data untuk Gemini
    market_state = {
        "symbol": symbol,
        "timeframe_utama": interval,
        "trading_mode_context": trading_mode,
        "target_profit_user": "Minimal $5 per hari",
        "indicators": {
            "current_price": round(current_price, 4),
            "ema20": round(ema20, 4),
            "ema50": round(ema50, 4),
            "ema200": round(ema200, 4),
            "rsi_14": round(rsi, 2),
            "macd_value": round(macd_val, 6),
            "macd_signal": round(macd_sig, 6),
            "bollinger_position_pct": round(bb_pos, 1),
            "volume_vs_average_20": round(vol_ratio, 2),
            "atr_volatility": round(atr, 4),
            "technical_score_total": total_score
        },
        "structure": {
            "nearest_resistances": resistances,
            "nearest_supports": supports
        },
        "multi_timeframe_bias": mtf_context
    }

    prompt = f"""
    Kamu adalah 'Otak Utama Decision Engine' dari sistem AI Trading Hunter.
    Tugasmu adalah menganalisis data teknikal riil di bawah ini untuk mengambil keputusan trading yang fleksibel, adaptif, namun rasional.

    User memiliki target profit kecil yang konsisten sebesar: MINIMAL $5 PER HARI.
    Oleh karena itu:
    - Jika mode='Scalping', carilah celah profit mikro secara agresif meskipun konfirmasi indikator belum 100% sempurna.
    - Jika mode='Ketat', tetaplah selektif namun jangan sekaku rumus matematika. Gunakan logika kontekstual trader profesional.

    DATA MARKET RIIL (JSON):
    {json.dumps(market_state, indent=2)}

    WAJIB mengembalikan output dalam format JSON mentah dengan struktur tepat seperti di bawah ini tanpa teks tambahan di luar JSON:
    {{
        "signal": "BUY", "SELL", atau "HOLD",
        "signal_reason": "Alasan singkat di balik sinyal arah",
        "confidence_score": 50 sampai 100,
        "decision": "ENTER", "WAIT", atau "SKIP",
        "decision_reason": "Penjelasan mengapa harus langsung masuk pasar, menunggu, atau skip",
        "ai_insights": [
            "Poin analisis trend berdasarkan data di atas",
            "Poin analisis momentum dan volume",
            "Poin analisis struktur lokasi harga terhadap S/R",
            "Analisis pemenuhan target harian $5"
        ]
    }}
    """

    try:
        model = genai.GenerativeModel("gemini-3.1-flash-lite")
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        res_data = json.loads(response.text.strip())

        signal = res_data.get("signal", "HOLD")
        signal_reason = res_data.get("signal_reason", "AI default hold")
        confidence = int(res_data.get("confidence_score", 50))
        decision = res_data.get("decision", "SKIP")
        decision_reason = res_data.get("decision_reason", "AI default skip")
        ai_insights = res_data.get("ai_insights", [])

    except Exception as e:
        signal, signal_reason, confidence = "HOLD", f"AI API Error: {str(e)}", 50
        decision, decision_reason, ai_insights = "SKIP", "Sistem dialihkan ke default aman", ["Koneksi API AI terganggu."]

    # Badge indikator untuk UI
    signals = {
        "RSI": ("BULLISH" if rsi < 45 else "BEARISH" if rsi > 55 else "NEUTRAL",
                "green" if rsi < 45 else "red" if rsi > 55 else "neutral"),
        "MACD": ("BULLISH" if macd_val > macd_sig else "BEARISH",
                 "green" if macd_val > macd_sig else "red"),
        "EMA": ("UPTREND" if current_price > ema50 else "DOWNTREND",
                "green" if current_price > ema50 else "red"),
        "VOL": ("SURGE ⚡" if vol_ratio >= 1.5 else "NORMAL",
                "green" if vol_ratio >= 1.5 else "neutral")
    }

    indicators_raw = {
        "RSI": round(rsi, 2),
        "MACD": round(macd_val, 6),
        "BB_pos": round(bb_pos, 1),
        "EMA20": round(ema20, 4),
        "EMA50": round(ema50, 4),
        "EMA200": round(ema200, 4)
    }

    decision_color = "#3fb950" if decision == "ENTER" else "#f0883e" if decision == "WAIT" else "#f85149"

    return signal, signal_reason, signals, indicators_raw, confidence, decision, decision_reason, decision_color, ai_insights, score_detail

# ─────────────────────────────────────────────
#  CHART BUILDER (Full Version dengan EMA + Volume)
# ─────────────────────────────────────────────
def build_chart(df, symbol, resistances, supports):
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f"{symbol} Price", "Volume", "RSI")
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df["timestamp"],
        open=df["open"], high=df["high"],
        low=df["low"], close=df["close"],
        name="Price",
        increasing_line_color="#3fb950",
        decreasing_line_color="#f85149"
    ), row=1, col=1)

    # EMA Overlays
    close = df["close"]
    ema20 = ta.trend.EMAIndicator(close, window=20).ema_indicator()
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator()
    fig.add_trace(go.Scatter(x=df["timestamp"], y=ema20, name="EMA 20",
                             line=dict(color="#388bfd", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=ema50, name="EMA 50",
                             line=dict(color="#f0883e", width=1.5)), row=1, col=1)
    if len(close) >= 200:
        ema200 = ta.trend.EMAIndicator(close, window=200).ema_indicator()
        fig.add_trace(go.Scatter(x=df["timestamp"], y=ema200, name="EMA 200",
                                 line=dict(color="#8b949e", width=1.5)), row=1, col=1)

    # Support & Resistance lines
    for r in resistances:
        fig.add_trace(go.Scatter(
            x=[df["timestamp"].iloc[0], df["timestamp"].iloc[-1]], y=[r, r],
            mode="lines", name=f"Res {r}",
            line=dict(color="#f85149", width=1, dash="dash")
        ), row=1, col=1)
    for s in supports:
        fig.add_trace(go.Scatter(
            x=[df["timestamp"].iloc[0], df["timestamp"].iloc[-1]], y=[s, s],
            mode="lines", name=f"Sup {s}",
            line=dict(color="#3fb950", width=1, dash="dash")
        ), row=1, col=1)

    # Volume bar
    colors = ["#3fb950" if df["close"].iloc[i] >= df["open"].iloc[i] else "#f85149"
              for i in range(len(df))]
    fig.add_trace(go.Bar(x=df["timestamp"], y=df["volume"], name="Volume",
                         marker_color=colors), row=2, col=1)

    # RSI
    rsi_series = ta.momentum.RSIIndicator(close, window=14).rsi()
    fig.add_trace(go.Scatter(x=df["timestamp"], y=rsi_series, name="RSI",
                             line=dict(color="#f0883e", width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=[df["timestamp"].iloc[0], df["timestamp"].iloc[-1]], y=[70, 70],
        mode="lines", name="OB (70)", line=dict(color="#f85149", width=1, dash="dot")
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=[df["timestamp"].iloc[0], df["timestamp"].iloc[-1]], y=[30, 30],
        mode="lines", name="OS (30)", line=dict(color="#3fb950", width=1, dash="dot")
    ), row=3, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        height=650,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(rangeslider=dict(visible=False)),
        showlegend=False
    )
    return fig

# ─────────────────────────────────────────────
#  TRADING PLAN GENERATOR (Full TP2 + TP3 pct)
# ─────────────────────────────────────────────
def generate_trading_plan(df, price_data, signal, supports, resistances, modal_usdt=100, trading_mode="Ketat"):
    if df is None or len(df) < 20 or signal == "HOLD":
        return None

    current_price = price_data["price"]
    atr = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range().iloc[-1]
    qty = round(modal_usdt / current_price, 6)

    sl_mult, tp1_mult, tp2_mult, tp3_mult = (0.8, 0.7, 1.0, 1.4) if trading_mode == "Scalping" else (1.5, 2.0, 3.5, 5.0)
    min_tp_pct, min_sl_pct = (0.0005, 0.0015) if trading_mode == "Scalping" else (0.001, 0.005)

    if signal == "BUY":
        entry = round(current_price, 4)
        sl = round(entry - (atr * sl_mult), 4)
        sl = min(sl, round(entry * (1 - min_sl_pct), 4))

        tp1 = round(entry + (atr * tp1_mult), 4)
        if resistances and resistances[0] > entry:
            tp1 = min(tp1, round(resistances[0] * 0.999, 4))
        tp1 = max(tp1, round(entry * (1 + min_tp_pct), 4))
        tp2 = round(entry + (atr * tp2_mult), 4)
        tp3 = round(entry + (atr * tp3_mult), 4)

        profit_tp1 = round((tp1 - entry) * qty, 2)
        profit_tp2 = round((tp2 - entry) * qty, 2)
        profit_tp3 = round((tp3 - entry) * qty, 2)
        loss_sl = round(abs((entry - sl) * qty), 2)

    elif signal == "SELL":
        entry = round(current_price, 4)
        sl = round(entry + (atr * sl_mult), 4)
        sl = max(sl, round(entry * (1 + min_sl_pct), 4))

        tp1 = round(entry - (atr * tp1_mult), 4)
        if supports and supports[0] < entry:
            tp1 = max(tp1, round(supports[0] * 1.001, 4))
        tp1 = min(tp1, round(entry * (1 - min_tp_pct), 4))
        tp2 = round(entry - (atr * tp2_mult), 4)
        tp3 = round(entry - (atr * tp3_mult), 4)

        profit_tp1 = round((entry - tp1) * qty, 2)
        profit_tp2 = round((entry - tp2) * qty, 2)
        profit_tp3 = round((entry - tp3) * qty, 2)
        loss_sl = round(abs((sl - entry) * qty), 2)
    else:
        return None

    sl_pct = round(abs((sl - entry) / entry * 100), 2)
    tp1_pct = round(abs((tp1 - entry) / entry * 100), 2)
    tp2_pct = round(abs((tp2 - entry) / entry * 100), 2)
    tp3_pct = round(abs((tp3 - entry) / entry * 100), 2)
    rr_ratio = round(tp1_pct / sl_pct, 2) if sl_pct > 0 else 0

    return {
        "signal": signal, "entry": entry,
        "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3,
        "sl_pct": sl_pct, "tp1_pct": tp1_pct, "tp2_pct": tp2_pct, "tp3_pct": tp3_pct,
        "rr_ratio": rr_ratio, "qty": qty, "modal": modal_usdt,
        "profit_tp1": profit_tp1, "profit_tp2": profit_tp2, "profit_tp3": profit_tp3,
        "loss_sl": loss_sl
    }

# ─────────────────────────────────────────────
#  SESSION STATE INITIALIZATION
# ─────────────────────────────────────────────
defaults = {
    "symbol": "BTCUSDT",
    "trading_mode": "Ketat",
    "modal": 100,
    "wallet_usdt": 1000.0,
    "wallet_crypto": 0.0,
    "history": [],
    "auto_refresh": False
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎛️ AI TRADING HUNTER")

    ticker_options = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT"]
    symbol_input = st.text_input("🪙 SYMBOL PAIR", value=st.session_state["symbol"]).upper()
    if symbol_input not in ticker_options:
        ticker_options.insert(0, symbol_input)
    st.session_state["symbol"] = symbol_input

    trading_mode = st.radio("⚙️ Mode Analisis", ["Ketat", "Scalping"],
                            index=0 if st.session_state["trading_mode"] == "Ketat" else 1)
    st.session_state["trading_mode"] = trading_mode

    tf_options = ["5m", "15m", "1h", "4h", "1d"]
    default_tf = 1 if trading_mode == "Scalping" else 2
    interval = st.selectbox("⏳ Timeframe Utama", tf_options, index=default_tf)

    modal = st.number_input("💰 Modal (USDT)", min_value=10, max_value=100000,
                            value=st.session_state["modal"], step=10)
    st.session_state["modal"] = modal

    st.markdown("---")
    st.markdown("**📊 MOCK WALLET**")
    st.markdown(f"**USDT:** `{st.session_state['wallet_usdt']:.2f}`")
    st.markdown(f"**Asset:** `{st.session_state['wallet_crypto']:.6f}`")
    st.markdown("---")

    auto_refresh = st.checkbox("🔄 Auto Refresh (30s)", value=st.session_state["auto_refresh"])
    st.session_state["auto_refresh"] = auto_refresh

    if st.button("🔄 Force Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ─────────────────────────────────────────────
#  MAIN LOGIC PIPELINE
# ─────────────────────────────────────────────
symbol = st.session_state["symbol"]
mode = st.session_state["trading_mode"]

price_data = get_price(symbol, BINANCE_API_KEY, BINANCE_API_SECRET)
df = get_klines(symbol, interval, 200, BINANCE_API_KEY, BINANCE_API_SECRET)

if df is None or len(df) < 50:
    st.error("⚠️ Data candlestick tidak cukup dari Binance.")
    st.stop()

resistances, supports = get_support_resistance(df)
mtf_context = get_mtf_context_data(symbol, interval, BINANCE_API_KEY, BINANCE_API_SECRET, trading_mode=mode)

signal, reason, signals, indicators, confidence, decision, decision_reason, decision_color, ai_insights, score_detail = execute_hybrid_engine(
    df, symbol, interval, mode, resistances, supports, mtf_context
)

plan = generate_trading_plan(df, price_data, signal, supports, resistances,
                             modal_usdt=st.session_state["modal"], trading_mode=mode)

# ─────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center;
     border-bottom:1px solid #30363d; padding-bottom:12px; margin-bottom:20px;">
    <div>
        <h2 style="margin:0; font-weight:800; color:#e6edf3;">📈 AI Trading Hunter</h2>
        <p style="margin:0; font-size:13px; color:#8b949e;">
            Hybrid Brain Engine v2.8.0 &nbsp;|&nbsp; {symbol} ({interval.upper()}) &nbsp;|&nbsp; Mode: {mode}
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── TOP METRICS ROW ───
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Live Price", f"{price_data['price']:,}", f"{price_data['change']}%")
with m2:
    st.metric("24h High", f"{price_data['high']:,}")
with m3:
    st.metric("24h Low", f"{price_data['low']:,}")
with m4:
    st.metric("24h Volume (USDT)", f"{int(price_data['quoteVolume']):,}")

# ─────────────────────────────────────────────
#  MAIN TABS (5 Tab)
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 AI Signal & Chart",
    "📊 Technical Breakdown",
    "📋 Trading Plan",
    "💼 Mock Wallet",
    "⚙️ Settings"
])

# ─── TAB 1: AI SIGNAL & CHART ───
with tab1:
    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown('<p class="section-header">🤖 Hybrid AI Signal Engine</p>', unsafe_allow_html=True)

        sig_class = "signal-buy" if signal == "BUY" else "signal-sell" if signal == "SELL" else "signal-hold"
        st.markdown(f"""
        <div class="{sig_class}">
            <p style="margin:0; font-size:11px; text-transform:uppercase; letter-spacing:2px; opacity:0.7;">Sinyal Utama</p>
            <p class="signal-text">{signal}</p>
            <p class="signal-reason">{reason}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:#161b22; border:1px solid #30363d; border-left:4px solid {decision_color};
             border-radius:8px; padding:16px;">
            <p style="margin:0; font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#8b949e;">Rekomendasi Aksi</p>
            <h3 style="margin:4px 0; color:{decision_color}; font-weight:800; letter-spacing:0.5px;">{decision}</h3>
            <p style="margin:0; font-size:13px; color:#e6edf3;">{decision_reason}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p class="section-header">🛡️ AI Confidence Level</p>', unsafe_allow_html=True)
        fill_color = "#3fb950" if signal == "BUY" else "#f85149" if signal == "SELL" else "#388bfd"
        st.markdown(f"""
        <div class="strength-bar-container">
            <div class="strength-bar-fill" style="width:{confidence}%; background-color:{fill_color};"></div>
        </div>
        <p style='font-size:11px; color:#8b949e; text-align:right;'>Confidence: {confidence}/100</p>
        """, unsafe_allow_html=True)

        st.markdown('<p class="section-header" style="margin-top:16px;">🧠 Gemini AI Insights</p>', unsafe_allow_html=True)
        for insight in ai_insights:
            st.markdown(f"• {insight}")

    with c2:
        st.markdown('<p class="section-header">📈 Live Chart (EMA + Volume + RSI)</p>', unsafe_allow_html=True)
        chart_fig = build_chart(df, symbol, resistances, supports)
        st.plotly_chart(chart_fig, use_container_width=True)

# ─── TAB 2: TECHNICAL BREAKDOWN ───
with tab2:
    col_b1, col_b2, col_b3 = st.columns(3)

    with col_b1:
        st.markdown('<p class="section-header">🛑 Badges Indikator</p>', unsafe_allow_html=True)
        for ind_name, (label, color) in signals.items():
            badge_class = f"badge-{color}"
            st.markdown(f"**{ind_name}:** <span class='badge {badge_class}'>{label} ({indicators.get(ind_name, '')})</span>",
                        unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"**EMA20:** `{indicators.get('EMA20','')}`")
        st.markdown(f"**EMA50:** `{indicators.get('EMA50','')}`")
        st.markdown(f"**EMA200:** `{indicators.get('EMA200','')}`")
        st.markdown(f"**BB Position:** `{indicators.get('BB_pos','')}%`")

    with col_b2:
        st.markdown('<p class="section-header">🔢 Score Breakdown</p>', unsafe_allow_html=True)
        categories = [
            ("Trend Weight", "trend", "trend_max"),
            ("Momentum Weight", "momentum", "momentum_max"),
            ("Structure (S/R)", "structure", "structure_max"),
            ("Multi-Timeframe", "mtf", "mtf_max"),
            ("Volume Force", "volume", "volume_max"),
        ]
        for name, key, max_key in categories:
            val = score_detail.get(key, 0)
            mx = score_detail.get(max_key, 0)
            pct = round(val / max(mx, 1) * 100)
            st.markdown(f"**{name}:** `{val}/{mx}` ({pct}%)")
        st.markdown("---")
        total = score_detail.get("total", 0)
        color_t = "#3fb950" if total >= 65 else "#f0883e" if total >= 45 else "#f85149"
        st.markdown(f"**Total Score:** <span style='color:{color_t}; font-size:20px; font-weight:800;'>{total}/100</span>",
                    unsafe_allow_html=True)

    with col_b3:
        st.markdown('<p class="section-header">🌍 Multi Timeframe Status</p>', unsafe_allow_html=True)
        mtf_data = multi_timeframe_analysis(symbol, BINANCE_API_KEY, BINANCE_API_SECRET, trading_mode=mode)
        for tf_label, tf_sig, tf_reason, tf_conf in mtf_data:
            tf_color = "🟢" if tf_sig == "BUY" else "🔴" if tf_sig == "SELL" else "🔵"
            st.markdown(f"{tf_color} **{tf_label}**: `{tf_sig}` — {tf_reason} ({tf_conf}/100)")

# ─── TAB 3: TRADING PLAN ───
with tab3:
    st.markdown('<p class="section-header">📋 Setup Trading Plan Aktif</p>', unsafe_allow_html=True)
    if plan:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p_color = "tp-green" if plan["signal"] == "BUY" else "tp-red"
            st.markdown(f"""
            <div class="tp-card">
                <h4 style="margin-top:0; color:#8b949e;">🎯 ENTRY CONFIGURATION</h4>
                <div class="tp-row"><span class="tp-label">Arah Posisi</span><span class="tp-value {p_color}" style="font-size:16px;">{plan['signal']}</span></div>
                <div class="tp-row"><span class="tp-label">Entry Price</span><span class="tp-value">{plan['entry']:,} USDT</span></div>
                <div class="tp-row"><span class="tp-label">Kuantitas Size</span><span class="tp-value">{plan['qty']} Token</span></div>
                <div class="tp-row"><span class="tp-label">Stop Loss</span><span class="tp-value tp-red">{plan['sl']:,} USDT (-{plan['sl_pct']}%)</span></div>
                <div class="tp-row"><span class="tp-label">Take Profit 1</span><span class="tp-value tp-green">{plan['tp1']:,} USDT (+{plan['tp1_pct']}%)</span></div>
                <div class="tp-row"><span class="tp-label">Take Profit 2</span><span class="tp-value tp-green">{plan['tp2']:,} USDT (+{plan['tp2_pct']}%)</span></div>
                <div class="tp-row"><span class="tp-label">Take Profit 3 (Runner)</span><span class="tp-value tp-green">{plan['tp3']:,} USDT (+{plan['tp3_pct']}%)</span></div>
            </div>
            """, unsafe_allow_html=True)
        with col_p2:
            st.markdown(f"""
            <div class="tp-card">
                <h4 style="margin-top:0; color:#8b949e;">💰 RISK / REWARD MATRIX</h4>
                <div class="tp-row"><span class="tp-label">Risk Reward Ratio</span><span class="tp-value tp-yellow">1 : {plan['rr_ratio']}</span></div>
                <div class="tp-row"><span class="tp-label">Profit TP1</span><span class="tp-value tp-green">+{plan['profit_tp1']} USDT</span></div>
                <div class="tp-row"><span class="tp-label">Profit TP2</span><span class="tp-value tp-green">+{plan['profit_tp2']} USDT</span></div>
                <div class="tp-row"><span class="tp-label">Profit TP3</span><span class="tp-value tp-green">+{plan['profit_tp3']} USDT</span></div>
                <div class="tp-row"><span class="tp-label">Resiko Maks (SL)</span><span class="tp-value tp-red">-{plan['loss_sl']} USDT</span></div>
                <div class="tp-row"><span class="tp-label">Modal Dipakai</span><span class="tp-value">{plan['modal']} USDT</span></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p class="section-header">🧠 Gemini AI Reasoning</p>', unsafe_allow_html=True)
        for insight in ai_insights:
            st.markdown(f"• {insight}")
    else:
        st.info("Sinyal HOLD — Trading plan dinonaktifkan. Tunggu momentum dari AI sebelum entry.")

# ─── TAB 4: MOCK WALLET ───
with tab4:
    st.markdown('<p class="section-header">💼 Simulasi Mock Trading</p>', unsafe_allow_html=True)

    col_w1, col_w2 = st.columns(2)
    with col_w1:
        if st.button("🛒 Eksekusi Sesuai Sinyal (Simulasi Entry)", use_container_width=True):
            current_p = price_data["price"]
            if signal == "BUY" and st.session_state["wallet_usdt"] >= 100:
                st.session_state["wallet_usdt"] -= 100
                st.session_state["wallet_crypto"] += (100 / current_p)
                st.session_state["history"].append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "type": "BUY", "price": current_p, "amount": 100, "pnl": "-"
                })
                st.success("✅ Simulasi BUY senilai 100 USDT berhasil!")
            elif signal == "SELL" and st.session_state["wallet_crypto"] > 0:
                crypto_to_sell = st.session_state["wallet_crypto"]
                usdt_received = round(crypto_to_sell * current_p, 2)
                st.session_state["wallet_usdt"] += usdt_received
                st.session_state["wallet_crypto"] = 0.0
                st.session_state["history"].append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "type": "SELL", "price": current_p, "amount": usdt_received, "pnl": "Variable"
                })
                st.success(f"✅ Simulasi SELL berhasil! Diterima {usdt_received} USDT")
            else:
                st.warning("⚠️ Tidak bisa eksekusi — sinyal HOLD atau saldo tidak cukup.")

    with col_w2:
        if st.button("🔄 Reset Wallet ke $1,000", use_container_width=True):
            st.session_state["wallet_usdt"] = 1000.0
            st.session_state["wallet_crypto"] = 0.0
            st.session_state["history"] = []
            st.info("🔄 Wallet direset ke $1,000 USDT.")

    st.markdown("<br>", unsafe_allow_html=True)
    col_w3, col_w4 = st.columns(2)
    with col_w3:
        st.metric("USDT Balance", f"{st.session_state['wallet_usdt']:.2f} USDT")
    with col_w4:
        st.metric("Asset Hold", f"{st.session_state['wallet_crypto']:.6f} Token")

    st.markdown('<p class="section-header" style="margin-top:16px;">📜 Riwayat Transaksi</p>', unsafe_allow_html=True)
    if not st.session_state["history"]:
        st.text("Belum ada riwayat transaksi.")
    else:
        for t in reversed(st.session_state["history"]):
            outcome_color = "#3fb950" if t["type"] == "BUY" else "#f85149"
            st.markdown(f"""
            <div style="background:#161b22; padding:10px 16px; border-radius:6px; margin:4px 0;
                 border:1px solid #30363d; border-left:3px solid {outcome_color};">
                ⏱️ {t["time"]} — <b>{t["type"]}</b> @ {t["price"]:,} USDT (Value: ${t["amount"]:.2f})
            </div>
            """, unsafe_allow_html=True)

# ─── TAB 5: SETTINGS ───
with tab5:
    st.markdown('<p class="section-header">⚙️ System Info & Settings</p>', unsafe_allow_html=True)

    st.markdown("**🔄 Auto Refresh**")
    if st.session_state["auto_refresh"]:
        st.success("✅ Auto refresh aktif — data update tiap 30 detik")
    else:
        st.info("ℹ️ Auto refresh nonaktif — toggle dari sidebar")

    st.markdown("---")
    st.markdown("**ℹ️ App Info**")
    st.markdown(f"""
    <div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:16px;">
        <p style="color:#8b949e; font-size:12px; margin:0;">
        Version: <span style="color:#e6edf3;">v2.8.0 (Hybrid Brain Engine — Full Merge)</span><br>
        AI Decision: <span style="color:#e6edf3;">Gemini 1.5 Flash (JSON Schema Mode)</span><br>
        Exchange: <span style="color:#e6edf3;">Binance Spot API</span><br>
        Features: <span style="color:#e6edf3;">Hybrid Gemini Engine, Real MTF Score, ATR TP/SL (TP1/2/3), Score Breakdown 5 Kategori, Mock Wallet, Auto Refresh</span><br>
        Strategy: <span style="color:#3fb950; font-weight:bold;">Target Efisiensi Mikro $5/Hari</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  AUTO REFRESH LOOP
# ─────────────────────────────────────────────
if st.session_state["auto_refresh"]:
    time.sleep(30)
    st.rerun()
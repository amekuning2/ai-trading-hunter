# binance_helper.py
import pandas as pd
from binance.client import Client

def get_local_client(api_key, api_secret):
    """Inisialisasi Client Binance"""
    return Client(api_key, api_secret)

def fetch_ticker_price(client, symbol, market_type="Spot"):
    """Mengambil harga live berdasarkan tipe market (Spot / Futures)"""
    if market_type == "Futures":
        ticker = client.futures_symbol_ticker(symbol=symbol)
        # Struktur data futures mengembalikan {'symbol': '...', 'price': '...'}
        return {
            "price": float(ticker["price"]),
            "change": 0.0, # Akan dilengkapi lewat fungsi 24h ticker jika dibutuhkan
            "high": 0.0,
            "low": 0.0,
            "quoteVolume": 0.0
        }
    else:
        ticker = client.get_ticker(symbol=symbol)
        return {
            "price": float(ticker["lastPrice"]),
            "change": float(ticker["priceChangePercent"]),
            "high": float(ticker["highPrice"]),
            "low": float(ticker["lowPrice"]),
            "quoteVolume": float(ticker["quoteVolume"]),
        }

def fetch_klines_data(client, symbol, interval, limit=150, market_type="Spot"):
    """Mengambil data candlestick dari Spot atau Futures Market secara dinamis"""
    try:
        if market_type == "Futures":
            # Menggunakan endpoint khusus USDS-M Futures
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
# market_data.py
import requests
import pandas as pd

# -----------------------------
# Функция получения свечей OHLCV
# -----------------------------
def fetch_klines(symbol, interval="1h", limit=200):
    """
    Загружает свечи OHLCV для указанного символа.
    interval: '1m', '5m', '15m', '1h', '4h', '1d'
    """
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("retCode") != 0:
            print(f"Ошибка получения свечей для {symbol}: {data.get('retMsg')}")
            return pd.DataFrame()

        rows = data["result"]["list"]
        df = pd.DataFrame(rows, columns=[
            "timestamp", "open", "high", "low", "close", "vol", "turnover"
        ])
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["vol"] = df["vol"].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')

        return df.sort_values("timestamp").reset_index(drop=True)
    except Exception as e:
        print(f"❌ Ошибка fetch_klines для {symbol}: {e}")
        return pd.DataFrame()

# -----------------------------
# Функция получения funding rate
# -----------------------------
def fetch_funding_rate(symbol):
    """
    Возвращает предыдущий funding rate для указанного символа.
    Если не найдено (404) — возвращает 0.0.
    """
    try:
        url = "https://api.bybit.com/v5/market/funding/prev-funding-rate"
        params = {"symbol": symbol}
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return float(data['result']['fundingRate'])
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return 0.0
        raise
    except Exception:
        return 0.0

# -----------------------------
# Функция получения книги ордеров
# -----------------------------
def fetch_orderbook(symbol, limit=25):
    """
    Возвращает словарь с топами книги ордеров.
    """
    try:
        url = "https://api.bybit.com/v5/market/orderbook"
        params = {"symbol": symbol, "limit": limit}
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", {})
    except Exception as e:
        print(f"❌ Ошибка fetch_orderbook для {symbol}: {e}")
        return {}

# -----------------------------
# Функция получения тикера (open interest и др.)
# -----------------------------
def fetch_ticker_info(symbol):
    try:
        url = "https://api.bybit.com/v5/market/tickers"
        params = {"symbol": symbol}
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        tick = data.get("result", [])
        return tick[0] if tick else {}
    except Exception as e:
        print(f"❌ Ошибка fetch_ticker_info для {symbol}: {e}")
        return {}

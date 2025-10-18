# -*- coding: utf-8 -*-
"""
smart_money.py
Минимальный Smart Money Concept (SMC) анализ для FinAI
"""

# -----------------------------
# Загрузка свечей OHLCV с Bybit
# -----------------------------
def load_ohlcv(symbol: str, interval="1h", limit=500):
    """
    Загружает свечи OHLCV для Smart Money анализа.
    """
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("retCode") != 0:
            print(f"Ошибка получения свечей для {symbol}: {data.get('retMsg')}")
            return None

        rows = data["result"]["list"]
        df = pd.DataFrame(rows, columns=[
            "timestamp", "open", "high", "low", "close", "volume", "turnover"
        ])
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')

        return df.sort_values("timestamp").reset_index(drop=True)

    except Exception as e:
        print(f"❌ Ошибка загрузки OHLCV для {symbol}: {e}")
        return None

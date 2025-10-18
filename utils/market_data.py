import requests

def fetch_klines(symbol, interval="15m", limit=200):
    """Загрузка свечей с Bybit."""
    try:
        url = "https://api.bybit.com/v5/market/kline"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()
        if "result" not in data or "list" not in data["result"]:
            return []
        import pandas as pd
        df = pd.DataFrame(data["result"]["list"], columns=[
            "timestamp", "open", "high", "low", "close", "volume", "turnover"
        ])
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["vol"] = df["volume"].astype(float)
        return df
    except Exception as e:
        print(f"fetch_klines error {symbol}", e)
        return []

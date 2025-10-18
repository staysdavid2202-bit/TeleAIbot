import requests
import pandas as pd


# --- Получаем свечи с Bybit ---
def get_candles(symbol: str, timeframe="1W", limit=200):
    """
    Загружает исторические свечи с Bybit API (линейные контракты USDT).
    timeframe: '1', '5', '15', '60', '240', 'D', 'W', 'M'
    """
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": timeframe,
        "limit": limit
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        if data.get("retCode") != 0:
            print(f"⚠️ Ошибка API Bybit для {symbol}: {data.get('retMsg')}")
            return pd.DataFrame()

        rows = data["result"]["list"]
        df = pd.DataFrame(rows, columns=[
            "timestamp", "open", "high", "low", "close", "volume", "turnover"
        ])

        df["close"] = df["close"].astype(float)
        return df.iloc[::-1]  # Переворачиваем, чтобы шло от старых к новым свечам

    except Exception as e:
        print(f"Ошибка при загрузке свечей {symbol}: {e}")
        return pd.DataFrame()


# --- Определяем тренд по SMA50/200 ---
def get_weekly_trend(symbol: str):
    """
    Определяет направление глобального тренда на 1W таймфрейме по SMA50 и SMA200.
    Возвращает 'bullish', 'bearish' или 'neutral'.
    """
    df = get_candles(symbol, timeframe="W", limit=250)
    if df.empty:
        return "neutral"

    df["sma50"] = df["close"].rolling(50).mean()
    df["sma200"] = df["close"].rolling(200).mean()

    sma50 = df["sma50"].iloc[-1]
    sma200 = df["sma200"].iloc[-1]

    if pd.isna(sma50) or pd.isna(sma200):
        return "neutral"

    if sma50 > sma200 * 1.01:
        return "bullish"
    elif sma50 < sma200 * 0.99:
        return "bearish"
    else:
        return "neutral"

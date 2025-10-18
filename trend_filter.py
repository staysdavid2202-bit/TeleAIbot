# trend_filter.py
import requests
import pandas as pd

# --- Получаем данные свечей с Binance (или другого API) ---
def get_candles(symbol: str, timeframe="1w", limit=300):
    """
    Загружает исторические свечи с Binance API.
    timeframe="1w" — недельный тренд.
    """
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={timeframe}&limit={limit}"
    r = requests.get(url)
    data = r.json()

    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "trades",
        "taker_base_vol", "taker_quote_vol", "ignore"
    ])

    df["close"] = df["close"].astype(float)
    return df


# --- Определяем направление тренда ---
def get_weekly_trend(symbol: str):
    """
    Определяет направление глобального тренда на 1W таймфрейме по SMA50/200.
    Возвращает: 'bullish', 'bearish' или 'neutral'.
    """
    df = get_candles(symbol, timeframe="1w", limit=250)

    # Скользящие средние
    df["sma50"] = df["close"].rolling(50).mean()
    df["sma200"] = df["close"].rolling(200).mean()

    sma50 = df["sma50"].iloc[-1]
    sma200 = df["sma200"].iloc[-1]

    if pd.isna(sma50) or pd.isna(sma200):
        return "bullish"  # Если данных мало — не блокируем сигналы

    # Если разница между SMA маленькая — считаем всё равно тренд восходящим
    if sma50 > sma200 * 0.99:
        return "bullish"
    elif sma50 < sma200 * 1.01:
        return "bearish"
    else:
        return "bullish"  # По умолчанию — не останавливаем сигналы

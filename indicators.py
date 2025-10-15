# ====================== indicators.py ======================
# Дополнительные индикаторы для анализа рынка BTC
# Улучшают точность сигналов и уменьшают ложные входы

import pandas as pd
import numpy as np

# --- MACD ---
def macd(df, fast=12, slow=26, signal=9):
    ema_fast = df['закрывать'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['закрывать'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line

    if macd_line.iloc[-1] > signal_line.iloc[-1]:
        trend = "бычий"
    elif macd_line.iloc[-1] < signal_line.iloc[-1]:
        trend = "медвежий"
    else:
        trend = "нейтральный"

    return {
        "macd_trend": trend,
        "macd_value": round(macd_line.iloc[-1], 5),
        "signal_value": round(signal_line.iloc[-1], 5),
        "hist": round(hist.iloc[-1], 5)
    }

# --- Стохастический RSI ---
def stoch_rsi(df, period=14, smooth_k=3, smooth_d=3):
    delta = df['закрывать'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    min_rsi = rsi.rolling(window=period).min()
    max_rsi = rsi.rolling(window=period).max()

    stoch_rsi = (rsi - min_rsi) / (max_rsi - min_rsi)
    k = stoch_rsi.rolling(window=smooth_k).mean()
    d = k.rolling(window=smooth_d).mean()

    if k.iloc[-1] > d.iloc[-1]:
        state = "перекупленность" if k.iloc[-1] > 0.8 else "рост"
    else:
        state = "перепроданность" if k.iloc[-1] < 0.2 else "падение"

    return {
        "stoch_rsi_k": round(k.iloc[-1], 3),
        "stoch_rsi_d": round(d.iloc[-1], 3),
        "stoch_state": state
    }

# --- Полосы Боллинджера ---
def bollinger_bands(df, period=20, std_dev=2):
    sma = df['закрывать'].rolling(window=period).mean()
    std = df['закрывать'].rolling(window=period).std()

    upper_band = sma + std_dev * std
    lower_band = sma - std_dev * std
    price = df['закрывать'].iloc[-1]

    if price > upper_band.iloc[-1]:
        band_state = "пробой вверх"
    elif price < lower_band.iloc[-1]:
        band_state = "пробой вниз"
    else:
        band_state = "внутри диапазона"

    return {
        "upper_band": round(upper_band.iloc[-1], 2),
        "lower_band": round(lower_band.iloc[-1], 2),
        "band_state": band_state
  }

# ======================= btc_filter.py =======================
# Модуль: BTC Market Sentiment Filter
# Назначение: анализирует тренд, волатильность и импульс BTC,
# чтобы FinAI не торговал против основного движения рынка.

import requests
import pandas as pd
from indicators import macd, stoch_rsi, bollinger_bands
import numpy as np
from datetime import datetime

BYBIT_KLINE = "https://api.bybit.com/v5/market/kline"

# --- вспомогательные функции ---
def safe_get(url, params=None, timeout=10):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("BTC_FILTER: запрос не выполнен:", e)
        return None


def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()


def rsi(series, n=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.ewm(com=n - 1, adjust=False).mean()
    ma_down = down.ewm(com=n - 1, adjust=False).mean()
    rs = ma_up / (ma_down + 1e-9)
    return 100 - (100 / (1 + rs))


# --- основной анализ BTC ---
def fetch_btc_trend(interval="60", limit=200):
    try:
        j = safe_get(BYBIT_KLINE, params={
            "category": "linear",
            "symbol": "BTCUSDT",
            "interval": interval,
            "limit": limit
        })

        if not j or not j.get("result"):
            return {
                "trend": "NEUTRAL",
                "strength": 0,
                "rsi_state": "normal",
                "volatility": "medium"
            }

        data = j["result"]["list"]
        df = pd.DataFrame([{
            "time": int(c[0]),
            "open": float(c[1]),
            "high": float(c[2]),
            "low": float(c[3]),
            "close": float(c[4])
        } for c in data[::-1]])

        # --- Дополнительные индикаторы ---
        macd_res = macd(df)
        stoch_res = stoch_rsi(df)
        boll_res = bollinger_bands(df)

        # --- Определение надёжности сигнала ---
        подтверждения = 0
        if macd_res["macd_trend"] == "текущая_тенденция":
            подтверждения += 1
        if stoch_res["stoch_state"] in ["рост", "перекупленность"] and macd_res["macd_trend"] == "БЫЧИЙ":
            подтверждения += 1
        if stoch_res["stoch_state"] in ["падение", "перепроданность"] and macd_res["macd_trend"] == "МЕДВЕЖИЙ":
            подтверждения += 1

        if подтверждения >= 2:
            надёжность = "высокая"
        elif подтверждения == 1:
            надёжность = "средняя"
        else:
            надёжность = "низкая"

        # --- Возвращаем результат ---
        return {
            "trend": macd_res["macd_trend"],
            "strength": macd_res["strength"],
            "rsi_state": stoch_res["stoch_state"],
            "volatility": boll_res["volatility"],
            "macd": macd_res,
            "stoch_rsi": stoch_res,
            "bollinger": boll_res,
            "reliability": надёжность
        }

    except Exception as e:
        print("Ошибка в btc_filter:", e)
        return {"trend": "NEUTRAL", "strength": 0}

    try:
        j = safe_get(BYBIT_KLINE, params={
            "category": "linear",
            "symbol": "BTCUSDT",
            "interval": interval,
            "limit": limit
        })

        if not j or not j.get("result"):
            return {"trend": "NEUTRAL", "strength": 0, "rsi_state": "normal", "volatility": "medium"}
    "macd": macd_res,
        "stoch_rsi": stoch_res,
        "bollinger": boll_res,
        "надёжность": надежность,
        data = j["result"]["list"]
        df = pd.DataFrame([
            {"ts": int(c[0]), "open": float(c[1]), "high": float(c[2]),
             "low": float(c[3]), "close": float(c[4])}
            for c in data[::-1]
        ])

        # --- EMA анализ ---
        df["ema20"] = ema(df["close"], 20)
        df["ema50"] = ema(df["close"], 50)
        df["ema100"] = ema(df["close"], 100)

        # Определяем тренд по EMA
        if df["ema20"].iloc[-1] > df["ema50"].iloc[-1] > df["ema100"].iloc[-1]:
            trend = "BULLISH"
        elif df["ema20"].iloc[-1] < df["ema50"].iloc[-1] < df["ema100"].iloc[-1]:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"

        # --- сила тренда ---
        ema_diff = abs(df["ema20"].iloc[-1] - df["ema50"].iloc[-1])
        strength = min(1.0, ema_diff / df["close"].iloc[-1] * 80)

        # --- RSI ---
        df["rsi"] = rsi(df["close"], 14)
        rsi_last = df["rsi"].iloc[-1]
        if rsi_last >= 70:
            rsi_state = "overbought"
        elif rsi_last <= 30:
            rsi_state = "oversold"
        else:
            rsi_state = "normal"

        # --- волатильность (ATR-приближение) ---
        df["tr"] = np.maximum(df["high"] - df["low"],
                              np.maximum(abs(df["high"] - df["close"].shift()),
                                         abs(df["low"] - df["close"].shift())))
        atr = df["tr"].rolling(14).mean().iloc[-1]
        vol = atr / df["close"].iloc[-1]

        if vol < 0.005:
            volatility = "low"
        elif vol < 0.02:
            volatility = "medium"
        else:
            volatility = "high"

        print(f"[BTC_FILTER] {datetime.now().strftime('%H:%M:%S')} | Trend: {trend} | Strength: {strength:.2f} | RSI: {rsi_state} | Vol: {volatility}")

        return {
            "trend": trend,
            "strength": round(float(strength), 3),
            "rsi_state": rsi_state,
            "volatility": volatility
        }

    except Exception as e:
        print("BTC_FILTER: ошибка анализа:", e)
        return {"trend": "NEUTRAL", "strength": 0, "rsi_state": "normal", "volatility": "medium"}

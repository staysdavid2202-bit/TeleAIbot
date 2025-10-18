# utils/smart_money.py
import numpy as np
from market_data import fetch_klines
from indicators import ema, rsi, adx

def volume_spike(df, mult=2.5):
    recent_vol = df['volume'].iloc[-1]
    avg_vol = df['volume'].iloc[-30:].mean()
    return recent_vol > avg_vol * mult

def multi_tf_confirmation(symbol):
    """Проверяем тренд на H1 и D1"""
    df_h1 = fetch_klines(symbol, interval="60", limit=300)
    df_d1 = fetch_klines(symbol, interval="1d", limit=300)
    if df_h1.empty or df_d1.empty:
        return None

    df_h1['ema_fast'] = ema(df_h1['close'], 20)
    df_h1['ema_slow'] = ema(df_h1['close'], 50)
    df_d1['ema_fast'] = ema(df_d1['close'], 20)
    df_d1['ema_slow'] = ema(df_d1['close'], 50)

    dir_h1 = "LONG" if df_h1['ema_fast'].iloc[-1] > df_h1['ema_slow'].iloc[-1] else "SHORT"
    dir_d1 = "LONG" if df_d1['ema_fast'].iloc[-1] > df_d1['ema_slow'].iloc[-1] else "SHORT"

    return dir_h1 if dir_h1 == dir_d1 else None

def smart_filter(result, df):
    """Применяет фильтры к анализу"""
    if result is None or df.empty:
        return False

    # Исключаем слабый тренд
    if result["adx"] < 20:
        return False

    # Исключаем RSI в нейтральной зоне
    if 40 < result["rsi"] < 60:
        return False

    # Проверяем всплеск объема
    if not volume_spike(df):
        return False

    # Подтверждение по старшему ТФ
    tf_confirm = multi_tf_confirmation(result["symbol"])
    if not tf_confirm or tf_confirm != result["direction"]:
        return False

    return True

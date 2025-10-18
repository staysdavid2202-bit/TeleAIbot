# -*- coding: utf-8 -*-
"""
smart_money.py
Минимальный Smart Money Concept (SMC) анализ для FinAI
"""

import pandas as pd

def analyze_smc(df: pd.DataFrame):
    """
    Анализирует последние свечи по базовым правилам Smart Money Concept.
    Возвращает сигнал: 'buy', 'sell' или None.
    """

    # Проверка на наличие данных
    if df is None or len(df) < 20:
        return None

    # Убедимся, что есть нужные колонки
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        return None

    # Берём последние 20 свечей
    data = df.tail(20).reset_index(drop=True)

    # Определяем тренд (структура рынка)
    last_high = data['high'].iloc[-1]
    prev_high = data['high'].iloc[-5]
    last_low = data['low'].iloc[-1]
    prev_low = data['low'].iloc[-5]

    if last_high > prev_high and last_low > prev_low:
        market_structure = "bullish"
    elif last_high < prev_high and last_low < prev_low:
        market_structure = "bearish"
    else:
        market_structure = "range"

    # Проверка ликвидности (взятие стопов)
    liquidity_sweep_up = data['high'].iloc[-1] > max(data['high'].iloc[-5:-1])
    liquidity_sweep_down = data['low'].iloc[-1] < min(data['low'].iloc[-5:-1])

    # Проверка на дисбаланс (Fair Value Gap)
    fvg_detected = False
    for i in range(len(data) - 2):
        if data['low'].iloc[i + 2] > data['high'].iloc[i]:
            fvg_detected = True
            break

    # Решение по сигналу
    if market_structure == "bullish" and liquidity_sweep_down and fvg_detected:
        return "buy"
    elif market_structure == "bearish" and liquidity_sweep_up and fvg_detected:
        return "sell"
    else:
        return None

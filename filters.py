def get_market_context(prices, volumes):
    # Упрощённый контекст рынка (для совместимости)
    return "NEUTRAL"


def position_sizing(balance, risk_percent, entry, stop):
    # Оставим только расчёт объёма позиции
    risk_amount = balance * risk_percent
    stop_distance = abs(entry - stop)
    if stop_distance == 0:
        return 0
    position_size = risk_amount / stop_distance
    return round(position_size, 2)


def should_trade(signal, prices, volumes, balance):
    # Без фильтров — все сигналы разрешены
    entry = signal.get("entry_price", 0)
    stop = signal.get("sl", 0)
    position = position_sizing(balance, 0.01, entry, stop)

    print(f"✅ Торговля разрешена без фильтрации | Объём позиции: {position} USDT")
    return True

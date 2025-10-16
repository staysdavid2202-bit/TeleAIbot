# filters.py

def get_market_context(prices, volumes):
    trend_strength = (prices[-1] - prices[-20]) / prices[-20]
    vol_avg = sum(volumes[-10:]) / 10
    vol_now = volumes[-1]
    volatility = abs(prices[-1] - prices[-2]) / prices[-2]

    if trend_strength > 0.02 and vol_now > vol_avg * 1.2:
        return "UPTREND"
    elif trend_strength < -0.02 and vol_now > vol_avg * 1.2:
        return "DOWNTREND"
    elif volatility < 0.005:
        return "ACCUMULATION"
    else:
        return "DISTRIBUTION"


def position_sizing(balance, risk_percent, entry, stop):
    risk_amount = balance * risk_percent
    stop_distance = abs(entry - stop)
    if stop_distance == 0:
        return 0
    position_size = risk_amount / stop_distance
    return round(position_size, 2)


def price_behavior(prices, volumes):
    volatility = abs(prices[-1] - prices[-10]) / prices[-10]
    volume_trend = volumes[-1] / (sum(volumes[-5:]) / 5)

    if volatility < 0.002 or volume_trend < 0.7:
        print("⚠️ Низкая ликвидность или волатильность — сигнал игнорируем.")
        return False
    return True


def psychology_filter(prices):
    avg = sum(prices[-20:]) / 20
    deviation = (prices[-1] - avg) / avg

    if deviation > 0.05:
        print("🚫 Цена перегрета (эмоциональная покупка). Пропускаем.")
        return False
    elif deviation < -0.05:
        print("🚫 Паника на рынке (эмоциональная продажа). Пропускаем.")
        return False
    return True


def indicators_confirmation(signal):
    rsi = signal.get("rsi", 50)
    macd = signal.get("macd", 0)
    direction = signal.get("direction", "").upper()

    if direction == "LONG" and rsi > 55 and macd > 0:
        return True
    elif direction == "SHORT" and rsi < 45 and macd < 0:
        return True
    else:
        print(f"⚠️ Индикаторы не подтверждают сигнал {direction}")
        return False


def should_trade(signal, prices, volumes, balance):
    context = get_market_context(prices, volumes)
    if context == "UPTREND" and signal["direction"] != "LONG":
        return False
    if context == "DOWNTREND" and signal["direction"] != "SHORT":
        return False

    if not price_behavior(prices, volumes):
        return False
    if not psychology_filter(prices):
        return False
    if not indicators_confirmation(signal):
        return False

    entry = signal["entry_price"]
    stop = signal["sl"]
    position = position_sizing(balance, 0.01, entry, stop)

    print(f"✅ Финальное решение: Открыть {signal['direction']} | Контекст: {context} | Объём: {position} USDT")
    return True

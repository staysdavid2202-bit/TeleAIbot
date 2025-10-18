from indicators import ema, rsi, adx, atr
from market_data import fetch_klines

def analyze_symbol(symbol):
    df = fetch_klines(symbol, interval="60", limit=300)
    if df.empty:
        return None

    df['ema_fast'] = ema(df['close'], 20)
    df['ema_slow'] = ema(df['close'], 50)
    df['rsi'] = rsi(df['close'], 14)
    df['adx'] = adx(df, 14)

    direction = "LONG" if df['ema_fast'].iloc[-1] > df['ema_slow'].iloc[-1] else "SHORT"
    trend = "BULL" if direction == "LONG" else "BEAR"

    return {
        "symbol": symbol,
        "direction": direction,
        "trend": trend,
        "rsi": float(df['rsi'].iloc[-1]),
        "adx": float(df['adx'].iloc[-1])
    }

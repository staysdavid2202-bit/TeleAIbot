def detect_order_block(df, lookback=40, range_pct=0.005):
    """Простейший детектор order block (пример)."""
    if df.empty:
        return None
    high = df['high'].rolling(lookback).max().iloc[-1]
    low = df['low'].rolling(lookback).min().iloc[-1]
    return (high + low) / 2

# smart_money.py
import time
import pandas as pd
from market_data import fetch_klines, fetch_orderbook, fetch_funding_rate, fetch_ticker_info

VOLUME_SPIKE_MULT = 2.0
OB_IMBALANCE_THRESHOLD = 0.05

# ----------------- Technical indicators -----------------
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    return 100 - (100 / (1 + rs))

def atr(df, period=14):
    high = df['high']
    low = df['low']
    close = df['close']
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def adx(df, period=14):
    high = df['high']
    low = df['low']
    close = df['close']

    plus_dm = high.diff()
    minus_dm = low.diff().abs()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    atr_val = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).sum() / (atr_val + 1e-9))
    minus_di = 100 * (minus_dm.rolling(period).sum() / (atr_val + 1e-9))
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)) * 100
    return dx.rolling(period).mean()

# ----------------- Orderbook imbalance -----------------
def compute_ob_imbalance(ob, top_n=10):
    try:
        bids = ob.get('bids', [])[:top_n]
        asks = ob.get('asks', [])[:top_n]
        bid_vol = sum([float(b[1]) for b in bids])
        ask_vol = sum([float(a[1]) for a in asks])
        return (bid_vol - ask_vol) / (bid_vol + ask_vol + 1e-9)
    except:
        return 0.0

# ----------------- Dummy order block detection -----------------
def detect_order_block(df, lookback=40, range_pct=0.005):
    if df.empty:
        return None
    return df['low'].rolling(lookback).min().iloc[-1]

# ----------------- Multi-TF features builder -------------------
def build_advanced_features(symbol):
    try:
        df_m15 = fetch_klines(symbol, interval="15m", limit=200)
        df_h1  = fetch_klines(symbol, interval="1h", limit=300)
        df_h4  = fetch_klines(symbol, interval="4h", limit=300)
        df_d1  = fetch_klines(symbol, interval="1d", limit=200)

        if df_h1.empty or df_m15.empty:
            return None

        feat = {}
        feat['symbol'] = symbol
        feat['price'] = float(df_h1['close'].iloc[-1])

        # EMA trends
        feat['ema20_h1'] = float(ema(df_h1['close'],20).iloc[-1])
        feat['ema50_h1'] = float(ema(df_h1['close'],50).iloc[-1])
        feat['trend_h1'] = 1 if feat['ema20_h1'] > feat['ema50_h1'] else -1

        feat['ema20_h4'] = float(ema(df_h4['close'],20).iloc[-1]) if not df_h4.empty else feat['ema20_h1']
        feat['ema50_h4'] = float(ema(df_h4['close'],50).iloc[-1]) if not df_h4.empty else feat['ema50_h1']
        feat['trend_h4'] = 1 if feat['ema20_h4'] > feat['ema50_h4'] else -1

        feat['ema20_d1'] = float(ema(df_d1['close'],20).iloc[-1]) if not df_d1.empty else feat['ema20_h4']
        feat['ema50_d1'] = float(ema(df_d1['close'],50).iloc[-1]) if not df_d1.empty else feat['ema50_h4']
        feat['trend_d1'] = 1 if feat['ema20_d1'] > feat['ema50_d1'] else feat['trend_h4']

        # RSI/ADX/ATR/vol
        feat['rsi_h1'] = float(rsi(df_h1['close'],14).iloc[-1]) if len(df_h1)>14 else 50.0
        feat['adx_h1'] = float(adx(df_h1,14).iloc[-1]) if len(df_h1)>14 else 0.0
        feat['atr_h1'] = float(atr(df_h1,14).iloc[-1]) if len(df_h1)>14 else (feat['price']*0.01)

        vol_avg = df_h1['vol'].rolling(50).mean().iloc[-1] if len(df_h1)>50 else float(df_h1['vol'].mean())
        last_vol = float(df_h1['vol'].iloc[-1])
        feat['vol_spike'] = 1 if last_vol > (vol_avg * VOLUME_SPIKE_MULT) else 0
        feat['vol_ratio'] = last_vol / (vol_avg + 1e-9)

        feat['rsi_m15'] = float(rsi(df_m15['close'],14).iloc[-1]) if len(df_m15)>14 else 50.0

        # order-block H1
        feat['order_block'] = detect_order_block(df_h1, lookback=40, range_pct=0.005)

        # orderbook imbalance
        ob = fetch_orderbook(symbol, limit=25)
        feat['ob_imbalance'] = compute_ob_imbalance(ob, top_n=10)
        feat['ob_conf'] = 1 if abs(feat['ob_imbalance']) > OB_IMBALANCE_THRESHOLD else 0

        # Funding & Open Interest
        feat['funding'] = fetch_funding_rate(symbol)
        try:
            tick = fetch_ticker_info(symbol)
            feat['open_interest'] = float(tick.get('openInterest',0))
        except Exception:
            feat['open_interest'] = 0

        feat['ts'] = int(time.time())
        feat['last_high'] = float(df_h1['high'].iloc[-1])
        feat['last_low'] = float(df_h1['low'].iloc[-1])

        return feat
    except Exception as e:
        print("build_advanced_features error", e)
        return None

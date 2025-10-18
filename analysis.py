# analysis.py
import time
import pandas as pd
import requests
from config import TFS, VOLUME_SPIKE_MULT, OB_IMBALANCE_THRESHOLD
from indicators import ema, rsi  # твои функции для EMA и RSI
from utils import fetch_klines, detect_order_block, fetch_orderbook, compute_ob_imbalance, fetch_funding_rate, fetch_ticker_info
from utils.market_data_helpers import fetch_klines
from utils.orderbook_helpers import detect_order_block, compute_ob_imbalance, fetch_orderbook
from utils.funding_helpers import fetch_funding_rate, fetch_ticker_info

# ATR
def atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# ADX
def adx(df, period=14):
    df = df.copy()
    df['tr'] = atr(df, period)
    df['+dm'] = df['high'].diff()
    df['-dm'] = df['low'].diff() * -1
    df['+dm'] = df['+dm'].where((df['+dm'] > df['-dm']) & (df['+dm']>0), 0)
    df['-dm'] = df['-dm'].where((df['-dm'] > df['+dm']) & (df['-dm']>0), 0)
    df['+di'] = 100 * (df['+dm'].rolling(period).sum() / df['tr'].rolling(period).sum())
    df['-di'] = 100 * (df['-dm'].rolling(period).sum() / df['tr'].rolling(period).sum())
    df['dx'] = (abs(df['+di'] - df['-di']) / (df['+di'] + df['-di'] + 1e-9)) * 100
    return df['dx'].rolling(period).mean()

# Основная функция анализа одной пары
def analyze_symbol(symbol):
    try:
        df_h1 = fetch_klines(symbol, interval=TFS["H1"], limit=200)
        df_m15 = fetch_klines(symbol, interval=TFS["M15"], limit=200)

        if df_h1.empty or df_m15.empty:
            return None

        feat = {}
        feat['symbol'] = symbol
        feat['price'] = float(df_h1['close'].iloc[-1])

        # EMA
        feat['ema20'] = float(ema(df_h1['close'], 20).iloc[-1])
        feat['ema50'] = float(ema(df_h1['close'], 50).iloc[-1])
        feat['trend'] = "LONG" if feat['ema20'] > feat['ema50'] else "SHORT"

        # RSI
        feat['rsi'] = float(rsi(df_h1['close'], 14).iloc[-1])

        # ADX
        adx_val = adx(df_h1, 14)
        feat['adx'] = float(adx_val.iloc[-1]) if len(adx_val) > 0 else 0.0

        # ATR
        atr_val = atr(df_h1, 14)
        feat['atr'] = float(atr_val.iloc[-1]) if len(atr_val) > 0 else feat['price']*0.01

        # Объём
        vol_avg = df_h1['vol'].rolling(50).mean().iloc[-1] if len(df_h1)>50 else float(df_h1['vol'].mean())
        last_vol = float(df_h1['vol'].iloc[-1])
        feat['vol_spike'] = 1 if last_vol > (vol_avg * VOLUME_SPIKE_MULT) else 0
        feat['vol_ratio'] = last_vol / (vol_avg + 1e-9)

        # Order-block H1
        feat['order_block'] = detect_order_block(df_h1, lookback=40, range_pct=0.005)

        # Orderbook imbalance
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

        # Метаданные
        feat['ts'] = int(time.time())
        feat['last_high'] = float(df_h1['high'].iloc[-1])
        feat['last_low'] = float(df_h1['low'].iloc[-1])

        return feat
    except Exception as e:
        print(f"analyze_symbol error for {symbol}: {e}")
        return None

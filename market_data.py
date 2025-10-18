from pybit.unified_trading import HTTP
from config import BYBIT_API_KEY, BYBIT_API_SECRET

session = HTTP(api_key=BYBIT_API_KEY, api_secret=BYBIT_API_SECRET)

def fetch_klines(symbol, interval="60", limit=200):
    try:
        data = session.get_kline(category="linear", symbol=symbol, interval=interval, limit=limit)
        rows = data['result']['list']
        import pandas as pd
        df = pd.DataFrame(rows, columns=[
            "timestamp","open","high","low","close","volume","turnover"
        ])
        df = df.astype(float)
        df['vol'] = df['volume']
        return df
    except Exception as e:
        print(f"fetch_klines error {symbol}: {e}")
        import pandas as pd
        return pd.DataFrame()

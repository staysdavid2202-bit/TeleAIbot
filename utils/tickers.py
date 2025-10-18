import requests

def fetch_ticker_info(symbol):
    try:
        url = "https://api.bybit.com/v2/public/tickers"
        params = {"symbol": symbol}
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()
        if "result" in data and len(data["result"]) > 0:
            return data["result"][0]
        return {}
    except Exception as e:
        print(f"fetch_ticker_info error {symbol}", e)
        return {}

import requests

def fetch_funding_rate(symbol):
    try:
        url = "https://api.bybit.com/v5/market/funding/prev-funding-rate"
        params = {"symbol": symbol}
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return float(data['result']['fundingRate'])
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return 0.0
        raise
    except Exception:
        return 0.0

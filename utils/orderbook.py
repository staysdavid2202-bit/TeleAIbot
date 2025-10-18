import requests

def fetch_orderbook(symbol, limit=25):
    try:
        url = f"https://api.bybit.com/v2/public/orderBook/L2?symbol={symbol}&limit={limit}"
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        return data.get("result", [])
    except Exception as e:
        print(f"fetch_orderbook error {symbol}", e)
        return []

def compute_ob_imbalance(ob, top_n=10):
    """Вычисление дисбаланса в стакане."""
    if not ob:
        return 0
    bids = [float(x['price']) * float(x['size']) for x in ob if x['side'] == 'Buy'][:top_n]
    asks = [float(x['price']) * float(x['size']) for x in ob if x['side'] == 'Sell'][:top_n]
    return (sum(bids) - sum(asks)) / (sum(bids) + sum(asks) + 1e-9)

import requests
import json

def get_all_usdt_futures():
    url = "https://api.bybit.com/v5/market/instruments-info"
    params = {
        "category": "linear",   # USDT фьючерсы
        "instType": "contract"
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("retCode") != 0:
            print("Ошибка API:", data.get("retMsg"))
            return []
        
        symbols = [item.get("symbol") for item in data.get("result", []) if item.get("status") == "Trading"]
        return symbols
    
    except Exception as e:
        print("Ошибка при запросе:", e)
        return []

# Получаем список всех активных USDT-фьючерсов
usdt_futures = get_all_usdt_futures()
print(f"Найдено {len(usdt_futures)} активных пар.")

# Сохраняем в JSON для дальнейшего использования в боте
with open("bybit_usdt_futures.json", "w") as f:
    json.dump(usdt_futures, f, indent=4)

# Пример использования
for sym in usdt_futures:
    print(sym)

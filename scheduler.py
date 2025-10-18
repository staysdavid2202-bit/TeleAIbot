# scheduler.py
import time
from datetime import datetime
from config import SYMBOLS, MOLDOVA_TZ, SEND_INTERVAL_MINUTES, CHAT_ID, FRIEND_CHAT_ID
from smart_money import build_advanced_features
from telegram_bot import send_signal

def scheduler_loop():
    print("📅 Планировщик FinAI запущен.")
    last_run = 0

    while True:
        now = datetime.now(MOLDOVA_TZ)
        if (time.time() - last_run) > SEND_INTERVAL_MINUTES * 60:
            print(f"⏰ [{now.strftime('%H:%M')}] Генерация сигналов...")

            for sym in SYMBOLS:
                # Если SYMBOLS хранит списки, достаём первый элемент
                if isinstance(sym, list):
                    sym = sym[0]
                res = build_advanced_features(sym)
                if res:
                    # Пропускаем пары с неопределённым направлением (например EMA20=EMA50)
                    if res.get('trend_h1') is None:
                        print(f"⚠️ Пропущена неопределённая пара {sym}")
                        continue
                    send_signal(res)
                else:
                    print(f"⚠️ Нет данных для {sym}")

            last_run = time.time()
        time.sleep(60)

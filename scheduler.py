# scheduler.py
import time
from datetime import datetime
from config import SYMBOLS, MOLDOVA_TZ, SEND_INTERVAL_MINUTES
from analysis import analyze_symbol
from telegram_bot import send_signal

def scheduler_loop():
    print("📅 Планировщик FinAI запущен.")
    last_run = 0

    while True:
        now = datetime.now(MOLDOVA_TZ)
        if (time.time() - last_run) > SEND_INTERVAL_MINUTES * 60:
            print(f"⏰ [{now.strftime('%H:%M')}] Анализ рынка...")
            for sym_list in SYMBOLS:
                symbol = sym_list[0]  # берем строку из вложенного списка
                try:
                    res = analyze_symbol(symbol)
                    if res:
                        send_signal(res)
                except Exception as e:
                    print(f"❌ Ошибка при анализе {symbol}: {e}")
            last_run = time.time()
        time.sleep(60)

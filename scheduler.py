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
            for sym in SYMBOLS:
                res = analyze_symbol(sym)
                if res:
                    send_signal(res)
            last_run = time.time()
        time.sleep(60)

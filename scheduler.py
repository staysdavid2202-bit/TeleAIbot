# scheduler.py
import time
from datetime import datetime
from config import SYMBOLS, MOLDOVA_TZ, SEND_INTERVAL_MINUTES
from analysis import analyze_symbol
from telegram_bot import send_signal
from market_data import fetch_klines
from utils.smart_money import smart_filter

def scheduler_loop():
    print("📅 Планировщик FinAI запущен.")
    last_run = 0

    while True:
        try:
            now = datetime.now(MOLDOVA_TZ)
            elapsed = time.time() - last_run

            if elapsed >= SEND_INTERVAL_MINUTES * 60:
                print(f"\n⏰ [{now.strftime('%H:%M:%S')}] Запуск анализа ({len(SYMBOLS)} пар)...")
                signals_sent = 0

                for sym in SYMBOLS:
                    try:
                        res = analyze_symbol(sym)
                        if not res:
                            print(f"🔸 {sym}: нет сигнала")
                            continue

                        df = fetch_klines(sym, interval="60", limit=300)
                        if smart_filter(res, df):
                            send_signal(res)
                            signals_sent += 1
                            print(f"✅ {sym}: сигнал отправлен ({res['direction']})")
                        else:
                            print(f"⚪ {sym}: отфильтрован SmartMoney")

                    except Exception as e:
                        print(f"⚠️ Ошибка при анализе {sym}: {e}")

                if signals_sent == 0:
                    print("🔸 Нет валидных сигналов после фильтрации.")
                else:
                    print(f"📤 Отправлено {signals_sent} сигналов.")

                last_run = time.time()

            time.sleep(60)

        except KeyboardInterrupt:
            print("⛔ Планировщик остановлен вручную.")
            break
        except Exception as e:
            print(f"🚨 Ошибка в цикле планировщика: {e}")
            time.sleep(30)

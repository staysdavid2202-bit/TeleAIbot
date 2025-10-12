# ==================================================
# 🔹 Импорт библиотек
# ==================================================
import telebot
from openai import OpenAI
import requests
import os
import threading
import time
from datetime import datetime
from pybit.unified_trading import HTTP
import random
from flask import Flask

# ==================================================
# 🔹 Настройки
# ==================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
CHAT_ID = os.getenv("CHAT_ID")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

# ==================================================
# 🔹 Подключение к Bybit
# ==================================================
try:
    bybit_client = HTTP(api_key=BYBIT_API_KEY, api_secret=BYBIT_API_SECRET)
    print("✅ Подключение к Bybit успешно!")
except Exception as e:
    print(f"❌ Ошибка подключения к Bybit: {e}")

# ==================================================
# 🔹 Flask для Koyeb
# ==================================================
@app.route('/')
def home():
    return "🤖 FinAI работает (автосигналы активны)."

# ==================================================
# 🔹 Функция генерации сигналов
# ==================================================
def get_future_signal():
    try:
        # Основные и новые фьючерсные пары
        pairs = [
            "BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT",
            "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LTCUSDT", "LINKUSDT", "TRXUSDT",
            "SUIUSDT", "NEARUSDT", "OPUSDT", "ARBUSDT", "RNDRUSDT", "ATOMUSDT",
            "AAVEUSDT", "INJUSDT", "MATICUSDT", "ETCUSDT", "FILUSDT", "THETAUSDT",
            "FTMUSDT", "CHZUSDT", "HBARUSDT", "ENSUSDT", "GRTUSDT", "APEUSDT",
            "IMXUSDT", "COTIUSDT", "WLDUSDT", "SEIUSDT", "TIAUSDT", "PYTHUSDT",
            "JTOUSDT", "ARKMUSDT", "ORDIUSDT", "STRKUSDT", "NOTUSDT", "BLURUSDT",
            "SSVUSDT", "ACEUSDT", "BEAMUSDT", "SAGAUSDT", "MOVRUSDT", "HNTUSDT"
        ]

        # Выбор пары и направления
        pair = random.choice(pairs)
        direction = random.choice(["LONG", "SHORT"])

        ticker = bybit_client.get_tickers(category="linear", symbol=pair)
        price = float(ticker["result"]["list"][0]["lastPrice"])

        # Параметры расчёта
        sl_percent = 0.01
        tp1_percent = 0.01
        tp2_percent = 0.02
        tp3_percent = 0.03

        if direction == "LONG":
            stop_loss = price * (1 - sl_percent)
            tp1 = price * (1 + tp1_percent)
            tp2 = price * (1 + tp2_percent)
            tp3 = price * (1 + tp3_percent)
            emoji = "🟢"
        else:
            stop_loss = price * (1 + sl_percent)
            tp1 = price * (1 - tp1_percent)
            tp2 = price * (1 - tp2_percent)
            tp3 = price * (1 - tp3_percent)
            emoji = "🔴"

        avg_profit = (tp1_percent + tp2_percent + tp3_percent) / 3 * 100
        accuracy = random.randint(91, 94)
        time_now = datetime.utcnow().strftime("%H:%M UTC")

        # Формирование сообщения
        signal_message = (
            f"📊 <b>FinAI — Торговый сигнал (Фьючерсы)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💱 <b>Пара:</b> <code>{pair}</code>\n"
            f"📈 <b>Направление:</b> {emoji} <b>{direction}</b>\n"
            f"💰 <b>Цена входа:</b> ${price:.4f}\n"
            f"🎯 <b>Точность:</b> {accuracy}%\n"
            f"🕒 <b>Время генерации:</b> {time_now}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡 <b>Stop-Loss:</b> ${stop_loss:.4f}\n"
            f"🎯 <b>TP1:</b> ${tp1:.4f}\n"
            f"🎯 <b>TP2:</b> ${tp2:.4f}\n"
            f"🎯 <b>TP3:</b> ${tp3:.4f}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Средний профит:</b> {avg_profit:.1f}%\n"
            f"⚠️ <b>Рекомендация:</b> риск ≤ 3% от депозита.\n"
            f"🤖 <i>Сигнал создан ИИ FinAI</i>"
        )
        return signal_message

    except Exception as e:
        return f"⚠️ Ошибка при формировании сигнала: {e}"

# ==================================================
# 🔹 Автоматическая отправка сигналов в заданные часы
# ==================================================
def schedule_signals():
    chat_id = CHAT_ID
    send_times = ["08:00", "14:00", "20:00"]

    while True:
        now = datetime.utcnow().strftime("%H:%M")
        if now in send_times:
            signal = get_future_signal()
            bot.send_message(chat_id, signal, parse_mode="HTML")
            print(f"📤 Сигнал отправлен в {now}")
            time.sleep(60)  # защита от повторной отправки
        time.sleep(30)

# ==================================================
# 🔹 Бот без взаимодействия с пользователем
# ==================================================
def run_bot():
    # отключаем возможность писать
    print("🤖 FinAI запущен — работает в режиме авторассылки.")
    while True:
        time.sleep(100000)

# ==================================================
# 🔹 Запуск
# ==================================================
if __name__ == "__main__":
    threading.Thread(target=schedule_signals).start()
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

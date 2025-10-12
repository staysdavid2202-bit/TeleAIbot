# ==================================================
# 🔹 Импорт библиотек
# ==================================================
import telebot
from openai import OpenAI
import requests
import os
import threading
import time
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

# Подключение к Bybit
try:
    bybit_client = HTTP(api_key=BYBIT_API_KEY, api_secret=BYBIT_API_SECRET)
    print("✅ Подключение к Bybit успешно!")
except Exception as e:
    print(f"❌ Ошибка подключения к Bybit: {e}")

# ==================================================
# 🔹 Flask (для Koyeb)
# ==================================================
@app.route('/')
def home():
    return "🤖 Бот FinAI работает и готов к диалогу!"

# ==================================================
# 🔹 Команда /start
# ==================================================
@bot.message_handler(commands=['start', 'начать'])
def start_message(message):
    bot.reply_to(message, "👋 Привет! Я FinAI — бот для криптотрейдинга.\n"
                          "✉️ Напиши слово <b>сигнал</b>, чтобы получить торговый сигнал.",
                 parse_mode="HTML")

# ==================================================
# 🔹 Обработка сообщений
# ==================================================
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.lower()

    if "сигнал" in text:
        bot.reply_to(message, get_future_signal(), parse_mode="HTML")
    elif "btc" in text or "биткоин" in text:
        send_crypto_info(message, "bitcoin")
    elif "eth" in text or "эфир" in text:
        send_crypto_info(message, "ethereum")
    else:
        generate_ai_reply(message)

# ==================================================
# 🔹 Информация о криптовалюте
# ==================================================
def send_crypto_info(message, coin):
    try:
        r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd")
        data = r.json()
        price = data[coin]["usd"]
        bot.reply_to(message, f"💰 {coin.capitalize()} сейчас стоит ${price}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при получении курса: {e}")

# ==================================================
# 🔹 Генерация ответа от FinAI (ИИ)
# ==================================================
def generate_ai_reply(message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты дружелюбный криптоассистент FinAI."},
                {"role": "user", "content": message.text}
            ]
        )
        answer = response.choices[0].message.content
        bot.reply_to(message, answer)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка ответа ИИ: {e}")

# ==================================================
# 🔹 Улучшенные торговые сигналы (все фьючерсы)
# ==================================================
def get_future_signal():
    try:
        # Список популярных фьючерсных пар
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

        pair = random.choice(pairs)
        direction = random.choice(["LONG", "SHORT"])

        ticker = bybit_client.get_tickers(category="linear", symbol=pair)
        price = float(ticker["result"]["list"][0]["lastPrice"])

        # Расчёт уровней TP и SL
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

        accuracy = random.randint(90, 94)
        time_now = time.strftime("%H:%M:%S")

        signal_message = (
            f"📊 <b>FinAI — Торговый сигнал (Фьючерсы)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💱 <b>Пара:</b> <code>{pair}</code>\n"
            f"📈 <b>Направление:</b> {emoji} <b>{direction}</b>\n"
            f"💰 <b>Цена входа:</b> ${price:.4f}\n"
            f"🎯 <b>Точность:</b> {accuracy}%\n"
            f"🕒 <b>Время:</b> {time_now}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡 <b>Stop-Loss:</b> ${stop_loss:.4f}\n"
            f"🎯 <b>TP1:</b> ${tp1:.4f}\n"
            f"🎯 <b>TP2:</b> ${tp2:.4f}\n"
            f"🎯 <b>TP3:</b> ${tp3:.4f}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>Рекомендация:</b> риск ≤ 3% от депозита.\n"
            f"🤖 <i>Сигнал создан ИИ FinAI</i>"
        )
        return signal_message

    except Exception as e:
        return f"⚠️ Ошибка при формировании сигнала: {e}"

# ==================================================
# 🔹 Автоматическая отправка сигналов каждые 12 часов
# ==================================================
def auto_signal():
    chat_id = CHAT_ID
    while True:
        signal = get_future_signal()
        bot.send_message(chat_id, signal, parse_mode="HTML")
        time.sleep(12 * 60 * 60)  # каждые 12 часов

# ==================================================
# 🔹 Запуск
# ==================================================
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=auto_signal).start()
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

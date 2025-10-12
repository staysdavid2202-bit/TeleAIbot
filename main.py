import telebot
from openai import OpenAI
import requests
import os
import threading
import time
from flask import Flask
from pybit.unified_trading import HTTP   # ✅ Pybit библиотека

# ======================================
# 🔧 Настройки
# ======================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)

# ======================================
# 📊 Подключаемся к Bybit через Pybit
# ======================================
try:
    bybit_client = HTTP(
        testnet=False,
        api_key=BYBIT_API_KEY,
        api_secret=BYBIT_API_SECRET
    )
    print("✅ Подключение к Bybit успешно!")
except Exception as e:
    print(f"⚠️ Ошибка подключения к Bybit: {e}")

# ======================================
# 🌐 Flask-сервер
# ======================================
@app.route('/')
def home():
    return "🤖 Бот работает и готов к диалогу!"

# ======================================
# 🚀 Команда /start
# ======================================
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "Привет! 🤖 Я твой ИИ-бот. Могу рассказать про крипту, нефть или выдать торговый сигнал 📈")

# ======================================
# 💬 Ответы на сообщения
# ======================================
@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    text = message.text.lower()

    if "биткоин" in text or "bitcoin" in text:
        send_crypto_info(message, "bitcoin")
    elif "эфир" in text or "ethereum" in text:
        send_crypto_info(message, "ethereum")
    elif "золото" in text:
        send_commodity_info(message, "золото")
    elif "нефть" in text:
        send_commodity_info(message, "нефть")
    elif "сигнал" in text:
        bot.reply_to(message, get_future_signal())
    else:
        generate_ai_reply(message)

# ======================================
# 💰 Курс криптовалюты
# ======================================
def send_crypto_info(message, coin):
    try:
        r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd")
        data = r.json()
        price = data[coin]["usd"]
        bot.reply_to(message, f"💰 {coin.capitalize()} сейчас стоит {price}$")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при получении курса: {e}")

# ======================================
# 📦 Инфо по товарам
# ======================================
def send_commodity_info(message, item):
    bot.reply_to(message, f"📦 {item.capitalize()} — популярный актив, подходящий для анализа рынка!")

# ======================================
# 🗣️ Озвучка текста
# ======================================
def speak_text(text):
    try:
        audio = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text
        )
        with open("voice.ogg", "wb") as f:
            f.write(audio.read())
        return "voice.ogg"
    except Exception as e:
        print(f"⚠️ Ошибка озвучки: {e}")
        return None

# ======================================
# 🤖 Генерация ответа ИИ
# ======================================
def generate_ai_reply(message):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты дружелюбный Telegram-бот помощник."},
                {"role": "user", "content": message.text}
            ]
        )
        reply = completion.choices[0].message.content
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка ИИ-ответа: {e}")

# ======================================
# 📈 Сигналы для Bybit
# ======================================
def get_future_signal():
    """Создаёт торговый сигнал по фьючерсам"""
    try:
        symbol = "BTCUSDT"
        ticker = bybit_client.get_tickers(category="linear", symbol=symbol)
        last_price = float(ticker["result"]["list"][0]["lastPrice"])

        import random
        direction = random.choice(["LONG", "SHORT"])
        return f"📊 Торговый сигнал: {direction} по {symbol} при цене {last_price}$"
    except Exception as e:
        return f"⚠️ Ошибка при создании сигнала: {e}"

# ======================================
# ⏰ Автосигнал каждые 12 часов
# ======================================
def auto_signal():
    chat_id = os.getenv("CHAT_ID")  # вставь свой Chat ID в переменные окружения
    while True:
        signal = get_future_signal()
        bot.send_message(chat_id, signal)
        time.sleep(12 * 60 * 60)

# ======================================
# 🚀 Запуск бота и Flask
# ======================================
def run_bot():
    bot.infinity_polling()

# Фоновая нить
thread = threading.Thread(target=run_bot)
thread.start()

# Flask для Koyeb
port = int(os.getenv("PORT", 8000))
app.run(host="0.0.0.0", port=port)

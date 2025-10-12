import telebot
from openai import OpenAI
import requests
import os
from flask import Flask
import threading
import bybit
import random
import time

# ===============================
# 🔑 Настройки
# ===============================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

# Подключаемся к Bybit API
try:
    bybit_client = bybit.bybit(test=False, api_key=BYBIT_API_KEY, api_secret=BYBIT_API_SECRET)
    print("✅ Bybit подключён успешно!")
except Exception as e:
    print(f"⚠️ Ошибка при подключении к Bybit: {e}")

# ===============================
# 🌐 Flask-сервер
# ===============================
@app.route('/')
def home():
    return "🤖 Бот работает и готов к диалогу!"

# ===============================
# 🧭 Команда /start
# ===============================
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "Привет! 🌟 Я твой ИИ-бот. Могу рассказать про крипту, золото, нефть и даже дать торговый сигнал 🚀")

# ===============================
# 📩 Ответы на сообщения
# ===============================
@bot.message_handler(func=lambda msg: True)
def reply_message(message):
    text = message.text.lower()

    if "биткоин" in text or "bitcoin" in text:
        send_crypto_info(message, "bitcoin")
    elif "эфир" in text or "ethereum" in text:
        send_crypto_info(message, "ethereum")
    elif "золото" in text or "gold" in text:
        send_commodity_info(message, "gold")
    elif "нефть" in text or "oil" in text:
        send_commodity_info(message, "oil")
    elif "сигнал" in text:
        bot.reply_to(message, get_future_signal())
    else:
        generate_ai_reply(message)

# ===============================
# 💹 Получение курса криптовалют
# ===============================
def send_crypto_info(message, coin):
    try:
        r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd")
        data = r.json()
        price = data[coin]["usd"]
        bot.reply_to(message, f"💰 {coin.capitalize()} сейчас стоит ${price}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при получении данных: {e}")

# ===============================
# 💎 Информация о сырье
# ===============================
def send_commodity_info(message, commodity):
    bot.reply_to(message, f"{commodity.capitalize()} — один из популярных активов. ⚙️ Скоро добавлю реальные котировки!")

# ===============================
# 🔊 Функция озвучки текста
# ===============================
def speak_text(text):
    try:
        response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text
        )
        audio_bytes = response.read()
        filename = "voice.ogg"
        with open(filename, "wb") as f:
            f.write(audio_bytes)
        return filename
    except Exception as e:
        print(f"⚠️ Ошибка при создании аудио: {e}")
        return None

# ===============================
# 🧠 Генерация ответа ИИ
# ===============================
def generate_ai_reply(message):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты дружелюбный Telegram-ассистент, говоришь просто и по существу."},
                {"role": "user", "content": message.text}
            ]
        )

        answer = response.choices[0].message.content
        bot.reply_to(message, answer)

        audio_file = speak_text(answer)
        if audio_file:
            with open(audio_file, "rb") as f:
                bot.send_voice(message.chat.id, f)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при ответе ИИ: {e}")

# ===============================
# 📊 Функции для сигналов Bybit
# ===============================
def get_future_signal():
    """Создаёт простой торговый сигнал по фьючерсам"""
    try:
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        symbol = random.choice(symbols)
        data = bybit_client.Market.Market_symbolInfo(symbol=symbol).result()[0]
        last_price = float(data['result'][0]['last_price'])
        
        if random.random() > 0.5:
            signal = f"📈 LONG {symbol} по цене {last_price}"
        else:
            signal = f"📉 SHORT {symbol} по цене {last_price}"

        return f"💡 Торговый сигнал:\n{signal}"
    except Exception as e:
        return f"⚠️ Ошибка при генерации сигнала: {e}"

def auto_signal():
    """Отправляет сигналы каждые 12 часов"""
    chat_id = os.getenv("CHAT_ID")  # добавь CHAT_ID в переменные окружения
    while True:
        signal = get_future_signal()
        bot.send_message(chat_id, signal)
        time.sleep(12 * 60 * 60)  # каждые 12 часов

# ===============================
# 🚀 Запуск Telegram-бота
# ===============================
def run_bot():
    bot.infinity_polling()

thread = threading.Thread(target=run_bot)
thread.start()

# ===============================
# 🌍 Flask-сервер (для Koyeb)
# ===============================
port = int(os.getenv("PORT", 8000))
app.run(host="0.0.0.0", port=port)

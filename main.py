import telebot
import requests
import openai
import os
from flask import Flask
import threading

# Настройки
openai.api_key = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

# Команда /start
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "Привет! 🤖 Я твой ИИ-бот. Напиши что-нибудь!")

# Ответы на сообщения
@bot.message_handler(func=lambda msg: True)
def reply_message(message):
    text = message.text.lower()

    if "биткоин" in text or "bitcoin" in text:
        bot.reply_to(message, "🪙 Биткоин — это известная криптовалюта!")
    elif "курс" in text:
        try:
            r = requests.get("https://api.coindesk.com/v1/bpi/currentprice/USD.json")
            price = r.json()["bpi"]["USD"]["rate"]
            bot.reply_to(message, f"💰 Текущий курс биткоина: {price} USD")
        except:
            bot.reply_to(message, "Не удалось получить курс 😕")
    else:
        bot.reply_to(message, "🙂 Я учусь! Спроси про инвестиции или курс валют 😉")

# Запуск телеграм-бота в отдельном потоке
def run_bot():
    bot.infinity_polling()

thread = threading.Thread(target=run_bot)
thread.start()

# Flask-сервер (для Koyeb)
port = int(os.getenv("PORT", 8000))
app.run(host="0.0.0.0", port=port)

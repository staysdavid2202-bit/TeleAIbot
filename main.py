import telebot
import requests
from openai import OpenAI
import os
from flask import Flask
import threading

# Настройки
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

@app.route('/')
def home():
    return "🤖 Бот работает и готов к диалогу!"

# Команда /start
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "Привет! 🌟 Я твой ИИ-бот. Могу рассказать про курс валют, инвестиции или просто поболтать!")

# Ответы на сообщения
@bot.message_handler(func=lambda msg: True)
def reply_message(message):
    text = message.text.lower()

    if "биткоин" in text or "bitcoin" in text:
        bot.reply_to(message, "🪙 Биткоин — популярная криптовалюта с ограниченной эмиссией!")
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd")
            data = r.json()
            btc = data["bitcoin"]["usd"]
            eth = data["ethereum"]["usd"]
            bot.reply_to(message, f"💰 Курс:\n₿ BTC: {btc}$\n🦄 ETH: {eth}$")
        except Exception as e:
            bot.reply_to(message, f"⚠️ Не удалось получить курс.\nОшибка: {e}")
    else:
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": message.text}]
            )
            answer = response.choices[0].message.content
            bot.reply_to(message, answer)
        except Exception as e:
            bot.reply_to(message, f"⚠️ Я пока не могу ответить. Проверь, что ключ OpenAI указан правильно.\nОшибка: {e}")

# Запуск телеграм-бота в отдельном потоке
def run_bot():
    bot.infinity_polling()

thread = threading.Thread(target=run_bot)
thread.start()

# Flask-сервер (для Koyeb)
port = int(os.getenv("PORT", 8000))
app.run(host="0.0.0.0", port=port)

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
        bot.reply_to(message, "🪙 Биткоин — популярная криптовалюта с ограниченной эмиссией.")
    elif "курс" in text or "валют" in text:
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd")
            data = r.json()
            btc = data["bitcoin"]["usd"]
            eth = data["ethereum"]["usd"]
            bot.reply_to(message, f"💰 BTC: {btc}$\n🧠 ETH: {eth}$")
        except Exception as e:
            bot.reply_to(message, f"Не удалось получить курс 😕\nОшибка: {e}")
    else:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": message.text}]
            )
            answer = response.choices[0].message.content
            bot.reply_to(message, answer)
        except Exception as e:
            bot.reply_to(message, "⚠️ Я пока не могу ответить. Проверь, что ключ OpenAI указан правильно.")

# Запуск телеграм-бота в отдельном потоке
def run_bot():
    bot.infinity_polling()

thread = threading.Thread(target=run_bot)
thread.start()

# Flask-сервер (для Koyeb)
port = int(os.getenv("PORT", 8000))
app.run(host="0.0.0.0", port=port)

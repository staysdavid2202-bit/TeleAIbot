import telebot
import requests
import openai
import os
from flask import Flask

# Настройки
openai.api_key = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# Flask сервер для Koyeb
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# Команда /start
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "Привет! 🤖 Я твой ИИ-бот. Напиши что-нибудь!")

# Ответы на сообщения
@bot.message_handler(func=lambda message: True)
def reply_to_user(message):
    text = message.text.strip().lower()

    if "биткоин" in text or "bitcoin" in text:
        bot.reply_to(message, "₿ Биткоин — это известная криптовалюта!")
    elif "курс" in text:
        try:
            r = requests.get("https://api.coindesk.com/v1/bpi/currentprice.json").json()
            price = r["bpi"]["USD"]["rate"]
            bot.reply_to(message, f"💰 Текущий курс биткоина: {price} USD")
        except:
            bot.reply_to(message, "Не удалось получить курс 😕")
    else:
        bot.reply_to(message, "Я учусь отвечать! Спроси про биткоин 😊")

# Запуск
if __name__ == "__main__":
    import threading
    import time

    # Запускаем телеграм-бота в отдельном потоке
    def run_bot():
        bot.infinity_polling()

    thread = threading.Thread(target=run_bot)
    thread.start()

    # Flask-сервер (чтобы Koyeb видел, что приложение работает)
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

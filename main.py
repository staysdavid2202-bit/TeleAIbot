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
    bot.reply_to(message, "Привет! 🌞 Я твой ИИ-бот. Могу рассказать про инвестиции, анализ рынка или просто поболтать!")

# Основная логика ответов
@bot.message_handler(func=lambda msg: True)
def reply_message(message):
    text = message.text.lower()

    # Анализ рынка
    if "биткоин" in text or "bitcoin" in text:
        send_crypto_info(message, "bitcoin")
    elif "эфир" in text or "ethereum" in text:
        send_crypto_info(message, "ethereum")
    elif "золото" in text or "gold" in text:
        send_commodity_info(message, "gold")
    elif "нефть" in text or "oil" in text:
        send_commodity_info(message, "oil")
    else:
        generate_ai_reply(message)

# Получение курса криптовалют
def send_crypto_info(message, symbol):
    try:
        r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd")
        data = r.json()
        price = data[symbol]["usd"]
        bot.reply_to(message, f"💰 {symbol.capitalize()} сейчас стоит ${price:,}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Не удалось получить данные по {symbol}. Ошибка: {e}")

# Курс золота и нефти
def send_commodity_info(message, asset):
    try:
        if asset == "gold":
            url = "https://commodities-api.com/api/latest?access_key=YOUR_ACCESS_KEY&symbols=XAU"
            bot.reply_to(message, "🏅 Курс золота сейчас обновляется... (добавь свой ключ в API commodities-api.com)")
        elif asset == "oil":
            url = "https://api.api-ninjas.com/v1/commodities?symbol=WTI_OIL"
            bot.reply_to(message, "🛢 Курс нефти скоро появится... (можно добавить API ключ для нефти)")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при получении данных: {e}")

# Ответ от ChatGPT
def generate_ai_reply(message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message.text}]
        )
        answer = response.choices[0].message.content
        bot.reply_to(message, answer)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Я пока не могу ответить. Ошибка: {e}")

# Запуск телеграм-бота в отдельном потоке
def run_bot():
    bot.infinity_polling()

thread = threading.Thread(target=run_bot)
thread.start()

# Flask-сервер для Koyeb
port = int(os.getenv("PORT", 8000))
app.run(host="0.0.0.0", port=port)

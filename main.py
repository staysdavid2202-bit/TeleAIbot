import telebot
import requests
import os
import openai
import os
openai.api_key = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# Обработка команды /start
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "Привет! 🤖 Я твой ИИ-бот. Напиши мне любой вопрос — попробую ответить!")

# Основная логика ответов
@bot.message_handler(func=lambda message: True)
def reply_to_user(message):
    user_text = message.text.strip().lower()

    # Примеры "умных" ответов без OpenAI
    if "биткоин" in user_text or "bitcoin" in user_text:
        bot.reply_to(message, "Биткоин — это первая и самая известная криптовалюта. Хочешь, расскажу про текущий курс?")
    elif "курс" in user_text:
        try:
            r = requests.get("https://api.coindesk.com/v1/bpi/currentprice.json").json()
            price = r["bpi"]["USD"]["rate"]
            bot.reply_to(message, f"💰 Текущий курс биткоина: {price} USD")
        except:
            bot.reply_to(message, "Не удалось получить курс 😕 Попробуй позже.")
    elif "привет" in user_text:
        bot.reply_to(message, "Привет! Как настроение?")
    elif "как дела" in user_text:
        bot.reply_to(message, "У меня всё отлично, я бот 😄 А у тебя?")
    else:
        bot.reply_to(message, "Пока я только учусь. Но можешь спросить меня про биткоин или курс валют 😉")

# Запуск
bot.infinity_polling()

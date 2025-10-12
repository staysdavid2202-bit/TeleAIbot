import os
import time
import telebot

# Делаем небольшую паузу, чтобы сервер успел запуститься
time.sleep(5)

# Получаем токен из переменной окружения Koyeb
TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! 🤖 Я твой ИИ-бот. Напиши мне что-нибудь!")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Ты сказал: {message.text}")

print("Бот запущен...")
bot.polling(non_stop=True)

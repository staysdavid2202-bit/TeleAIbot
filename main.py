import os
import time

# Устанавливаем нужную библиотеку
os.system("pip install pyTelegramBotAPI")
time.sleep(5)

import telebot

# ВСТАВЬ сюда свой токен от BotFather
TOKEN = "сюда_вставь_твой_токен"

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! 🤖 Я твой ИИ-бот. Напиши мне что-нибудь!")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Ты сказал: {message.text}")

print("Бот запущен...")
bot.polling()

import telebot
import requests
from openai import OpenAI
import os
from flask import Flask
import threading
import base64  # 🔊 добавлено для голосового ответа

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

def send_crypto_info(message, coin):
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd")
        data = r.json()
        btc = data["bitcoin"]["usd"]
        eth = data["ethereum"]["usd"]
        bot.reply_to(message, f"💰 Курс:\n₿ BTC: {btc}$\n🌐 ETH: {eth}$")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Не удалось получить курс.\nОшибка: {e}")

def send_commodity_info(message, commodity):
    try:
        bot.reply_to(message, f"📊 {commodity.capitalize()} — один из ключевых активов. Могу рассказать подробнее, если хочешь!")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при получении данных по {commodity}: {e}")

# 🎤 Функция озвучки текста
def speak_text(text):
    try:
        response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",  # можно заменить на 'verse', 'sage' и др.
            input=text
        )
        audio_data = response.audio
        audio_bytes = base64.b64decode(audio_data)
        filename = "voice.ogg"
        with open(filename, "wb") as f:
            f.write(audio_bytes)
        return filename
    except Exception as e:
        print(f"Ошибка при создании аудио: {e}")
        return None

# Ответ ИИ
def generate_ai_reply(message):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты дружелюбный Telegram-ассистент."},
                {"role": "user", "content": message.text}
            ]
        )
        answer = response.choices[0].message.content
        bot.reply_to(message, answer)

        # 🔊 Добавляем голосовой ответ
        audio_file = speak_text(answer)
        if audio_file:
            with open(audio_file, "rb") as f:
                bot.send_voice(message.chat.id, f)

    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при ответе ИИ: {e}")

# Запуск телеграм-бота в отдельном потоке
def run_bot():
    bot.infinity_polling()

thread = threading.Thread(target=run_bot)
thread.start()

# Flask-сервер (для Koyeb)
port = int(os.getenv("PORT", 8000))
app.run(host="0.0.0.0", port=port)

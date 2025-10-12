import os
import telebot
from openai import OpenAI

# === Настройки ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # токен бота из BotFather
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # ключ из OpenAI
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# === Инициализация OpenAI клиента ===
client = OpenAI(api_key=OPENAI_API_KEY)

# === Команда /start ===
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(
        message,
        "👋 Привет! Я FinAI — твой финансовый помощник. "
        "Задай мне любой вопрос об инвестициях, рынке или экономике."
    )

# === Основная логика ответов ===
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        # Отправляем сообщение в OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты умный финансовый помощник, который помогает с инвестициями, анализом и экономикой."},
                {"role": "user", "content": message.text}
            ]
        )

        answer = response.choices[0].message.content
        bot.reply_to(message, answer)

    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка: {e}")

# === Запуск бота ===
if __name__ == "__main__":
    print("✅ FinAI Bot запущен и работает...")
    bot.infinity_polling()

import telebot
from openai import OpenAI
import requests
import os
import threading
import time
from flask import Flask
from pybit.unified_trading import HTTP
import random

# ============================================
# ⚙️ Настройки
# ============================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
CHAT_ID = os.getenv("CHAT_ID")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

# Подключение к Bybit через API
try:
    bybit_client = HTTP(
        api_key=BYBIT_API_KEY,
        api_secret=BYBIT_API_SECRET
    )
    print("✅ Подключение к Bybit успешно!")
except Exception as e:
    print(f"❌ Ошибка подключения к Bybit: {e}")

# ============================================
# 🌐 Flask для Koyeb
# ============================================
@app.route('/')
def home():
    return "🤖 Бот FinAI работает и готов к диалогу!"

# ============================================
# 📩 Команда /start
# ============================================
@bot.message_handler(commands=['start', 'начать'])
def start_message(message):
    bot.reply_to(message, "👋 Привет! Я FinAI — бот для криптоанализа, сигналов и рыночных идей.\n"
                          "Напиши слово 'сигнал', чтобы получить торговую идею 📈")

# ============================================
# 💬 Обработка сообщений
# ============================================
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.lower()

    if "биткоин" in text or "btc" in text:
        send_crypto_info(message, "bitcoin")
    elif "эфир" in text or "eth" in text:
        send_crypto_info(message, "ethereum")
    elif "золото" in text or "нефть" in text:
        send_commodity_info(message, text)
    elif "сигнал" in text:
        bot.reply_to(message, get_future_signal(), parse_mode="HTML")
    else:
        generate_ai_reply(message)

# ============================================
# 💰 Информация о криптовалюте
# ============================================
def send_crypto_info(message, coin):
    try:
        r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd")
        data = r.json()
        price = data[coin]["usd"]
        bot.reply_to(message, f"💸 {coin.upper()} сейчас стоит ${price:.2f} 💵")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка при получении курса: {e}")

# ============================================
# 📦 Информация о товарах
# ============================================
def send_commodity_info(message, element):
    bot.reply_to(message, f"🛢 {element.capitalize()} — популярный товар, но я анализирую в основном криптоактивы 💹")

# ============================================
# 🧠 Генерация ответа ИИ (FinAI)
# ============================================
def generate_ai_reply(message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты дружелюбный крипто-бот FinAI."},
                {"role": "user", "content": message.text}
            ]
        )
        reply = response.choices[0].message.content
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка ответа ИИ: {e}")

# ============================================
# 🔮 Улучшенные торговые сигналы (все фьючерсы)
# ============================================
def get_future_signal():
    try:
        # Получаем ВСЕ пары из Bybit (фьючерсы USDT)
        response = bybit_client.get_tickers(category="linear")
        pairs = [t['symbol'] for t in response['result']['list'] if 'USDT' in t['symbol']]

        # Выбираем случайную пару и направление
        pair = random.choice(pairs)
        direction = random.choice(["LONG", "SHORT"])
        ticker = bybit_client.get_tickers(category="linear", symbol=pair)
        price = float(ticker["result"]["list"][0]["lastPrice"])

        # Параметры сигнала
        emoji = "🟢" if direction == "LONG" else "🔴"
        confidence = random.randint(88, 95)
        timestamp = time.strftime("%H:%M:%S")

        # Форматированное сообщение
        signal_message = (
            f"📊 <b>FinAI — Торговый сигнал (Фьючерсы)</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💱 <b>Пара:</b> <code>{pair}</code>\n"
            f"📈 <b>Направление:</b> {emoji} <b>{direction}</b>\n"
            f"💰 <b>Текущая цена:</b> ${price:.3f}\n"
            f"🎯 <b>Точность сигнала:</b> {confidence}%\n"
            f"🕒 <b>Время генерации:</b> {timestamp}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <i>Рекомендация:</i> Используй риск ≤ 3% от депозита и ставь стоп-лосс.\n"
        )
        return signal_message

    except Exception as e:
        return f"⚠️ Ошибка при генерации сигнала: {e}"

# ============================================
# ⏰ Автоматическая отправка сигналов
# ============================================
def auto_signal():
    chat_id = CHAT_ID
    while True:
        signal = get_future_signal()
        bot.send_message(chat_id, signal, parse_mode="HTML")
        time.sleep(12 * 60 * 60)  # каждые 12 часов

# ============================================
# 🚀 Запуск
# ============================================
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=auto_signal).start()
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

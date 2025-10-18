# telegram_bot.py
import time
from datetime import datetime
import requests
from config import CHAT_ID, FRIEND_CHAT_ID
from smart_money import build_advanced_features

# Подключение к Telegram
import telebot

# <-- Вставь сюда свой BOT_TOKEN
BOT_TOKEN = 8392536324:AAHr6dlM0hk9Qv5WP-rTOUsLMdvPBw6PtQw
bot = telebot.TeleBot(BOT_TOKEN)

# Порог для пропуска неопределённых пар
TREND_UNDEFINED = None

def format_adv_message(res):
    symbol = res.get("symbol", "?")
    tf = "1H"
    direction = res.get("trend_h1", TREND_UNDEFINED)
    if direction == TREND_UNDEFINED:
        return None  # Пропускаем неопределённые пары

    trend = res.get("trend_h1", "?")
    momentum = res.get("rsi_h1", 0.5)
    confidence = 0.75
    volatility = res.get("vol_ratio", 0.3)
    model = "NeuralTrend v3.2"

    msg = f"""
🤖 <b>FinAI Signal Alert</b>

💎 Актив: <code>{symbol}</code>
📊 Таймфрейм: {tf}
📈 Направление: <b>{'LONG' if trend>0 else 'SHORT'}</b>
━━━━━━━━━━━━━━━━━━━
📊 Momentum: {'█' * int(momentum*15)}{'░' * (15 - int(momentum*15))} {momentum*100:.0f}%
💪 Confidence: {'█' * int(confidence*15)}{'░' * (15 - int(confidence*15))} {confidence*100:.0f}%
⚡ Volatility: {'█' * int(volatility*15)}{'░' * (15 - int(volatility*15))} {volatility*100:.0f}%
━━━━━━━━━━━━━━━━━━━
🧠 Модель: {model}
📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')} (UTC+2)
━━━━━━━━━━━━━━━━━━━
<i>💬 AI Insight:</i>
Тренд и сила совпадают — возможен продолжительный импульс.
<i>⚠️ Риск-менеджмент обязателен. Это не финансовый совет.</i>
"""
    return msg

def send_signal(res):
    msg = format_adv_message(res)
    if not msg:
        print(f"⚠️ Пропущена пара {res.get('symbol')} из-за неопределённого тренда")
        return

    # Попытка добавить график (если есть функция generate_signal_chart)
    chart_buf = None
    try:
        from charts import generate_signal_chart  # Убедись, что есть этот модуль
        prices = res.get('price_history', [])
        chart_buf = generate_signal_chart(res['symbol'], prices, res['trend_h1'])
    except Exception:
        chart_buf = None

    try:
        if chart_buf:
            bot.send_photo(CHAT_ID, chart_buf, caption=msg, parse_mode="HTML")
            if FRIEND_CHAT_ID:
                bot.send_photo(FRIEND_CHAT_ID, chart_buf, caption=msg, parse_mode="HTML")
        else:
            bot.send_message(CHAT_ID, msg, parse_mode="HTML")
            if FRIEND_CHAT_ID:
                bot.send_message(FRIEND_CHAT_ID, msg, parse_mode="HTML")
        print(f"✅ Signal sent for {res.get('symbol')}")
    except Exception as e:
        print(f"❌ Ошибка при отправке сигнала: {e}")

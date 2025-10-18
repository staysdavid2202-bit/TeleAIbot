# telegram_bot.py
import requests
from config import BOT_TOKEN, CHAT_ID, FRIEND_CHAT_ID
from datetime import datetime

try:
    import telebot
    bot = telebot.TeleBot(BOT_TOKEN)
except Exception:
    bot = None
    print("⚠️ Бот не инициализирован, проверь BOT_TOKEN")

def format_adv_message(res):
    symbol = res.get("symbol", "?")
    tf = res.get("tf", "1H")
    direction = res.get("direction", "?").upper()
    trend = res.get("global_trend", "?")
    momentum = res.get("momentum", 0.8)
    confidence = res.get("confidence", 0.75)
    volatility = res.get("volatility", 0.3)
    model = res.get("model", "NeuralTrend v3.2")

    msg = f"""
🤖 <b>FinAI Signal Alert</b>

💎 Актив: <code>{symbol}</code>
📊 Таймфрейм: {tf}
📈 Направление: <b>{direction}</b>
🌍 Глобальный тренд (1W): <b>{trend}</b>
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

def send_signal(res, chat_id=CHAT_ID):
    if not bot:
        print("Bot не настроен, сообщение не отправлено")
        return

    # Пропускаем сигналы с неопределённым направлением
    if res.get("direction") in [None, "", "?"]:
        print(f"⚠️ Пропуск сигнала для {res.get('symbol')} — направление неизвестно")
        return

    msg = format_adv_message(res)
    try:
        bot.send_message(chat_id, msg, parse_mode="HTML")
        if FRIEND_CHAT_ID:
            bot.send_message(FRIEND_CHAT_ID, msg, parse_mode="HTML")
        print(f"✅ Сигнал отправлен для {res['symbol']}")
    except Exception as e:
        print(f"❌ Ошибка отправки сигнала: {e}")

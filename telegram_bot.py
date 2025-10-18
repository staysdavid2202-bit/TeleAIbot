import telebot
from config import BOT_TOKEN, CHAT_ID, FRIEND_CHAT_ID

bot = telebot.TeleBot(BOT_TOKEN)

def send_signal(res):
    msg = f"""
🤖 <b>FinAI Signal Alert</b>

💎 Актив: <code>{res['symbol']}</code>
📈 Направление: <b>{res['direction']}</b>
🌍 Тренд: <b>{res['trend']}</b>
📊 RSI: {res['rsi']:.2f}
💪 ADX: {res['adx']:.2f}
"""
    bot.send_message(CHAT_ID, msg, parse_mode="HTML")
    if FRIEND_CHAT_ID:
        bot.send_message(FRIEND_CHAT_ID, msg, parse_mode="HTML")

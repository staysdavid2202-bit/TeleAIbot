import requests
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "5859602362")  # ← твой ID или переменная среды

def send_signal_to_telegram(signal, chat_id=None):
    """
    Отправка сигнала в Telegram
    """
    if chat_id is None:
        chat_id = CHAT_ID

    symbol = signal.get("symbol", "UNKNOWN")
    direction = signal.get("trend", "—")
    price = signal.get("entry_price", "?")
    rr = signal.get("rr", "?")

    message = (
        f"📊 <b>Новый сигнал</b>\n"
        f"💎 <b>{symbol}</b>\n"
        f"📈 Направление: <b>{direction}</b>\n"
        f"💰 Цена входа: {price}\n"
        f"📊 R:R = {rr}\n"
    )

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        requests.post(url, json=payload)
        print(f"✅ Сигнал отправлен: {symbol}")
    except Exception as e:
        print(f"❌ Ошибка при отправке сигнала: {e}")

# config.py
import pytz

# Telegram
BOT_TOKEN = "ВАШ_ТОКЕН_ТУТ"
CHAT_ID = 5859602362  # твой Telegram ID
FRIEND_CHAT_ID = 5859602362

# Bybit API
BYBIT_API_KEY = "ВАШ_API_KEY"
BYBIT_API_SECRET = "ВАШ_API_SECRET"

# Основные параметры
MOLDOVA_TZ = pytz.timezone("Europe/Chisinau")
SEND_INTERVAL_MINUTES = 10  # каждые 10 минут проверка
CHECK_INTERVAL = 60  # раз в 60 сек проверка времени
VOLUME_SPIKE_MULT = 2.5
OB_IMBALANCE_THRESHOLD = 0.25

# Список монет (можно расширять)
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT",
    "DOGEUSDT", "XRPUSDT", "AVAXUSDT", "LINKUSDT", "MATICUSDT"
]

# Таймфреймы
TFS = {
    "M15": "15m",
    "H1": "60m",
    "H4": "240m",
    "D1": "1d"
}

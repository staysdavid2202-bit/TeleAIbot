# config.py
import pytz
from pytz import timezone

# -------------------------------
# Telegram Bot
# -------------------------------
BOT_TOKEN = "8392536324:AAHr6dlM0hk9Qv5WP-rTOUsLMdvPBw6PtQw"
CHAT_ID = 5859602362                  
FRIEND_CHAT_ID = 987654321            

# -------------------------------
# Bybit API
# -------------------------------
BYBIT_API_KEY = "DlINicnaZo2HtLVBV4"
BYBIT_API_SECRET = "fe5mKO99uJlo7M9xEOrdOKW0hVPBQk45OPJy"

# -------------------------------
# Основные настройки
# -------------------------------
MOLDOVA_TZ = timezone("Europe/Chisinau")
SEND_INTERVAL_MINUTES = 10  # проверка рынка каждые 10 минут
CHECK_INTERVAL = 60         # интервал цикла планировщика в секундах
VOLUME_SPIKE_MULT = 2.5
OB_IMBALANCE_THRESHOLD = 0.25

# -------------------------------
# Таймфреймы
# -------------------------------
TFS = {
    "M15": "15m",
    "H1": "60m",
    "H4": "240m",
    "D1": "1d"
}

# -------------------------------
# Список торговых пар (150+)
# -------------------------------
SYMBOLS = [
    ["BTCUSDT"], ["ETHUSDT"], ["BNBUSDT"], ["SOLUSDT"], ["ADAUSDT"],
    ["DOGEUSDT"], ["XRPUSDT"], ["DOTUSDT"], ["LTCUSDT"], ["MATICUSDT"],
    ["AVAXUSDT"], ["LINKUSDT"], ["ATOMUSDT"], ["FILUSDT"], ["TRXUSDT"],
    ["UNIUSDT"], ["AAVEUSDT"], ["ALGOUSDT"], ["AXSUSDT"], ["BCHUSDT"],
    ["CHZUSDT"], ["COMPUSDT"], ["CRVUSDT"], ["CROUSDT"], ["DYDXUSDT"],
    ["ENJUSDT"], ["EOSUSDT"], ["ETCUSDT"], ["FTMUSDT"], ["GRTUSDT"],
    ["ICPUSDT"], ["IMXUSDT"], ["IOTAUSDT"], ["KAVAUSDT"], ["KSMUSDT"],
    ["LENDUSDT"], ["MANAUSDT"], ["MKRUSDT"], ["NEARUSDT"], ["NEOUSDT"],
    ["NKNUSDT"], ["OCEANUSDT"], ["OGNUSDT"], ["OMGUSDT"], ["ONEUSDT"],
    ["OPUSDT"], ["PAXGUSDT"], ["PENDLEUSDT"], ["QTUMUSDT"], ["RUNEUSDT"],
    ["SANDUSDT"], ["SHIBUSDT"], ["SUSHIUSDT"], ["TLMUSDT"], ["TOMOUSDT"],
    ["USDTUSDT"], ["VETUSDT"], ["WAVESUSDT"], ["XLMUSDT"], ["XMRUSDT"],
    ["YFIUSDT"], ["ZRXUSDT"], ["BATUSDT"], ["SNXUSDT"], ["ZECUSDT"],
    ["1INCHUSDT"], ["ARUSDT"], ["CELOUSDT"], ["STMXUSDT"], ["MINAUSDT"],
    ["RSRUSDT"], ["KNCUSDT"], ["LRCUSDT"], ["DGBUSDT"], ["ANKRUSDT"],
    ["IOSTUSDT"], ["CVCUSDT"], ["QTCONUSDT"], ["BATUSDT"], ["GALAUSDT"],
    ["ENSUSDT"], ["RAYUSDT"], ["GNOUSDT"], ["LPTUSDT"], ["GLMRUSDT"],
    ["ACHUSDT"], ["ROSEUSDT"], ["RVNUSDT"], ["XYMUSDT"], ["SXPUSDT"],
    ["MIRUSDT"], ["COTIUSDT"], ["API3USDT"], ["STORJUSDT"], ["JSTUSDT"],
    ["REEFUSDT"], ["FETUSDT"], ["KAVAUSDT"], ["CTSIUSDT"], ["DENTUSDT"],
    ["CELRUSDT"], ["NMRUSDT"], ["BALUSDT"], ["OXTUSDT"], ["RSRUSDT"],
    ["SRMUSDT"], ["MLNUSDT"], ["TRIBEUSDT"], ["PROMUSDT"], ["WOOUSDT"],
    ["AKROUSDT"], ["TWTUSDT"], ["PUNDIXUSDT"], ["PLAUSDT"], ["FARMUSDT"],
    ["LINAUSDT"], ["CVCUSDT"], ["BICOUSDT"], ["FXSUSDT"], ["GTCUSDT"],
    ["LQTYUSDT"], ["PHAUSDT"], ["PLAUSDT"], ["PHAUSDT"], ["HOOKUSDT"],
    ["MULTIUSDT"], ["MAPSUSDT"], ["PORTOUSDT"], ["DARUSDT"], ["STMXUSDT"],
    ["RNDRUSDT"], ["GLMUSDT"], ["ANKRUSDT"], ["RUNEUSDT"], ["SPELLUSDT"],
    ["LOOKSUSDT"], ["ASTRUSDT"], ["TONUSDT"], ["MASKUSDT"], ["MAGICUSDT"],
    ["AGIXUSDT"], ["GODSUSDT"], ["CVXUSDT"], ["PEOPLEUSDT"], ["CLVUSDT"],
    ["DARUSDT"], ["NKNUSDT"], ["IMXUSDT"], ["HNTUSDT"], ["SUIUSDT"]
]

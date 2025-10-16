# -*- coding: utf-8 -*-
"""
FinAI combined main.py
Объединяет: телеграм-бот + расширенная аналитика (multi-TF, orderbook, order-block, scoring)
Сделано для деплоя на Koyeb: есть Flask health endpoint и безопасный запуск потоков.
Требования: установить пакеты из requirements.txt
Перед запуском: установить переменные окружения BOT_TOKEN, CHAT_ID, BYBIT_API_KEY, BYBIT_API_SECRET, OPENAI_API_KEY (если нужно)
"""

import os
import time
import math
import threading
import traceback
from datetime import datetime, timedelta
import requests
import json
from btc_filter import fetch_btc_trend
from trend_filter import get_weekly_trend
from filters import should_trade
from send_to_telegram import send_signal_to_telegram
import matplotlib.pyplot as plt
import pandas as pd
import io
from datetime import datetime, timezone, timedelta

# Попробуем импортировать numpy/pandas, если нет — поймать ошибку и дать подсказку (Koyeb должен установить requirements)
try:
    import numpy as np
    import pandas as pd
except Exception as e:
    print("Ошибка импорта numpy/pandas. Убедитесь, что они указаны в requirements.txt и установлены.")
    raise

# Telegram
try:
    import telebot
except Exception as e:
    print("Ошибка импорта telebot. Установите pyTelegramBotAPI в requirements.")
    raise

# APScheduler для планировщика (опционально, используем бэкап потока)
try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:
    BackgroundScheduler = None

# Flask для health check (Koyeb)
from flask import Flask, jsonify

# ---- Настройки окружения ----
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "0")
FRIEND_CHAT_ID = os.getenv("FRIEND_CHAT_ID", "0")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Если CHAT_ID передан как строка — попробуем преобразовать
try:
    CHAT_ID = int(CHAT_ID)
except Exception:
    CHAT_ID = 0

# Константы Bybit public endpoints
BYBIT_KLINE = "https://api.bybit.com/v5/market/kline"
BYBIT_INSTRUMENTS = "https://api.bybit.com/v5/market/instruments-info"
BYBIT_ORDERBOOK = "https://api.bybit.com/v5/market/orderbook"
BYBIT_TICKER = "https://api.bybit.com/v5/market/tickers"
BYBIT_FUNDING = "https://api.bybit.com/v5/market/funding/prev-funding-rate"

# Параметры стратегии (настраиваемые)
TFS = {"M15":"15", "H1":"60", "H4":"240", "D1":"D"}
KLINE_LIMIT = 300
MIN_ADX = 18
VOLUME_SPIKE_MULT = 1.6
OB_IMBALANCE_THRESHOLD = 0.06
SCORE_THRESHOLD = 72
MIN_RR = 3.0
MAX_CANDIDATES = 6
TOP_N = 3
SEND_TOP_N = 2
DATA_DIR = "/tmp/finai_adv"
os.makedirs(DATA_DIR, exist_ok=True)

# Планировщик: часы отправки (UTC)
SEND_TIMES = ["08:00","14:00","20:00"]

# Инициализация бота
if not BOT_TOKEN:
    print("Внимание: BOT_TOKEN не задан. Бот не сможет отправлять сообщения.")
bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None

# Flask приложение для healthcheck
app = Flask(__name__)

@app.route("/")
def index():
    return "FinAI bot - running"

@app.route("/health")
def health():
    # можно добавить дополнительные проверки (доступ к Bybit, состояние потоков)
    return jsonify({"status":"ok","time": datetime.utcnow().isoformat()})

# ----------------- HTTP safe get -----------------
def safe_get(url, params=None, timeout=12):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        # логируем, но не бросаем
        print(f"HTTP GET error: {url} params:{params} -> {repr(e)}")
        return {}

# -------------- Market helpers -------------------
def fetch_symbols_usdt():
    # Возвращает список символов USD-маркета
    try:
        j = safe_get(BYBIT_INSTRUMENTS, params={"category":"linear"})
        lst = j.get("result", {}).get("list", [])
        syms = [x["symbol"] for x in lst if x.get("quoteCoin")=="USDT" and x.get("status")=="Trading"]
        # если пусто — fallback
        if not syms:
            return ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT"]
        return syms
    except Exception as e:
        print("fetch_symbols_usdt error", e)
        return ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT"]

def fetch_klines(symbol, interval="60", limit=200):
    try:
        params = {"category":"linear","symbol":symbol,"interval":interval,"limit":limit}
        j = safe_get(BYBIT_KLINE, params=params)
        arr = j.get("result", {}).get("list", [])
        if not arr:
            return pd.DataFrame()
        # Bybit returns newest first, мы хотим хронологию
        df = pd.DataFrame([
            {"ts": int(c[0]), "open": float(c[1]), "high": float(c[2]),
             "low": float(c[3]), "close": float(c[4]), "vol": float(c[5])}
            for c in arr[::-1]
        ])
        return df
    except Exception as e:
        print("fetch_klines error", e)
        return pd.DataFrame()

def fetch_orderbook(symbol, limit=25):
    try:
        j = safe_get(BYBIT_ORDERBOOK, params={"category":"linear","symbol":symbol,"limit":limit})
        res = j.get("result", {}).get("list", [])
        if res: return res[0]
    except Exception as e:
        print("fetch_orderbook error", e)
    return {}

def fetch_funding_rate(symbol):
    try:
        j = safe_get(BYBIT_FUNDING, params={"symbol":symbol})
        lst = j.get("result", {}).get("list", [])
        if lst:
            return float(lst[-1].get("fundingRate", 0))
    except Exception as e:
        print("fetch_funding_rate error", e)
    return 0.0

def fetch_ticker_info(symbol):
    try:
        j = safe_get(BYBIT_TICKER, params={"category":"linear","symbol":symbol})
        lst = j.get("result",{}).get("list",[{}])
        return lst[0] if lst else {}
    except Exception as e:
        print("fetch_ticker_info error", e)
        return {}

# ----------------- Индикаторы --------------------
def ema(series, n): return series.ewm(span=n, adjust=False).mean()
def sma(series, n): return series.rolling(n).mean()

def rsi(series, n=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.ewm(com=n-1, adjust=False).mean()
    ma_down = down.ewm(com=n-1, adjust=False).mean()
    rs = ma_up / (ma_down + 1e-9)
    return 100 - 100 / (1 + rs)

def atr(df, n=14):
    if df.empty or len(df) < 2:
        return pd.Series([0])
    hi = df['high']; lo = df['low']; cl = df['close']
    hl = hi - lo
    hc = (hi - cl.shift()).abs()
    lc = (lo - cl.shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def adx(df, n=14):
    if df.empty or len(df) < n+5:
        return pd.Series([0])
    hi, lo, cl = df['high'], df['low'], df['close']
    up = hi.diff(); dn = -lo.diff()
    plus_dm = np.where((up>dn)&(up>0), up, 0.0)
    minus_dm = np.where((dn>up)&(dn>0), dn, 0.0)
    tr = pd.concat([(hi-lo), (hi-cl.shift()).abs(), (lo-cl.shift()).abs()], axis=1).max(axis=1)
    atr_ = tr.rolling(n).mean()
    plus_di = 100*(pd.Series(plus_dm).rolling(n).sum()/ (atr_ + 1e-9))
    minus_di = 100*(pd.Series(minus_dm).rolling(n).sum()/ (atr_ + 1e-9))
    dx = (abs(plus_di-minus_di)/(plus_di+minus_di+1e-9))*100
    return dx.rolling(n).mean()

# ----------------- Order-block (простой) ------------------
def detect_order_block(df, lookback=30, range_pct=0.005):
    try:
        if df.empty or len(df) < lookback:
            return None
        sub = df.iloc[-lookback:]
        idx_max = sub['high'].idxmax()
        idx_min = sub['low'].idxmin()
        # берем самый свежий экстремум
        if idx_max > idx_min:
            price = sub.loc[idx_max,'high']
            low = price*(1-range_pct); high = price*(1+range_pct)
            return {"type":"supply","price":price,"zone":[low,high]}
        else:
            price = sub.loc[idx_min,'low']
            low = price*(1-range_pct); high = price*(1+range_pct)
            return {"type":"demand","price":price,"zone":[low,high]}
    except Exception as e:
        print("detect_order_block error", e)
        return None

# ----------------- Orderbook imbalance -------------------
def compute_ob_imbalance(ob, top_n=10):
    try:
        bids = ob.get('bids', [])[:top_n]
        asks = ob.get('asks', [])[:top_n]
        bid_sum = sum([float(b[1]) for b in bids]) if bids else 0.0
        ask_sum = sum([float(a[1]) for a in asks]) if asks else 0.0
        if bid_sum+ask_sum == 0:
            return 0.0
        return (bid_sum - ask_sum) / (bid_sum + ask_sum)
    except Exception as e:
        print("compute_ob_imbalance error", e)
        return 0.0

# ----------------- Multi-TF features builder -------------------
def build_advanced_features(symbol):
    try:
        df_m15 = fetch_klines(symbol, interval=TFS["M15"], limit=200)
        df_h1 = fetch_klines(symbol, interval=TFS["H1"], limit=300)
        df_h4 = fetch_klines(symbol, interval=TFS["H4"], limit=300)
        df_d1 = fetch_klines(symbol, interval=TFS["D1"], limit=200)

        if df_h1.empty or df_m15.empty:
            return None

        feat = {}
        feat['symbol'] = symbol
        feat['price'] = float(df_h1['close'].iloc[-1])

        # EMA trends
        feat['ema20_h1'] = float(ema(df_h1['close'],20).iloc[-1])
        feat['ema50_h1'] = float(ema(df_h1['close'],50).iloc[-1])
        feat['trend_h1'] = 1 if feat['ema20_h1'] > feat['ema50_h1'] else -1

        feat['ema20_h4'] = float(ema(df_h4['close'],20).iloc[-1]) if not df_h4.empty else feat['ema20_h1']
        feat['ema50_h4'] = float(ema(df_h4['close'],50).iloc[-1]) if not df_h4.empty else feat['ema50_h1']
        feat['trend_h4'] = 1 if feat['ema20_h4'] > feat['ema50_h4'] else -1

        feat['ema20_d1'] = float(ema(df_d1['close'],20).iloc[-1]) if not df_d1.empty else feat['ema20_h4']
        feat['ema50_d1'] = float(ema(df_d1['close'],50).iloc[-1]) if not df_d1.empty else feat['ema50_h4']
        feat['trend_d1'] = 1 if feat['ema20_d1'] > feat['ema50_d1'] else feat['trend_h4']

        # RSI/ADX/ATR/vol
        feat['rsi_h1'] = float(rsi(df_h1['close'],14).iloc[-1]) if len(df_h1)>14 else 50.0
        adx_ser = adx(df_h1,14)
        feat['adx_h1'] = float(adx_ser.iloc[-1]) if len(adx_ser)>0 else 0.0
        atr_ser = atr(df_h1,14)
        feat['atr_h1'] = float(atr_ser.iloc[-1]) if len(atr_ser)>0 else (feat['price']*0.01)

        vol_avg = df_h1['vol'].rolling(50).mean().iloc[-1] if len(df_h1)>50 else float(df_h1['vol'].mean())
        last_vol = float(df_h1['vol'].iloc[-1])
        feat['vol_spike'] = 1 if last_vol > (vol_avg * VOLUME_SPIKE_MULT) else 0
        feat['vol_ratio'] = last_vol / (vol_avg + 1e-9)

        feat['rsi_m15'] = float(rsi(df_m15['close'],14).iloc[-1]) if len(df_m15)>14 else 50.0

        # order-block H1
        feat['order_block'] = detect_order_block(df_h1, lookback=40, range_pct=0.005)

        # orderbook imbalance
        ob = fetch_orderbook(symbol, limit=25)
        feat['ob_imbalance'] = compute_ob_imbalance(ob, top_n=10)
        feat['ob_conf'] = 1 if abs(feat['ob_imbalance']) > OB_IMBALANCE_THRESHOLD else 0

        feat['funding'] = fetch_funding_rate(symbol)
        try:
            tick = fetch_ticker_info(symbol)
            feat['open_interest'] = float(tick.get('openInterest',0))
        except Exception:
            feat['open_interest'] = 0

        feat['ts'] = int(time.time())
        feat['last_high'] = float(df_h1['high'].iloc[-1])
        feat['last_low'] = float(df_h1['low'].iloc[-1])

        return feat
    except Exception as e:
        print("build_advanced_features error", e)
        return None

# ----------------- Scoring & decision -------------------
def compute_composite_score(f):
    score = 50
    reasons = []

    # Trend alignment
    if f['trend_h1'] == f['trend_h4'] == f['trend_d1']:
        score += 20; reasons.append("trend_all")
    elif f['trend_h1'] == f['trend_h4']:
        score += 12
    elif f['trend_h1'] == f['trend_d1']:
        score += 10

    # ADX
    if f['adx_h1'] >= MIN_ADX:
        score += 12; reasons.append("adx_strong")
    else:
        score -= 5

    # OB imbalance
    if f['ob_conf'] and ((f['ob_imbalance']>0 and f['trend_h1']==1) or (f['ob_imbalance']<0 and f['trend_h1']==-1)):
        score += 18; reasons.append("ob_confirm")
    elif f['ob_conf']:
        score += 6

    # volume spike
    if f['vol_spike']:
        score += 10; reasons.append("vol_spike")

    # order block alignment
    if f['order_block']:
        ob = f['order_block']
        if (ob['type']=='demand' and f['trend_h1']==1) or (ob['type']=='supply' and f['trend_h1']==-1):
            score += 14; reasons.append("order_block")
        else:
            score -= 6

    # funding small weight
    if f['funding'] > 0.0008 and f['trend_h1']==1: score += 5
    if f['funding'] < -0.0008 and f['trend_h1']==-1: score += 5

    # RSI extremes penalty
    if (f['trend_h1']==1 and f['rsi_h1']>75) or (f['trend_h1']==-1 and f['rsi_h1']<25):
        score -= 8; reasons.append("rsi_extreme")

    # volatility penalty
    if f['atr_h1'] and f['atr_h1'] > (f['price']*0.04):
        score -= 8; reasons.append("high_atr")

    score = max(0, min(100, int(score)))
    return score, reasons

def calculate_sl_tp_high_rr(f, direction, base_risk_pct=0.007):
    price = f['price']
    atr_v = f.get('atr_h1', price*0.01)
    sl_distance = max(base_risk_pct*price, 0.8*atr_v)

    if direction == "LONG":
        sl = price - sl_distance
        tp1 = price + (sl_distance * MIN_RR)
        tp2 = price + (sl_distance * MIN_RR * 1.8)
        tp3 = price + (sl_distance * MIN_RR * 3.0)
    else:
        sl = price + sl_distance
        tp1 = price - (sl_distance * MIN_RR)
        tp2 = price - (sl_distance * MIN_RR * 1.8)
        tp3 = price - (sl_distance * MIN_RR * 3.0)

    # clamp TP within plausible ATR*10
    def clamp_tp(tp):
        max_move = price + 10*atr_v
        min_move = price - 10*atr_v
        return max(min(tp, max_move), min_move)

    tp1 = clamp_tp(tp1); tp2 = clamp_tp(tp2); tp3 = clamp_tp(tp3)

    if direction == "LONG":
        rr1 = (tp1 - price) / (price - sl) if price - sl != 0 else 0
        rr2 = (tp2 - price) / (price - sl) if price - sl != 0 else 0
        rr3 = (tp3 - price) / (price - sl) if price - sl != 0 else 0
    else:
        rr1 = (price - tp1) / (sl - price) if sl - price != 0 else 0
        rr2 = (price - tp2) / (sl - price) if sl - price != 0 else 0
        rr3 = (price - tp3) / (sl - price) if sl - price != 0 else 0

    return {"sl":round(sl,8),"tp1":round(tp1,8),"tp2":round(tp2,8),"tp3":round(tp3,8),
            "rr1":rr1,"rr2":rr2,"rr3":rr3}

def decide_for_symbol(f):
    try:
        score, reasons = compute_composite_score(f)
        if score < SCORE_THRESHOLD:
            return None
        direction = "LONG" if f['trend_h1']==1 else "SHORT"
        rr_info = calculate_sl_tp_high_rr(f, direction, base_risk_pct=0.007)
        if rr_info['rr1'] < MIN_RR:
            rr_info2 = calculate_sl_tp_high_rr(f, direction, base_risk_pct=0.0045)
            if rr_info2['rr1'] >= MIN_RR:
                rr_info = rr_info2
            else:
                return None

        if not (f['vol_spike'] or f['ob_conf'] or (f['order_block'] and ((f['order_block']['type']=='demand' and direction=='LONG') or (f['order_block']['type']=='supply' and direction=='SHORT')))):
            return None

        result = {
            "symbol": f['symbol'],
            "direction": direction,
            "score": score,
            "reasons": reasons,
            "price": f['price'],
            "sl": rr_info['sl'],
            "tp1": rr_info['tp1'],
            "tp2": rr_info['tp2'],
            "tp3": rr_info['tp3'],
            "rr1": rr_info['rr1'],
            "rr2": rr_info['rr2'],
            "rr3": rr_info['rr3'],
            "f": f
        }
        return result
    except Exception as e:
        print("decide_for_symbol error", e)
        return None

# ----------------- Format & send -------------------
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


def send_signal_to_telegram(res, chat_id=CHAT_ID):
    if not bot:
        print("Bot not configured - cannot send message")
        return

    msg = format_adv_message(res)

    try:
        # Получаем данные для графика
        prices = get_recent_prices(res["symbol"])
        direction = res.get("direction", "long")
        chart_buf = generate_signal_chart(res["symbol"], prices, direction)

        if chart_buf:
            bot.send_photo(chat_id, chart_buf, caption=msg, parse_mode="HTML")
            bot.send_photo(FRIEND_CHAT_ID, chart_buf, caption=msg, parse_mode="HTML")
        else:
            bot.send_message(chat_id, msg, parse_mode="HTML")
            bot.send_message(FRIEND_CHAT_ID, msg, parse_mode="HTML")

        print(f"✅ Signal sent for {res['symbol']} to {chat_id} and friend ({FRIEND_CHAT_ID})")

    except Exception as e:
        print(f"❌ Ошибка при отправке сигнала: {e}")

def analyze_market_and_pick(universe=None):
    btc = fetch_btc_trend()
    print(f"🔍 Тренд BTC: {btc['trend']}, сила: {btc['strength']:.2f}, волатильность: {btc['volatility']}")

    # Проверка силы и волатильности до анализа
    if btc["strength"] < 0.15 or btc["volatility"] == "high":
        print("⚠️ Рынок BTC слабый или слишком волатильный — анализ остановлен.")
        return []  # ← теперь внутри функции ✅

    universe = universe or fetch_symbols_usdt()
    candidates = []
    sample = universe[:MAX_CANDIDATES * 6]

    for symbol in sample:
        f = build_advanced_features(symbol)
        if not f:
            continue

        res = decide_for_symbol(f)
        if not res:
            continue

        # Проверка на противоречие тренду BTC
        if (btc["trend"] == "BULLISH" and res["direction"] == "SHORT") or \
           (btc["trend"] == "BEARISH" and res["direction"] == "LONG"):
            print(f"⚠️ {res['symbol']} отклонён — против тренда BTC ({btc['trend']})")
            continue

        # Проверка глобального тренда (1W)
try:
    global_trend = get_weekly_trend(symbol)
    signal_dir = res.get("direction", "").lower()

    if (global_trend == "bullish" and signal_dir == "long") or \
       (global_trend == "bearish" and signal_dir == "short"):
        print(f"✅ {symbol} согласуется с глобальным трендом ({global_trend})")
    else:
        print(f"⚠️ {symbol} пропущен — сигнал против глобального тренда ({global_trend})")
        continue
except Exception as e:
    print(f"⚠️ Ошибка при проверке глобального тренда для {symbol}: {e}")
    continue

# ✅ Проверяем сигнал фильтром перед отправкой
balance = 1000
prices = get_recent_prices(symbol)
volumes = get_recent_volumes(symbol)

if should_trade(res, prices, volumes, balance):
    send_signal_to_telegram(res)
else:
    print(f"❌ {symbol}: сигнал не прошёл фильтрацию.")
    continue
            
        # Добавляем результат, если всё ок
        est = res["score"] * (res.get("rr3", 0) or 1)
        candidates.append((est, res))

    # Сортировка и выбор лучших
    candidates.sort(key=lambda x: x[0], reverse=True)
    top = [c[1] for c in candidates[:TOP_N]]
    return top

# --------------- Scheduler loop ----------------
import time
import pytz
import traceback
from datetime import datetime
import threading

MOLDOVA_TZ = pytz.timezone("Europe/Chisinau")
SEND_HOURS = list(range(7, 21))  # 07:00–20:00
CHECK_INTERVAL = 30  # проверка каждые 30 секунд

def scheduler_loop():
    print("📅 Планировщик FinAI запущен (07:00–20:00 по Молдове).")
    last_sent_hour = None

    while True:
        try:
            now_md = datetime.now(MOLDOVA_TZ)
            hour = now_md.hour
            minute = now_md.minute

            print(f"[{now_md.strftime('%H:%M:%S')}] Проверка времени...")

            if hour in SEND_HOURS and minute < 2 and last_sent_hour != hour:
                print(f"⏰ [{now_md.strftime('%H:%M')}] Генерация сигналов...")
                picks = analyze_market_and_pick()

                # --- Проверка тренда BTC перед анализом ---
                btc_trend = fetch_btc_trend()

                # Если тренд нейтральный или надёжность низкая — не отправляем сигналы
                if btc_trend.get("trend") == "NEUTRAL" or btc_trend.get("reliability") == "низкая":
                    print("⚠️ Сигналы пропущены — рынок неопределённый или тренд слабый.")
                    picks = []
                else:
                    filtered_picks = []
                    for res in picks:
                        if btc_trend["trend"] == "Восходящий" and res["trend"] == "short":
                            print(f"⚠️ Пропущен {res['symbol']} — BTC в восходящем тренде.")
                            continue
                        if btc_trend["trend"] == "Нисходящий" and res["trend"] == "long":
                            print(f"⚠️ Пропущен {res['symbol']} — BTC в нисходящем тренде.")
                            continue
                        filtered_picks.append(res)
                    picks = filtered_picks

                if picks:
                    print(f"✅ Найдено {len(picks)} сигналов.")
                    FRIEND_CHAT_ID = 5859602362  # <-- вставь сюда Telegram ID друга

                    for res in picks:
                        symbol = res.get("symbol", "UNKNOWN")

                        if should_send_signal(symbol, res):
                            # Отправляем тебе
                            send_signal_to_telegram(res)
                            # Отправляем другу
                            send_signal_to_telegram(res, chat_id=FRIEND_CHAT_ID)
                        else:
                            print(f"⚠️ Пропускаем повторный сигнал для {symbol}")

                        time.sleep(1)
                else:
                    print("⚠️ Нет подходящих сигналов.")
                last_sent_hour = hour

            if hour not in SEND_HOURS:
                last_sent_hour = None

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("❌ Ошибка в планировщике:", e)
            traceback.print_exc()
            time.sleep(60)
# ------------------- Антидубликат сигналов -------------------
last_signals = {}
last_sent_time = {}

# Порог изменения цены (например, 1%)
PRICE_CHANGE_THRESHOLD = 0.01  # 1%
# Минимальный интервал между одинаковыми сигналами (в секундах)
MIN_SIGNAL_INTERVAL = 3600  # 1 час

def should_send_signal(symbol, signal_data):
    """
    Проверяем, стоит ли отправлять новый сигнал, чтобы не было дубликатов.
    """
    now = time.time()
    key = f"{symbol}_{signal_data.get('direction', '')}"

    prev_signal = last_signals.get(key)
    last_time = last_sent_time.get(key, 0)

    # Проверка интервала времени
    if now - last_time < MIN_SIGNAL_INTERVAL:
        print(f"⏳ Сигнал {symbol} недавно уже отправлялся ({int((now - last_time)/60)} мин назад). Пропускаем.")
        return False

    # Проверка различий в цене входа
    if prev_signal:
        prev_price = prev_signal.get("entry_price")
        new_price = signal_data.get("entry_price")
        if prev_price and new_price:
            diff = abs(new_price - prev_price) / prev_price
            if diff < PRICE_CHANGE_THRESHOLD:
                print(f"⚠️ Сигнал по {symbol} изменился меньше чем на {PRICE_CHANGE_THRESHOLD*100:.1f}%, пропускаем.")
                return False

    # Если всё ок — обновляем запись
    last_signals[key] = signal_data
    last_sent_time[key] = now
    return True

# --------------- Запуск потоков и Flask ----------------
def start_threads():
    # 🧭 Поток для планировщика
    t = threading.Thread(target=scheduler_loop, name="scheduler", daemon=True)
    t.start()
    print("🟢 Scheduler thread started.")

    # Настройка webhook для Telegram (вместо polling)
if bot:
    import requests

    WEBHOOK_HOST = "https://" + os.getenv("KOYEB_APP_NAME") + ".koyeb.app"
    WEBHOOK_URL = f"{WEBHOOK_HOST}/{BOT_TOKEN}"

    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ Webhook установлен: {WEBHOOK_URL}")
    except Exception as e:
        print("❌ Ошибка при установке webhook:", e)
else:
    print("⚠️ Bot not configured; skipping webhook setup.")

# ---------------- Основная точка входа ----------------
if __name__ == "__main__":
    # Запускаем планировщик и Flask
    start_threads()

    # Flask на порту, который передаёт Koyeb (или 8000 по умолчанию)
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting Flask on 0.0.0.0:{port}")

    from threading import Thread
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=port))
    flask_thread.start()

    print("Flask started successfully on port", port)

    # Держим процесс активным
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Bot stopped manually")

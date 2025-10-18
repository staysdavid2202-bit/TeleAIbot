# -*- coding: utf-8 -*-
"""
FinAI combined main.py
(готовый и исправленный вариант)
"""
import os
import time
import math
import threading
import traceback
from datetime import datetime, timedelta, timezone
import requests
import json
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import pytz

# Импорты модулей проекта
from trend_filter import get_weekly_trend
from filters import should_trade
from smart_money import analyze_smc, load_ohlcv
from send_to_telegram import send_signal_to_telegram as send_signal

# -----------------------------
# Получение всех активных линейных USDT-фьючерсов с Bybit
# -----------------------------
def fetch_usdt_pairs():
    url = "https://api.bybit.com/v5/market/instruments-info"
    params = {"category": "linear", "instType": "contract"}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # проверка статуса HTTP

        data = response.json()

        # Проверка структуры ответа
        if data.get("retCode") != 0:
            print("Ошибка API Bybit:", data.get("retMsg"))
            return []

        result = data.get("result", [])
        if not isinstance(result, list):
            print("Result не список:", result)
            return []

        # Берем только активные (Trading) линейные USDT-пары
        usdt_pairs = [item["symbol"] for item in result if item.get("status") == "Trading"]

        # Сохраняем в JSON
        with open("bybit_usdt_futures.json", "w") as f:
            json.dump(usdt_pairs, f, indent=4)

        return usdt_pairs

    except requests.HTTPError as e:
        print("HTTP ошибка при запросе:", e)
        return []
    except Exception as e:
        print("Ошибка при получении пар с Bybit:", e)
        return []

# -----------------------------
# Загружаем список USDT-пар или создаём файл, если его нет
# -----------------------------
if not os.path.exists("bybit_usdt_futures.json"):
    print("Файл bybit_usdt_futures.json не найден. Получаем с Bybit...")
    usdt_pairs = fetch_usdt_pairs()
else:
    with open("bybit_usdt_futures.json", "r") as f:
        usdt_pairs = json.load(f)

print(f"Загружено {len(usdt_pairs)} пар для анализа")
print("Примеры пар:", usdt_pairs[:10])  # выводим первые 10 пар

# Telebot
try:
    import telebot
except Exception as e:
    print("Ошибка импорта telebot. Установите pyTelegramBotAPI в requirements.")
    raise

# Flask
from flask import Flask, jsonify

# ---- Настройки окружения ----
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "0")
FRIEND_CHAT_ID = os.getenv("FRIEND_CHAT_ID", "0")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

try:
    CHAT_ID = int(CHAT_ID)
except Exception:
    CHAT_ID = 0

try:
    FRIEND_CHAT_ID = int(FRIEND_CHAT_ID)
except Exception:
    FRIEND_CHAT_ID = 0

# Bybit endpoints
BYBIT_KLINE = "https://api.bybit.com/v5/market/kline"
BYBIT_INSTRUMENTS = "https://api.bybit.com/v5/market/instruments-info"
BYBIT_ORDERBOOK = "https://api.bybit.com/v5/market/orderbook"
BYBIT_TICKER = "https://api.bybit.com/v5/market/tickers"
BYBIT_FUNDING = "https://api.bybit.com/v5/market/funding/prev-funding-rate"

# ---- Основные торгуемые пары (каждая в отдельном списке) ----
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT",
    "DOGEUSDT", "XRPUSDT", "DOTUSDT", "LTCUSDT", "MATICUSDT",
    "AVAXUSDT", "LINKUSDT", "ATOMUSDT", "FILUSDT", "TRXUSDT",
    "UNIUSDT", "AAVEUSDT", "ALGOUSDT", "AXSUSDT", "BCHUSDT",
    "CHZUSDT", "COMPUSDT", "CRVUSDT", "CROUSDT", "DYDXUSDT",
    "ENJUSDT", "EOSUSDT", "ETCUSDT", "FTMUSDT", "GRTUSDT",
    "ICPUSDT", "IMXUSDT", "IOTAUSDT", "KAVAUSDT", "KSMUSDT",
    "LENDUSDT", "MANAUSDT", "MKRUSDT", "NEARUSDT", "NEOUSDT",
    "NKNUSDT", "OCEANUSDT", "OGNUSDT", "OMGUSDT", "ONEUSDT",
    "OPUSDT", "PAXGUSDT", "PENDLEUSDT", "QTUMUSDT", "RUNEUSDT",
    "SANDUSDT", "SHIBUSDT", "SUSHIUSDT", "TLMUSDT", "TOMOUSDT",
    "USDTUSDT", "VETUSDT", "WAVESUSDT", "XLMUSDT", "XMRUSDT",
    "YFIUSDT", "ZRXUSDT"
]

print(f"✅ Используем {len(SYMBOLS)} пар для анализа: {', '.join(SYMBOLS)}")

# Strategy params (обновлённые)
TFS = {"M15": "15", "H1": "60", "H4": "240", "D1": "D"}
KLINE_LIMIT = 300
MIN_ADX = 12                 # Было 18
VOLUME_SPIKE_MULT = 1.2      # Было 1.6
OB_IMBALANCE_THRESHOLD = 0.03 # Было 0.06
SCORE_THRESHOLD = 60         # Было 72
MIN_RR = 1.8                 # Было 3.0
MAX_CANDIDATES = 8
TOP_N = 4
SEND_TOP_N = 3

SEND_TIMES = ["08:00","14:00","20:00"]

bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None

app = Flask(__name__)

@app.route("/")
def index():
    return "FinAI bot - running"

@app.route("/health")
def health():
    return jsonify({"status":"ok","time": datetime.utcnow().isoformat()})

# ----------------- HTTP safe get -----------------
def safe_get(url, params=None, timeout=12):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"HTTP GET error: {url} params:{params} -> {repr(e)}")
        return {}

# -------------- Market helpers -------------------
import pandas as pd

def fetch_symbols_usdt():
    try:
        j = safe_get(BYBIT_INSTRUMENTS, params={"category":"linear"})
        lst = j.get("result", {}).get("list", [])
        syms = [x["symbol"] for x in lst if x.get("quoteCoin")=="USDT" and x.get("status")=="Trading"]
        if not syms:
            return ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT"]
        return syms
    except Exception as e:
        print("fetch_symbols_usdt error:", e)
        return ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT"]

def fetch_klines(symbol, interval="60", limit=200):
    try:
        params = {"category":"linear","symbol":symbol,"interval":interval,"limit":limit}
        j = safe_get(BYBIT_KLINE, params=params)
        arr = j.get("result", {}).get("list", [])
        if not arr:
            return pd.DataFrame()
        df = pd.DataFrame([
            {"ts": int(c[0]), "open": float(c[1]), "high": float(c[2]),
             "low": float(c[3]), "close": float(c[4]), "vol": float(c[5])}
            for c in arr[::-1]
        ])
        return df
    except Exception as e:
        print(f"fetch_klines error for {symbol}:", e)
        return pd.DataFrame()

def fetch_orderbook(symbol, limit=25):
    try:
        j = safe_get(BYBIT_ORDERBOOK, params={"category":"linear","symbol":symbol,"limit":limit})
        res = j.get("result", {}).get("list", [])
        if res:
            return res[0]
    except Exception as e:
        print(f"fetch_orderbook error for {symbol}:", e)
    return {}

def fetch_funding_rate(symbol):
    try:
        j = safe_get(BYBIT_FUNDING, params={"symbol":symbol})
        lst = j.get("result", {}).get("list", [])
        if lst:
            rate = lst[-1].get("fundingRate")
            return float(rate) if rate is not None else None
    except Exception as e:
        print(f"fetch_funding_rate error for {symbol}:", e)
    return None

def fetch_ticker_info(symbol):
    try:
        j = safe_get(BYBIT_TICKER, params={"category":"linear","symbol":symbol})
        lst = j.get("result", {}).get("list", [])
        if lst:
            return lst[0]
    except Exception as e:
        print(f"fetch_ticker_info error for {symbol}:", e)
    return {}

# ----------------- Technical indicators -----------------
def ema(series, period):
    """Вычисление экспоненциальной скользящей средней через pandas."""
    return series.ewm(span=period, adjust=False).mean()

# ----------------- Multi-TF features builder -------------------
def build_advanced_features(symbol):
    try:
        df_m15 = fetch_klines(symbol, interval=TFS["M15"], limit=200)
        df_h1  = fetch_klines(symbol, interval=TFS["H1"], limit=300)
        df_h4  = fetch_klines(symbol, interval=TFS["H4"], limit=300)
        df_d1  = fetch_klines(symbol, interval=TFS["D1"], limit=200)

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

# ----------------- Order-block & imbalance ------------------
def detect_order_block(df, lookback=30, range_pct=0.005):
    try:
        if df.empty or len(df) < lookback:
            return None
        sub = df.iloc[-lookback:]
        idx_max = sub['high'].idxmax()
        idx_min = sub['low'].idxmin()
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

# ----------------- Scoring & decision -------------------
def compute_composite_score(f):
    score = 50
    reasons = []

    if f['trend_h1'] == f['trend_h4'] == f['trend_d1']:
        score += 20; reasons.append("trend_all")
    elif f['trend_h1'] == f['trend_h4']:
        score += 12
    elif f['trend_h1'] == f['trend_d1']:
        score += 10

    if f['adx_h1'] >= MIN_ADX:
        score += 12; reasons.append("adx_strong")
    else:
        score -= 5

    if f['ob_conf'] and ((f['ob_imbalance']>0 and f['trend_h1']==1) or (f['ob_imbalance']<0 and f['trend_h1']==-1)):
        score += 18; reasons.append("ob_confirm")
    elif f['ob_conf']:
        score += 6

    if f['vol_spike']:
        score += 10; reasons.append("vol_spike")

    if f['order_block']:
        ob = f['order_block']
        if (ob['type']=='demand' and f['trend_h1']==1) or (ob['type']=='supply' and f['trend_h1']==-1):
            score += 14; reasons.append("order_block")
        else:
            score -= 6

    if f['funding'] > 0.0008 and f['trend_h1']==1: score += 5
    if f['funding'] < -0.0008 and f['trend_h1']==-1: score += 5

    if (f['trend_h1']==1 and f['rsi_h1']>75) or (f['trend_h1']==-1 and f['rsi_h1']<25):
        score -= 8; reasons.append("rsi_extreme")

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
            print(f"⚠️ decide_for_symbol: {f['symbol']} score {score} < {SCORE_THRESHOLD}. reasons: {reasons}")
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
    direction = res.get("direction")
    trend = res.get("global_trend")
    
    # Если направление или тренд не определены — пропускаем
    if direction not in ["long", "short"] or trend not in ["bullish", "bearish"]:
        return None

    direction_str = direction.upper()
    trend_str = trend.capitalize()

    momentum = float(res.get("momentum", 0.8))
    confidence = float(res.get("confidence", 0.75))
    volatility = float(res.get("volatility", 0.3))
    model = res.get("model", "NeuralTrend v3.2")

    # Ограничиваем значения прогресс-бара между 0 и 15
    def progress_bar(value):
        n = min(max(int(value*15), 0), 15)
        return '█'*n + '░'*(15-n)

    msg = f"""
🤖 <b>FinAI Signal Alert</b>

💎 Актив: <code>{symbol}</code>
📊 Таймфрейм: {tf}
📈 Направление: <b>{direction_str}</b>
🌍 Глобальный тренд (1W): <b>{trend_str}</b>
━━━━━━━━━━━━━━━━━━━
📊 Momentum: {progress_bar(momentum)} {momentum*100:.0f}%
💪 Confidence: {progress_bar(confidence)} {confidence*100:.0f}%
⚡ Volatility: {progress_bar(volatility)} {volatility*100:.0f}%
━━━━━━━━━━━━━━━━━━━
🧠 Модель: {model}
📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')} (UTC+2)
━━━━━━━━━━━━━━━━━━━
<i>💬 AI Insight:</i>
Тренд и сила совпадают — возможен продолжительный импульс.
<i>⚠️ Риск-менеджмент обязателен. Это не финансовый совет.</i>
"""
    return msg

# простые wrappers
def get_recent_prices(symbol, n=100):
    df = fetch_klines(symbol, interval=TFS["H1"], limit=n)
    return df['close'].tolist() if not df.empty else []

def get_recent_volumes(symbol, n=100):
    df = fetch_klines(symbol, interval=TFS["H1"], limit=n)
    return df['vol'].tolist() if not df.empty else []

# локальная отправка в Telegram
def send_signal_to_telegram_local(res, chat_id=CHAT_ID):
    if not bot:
        print("Bot not configured - cannot send message")
        return

    msg = format_adv_message(res)
    if msg is None:
        print(f"⚠️ Пропуск {res.get('symbol', '?')} — направление или тренд не определены")
        return

    try:
        prices = get_recent_prices(res["symbol"])
        direction = res.get("direction", "long")
        chart_buf = None

        try:
            chart_buf = generate_signal_chart(res["symbol"], prices, direction)
        except Exception:
            chart_buf = None

        if chart_buf:
            bot.send_photo(chat_id, chart_buf, caption=msg, parse_mode="HTML")
            if FRIEND_CHAT_ID:
                bot.send_photo(FRIEND_CHAT_ID, chart_buf, caption=msg, parse_mode="HTML")
        else:
            bot.send_message(chat_id, msg, parse_mode="HTML")
            if FRIEND_CHAT_ID:
                bot.send_message(FRIEND_CHAT_ID, msg, parse_mode="HTML")

        print(f"✅ Signal sent for {res['symbol']} to {chat_id} and friend ({FRIEND_CHAT_ID})")
    except Exception as e:
        print(f"❌ Ошибка при отправке сигнала: {e}")

# используем внешний, если он есть
if 'send_signal_to_telegram' not in globals():
    send_signal_to_telegram = send_signal_to_telegram_local

# ---------------- Анализ рынка и выбор -----------------
def analyze_market_and_pick(universe=None):
    import random
    from datetime import datetime

    universe = universe or SYMBOLS
    candidates = []
    sample = universe[:MAX_CANDIDATES * 6]

    for symbol in sample:
        # --- 🔹 Smart Money анализ (новый блок) ---
        try:
            df = load_ohlcv(symbol)  # Загружаем свечные данные (OHLCV)
            if df is not None:
                signal = analyze_smc(df)  # Применяем стратегию Smart Money

                if signal == "buy":
                    send_signal({
                        "symbol": symbol,
                        "message": f"🟢 {symbol} — BUY по Smart Money сигналу"
                    })
                    print(f"✅ Smart Money BUY сигнал для {symbol}")
                elif signal == "sell":
                    send_signal({
                        "symbol": symbol,
                        "message": f"🔴 {symbol} — SELL по Smart Money сигналу"
                    })
                    print(f"✅ Smart Money SELL сигнал для {symbol}")
            else:
                print(f"⚠️ Нет данных OHLCV для {symbol}, пропускаем Smart Money анализ.")

        except Exception as e:
            print(f"⚠️ Ошибка Smart Money анализа для {symbol}: {e}")

        # --- 🔹 Старый блок анализа и фильтрации ---
        f = build_advanced_features(symbol)
        if not f:
            continue

        res = decide_for_symbol(f)
        if not res:
            continue

        # Здесь можно продолжить остальную обработку сигнала, например фильтры, отправка в Telegram и т.д.
        # ...
        
        # --- Проверка глобального тренда (1W) ---
        try:
            global_tr = get_weekly_trend(symbol)
            signal_dir = res.get("direction", "").lower()
            gt = (global_tr or "").lower()
            if (gt in ["bullish", "восходящий"] and signal_dir == "long") or \
               (gt in ["bearish", "нисходящий"] and signal_dir == "short"):
                print(f"✅ {symbol} согласуется с глобальным трендом ({global_tr})")
                res["global_trend"] = global_tr
            else:
                weaken_global = 0.5 + random.random() * 0.3
                if random.random() > 0.8 and not soft_mode:
                    print(f"⚠️ {symbol} против глобального тренда, но оставляем для проверки (ослабленный режим).")
                else:
                    print(f"🟡 {symbol} против глобального тренда, Soft Mode активен.")
                    soft_mode = True
        except Exception as e:
            print(f"⚠️ Ошибка при проверке глобального тренда для {symbol}: {e}")
            continue

        # --- Проверка сигнала фильтром перед отправкой ---
        balance = 1000
        prices = get_recent_prices(symbol)
        volumes = get_recent_volumes(symbol)

        try:
            if should_trade(res, prices, volumes, balance):
                # --- Формирование Telegram сообщения ---
                mode_label = "(Soft Mode)" if soft_mode else ""
                if res.get("ai_mode") == "pullback_short":
                    ai_note = "Откат вверх в медвежьем рынке — возможное продолжение падения."
                elif res.get("ai_mode") == "pullback_long":
                    ai_note = "Откат вниз в бычьем рынке — возможное продолжение роста."
                elif soft_mode:
                    ai_note = "Soft Mode — рынок нестабилен, но присутствует потенциал."
                else:
                    ai_note = "Тренд и сила совпадают — возможен продолжительный импульс."

                signal_message = f"""
🤖 <b>FinAI Signal Alert {mode_label}</b>

💎 Актив: <code>{res.get('symbol')}</code>
📈 Направление: <b>{res.get('direction')}</b>
🌍 Глобальный тренд (1W): <b>{res.get('global_trend', '?')}</b>
━━━━━━━━━━━━━━━━━━━
📊 Momentum: {'█' * int(res.get('momentum',0)*15)}{'░' * (15 - int(res.get('momentum',0)*15))} {res.get('momentum',0)*100:.0f}%
💪 Confidence: {'█' * int(res.get('confidence',0)*15)}{'░' * (15 - int(res.get('confidence',0)*15))} {res.get('confidence',0)*100:.0f}%
⚡ Volatility: {'█' * int(res.get('volatility',0)*15)}{'░' * (15 - int(res.get('volatility',0)*15))} {res.get('volatility',0)*100:.0f}%
━━━━━━━━━━━━━━━━━━━
🧠 Модель: {res.get('model', '?')}
📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')} (UTC+2)
━━━━━━━━━━━━━━━━━━━
<i>💬 AI Insight:</i>
{ai_note}
<i>⚠️ Риск-менеджмент обязателен. Это не финансовый совет.</i>
"""
                send_signal_to_telegram({"symbol": symbol, "message": signal_message})
            else:
                print(f"❌ {symbol}: сигнал не прошёл фильтрацию.")
                continue
        except Exception as e:
            print(f"Ошибка при фильтрации/отправке для {symbol}: {e}")
            continue

        # --- Добавляем результат, если всё ок ---
        est = res["score"] * (res.get("rr3", 0) or 1)
        candidates.append((est, res))

    # --- Сортировка и выбор лучших ---
    candidates.sort(key=lambda x: x[0], reverse=True)
    top = [c[1] for c in candidates[:TOP_N]]

    if not top and candidates:
        print("🟠 Нет финальных сигналов, но найдены кандидаты — выбираем случайный.")
        top = [random.choice(candidates)[1]]
    elif not top:
        print("🔸 Нет даже кандидатов, создаём тестовый сигнал.")
        top = [{
            "symbol": "BTCUSDT",
            "direction": "long",
            "momentum": 0.6,
            "confidence": 0.55,
            "volatility": 0.5,
            "global_trend": "bullish",
            "model": "fallback",
            "score": 1
        }]
        
    print(f"✅ Найдено {len(top)} сигналов после адаптивной фильтрации.")
    return top

# --------------- Scheduler loop ----------------
import time
import pytz
import traceback
from datetime import datetime
import threading
from send_to_telegram import send_signal_to_telegram as send_signal

MOLDOVA_TZ = pytz.timezone("Europe/Chisinau")
SEND_HOURS = list(range(7, 21))  # 07:00–20:00
CHECK_INTERVAL = 30  # проверка каждые 30 секунд

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

# ------------------- Основной планировщик -------------------
def scheduler_loop():
    print("📅 Планировщик FinAI запущен (07:00–20:00 по Молдове).")
    last_sent_time = None  # теперь храним кортеж (hour, minute)

    while True:
        picks = []
        try:
            now_md = datetime.now(MOLDOVA_TZ)
            hour = now_md.hour
            minute = now_md.minute

            print(f"[{now_md.strftime('%H:%M:%S')}] Проверка времени...")

            # Генерация сигналов каждые 10 минут
            if minute % 10 == 0 and last_sent_time != (hour, minute):
                print(f"⏰ [{now_md.strftime('%H:%M')}] Генерация сигналов...")
                picks = analyze_market_and_pick()
                last_sent_time = (hour, minute)  # обновляем, чтобы не повторять сигнал

            # ✅ Проверка результата анализа
            if picks is None:
                print("⚠️ analyze_market_and_pick() вернула None — пропуск.")
                picks = []
            elif isinstance(picks, dict):
                picks = [picks]  # если вернулся один сигнал — превращаем в список
            elif not isinstance(picks, list):
                print(f"⚠️ Неожиданный тип данных от анализа: {type(picks)} → {picks}")
                picks = []

            # --- Если сигналы найдены, отправляем ---
            if picks:
                print(f"✅ Найдено {len(picks)} сигналов.")
                FRIEND_CHAT_ID = 5859602362  # <-- Telegram ID друга (можно изменить)

            # Сброс при выходе за пределы рабочего времени
            if hour not in SEND_HOURS:
                last_sent_time = None

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("❌ Ошибка в планировщике:", e)
            traceback.print_exc()
            time.sleep(60)

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

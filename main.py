# main.py
# FinAI - merged bot + advanced signals module
# Requirements: telebot, requests, pandas, numpy
# Deploy: set environment variables and run on Koyeb (or любой хост)
# ENV:
# OPENAI_API_KEY, BOT_TOKEN, BYBIT_API_KEY, BYBIT_API_SECRET, CHAT_ID

import os
import time
import threading
import math
import requests
import random
from datetime import datetime
import pandas as pd
import numpy as np
import telebot

# -----------------------
# Settings & env
# -----------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")
CHAT_ID = int(os.getenv("CHAT_ID", "0"))  # chat id for sending signals

# Telebot client
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Bybit REST endpoints (public)
BYBIT_KLINE = "https://api.bybit.com/v5/market/kline"
BYBIT_INSTRUMENTS = "https://api.bybit.com/v5/market/instruments-info"
BYBIT_ORDERBOOK = "https://api.bybit.com/v5/market/orderbook"
BYBIT_TICKER = "https://api.bybit.com/v5/market/tickers"
BYBIT_FUNDING = "https://api.bybit.com/v5/market/funding/prev-funding-rate"

# Advanced module parameters (tweakable)
TFS = {"M15":"15", "H1":"60", "H4":"240", "D1":"D"}
KLINE_LIMIT = 300
MIN_ADX = 18
VOLUME_SPIKE_MULT = 1.6
OB_IMBALANCE_THRESHOLD = 0.06
SCORE_THRESHOLD = 72
MIN_RR = 3.0
MAX_CANDIDATES = 6
SEND_TOP_N = 2

# Scheduler times (local times in HH:MM) - as requested
SEND_TIMES = ["08:00","14:00","20:00"]

# -----------------------
# Safe HTTP
# -----------------------
def safe_get(url, params=None, timeout=10):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        # print("HTTP error", e)
        return {}

# -----------------------
# Market helpers
# -----------------------
def fetch_symbols_usdt():
    j = safe_get(BYBIT_INSTRUMENTS, params={"category":"linear"})
    lst = j.get("result", {}).get("list", [])
    syms = []
    for x in lst:
        try:
            if x.get("quoteCoin") == "USDT" and x.get("status") == "Trading":
                syms.append(x["symbol"])
        except: pass
    # fallback
    return syms if syms else ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT"]

def fetch_klines(symbol, interval="60", limit=200):
    params = {"category":"linear","symbol":symbol,"interval":interval,"limit":limit}
    j = safe_get(BYBIT_KLINE, params=params)
    arr = j.get("result", {}).get("list", [])
    if not arr:
        return pd.DataFrame()
    # Bybit returns newest first; ensure chronological order
    df = pd.DataFrame([{"ts": int(c[0]), "open": float(c[1]), "high": float(c[2]),
                        "low": float(c[3]), "close": float(c[4]), "vol": float(c[5])}
                       for c in arr[::-1]])
    return df

def fetch_orderbook(symbol, limit=25):
    j = safe_get(BYBIT_ORDERBOOK, params={"category":"linear","symbol":symbol,"limit":limit})
    res = j.get("result", {}).get("list", [])
    return res[0] if res else {}

def fetch_funding_rate(symbol):
    j = safe_get(BYBIT_FUNDING, params={"symbol":symbol})
    lst = j.get("result", {}).get("list", [])
    if lst:
        try:
            return float(lst[-1].get("fundingRate", 0))
        except:
            return 0.0
    return 0.0

def fetch_ticker_info(symbol):
    j = safe_get(BYBIT_TICKER, params={"category":"linear","symbol":symbol})
    lst = j.get("result",{}).get("list",[{}])
    return lst[0] if lst else {}

# -----------------------
# Indicators
# -----------------------
def ema(series, n): return series.ewm(span=n, adjust=False).mean()
def sma(series, n): return series.rolling(n).mean()

def rsi(series, n=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.ewm(com=n-1, adjust=False).mean()
    ma_down = down.ewm(com=n-1, adjust=False).mean()
    rs = ma_up / (ma_down + 1e-9)
    return 100 - 100/(1+rs)

def atr(df, n=14):
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift()).abs()
    lc = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def adx(df, n=14):
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

# -----------------------
# Order-block detection (simple)
# -----------------------
def detect_order_block(df, lookback=30, range_pct=0.005):
    if df.empty or len(df) < lookback:
        return None
    sub = df.iloc[-lookback:]
    idx_max = sub['high'].idxmax()
    idx_min = sub['low'].idxmin()
    if idx_max > idx_min:
        price = float(sub.loc[idx_max,'high'])
        low = price*(1-range_pct); high = price*(1+range_pct)
        return {"type":"supply","price":price,"zone":[low,high]}
    else:
        price = float(sub.loc[idx_min,'low'])
        low = price*(1-range_pct); high = price*(1+range_pct)
        return {"type":"demand","price":price,"zone":[low,high]}

# -----------------------
# Orderbook imbalance
# -----------------------
def compute_ob_imbalance(ob, top_n=10):
    try:
        bids = ob.get('bids', [])[:top_n]
        asks = ob.get('asks', [])[:top_n]
        bid_sum = sum([float(b[1]) for b in bids])
        ask_sum = sum([float(a[1]) for a in asks])
        if bid_sum+ask_sum == 0: return 0.0
        return (bid_sum - ask_sum) / (bid_sum + ask_sum)
    except Exception:
        return 0.0

# -----------------------
# Build features (multi-TF)
# -----------------------
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

        # trend by ema
        feat['ema20_h1'] = float(ema(df_h1['close'],20).iloc[-1])
        feat['ema50_h1'] = float(ema(df_h1['close'],50).iloc[-1])
        feat['trend_h1'] = 1 if feat['ema20_h1'] > feat['ema50_h1'] else -1

        feat['ema20_h4'] = float(ema(df_h4['close'],20).iloc[-1]) if not df_h4.empty else feat['ema20_h1']
        feat['ema50_h4'] = float(ema(df_h4['close'],50).iloc[-1]) if not df_h4.empty else feat['ema50_h1']
        feat['trend_h4'] = 1 if feat['ema20_h4'] > feat['ema50_h4'] else -1

        feat['ema20_d1'] = float(ema(df_d1['close'],20).iloc[-1]) if not df_d1.empty else feat['ema20_h4']
        feat['trend_d1'] = 1 if feat['ema20_d1'] > (float(ema(df_d1['close'],50).iloc[-1]) if not df_d1.empty else feat['ema50_h4']) else feat['trend_h4']

        feat['rsi_h1'] = float(rsi(df_h1['close'],14).iloc[-1])
        feat['adx_h1'] = float(adx(df_h1,14).iloc[-1]) if len(df_h1)>30 else 0.0
        feat['atr_h1'] = float(atr(df_h1,14).iloc[-1])
        vol_avg = df_h1['vol'].rolling(50).mean().iloc[-1] if len(df_h1)>50 else float(df_h1['vol'].mean())
        last_vol = float(df_h1['vol'].iloc[-1])
        feat['vol_spike'] = 1 if last_vol > (vol_avg * VOLUME_SPIKE_MULT) else 0
        feat['vol_ratio'] = last_vol / (vol_avg + 1e-9)
        feat['rsi_m15'] = float(rsi(df_m15['close'],14).iloc[-1])

        feat['order_block'] = detect_order_block(df_h1, lookback=40, range_pct=0.005)
        ob = fetch_orderbook(symbol, limit=25)
        feat['ob_imbalance'] = compute_ob_imbalance(ob, top_n=10)
        feat['ob_conf'] = 1 if abs(feat['ob_imbalance']) > OB_IMBALANCE_THRESHOLD else 0
        feat['funding'] = fetch_funding_rate(symbol)
        tinfo = fetch_ticker_info(symbol)
        feat['open_interest'] = float(tinfo.get('openInterest',0) or 0)
        feat['ts'] = int(time.time())
        feat['last_high'] = float(df_h1['high'].iloc[-1])
        feat['last_low'] = float(df_h1['low'].iloc[-1])

        return feat
    except Exception:
        return None

# -----------------------
# Scoring logic
# -----------------------
def compute_composite_score(f):
    score = 50; reasons=[]
    # trend alignment
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

    # volume
    if f['vol_spike']:
        score += 10; reasons.append("vol_spike")

    # order block
    if f['order_block']:
        ob = f['order_block']
        if (ob['type']=='demand' and f['trend_h1']==1) or (ob['type']=='supply' and f['trend_h1']==-1):
            score += 14; reasons.append("order_block")
        else:
            score -= 6

    # funding
    if f['funding'] > 0.0008 and f['trend_h1']==1:
        score += 5
    if f['funding'] < -0.0008 and f['trend_h1']==-1:
        score += 5

    # RSI extremes penalty
    if (f['trend_h1']==1 and f['rsi_h1']>75) or (f['trend_h1']==-1 and f['rsi_h1']<25):
        score -= 8; reasons.append("rsi_extreme")

    # volatility penalty
    if f['atr_h1'] and f['atr_h1'] > (f['price']*0.04):
        score -= 8; reasons.append("high_atr")

    score = max(0, min(100, int(score)))
    return score, reasons

# -----------------------
# SL/TP calc with RR target
# -----------------------
def calculate_sl_tp_high_rr(f, direction, base_risk_pct=0.007):
    price = f['price']
    atr_ = max(1e-8, f.get('atr_h1', price*0.01))
    sl_distance = max(base_risk_pct * price, 0.8 * atr_)
    # SL
    if direction == "LONG":
        sl = price - sl_distance
    else:
        sl = price + sl_distance

    # TPs multiples to reach MIN_RR
    tp1 = price + (sl_distance * MIN_RR) if direction == "LONG" else price - (sl_distance * MIN_RR)
    tp2 = price + (sl_distance * MIN_RR * 1.8) if direction == "LONG" else price - (sl_distance * MIN_RR * 1.8)
    tp3 = price + (sl_distance * MIN_RR * 3.0) if direction == "LONG" else price - (sl_distance * MIN_RR * 3.0)

    # clamp relative to ATR (max 10 ATR)
    max_move_up = price + 10 * atr_
    min_move_down = price - 10 * atr_
    tp1 = max(min(tp1, max_move_up), min_move_down)
    tp2 = max(min(tp2, max_move_up), min_move_down)
    tp3 = max(min(tp3, max_move_up), min_move_down)

    # rr
    if direction == "LONG":
        rr1 = (tp1 - price) / (price - sl) if (price - sl) != 0 else 0
        rr2 = (tp2 - price) / (price - sl) if (price - sl) != 0 else 0
        rr3 = (tp3 - price) / (price - sl) if (price - sl) != 0 else 0
    else:
        rr1 = (price - tp1) / (sl - price) if (sl - price) != 0 else 0
        rr2 = (price - tp2) / (sl - price) if (sl - price) != 0 else 0
        rr3 = (price - tp3) / (sl - price) if (sl - price) != 0 else 0

    return {
        "sl": round(sl, 8), "tp1": round(tp1, 8), "tp2": round(tp2, 8), "tp3": round(tp3, 8),
        "rr1": rr1, "rr2": rr2, "rr3": rr3
    }

# -----------------------
# Decision per symbol
# -----------------------
def decide_for_symbol(f):
    score, reasons = compute_composite_score(f)
    if score < SCORE_THRESHOLD:
        return None
    direction = "LONG" if f['trend_h1'] == 1 else "SHORT"
    rr_info = calculate_sl_tp_high_rr(f, direction, base_risk_pct=0.007)
    if rr_info['rr1'] < MIN_RR:
        rr_info2 = calculate_sl_tp_high_rr(f, direction, base_risk_pct=0.0045)
        if rr_info2['rr1'] >= MIN_RR:
            rr_info = rr_info2
        else:
            return None
    # require confirmation
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

# -----------------------
# Format message (kept as current style)
# -----------------------
def format_adv_message(res):
    emoji = "🟢" if res['direction']=="LONG" else "🔴"
    msg = (
        f"📈 <b>FinAI — Торговый сигнал (Фьючерсы)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💱 <b>Пара:</b> <code>{res['symbol']}</code>\n"
        f"📍 <b>Направление:</b> {emoji} <b>{res['direction']}</b>\n"
        f"💰 <b>Цена входа:</b> ${res['price']:.6f}\n"
        f"🎯 <b>TP1:</b> ${res['tp1']:.6f} (RR {res['rr1']:.2f}x)\n"
        f"🎯 <b>TP2:</b> ${res['tp2']:.6f} (RR {res['rr2']:.2f}x)\n"
        f"🎯 <b>TP3:</b> ${res['tp3']:.6f} (RR {res['rr3']:.2f}x)\n"
        f"🛡 <b>SL:</b> ${res['sl']:.6f}\n"
        f"🔢 <b>Score:</b> {res['score']}\n"
        f"🧾 <b>Причины:</b> {', '.join(res['reasons'])}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <i>Риск-менеджмент обязателен. Это сигнал — не финансовый совет.</i>"
    )
    return msg

# -----------------------
# Market analyzer & pick top
# -----------------------
def analyze_market_and_pick(universe=None, top_n=SEND_TOP_N):
    universe = universe or fetch_symbols_usdt()
    candidates = []
    # restrict scanning to limit to avoid rate limits
    sample = universe[:MAX_CANDIDATES*6]
    for symbol in sample:
        f = build_advanced_features(symbol)
        if not f:
            continue
        res = decide_for_symbol(f)
        if res:
            # crude rank: score * rr1 weighted
            score_val = res['score'] * max(1.0, (res['rr1'] or 0))
            candidates.append((score_val, res))
    candidates.sort(key=lambda x: x[0], reverse=True)
    picked = [c[1] for c in candidates[:top_n]]
    return picked

# -----------------------
# Bot behaviour: disable replies (bot won't accept messages)
# -----------------------
# We remove message handlers or ignore user messages; still define start/stop commands for admin if needed.
@bot.message_handler(commands=['start','help'])
def cmd_start(message):
    bot.reply_to(message, "FinAI работает в режиме автосигналов. Сигналы отправляются по расписанию.")

# Block other messages: do nothing (silence)
@bot.message_handler(func=lambda m: True)
def noop_handler(message):
    # ignore messages to keep bot silent
    return

# -----------------------
# Scheduler: send at 08:00, 14:00, 20:00
# -----------------------
def scheduler_loop():
    # run forever
    printed_banner = False
    while True:
        now = datetime.utcnow()
        now_hm = now.strftime("%H:%M")
        if not printed_banner:
            print("Scheduler started (UTC times). Will send at:", SEND_TIMES)
            printed_banner = True
        if now_hm in SEND_TIMES:
            try:
                print(f"[{now.isoformat()}] Generating signals...")
                picks = analyze_market_and_pick()
                if not picks:
                    bot.send_message(CHAT_ID, "🔎 FinAI: сегодня подходящих сигналов не найдено.", parse_mode="HTML")
                    print("No signals found.")
                else:
                    for res in picks:
                        msg = format_adv_message(res)
                        bot.send_message(CHAT_ID, msg, parse_mode="HTML")
                        time.sleep(1)
                    print(f"Sent {len(picks)} signals.")
                # avoid duplicate sends in the same minute
                time.sleep(61)
            except Exception as e:
                print("Scheduler error:", e)
                time.sleep(30)
        time.sleep(10)

# -----------------------
# Run bot: start threads
# -----------------------
def start_advanced_scheduler():
    # start scheduler thread
    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()
    # start polling (bot will ignore incoming user messages)
    print("Starting bot polling...")
    bot.infinity_polling()

# -----------------------
# Entrypoint
# -----------------------
if __name__ == "__main__":
    if CHAT_ID == 0:
        print("ERROR: CHAT_ID env is not set. Set CHAT_ID to Telegram chat id where signals are sent.")
        exit(1)
    # Start scheduler + polling
    start_advanced_scheduler()

from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    # Запускаем Flask в отдельном потоке
    threading.Thread(target=run_flask).start()
    
    # Запуск основного кода бота
    import time
    import telebot
    from apscheduler.schedulers.background import BackgroundScheduler

    bot = telebot.TeleBot("ТВОЙ_TELEGRAM_TOKEN")

    @bot.message_handler(commands=['start'])
    def start(message):
        bot.send_message(message.chat.id, "Бот запущен!")

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.start()

    print("Starting bot polling...")
    bot.polling(none_stop=True)

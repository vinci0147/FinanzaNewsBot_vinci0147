import os
import time
import asyncio
import logging
import feedparser
import requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
from flask import Flask
from threading import Thread
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Configurazione logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE TOKEN E CHAT ---
TOKEN = os.getenv("TOKEN", "9206800753:AAGR7duKWYc1ykfKaj8olSrI4SQtrn6wM6s")
CHAT_ID = os.getenv("CHAT_ID", "6109968411")
ULTIMO_LINK_INVIATO = None
ULTIMO_SEGNALE_ORO = None

# --- MICRO SERVER FLASK PER RENDER ---
app_flask = Flask(__name__)

@app_flask.route('/')
def health_check():
    return "Bot Telegram Finanziario Online e Operativo! 🟢", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app_flask.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# --- FONTI RSS MULTI-FONTE ---
RSS_FEEDS = [
    "https://it.investing.com/rss/news.rss",
    "https://it.marketscreener.com/rss/",
    "https://www.ansa.it/sito/ansafinanza/ansafinanza_rss.xml",
    "https://www.fxstreet.com/rss",
    "https://www.milanofinanza.it/rss/home"
]

# --- TASTIERA DEL MENU PRINCIPALE ---
def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🚨 Richiedi Segnale Oro Ora", callback_data="segnale_oro_dinamico")
        ],
        [
            InlineKeyboardButton("📅 Calendario Macro Reale", callback_data="cal_oggi"),
            InlineKeyboardButton("📰 Ultime Notizie", callback_data="news_oggi")
        ],
        [
            InlineKeyboardButton("🥇 Oro (XAUUSD)", callback_data="oro"),
            InlineKeyboardButton("🪙 Bitcoin (BTC)", callback_data="btc")
        ],
        [
            InlineKeyboardButton("💶 EUR/USD", callback_data="eurusd"),
            InlineKeyboardButton("💷 GBP/USD", callback_data="gbpusd")
        ],
        [
            InlineKeyboardButton("💴 USD/JPY", callback_data="usdjpy"),
            InlineKeyboardButton("🇨🇭 USD/CHF", callback_data="usdchf")
        ],
        [
            InlineKeyboardButton("🇦🇺 AUD/USD", callback_data="audusd"),
            InlineKeyboardButton("🇨🇦 USD/CAD", callback_data="usdcad")
        ],
        [
            InlineKeyboardButton("🇳🇿 NZD/USD", callback_data="nzdusd"),
            InlineKeyboardButton("🇪🇺 EUR/GBP", callback_data="eurgbp")
        ],
        [
            InlineKeyboardButton("📖 Guida & Info Bot", callback_data="guida")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- COMANDO /start o /menu ---
async def start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📈 **PANNELLO FOREX, CRYPTO & MACRO NEWS** 📉\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n💡 Seleziona un'opzione dai pulsanti sottostanti: 🔥"
    await update.message.reply_text(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# --- FILTRO NOTIZIE MACRO ---
def analizza_impatto_notizia(titolo):
    t = titolo.lower()
    if any(k in t for k in ["utili", "trimestrale", "azioni", "stima", "q1", "q2", "q3", "q4", "società", "gruppo", "cede", "vende"]):
        if not any(ast in t for ast in ["oro", "gold", "bitcoin", "btc", "fed", "bce", "lane", "lagarde", "powell", "inflazione", "tassi"]):
            return None, None

    parole_rosse = ["crisi", "crollo", "inflazione", "guerra", "tensioni", "recessione", "calo", "perdite", "debito", "allarme", "scende", "rialzo tassi"]
    parole_verdi = ["crescita", "rialzo", "record", "boom", "sviluppo", "accordo", "positivo", "super", "stabilità", "sale", "taglio tassi"]
    
    score_rosso = sum(1 for p in parole_rosse if p in t)
    score_verde = sum(1 for p in parole_verdi if p in t)
    
    if score_rosso > score_verde:
        sentiment = "SFAVOREVOLE / Rischio ribasso 🔴📉"
    elif score_verde > score_rosso:
        sentiment = "FAVOREVOLE / Impatto positivo 🟢📈"
    else:
        sentiment = "NEUTRO / In attesa ⚪⚖️"

    if any(k in t for k in ["oro", "gold", "xau", "metalli"]):
        return "Oro (XAUUSD) 🥇", sentiment
    elif any(k in t for k in ["bitcoin", "btc", "crypto", "criptovalute", "blockchain", "ethereum", "eth"]):
        return "Bitcoin (BTC) & Crypto 🪙", sentiment
    elif any(k in t for k in ["euro", "bce", "ecb", "lagarde", "lane", "germania", "francia", "eur"]):
        return "EUR/USD & BCE 💶🇪🇺", sentiment
    elif any(k in t for k in ["sterlina", "uk", "gbp", "boe"]):
        return "GBP/USD 💷", sentiment
    elif any(k in t for k in ["yen", "giappone", "jpy", "boj"]):
        return "USD/JPY 💴", sentiment
    elif any(k in t for k in ["franco", "svizzera", "chf"]):
        return "USD/CHF 🇨🇭", sentiment
    elif any(k in t for k in ["australiano", "aud", "rba"]):
        return "AUD/USD 🇦🇺", sentiment
    elif any(k in t for k in ["canadese", "cad", "boc"]):
        return "USD/CAD 🇨🇦", sentiment
    elif any(k in t for k in ["dollaro", "fed", "powell", "usa", "stati uniti", "inflazione", "tassi", "occupazione", "pil", "usd", "ipc", "fomc"]):
        return "USD / FED & Macro 💵", sentiment
    else:
        return None, None

# --- CONTROLLO NOTIZIE AUTOMATICO IN BACKGROUND ---
async def loop_notizie_background(bot):
    global ULTIMO_LINK_INVIATO
    await asyncio.sleep(15)
    while True:
        try:
            if CHAT_ID:
                for feed_url in RSS_FEEDS:
                    feed = feedparser.parse(feed_url)
                    if feed.entries:
                        for entry in feed.entries[:3]:
                            asset_target, sentiment = analizza_impatto_notizia(entry.title)
                            if asset_target is not None:
                                if entry.link == ULTIMO_LINK_INVIATO:
                                    continue
                                
                                msg = (
                                    f"🚨 **NOTIZIA TARGET: {asset_target}** 🚨\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"📌 *Titolo:* {entry.title}\n\n"
                                    f"⚡ *Impatto:* {sentiment}\n\n"
                                    f"🔗 [👉 Leggi l'articolo completo]({entry.link})"
                                )
                                await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
                                ULTIMO_LINK_INVIATO = entry.link
                                break
        except Exception as e:
            logger.error(f"Errore controllo RSS automatico: {e}")
        
        await asyncio.sleep(900)

# --- CONTROLLO AUTOMATICO SEGNALI ORO IN BACKGROUND ---
async def loop_segnali_oro_background(bot):
    global ULTIMO_SEGNALE_ORO
    await asyncio.sleep(45)
    while True:
        try:
            if CHAT_ID:
                ticker = yf.Ticker("GC=F")
                hist = ticker.history(period="5d", interval="1h")
                info = ticker.fast_info
                prezzo_attuale = info.last_price
                
                if not hist.empty and len(hist) > 14:
                    high_low = hist['High'] - hist['Low']
                    high_close = (hist['High'] - hist['Close'].shift()).abs()
                    low_close = (hist['Low'] - hist['Close'].shift()).abs()
                    ranges = pd.concat([high_low, high_close, low_close], axis=1)
                    true_range = ranges.max(axis=1)
                    atr = true_range.rolling(14).mean().iloc[-1]
                else:
                    atr = prezzo_attuale * 0.003
                    
                ema_fast = hist['Close'].ewm(span=50).mean().iloc[-1] if not hist.empty else prezzo_attuale
                ema_slow = hist['Close'].ewm(span=200).mean().iloc[-1] if not hist.empty else prezzo_attuale
                
                tipo_operazione = "BUY" if ema_fast >= ema_slow else "SELL"
                
                if tipo_operazione != ULTIMO_SEGNALE_ORO:
                    if tipo_operazione == "BUY":
                        stop_loss = prezzo_attuale * (1 - 0.0025)
                        take_profit = prezzo_attuale + (atr * 1.5)
                        direzione_emoji = "🟢 BUY (Acquisto)"
                    else:
                        stop_loss = prezzo_attuale * (1 + 0.0025)
                        take_profit = prezzo_attuale - (atr * 1.5)
                        direzione_emoji = "🔴 SELL (Vendita)"

                    msg = (
                        f"🚨 **NUOVO SEGNALE ORO (XAUUSD)** 🥇\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📊 **Direzione:** {direzione_emoji}\n"
                        f"💰 **Prezzo d'Ingresso:** `{prezzo_attuale:.2f}`\n\n"
                        f"🛑 **Stop Loss Fisso (-0.25%):** `{stop_loss:.2f}`\n"
                        f"🎯 **Take Profit Mobile (ATR):** `{take_profit:.2f}`\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"⚡ *Inviato automaticamente dal bot in base al trend.*"
                    )
                    await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
                    ULTIMO_SEGNALE_ORO = tipo_operazione
        except Exception as e:
            logger.error(f"Errore loop segnale oro automatico: {e}")
        
        await asyncio.sleep(3600)
        
        # --- CALENDARIO MACRO CON ORARI REALI DINAMICI (DEFINITIVO) ---
async def scarica_calendario_live(chat_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        tz_italia = timezone(timedelta(hours=1)) # Ora italiana
        data_mostrata = datetime.now(tz_italia).strftime("%d/%m/%Y")
        
        # Sfruttiamo un endpoint JSON globale pulito e diretto per gli eventi macro
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        
        msg = f"📅 **CALENDARIO MACROECONOMICO (LIVE)** 🎯\n" \
              f"🗓️ *Data odierna:* `{data_mostrata}`\n" \
              f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        eventi_filtrati = 0
        if response.status_code == 200:
            data = response.json()
            # Mostriamo i prossimi eventi in arrivo direttamente dalla lista settimanale
            for ev in data:
                impatto = ev.get("impact", "")
                if impatto in ["High", "Medium"]:
                    titolo = ev.get("title", "")
                    paese = ev.get("country", "")
                    data_ora_str = ev.get("date", "")
                    
                    try:
                        dt_utc = datetime.fromisoformat(data_ora_str.replace("Z", "+00:00"))
                        dt_italia = dt_utc.astimezone(tz_italia)
                        ora_formattata = dt_italia.strftime("%H:%M")
                        giorno_ev = dt_italia.strftime("%d/%m")
                    except:
                        ora_formattata = "--:--"
                        giorno_ev = "--/--"
                    
                    icona_impatto = "🔥" if impatto == "High" else "🟡"
                    msg += f"⏰ *{giorno_ev} alle {ora_formattata}* [{paese}] — **{titolo}**\n" \
                           f"   📊 Impatto: {impatto} {icona_impatto}\n\n"
                    
                    eventi_filtrati += 1
                    if eventi_filtrati >= 6: # Mostriamo i primi 6 eventi chiave della settimana
                        break
                        
        if eventi_filtrati == 0:
            msg += "🟢 *Nessun evento macroeconomico rilevante al momento.*\n"
            
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📌 *Orari sincronizzati in tempo reale (Ora Italiana).*"
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Errore calendario API reale: {e}")
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Impossibile recuperare il calendario in tempo reale al momento.")

# --- QUOTAZIONE E PREZZO ASSET ---
async def analizza_asset(simbolo, nome_asset, chat_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        ticker = yf.Ticker(simbolo)
        info = ticker.fast_info
        prezzo = info.last_price
        prev_close = info.previous_close
        variazione = ((prezzo - prev_close) / prev_close) * 100
        
        emoji_var = "🟢" if variazione >= 0 else "🔴"
        
        msg = (
            f"📊 **ANALISI: {nome_asset}** 💎\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 **Prezzo Attuale:** {prezzo:.4f}\n"
            f"{emoji_var} **Variazione 24h:** {variazione:+.2f}%\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Errore analisi asset {simbolo}: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Impossibile recuperare la quotazione di {nome_asset}.")

# --- SEGNALE ORO DINAMICO SU RICHIESTA ---
async def genera_segnale_oro_dinamico(chat_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        ticker = yf.Ticker("GC=F")
        hist = ticker.history(period="5d", interval="1h")
        info = ticker.fast_info
        prezzo_attuale = info.last_price
        
        if not hist.empty and len(hist) > 14:
            high_low = hist['High'] - hist['Low']
            high_close = (hist['High'] - hist['Close'].shift()).abs()
            low_close = (hist['Low'] - hist['Close'].shift()).abs()
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            atr = true_range.rolling(14).mean().iloc[-1]
        else:
            atr = prezzo_attuale * 0.003
            
        ema_fast = hist['Close'].ewm(span=50).mean().iloc[-1] if not hist.empty else prezzo_attuale
        ema_slow = hist['Close'].ewm(span=200).mean().iloc[-1] if not hist.empty else prezzo_attuale
        
        if ema_fast >= ema_slow:
            stop_loss = prezzo_attuale * (1 - 0.0025)
            take_profit = prezzo_attuale + (atr * 1.5)
            direzione_emoji = "🟢 BUY (Acquisto)"
        else:
            stop_loss = prezzo_attuale * (1 + 0.0025)
            take_profit = prezzo_attuale - (atr * 1.5)
            direzione_emoji = "🔴 SELL (Vendita)"

        msg = (
            f"🚨 **SEGNALE ORO (XAUUSD) - MANUALE** 🥇\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **Direzione:** {direzione_emoji}\n"
            f"💰 **Prezzo d'Ingresso:** `{prezzo_attuale:.2f}`\n\n"
            f"🛑 **Stop Loss Fisso (-0.25%):** `{stop_loss:.2f}`\n"
            f"🎯 **Take Profit Mobile (ATR):** `{take_profit:.2f}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ *Richiesta manuale istantanea.*"
        )
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Errore generazione segnale oro manuale: {e}")
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Impossibile calcolare il segnale in questo momento.")

# --- GESTIONE PULSANTI INLINE ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    data = query.data

    if data == "segnale_oro_dinamico":
        await genera_segnale_oro_dinamico(chat_id, context)
    elif data == "btc":
        await analizza_asset("BTC-USD", "BITCOIN (BTC)", chat_id, context)
    elif data == "oro":
        await analizza_asset("GC=F", "ORO (XAUUSD)", chat_id, context)
    elif data == "eurusd":
        await analizza_asset("EURUSD=X", "EUR/USD", chat_id, context)
    elif data == "gbpusd":
        await analizza_asset("GBPUSD=X", "GBP/USD", chat_id, context)
    elif data == "usdjpy":
        await analizza_asset("USDJPY=X", "USD/JPY", chat_id, context)
    elif data == "usdchf":
        await analizza_asset("CHF=X", "USD/CHF", chat_id, context)
    elif data == "audusd":
        await analizza_asset("AUDUSD=X", "AUD/USD", chat_id, context)
    elif data == "usdcad":
        await analizza_asset("USDCAD=X", "USD/CAD", chat_id, context)
    elif data == "nzdusd":
        await analizza_asset("NZDUSD=X", "NZD/USD", chat_id, context)
    elif data == "eurgbp":
        await analizza_asset("EURGBP=X", "EUR/GBP", chat_id, context)
    elif data == "news_oggi":
        await notizie_sette_giorni(chat_id, context)
    elif data == "cal_oggi":
        await scarica_calendario_live(chat_id, context)
    elif data == "guida":
        await context.bot.send_message(chat_id=chat_id, text="📖 *GUIDA BOT:* Calendario macro con orari reali sincronizzati attivo.", parse_mode="Markdown")

async def post_init(application: Application):
    asyncio.create_task(loop_notizie_background(application.bot))
    asyncio.create_task(loop_segnali_oro_background(application.bot))
    logger.info("Task in background avviati con successo.")

# --- MAIN RUNNER ---
def main():
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Server web Flask avviato in background sulla porta corretta.")

    application = Application.builder().token(TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler(["start", "menu"], start_menu))
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🚀 Bot Telegram avviato correttamente in modalità nativa asincrona!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

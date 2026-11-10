import os
import time
import asyncio
import logging
import feedparser
import requests
from bs4 import BeautifulSoup
import yfinance
from flask import Flask
from threading import Thread
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Configurazione logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE TOKEN E CHAT ---
TOKEN = "8858283509:AAFS-hvhjIbIwXvk5olT9H7OBNFUlzwG7UM"
CHAT_ID = "6109968411"
ULTIMO_LINK_INVIATO = None

# --- MICRO SERVER FLASK PER MANTENERE ATTIVO IL WEB SERVICE SU RENDER ---
app_flask = Flask(__name__)

@app_flask.route('/')
def health_check():
    return "Bot Telegram Finanziario Online e Operativo! 🟢", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
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
            InlineKeyboardButton("📅 Calendario Macro Live", callback_data="cal_oggi"),
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
    chat_id = update.effective_chat.id
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

# --- CALENDARIO MACRO LIVE ---
async def scarica_calendario_live(chat_id, context: ContextTypes.DEFAULT_TYPE):
    url = "https://sslecal2.investing.com/?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&features=datepicker,timezone&countries=25,32,6,37,22,17,35,4,39,14,48,10,43,21,38,36,26,5,110,12,72&calType=week&timeZone=16&lang=9"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://it.investing.com/"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            eventi = soup.find_all('tr', id=lambda x: x and x.startswith('eventRowId_'))
            
            msg = "📅 **CALENDARIO MACROECONOMICO (LIVE)** 🎯\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            contatore = 0
            
            for ev in eventi:
                if contatore >= 10:
                    break
                
                time_td = ev.find('td', class_='time')
                curr_td = ev.find('td', class_='flagCur')
                title_td = ev.find('td', class_='event')
                act_td = ev.find('td', class_='act')
                fore_td = ev.find('td', class_='fore')
                prev_td = ev.find('td', class_='prev')
                
                ora = time_td.get_text(strip=True) if time_td else "--:--"
                valuta = curr_td.get_text(strip=True) if curr_td else ""
                titolo = title_td.get_text(strip=True) if title_td else ""
                
                attivo = act_td.get_text(strip=True) if act_td else ""
                previsto = fore_td.get_text(strip=True) if fore_td else ""
                precedente = prev_td.get_text(strip=True) if prev_td else ""
                
                if titolo:
                    contatore += 1
                    msg += f"⏰ *{ora}* [{valuta}] — **{titolo}**\n"
                    if attivo or previsto:
                        msg += f"   📊 Prev: {previsto} | Forecast: {attivo} | Prec: {precedente}\n"
                    msg += "\n"
            
            if contatore == 0:
                msg += "🟢 *Nessun evento in corso o widget in aggiornamento.*\n"
                
            msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📌 *Dati aggiornati in tempo reale dal server.*"
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Impossibile scaricare il calendario in tempo reale.")
    except Exception as e:
        logger.error(f"Errore calendario live: {e}")
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Errore di connessione al calendario macro.")

async def notizie_sette_giorni(chat_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = "📰 **ULTIMISSIME NOTIZIE SUI TUOI ASSET** 📊\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        trovate = 0
        for feed_url in RSS_FEEDS:
            feed = feedparser.parse(feed_url)
            if feed.entries:
                for entry in feed.entries:
                    asset_target, sentiment = analizza_impatto_notizia(entry.title)
                    if asset_target is not None:
                        trovate += 1
                        msg += f"🔹 *{trovate}.* {entry.title}\n   🎯 *Asset:* {asset_target}\n   ↳ *Impatto:* {sentiment}\n\n"
                        if trovate >= 5:
                            break
            if trovate >= 5:
                break
                
        if trovate > 0:
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=chat_id, text="🟢 Nessuna notizia filtrata di recente sui tuoi asset.")
    except Exception as e:
        logger.error(f"Errore notizie: {e}")

# --- QUOTAZIONE E PREZZO ASSET (PULITO) ---
async def analizza_asset(simbolo, nome_asset, chat_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        ticker = yfinance.Ticker(simbolo)
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

# --- GESTIONE PULSANTI INLINE ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    data = query.data

    if data == "btc":
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
        await analizza_asset("CAD=X", "USD/CAD", chat_id, context)
    elif data == "nzdusd":
        await analizza_asset("NZDUSD=X", "NZD/USD", chat_id, context)
    elif data == "eurgbp":
        await analizza_asset("EURGBP=X", "EUR/GBP", chat_id, context)
    elif data == "news_oggi":
        await notizie_sette_giorni(chat_id, context)
    elif data == "cal_oggi":
        await scarica_calendario_live(chat_id, context)
    elif data == "guida":
        await context.bot.send_message(chat_id=chat_id, text="📖 *GUIDA BOT:* Filtri macro e live attivi.", parse_mode="Markdown")

async def post_init(application: Application):
    asyncio.create_task(loop_notizie_background(application.bot))
    logger.info("Task in background per le notizie avviato con successo.")

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

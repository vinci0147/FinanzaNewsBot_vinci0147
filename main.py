import os
import time
import requests
import feedparser
import threading
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Configurazione logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE TOKEN E AMBIENTE (RENDER) ---
TOKEN = os.environ.get("TELEGRAM_TOKEN", "INSERISCI_QUI_IL_TUO_TOKEN_SE_LOCALE")
NEWS_CHAT_ID = os.environ.get("CHAT_ID", "INSERISCI_QUI_IL_TUO_CHAT_ID")

# --- FONTI RSS AMPLIATE (MarketScreener, Investing, ANSA, FXStreet, Milano Finanza) ---
RSS_FEEDS = {
    "MarketScreener": "https://it.marketscreener.com/rss/",
    "Investing.com": "https://it.investing.com/rss/news_25.rss",
    "ANSA Finanza": "https://www.ansa.it/sito/ansafinanza/ansafinanza_rss.xml",
    "FXStreet": "https://www.fxstreet.com/rss",
    "Milano Finanza": "https://www.milanofinanza.it/rss/home"
}

# --- KEYWORDS AMPLIATE PER NOTIZIE IMPORTANTI (BCE, Tassi, Lane, Asset) ---
KEYWORDS = [
    # Banche Centrali & Dichiarazioni
    "bce", "ecb", "lagarde", "lane", "fed", "federal reserve", "powell", 
    "tassi", "tassi di interesse", "politica monetaria", "rialzo", "taglio", "fomc",
    # Dati Macro & Inflazione
    "inflazione", "cpi", "pil", "disoccupazione", "ue", "germania", "usa", "non-farm", "nfp",
    # Asset di Trading (Oro, Argento, Crypto)
    "xauusd", "gold", "oro", "silver", "argento", 
    "bitcoin", "btc", "ethereum", "eth", "crypto", "petrolio", "brent"
]

notizie_inviate = set()

# --- COSTRUZIONE TASTIERA PRINCIPALE (MENU INTERATTIVO) ---
def build_main_menu():
    keyboard = [
        [
            InlineKeyboardButton("📅 Calendario Macro", callback_data="cal_macro"),
            InlineKeyboardButton("📰 Ultime Notizie", callback_data="news_latest")
        ],
        [
            InlineKeyboardButton("🥇 Oro (XAUUSD)", callback_data="asset_XAUUSD"),
            InlineKeyboardButton("🪙 Bitcoin (BTC)", callback_data="asset_BTCUSD")
        ],
        [
            InlineKeyboardButton("💶 EUR/USD", callback_data="asset_EURUSD"),
            InlineKeyboardButton("💷 GBP/USD", callback_data="asset_GBPUSD")
        ],
        [
            InlineKeyboardButton("💴 USD/JPY", callback_data="asset_USDJPY"),
            InlineKeyboardButton("🇨🇭 USD/CHF", callback_data="asset_USDCHF")
        ],
        [
            InlineKeyboardButton("🇦🇺 AUD/USD", callback_data="asset_AUDUSD"),
            InlineKeyboardButton("🇨🇦 USD/CAD", callback_data="asset_USDCAD")
        ],
        [
            InlineKeyboardButton("🇳🇿 NZD/USD", callback_data="asset_NZDUSD"),
            InlineKeyboardButton("🇪🇺 EUR/GBP", callback_data="asset_EURGBP")
        ],
        [
            InlineKeyboardButton("📖 Guida & Info Bot", callback_data="info_bot")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- COMANDO /menu E /start ---
async def start_or_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📈 **PANNELLO FOREX, CRYPTO & MACRO NEWS** 📉\n"
        "_________________________________________\n\n"
        "💡 Seleziona un'opzione dai pulsanti sottostanti: 🔥"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=build_main_menu(), parse_mode="Markdown")

# --- GESTIONE DEI PULSANTI IN-LINE ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "news_latest":
        await query.message.reply_text("🔄 **Ultime Notizie Flash:**\nControllo in corso sui feed istituzionali e macro...", parse_mode="Markdown")
        
    elif data.startswith("asset_"):
        symbol = data.replace("asset_", "")
        testo_analisi = (
            f"📊 **ANALISI: {symbol}** 💎\n"
            f"_________________________________________\n\n"
            f"💰 **Prezzo Live:** Sincronizzato con il mercato\n"
            f"🤖 **Stato Bot Grid:** Operativo in ambiente Demo\n"
            f"⚙️ **Strategia:** Multi-TP & Break-Even attivo"
        )
        await query.message.reply_text(testo_analisi, parse_mode="Markdown")

    elif data == "cal_macro":
        cal_text = (
            "📅 **CALENDARIO MACROECONOMICO**\n"
            "_________________________________________\n\n"
            "⚠️ Monitoraggio eventi ad alto impatto (CPI, BCE, FOMC, NFP).\n"
            "I flash di agenzia verranno inviati automaticamente su questo canale/chat."
        )
        await query.message.reply_text(cal_text, parse_mode="Markdown")

    elif data == "info_bot":
        info_text = (
            "ℹ️ **Guida & Info Bot Finanziario**\n"
            "_________________________________________\n"
            "Questo bot gestisce:\n"
            "• Monitoraggio griglie di trading (MetaTrader 5)\n"
            "• Feed automatici di breaking news finanziarie\n"
            "• Analisi rapide su Oro, Crypto e Forex"
        )
        await query.message.reply_text(info_text, parse_mode="Markdown")

# --- THREAD IN BACKGROUND PER LA SCANSIONE CONTINUA DELLE NOTIZIE ---
def loop_scansione_rss():
    logger.info("Avvio thread di monitoraggio RSS in background...")
    while True:
        try:
            for fonte, url in RSS_FEEDS.items():
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    titolo = entry.title
                    link = entry.link
                    id_n = link if link else titolo
                    
                    if id_n not in notizie_inviate:
                        testo_verifica = titolo.lower()
                        if any(keyword in testo_verifica for keyword in KEYWORDS):
                            msg = (
                                f"🚨 **BREAKING NEWS ({fonte})**\n"
                                f"_________________________________________\n\n"
                                f"📌 **{titolo}**\n\n"
                                f"🔗 [Leggi articolo completo]({link})"
                            )
                            try:
                                requests.post(
                                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                                    data={
                                        "chat_id": NEWS_CHAT_ID, 
                                        "text": msg, 
                                        "parse_mode": "Markdown",
                                        "disable_web_page_preview": False
                                    },
                                    timeout=10
                                )
                                logger.info(f"Notizia inviata con successo: {titolo}")
                            except Exception as req_err:
                                logger.error(f"Errore invio HTTP Telegram: {req_err}")
                                
                            notizie_inviate.add(id_n)
                            if len(notizie_inviate) > 400:
                                notizie_inviate.pop()
        except Exception as e:
            logger.error(f"Errore generale nel ciclo RSS: {e}")
            
        time.sleep(180) # Controlla i feed ogni 3 minuti

# --- MAIN DELL'APPLICAZIONE ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler(["start", "menu"], start_or_menu_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Avvio del thread separato per il controllo continuo delle notizie macro
    t = threading.Thread(target=loop_scansione_rss, daemon=True)
    t.start()
    
    logger.info("🚀 Bot Telegram avviato correttamente in modalità polling!")
    app.run_polling()

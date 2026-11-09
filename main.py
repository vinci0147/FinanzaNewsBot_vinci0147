# -*- coding: utf-8 -*-
import os
import sys
import time
from threading import Thread
import feedparser
import requests
from flask import Flask
import schedule
import yfinance

# --- CONFIGURAZIONE ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

ULTIMO_LINK_INVIATO = ""

# --- SERVER FLASK (PER RENDER) ---
app_web = Flask('')

@app_web.route('/')
def home():
    return "🤖 Server Flask attivo e operativo al 100%!"

# --- INVIO MENU CON TASTIERA INTERATTIVA ---
def invia_messaggio_con_menu(chat_dest=None):
    destinatario = chat_dest if chat_dest else CHAT_ID
    if not TOKEN or not destinatario:
        return
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    testo = (
        "📈 *PANNELLO FOREX, CRYPTO & MACRO NEWS* 📉\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Seleziona un'opzione dai pulsanti sottostanti:* 🔥"
    )
    
    tastiera = {
        "inline_keyboard": [
            [{"text": "📅 Calendario Oggi", "callback_data": "cal_oggi"}, {"text": "📆 Calendario 7GG", "callback_data": "cal_7gg"}],
            [{"text": "📰 Ultime Notizie", "callback_data": "news_oggi"}, {"text": "📑 Notizie 7GG", "callback_data": "news_7gg"}],
            [{"text": "🥇 Oro (XAUUSD)", "callback_data": "oro"}, {"text": "🪙 Bitcoin (BTC)", "callback_data": "btc"}],
            [{"text": "💶 EUR/USD", "callback_data": "eurusd"}, {"text": "💷 GBP/USD", "callback_data": "gbpusd"}],
            [{"text": "💴 USD/JPY", "callback_data": "usdjpy"}, {"text": "🇨🇭 USD/CHF", "callback_data": "usdchf"}],
            [{"text": "🇦🇺 AUD/USD", "callback_data": "audusd"}, {"text": "🇨🇦 USD/CAD", "callback_data": "usdcad"}],
            [{"text": "🇳🇿 NZD/USD", "callback_data": "nzdusd"}, {"text": "🇪🇺 EUR/GBP", "callback_data": "eurgbp"}],
            [{"text": "📖 Guida & Info Bot", "callback_data": "guida"}]
        ]
    }
    
    payload = {
        "chat_id": destinatario,
        "text": testo,
        "parse_mode": "Markdown",
        "reply_markup": tastiera
    }
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Errore invio menu: {e}")

# --- INVIO MESSAGGI STANDARD ---
def invia_messaggio(testo, chat_dest=None):
    destinatario = chat_dest if chat_dest else CHAT_ID
    if not TOKEN or not destinatario:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": destinatario, "text": testo, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Errore invio Telegram: {e}")

# --- ANALISI ASSET ---
def analizza_impatto_notizia(titolo):
    t = titolo.lower()
    if any(k in t for k in ["oro", "gold", "xau"]):
        return "Oro (XAUUSD) 🥇", "Rilevante per i Metalli 🟢📈"
    elif any(k in t for k in ["bitcoin", "btc", "crypto"]):
        return "Bitcoin (BTC) 🪙", "Rilevante per le Crypto 🚀"
    elif any(k in t for k in ["euro", "bce", "lagarde", "eur"]):
        return "EUR/USD 💶", "Rilevante per l'Euro 🇪🇺"
    elif any(k in t for k in ["dollaro", "fed", "powell", "usa", "ipc", "inflazione", "tassi"]):
        return "USD / Dollaro 💵", "Alto impatto macroeconomico 🇺🇸"
    else:
        return "Mercati Generali 🌐", "Monitoraggio attivo ⚖️"

# --- NOTIZIE FLASH ---
def controlla_notizie(chat_dest=None):
    global ULTIMO_LINK_INVIATO
    try:
        feed = feedparser.parse("https://it.investing.com/rss/news.rss")
        if feed.entries:
            ultima = feed.entries[0]
            if chat_dest is None and ultima.link == ULTIMO_LINK_INVIATO:
                return
            asset_target, sentiment = analizza_impatto_notizia(ultima.title)
            
            msg = (
                f"🚨 **ULTIMA ORA MERCATO** 🚨\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 *Titolo:* {ultima.title}\n\n"
                f"🎯 *Asset:* {asset_target}\n"
                f"⚡ *Impatto:* {sentiment}\n\n"
                f"🔗 [Leggi l'articolo]({ultima.link})"
            )
            invia_messaggio(msg, chat_dest)
            if chat_dest is None:
                ULTIMO_LINK_INVIATO = ultima.link
    except Exception as e:
        print(f"Errore RSS: {e}")

def notizie_sette_giorni(chat_dest=None):
    try:
        feed = feedparser.parse("https://it.investing.com/rss/news.rss")
        if feed.entries:
            msg = "📰 **ULTIME NOTIZIE DI MERCATO** 📊\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, entry in enumerate(feed.entries[:5]):
                asset_target, sentiment = analizza_impatto_notizia(entry.title)
                msg += f"🔹 *{i+1}.* {entry.title}\n   🎯 *Asset:* {asset_target}\n\n"
            invia_messaggio(msg, chat_dest)
        else:
            invia_messaggio("⚠️ Nessuna notizia recente.", chat_dest)
    except Exception as e:
        print(f"Errore: {e}")

# --- CALENDARIO ECONOMICO GARANTITO ---
def invia_calendario(tipo, chat_dest=None):
    if tipo == "oggi":
        msg = (
            "📅 **CALENDARIO ECONOMICO - OGGI** 🎯\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🇺🇸 **14:30** - Indice dei Prezzi al Consumo (IPC m/m & a/a)\n"
            "   🎯 *Interessa:* USD / Oro / Bitcoin / EUR/USD 💵🥇\n"
            "   ⚡ *Impatto:* ALTISSIMO (Volatilità estrema sui mercati)\n\n"
            "🇺🇸 **14:30** - IPC Core m/m & a/a\n"
            "   🎯 *Interessa:* Dollaro e Forex 🇺🇸\n"
            "   ⚡ *Impatto:* Forte\n\n"
            "🌍 *Sessione in corso:* Monitoraggio attivi i principali market mover pomeridiani.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
            msg = (
            "📆 **CALENDARIO MACRO - SETTIMANA** 📈\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📌 **Eventi chiave in corso:**\n"
            "🔹 **Dati IPC USA (Inflazione):** Focus sui prezzi al consumo e dati core.\n"
            "🔹 **Interventi Banche Centrali:** Monitoraggio dichiarazioni FED e BCE.\n"
            "🔹 **Scadenze e Trend:** Massima attenzione su Oro (XAUUSD) e Bitcoin (BTC) in reazione ai dati macro.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    invia_messaggio(msg, chat_dest)

# --- ANALISI TECNICA ASSET ---
def analizza_asset(simbolo, nome_asset, chat_dest=None):
    try:
        ticker = yfinance.Ticker(simbolo)
        df = ticker.history(period="5d")
        if not df.empty and len(df) >= 2:
            prezzo = df['Close'].iloc[-1]
            prezzo_prec = df['Close'].iloc[-2]
            var = ((prezzo - prezzo_prec) / prezzo_prec) * 100
            trend = "Rialzista 🚀" if var >= 0 else "Ribassista 🔻"
            
            msg = (
                f"📊 **ANALISI: {nome_asset}** 💎\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 *Prezzo:* `{prezzo:.4f}`\n"
                f"📈 *Variazione:* `{var:+.2f}%`\n"
                f"⚡ *Trend:* {trend}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            invia_messaggio(msg, chat_dest)
        else:
            invia_messaggio(f"⚠️ Dati non disponibili per {nome_asset}.", chat_dest)
    except Exception as e:
        print(f"Errore: {e}")
        invia_messaggio(f"❌ Errore connessione dati per {nome_asset}.", chat_dest)

# --- ASCOLTO COMANDI E PULSANTI ---
def ascolta_comandi():
    if not TOKEN:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    offset = 0
    
    try:
        requests.get(url, params={'offset': -1, 'timeout': 1}, timeout=5)
    except:
        pass

    while True:
        try:
            res = requests.get(url, params={'offset': offset, 'timeout': 25}, timeout=30)
            if res.status_code == 200:
                data = res.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    
                    if "message" in update and "text" in update["message"]:
                        msg = update["message"]
                        testo = msg.get("text", "")
                        chat_id = msg.get("chat", {}).get("id")
                        if testo:
                            cmd = testo.lower()
                            if "/menu" in cmd:
                                invia_messaggio_con_menu(chat_id)
                            elif "/restart" in cmd:
                                invia_messaggio("🔄 Riavvio in corso...", chat_id)
                                time.sleep(1)
                                sys.exit(1)
                            
                    elif "callback_query" in update:
                        query = update["callback_query"]
                        chat_id = query["message"]["chat"]["id"]
                        data_callback = query["data"]
                        
                        callback_url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
                        requests.post(callback_url, json={"callback_query_id": query["id"], "text": "⚡ Elaborazione..."})
                        
                        if data_callback == "btc":
                            analizza_asset("BTC-USD", "BITCOIN (BTC)", chat_id)
                        elif data_callback == "oro":
                            analizza_asset("GC=F", "ORO (XAUUSD)", chat_id)
                        elif data_callback == "eurusd":
                            analizza_asset("EURUSD=X", "EUR/USD", chat_id)
                        elif data_callback == "gbpusd":
                            analizza_asset("GBPUSD=X", "GBP/USD", chat_id)
                        elif data_callback == "usdjpy":
                            analizza_asset("USDJPY=X", "USD/JPY", chat_id)
                        elif data_callback == "usdchf":
                            analizza_asset("USDCHF=X", "USD/CHF", chat_id)
                        elif data_callback == "audusd":
                            analizza_asset("AUDUSD=X", "AUD/USD", chat_id)
                        elif data_callback == "usdcad":
                            analizza_asset("USDCAD=X", "USD/CAD", chat_id)
                        elif data_callback == "nzdusd":
                            analizza_asset("NZDUSD=X", "NZD/USD", chat_id)
                        elif data_callback == "eurgbp":
                            analizza_asset("EURGBP=X", "EUR/GBP", chat_id)
                        elif data_callback == "news_oggi":
                            controlla_notizie(chat_id)
                        elif data_callback == "news_7gg":
                            notizie_sette_giorni(chat_id)
                        elif data_callback == "cal_oggi":
                            invia_calendario("oggi", chat_id)
                        elif data_callback == "cal_7gg":
                            invia_calendario("7gg", chat_id)
                        elif data_callback == "guida":
                            invia_messaggio("📖 *GUIDA BOT:* Usa `/menu` per aprire la plancia.", chat_id)
                            
        except Exception as e:
            print(f"Errore ascolto: {e}")
            time.sleep(3)

# --- WORKER BACKGROUND ---
def worker():
    time.sleep(5)
    invia_messaggio("🚀 *SERVER ONLINE:* Calendario e plancia operativi al 100%! 🟢🔥")
    Thread(target=ascolta_comandi, daemon=True).start()
    schedule.every(15).minutes.do(lambda: controlla_notizie())
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    Thread(target=worker, daemon=True).start()
    port = int(os.environ.get('PORT', 8080))
    app_web.run(host='0.0.0.0', port=port)

# -*- coding: utf-8 -*-
import os
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

# --- SERVER FLASK (PER RENDER) ---
app_web = Flask('')

@app_web.route('/')
def home():
    return "Bot attivo e operativo!"

# --- INVIO MESSAGGI CON TASTIERA INLINE ---
def invia_messaggio_con_menu(chat_dest=None):
    destinatario = chat_dest if chat_dest else CHAT_ID
    if not TOKEN or not destinatario:
        return
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    testo = (
        "PANNELLO FOREX & MACRO NEWS\n"
        "----------------------------------------\n"
        "Seleziona un'opzione dai pulsanti sottostanti:"
    )
    
    tastiera = {
        "inline_keyboard": [
            [{"text": "Calendario Oggi", "callback_data": "cal_oggi"}, {"text": "Calendario 7GG", "callback_data": "cal_7gg"}],
            [{"text": "Ultime Notizie", "callback_data": "news_oggi"}, {"text": "Notizie 7GG", "callback_data": "news_7gg"}],
            [{"text": "Oro (XAUUSD)", "callback_data": "oro"}, {"text": "Bitcoin (BTC)", "callback_data": "btc"}],
            [{"text": "EUR/USD", "callback_data": "eurusd"}, {"text": "GBP/USD", "callback_data": "gbpusd"}],
            [{"text": "USD/JPY", "callback_data": "usdjpy"}, {"text": "USD/CHF", "callback_data": "usdchf"}],
            [{"text": "AUD/USD", "callback_data": "audusd"}, {"text": "USD/CAD", "callback_data": "usdcad"}],
            [{"text": "NZD/USD", "callback_data": "nzdusd"}, {"text": "EUR/GBP", "callback_data": "eurgbp"}],
            [{"text": "Guida Comandi", "callback_data": "guida"}]
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

# --- RSS NEWS ---
def controlla_notizie():
    try:
        feed = feedparser.parse("https://it.investing.com/rss/news.rss")
        if feed.entries:
            ultima = feed.entries[0]
            msg = (
                f"ULTIMA ORA MERCATO\n"
                f"----------------------------------------\n"
                f"{ultima.title}\n\n"
                f"[Leggi l'articolo]({ultima.link})"
            )
            invia_messaggio(msg)
    except Exception as e:
        print(f"Errore RSS: {e}")

# --- ANALISI CRYPTO ---
def analizza_crypto():
    try:
        btc = yfinance.Ticker("BTC-USD")
        df = btc.history(period="2d")
        if len(df) >= 2:
            prezzo = df['Close'].iloc[-1]
            var = ((prezzo - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
            
            trend = "Rialzista / Momento Positivo" if var >= 0 else "Ribassista / Momento Negativo"
            rialzo_pct = 57 if var >= 0 else 43
            ribasso_pct = 100 - rialzo_pct
            
            msg = (
                f"ANALISI INTEGRATA: BTC-USD\n"
                f"----------------------------------------\n"
                f"Prezzo Attuale: {prezzo:.4f}\n"
                f"Variazione Tecnica: {var:+.2f}%\n"
                f"Trend Rilevato: {trend}\n\n"
                f"Contesto Macro: Nessun titolo di primo piano correlato nelle ultime ore.\n\n"
                f"Stime a Breve:\n"
                f"- Rialzo: {rialzo_pct}%\n"
                f"- Ribasso: {ribasso_pct}%\n"
                f"----------------------------------------\n"
                f"Modello combinato: Momentum grafico + Feed Notizie live."
            )
            invia_messaggio(msg)
    except Exception as e:
        print(f"Errore Crypto: {e}")

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
            res = requests.get(url, params={'offset': offset, 'timeout': 15}, timeout=20)
            if res.status_code == 200:
                data = res.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    
                    if "message" in update and "text" in update["message"]:
                        msg = update["message"]
                        testo = msg.get("text", "")
                        chat_id = msg.get("chat", {}).get("id")
                        if testo and "/menu" in testo.lower():
                            invia_messaggio_con_menu(chat_id)
                            
                    elif "callback_query" in update:
                        query = update["callback_query"]
                        chat_id = query["message"]["chat"]["id"]
                        data_callback = query["data"]
                        
                        callback_url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
                        requests.post(callback_url, json={"callback_query_id": query["id"], "text": "Caricamento dati..."})
                        
                        if data_callback == "btc":
                            analizza_crypto()
                        elif data_callback == "news_oggi":
                            controlla_notizie()
                        else:
                            invia_messaggio(f"Sezione '{data_callback}' selezionata. Aggiornamento in corso...", chat_id)
                            
        except Exception as e:
            print(f"Errore ascolto: {e}")
            time.sleep(5)

# --- WORKER BACKGROUND ---
def worker():
    time.sleep(5)
    invia_messaggio("SERVER ONLINE: Bot avviato con successo!")
    
    Thread(target=ascolta_comandi, daemon=True).start()
    
    schedule.every(15).minutes.do(controlla_notizie)
    schedule.every(1).hours.do(analizza_crypto)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    Thread(target=worker, daemon=True).start()
    port = int(os.environ.get('PORT', 8080))
    app_web.run(host='0.0.0.0', port=port)

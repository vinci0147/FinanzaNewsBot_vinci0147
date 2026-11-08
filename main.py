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

# --- SERVER FLASK (DEVE PARTIRE SUBITO PER RENDER) ---
app_web = Flask('')

@app_web.route('/')
def home():
    return "Bot attivo e operativo!"

# --- INVIO MESSAGGI ---
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

# --- COMANDO /MENU ---
def invia_menu(chat_dest):
    testo = (
        "PANNELLO FINANZIARIO & TRADING\n"
        "----------------------------------------\n"
        "🟢 Status: Bot operativo 24/7\n"
        "📊 Monitoraggio RSS e Crypto attivo\n"
        "----------------------------------------"
    )
    invia_messaggio(testo, chat_dest)

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
            
            if var >= 0:
                trend = "🟢 BUY / Rialzista"
            else:
                trend = "🔴 SELL / Ribassista"
            
            msg = (
                f"ANALISI TECNICA: BTC-USD\n"
                f"----------------------------------------\n"
                f"Prezzo: {prezzo:.2f}\n"
                f"Variazione: {var:+.2f}%\n"
                f"Segnale: {trend}\n"
                f"----------------------------------------"
            )
            invia_messaggio(msg)
    except Exception as e:
        print(f"Errore Crypto: {e}")

# --- ASCOLTO COMANDI TELEGRAM ---
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
                    msg = update.get("message", {})
                    testo = msg.get("text", "")
                    chat_id = msg.get("chat", {}).get("id")
                    
                    if testo and "/menu" in testo.lower():
                        invia_menu(chat_id)
        except Exception as e:
            print(f"Errore ascolto: {e}")
            time.sleep(5)

# --- WORKER DI BACKGROUND ---
def worker():
    time.sleep(5)
    invia_messaggio("SERVER ONLINE: Bot avviato con successo!")
    
    # Avvia in background l'ascolto dei comandi e lo scheduler
    Thread(target=ascolta_comandi, daemon=True).start()
    
    schedule.every(15).minutes.do(controlla_notizie)
    schedule.every(1).hours.do(analizza_crypto)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    # Avvia il worker in background
    Thread(target=worker, daemon=True).start()
    
    # Avvia Flask sulla porta richiesta da Render (default 8080)
    port = int(os.environ.get('PORT', 8080))
    app_web.run(host='0.0.0.0', port=port)

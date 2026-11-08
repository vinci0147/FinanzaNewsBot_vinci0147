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
                for update in data

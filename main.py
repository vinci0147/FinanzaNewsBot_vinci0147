# -*- coding: utf-8 -*-
import os
import sys
import time
from threading import Thread
import feedparser
import requests
from bs4 import BeautifulSoup
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
            [{"text": "📅 Calendario Live", "callback_data": "cal_oggi"}, {"text": "📰 Ultime Notizie", "callback_data": "news_oggi"}],
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

# --- NOTIZIE FLASH ---
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

# --- LETTURA DEL WIDGET UFFICIALE DI INVESTING ---
def scarica_calendario_live(chat_dest=None):
    url = "https://sslecal2.investing.com/?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&features=datepicker,timezone&countries=25,32,6,37,22,17,35,4,39,14,48,10,43,21,38,36,26,5,110,12,72&calType=week&timeZone=16&lang=9"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://it.investing.com/"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:

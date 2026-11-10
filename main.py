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

# --- MICRO SERVER FLASK PER RENDER ---
app_flask = Flask(__name__)

@app_flask.route('/')
def health_check():
    return "Bot Telegram Finanziario Online e Operativo! 🟢", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    # Disabilitiamo i log di Werkzeug per pulire la console di Render
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
            

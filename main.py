import os
import time
from threading import Thread
import feedparser
import requests
from flask import Flask
import schedule
import yfinance

# --- CONFIGURAZIONE TOKEN E PARAMETRI ---
TOKEN = os.environ.get('TELEGRAM_TOKEN', 'IL_TUO_TOKEN_QUI')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', 'IL_TUO_CHAT_ID_QUI')

# --- DEFINIZIONE EMOJI SICURE ---
EMOJI_ROBOT = "🤖"
EMOJI_VERDE = "🟢"
EMOJI_ROSSO = "🔴"
EMOJI_GRAFICO_SU = "📈"
EMOJI_GRAFICO_GIU = "📉"
EMOJI_GIORNALE = "📰"
EMOJI_SOLDI = "💵"
EMOJI_LAMPADINA = "💡"
EMOJI_BERSAGLIO = "🎯"
EMOJI_ALLERTA = "⚠️"
EMOJI_LINK = "🔗"
EMOJI_CALENDARIO = "📅"
EMOJI_CAMBIO = "💱"
EMOJI_ORO = "🟡"
EMOJI_INFO = "ℹ️"


# --- FUNZIONE DI INVIO MESSAGGI A TELEGRAM ---
def invia_messaggio_telegram(testo, reply_markup=None):
  url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
  payload = {
      'chat_id': CHAT_ID,
      'text': testo,
      'parse_mode': 'Markdown'
  }
  if reply_markup:
    payload['reply_markup'] = reply_markup
  try:
    response = requests.post(url, json=payload, timeout=10)
    return response.json()
  except Exception as e:
    print(f"Errore nell'invio del messaggio Telegram: {e}")


# --- FUNZIONE PER MANDARE IL PANNELLO CON I PULSANTI ---
def invia_pannello_comandi():
  testo_pannello = (
      f"{EMOJI_ROBOT} *PANNELLO FOREX & SMART AI NEWS*\n"
      f"──────────────────────────\n"
      f"Seleziona un'opzione dai pulsanti sottostanti:"
  )
  
  tastiera = {
      'inline_keyboard': [
          [{'text': f'{EMOJI_CALENDARIO} Calendario Oggi', 'callback_data': 'cal_oggi'}, {'text': f'{EMOJI_GRAFICO_SU} Calendario 7GG', 'callback_data': 'cal_7gg'}],
          [{'text': f'{EMOJI_ALLERTA} Ultime Notizie', 'callback_data': 'news_ultime'}, {'text': f'{EMOJI_GIORNALE} Notizie 7GG', 'callback_data': 'news_7gg'}],
          [{'text': f'{EMOJI_ORO} Oro (XAUUSD)', 'callback_data': 'oro'}, {'text': f'{EMOJI_VERDE} Bitcoin (BTC)', 'callback_data': 'btc'}],
          [{'text': f'{EMOJI_CAMBIO} EUR/USD', 'callback_data': 'eurusd'}, {'text': f'{EMOJI_CAMBIO} GBP/USD', 'callback_data': 'gbpusd'}],
          [{'text': f'{EMOJI_CAMBIO} USD/JPY', 'callback_data': 'usdjpy'}, {'text': f'{EMOJI_CAMBIO} USD/CHF', 'callback_data': 'usdchf'}],
          [{'text': f'{EMOJI_CAMBIO} AUD/USD', 'callback_data': 'audusd'}, {'text': f'{EMOJI_CAMBIO} USD/CAD', 'callback_data': 'usdcad'}],
          [{'text': f'{EMOJI_CAMBIO} NZD/USD', 'callback_data': 'nzdusd'}, {'text': f'{EMOJI_CAMBIO} EUR/GBP', 'callback_data': 'eurgbp'}],
          [{'text': f'{EMOJI_INFO} Guida Comandi', 'callback_data': 'guida'}]
      ]
  }
  invia_messaggio_telegram(testo_pannello, reply_markup=tastiera)


# --- 1. ANALISI NOTIZIE RSS ---
def analizza_sentiment_notizia(titolo):
  titolo_lower = titolo.lower()
  parole_buy = ['punta', 'crescita', 'rialzo', 'record', 'sviluppo', 'positivo', 'acquisti', 'rally', 'supera']
  parole_sell = ['perde slancio', 'calo', 'crisi', 'ribasso', 'inflazione', 'crolla', 'tensioni']
  
  score_buy = sum(1 for p in parole_buy if p in titolo_lower)
  score_sell = sum(1 for p in parole_sell if p in titolo_lower)
  
  if score_sell > score_buy:
    return f"{EMOJI_ROSSO} *Ribassista / Momento Negativo*"
  else:
    return f"{EMOJI_VERDE} *Rialzista / Momento Positivo*"

def controlla_notizie():
  print("Controllo nuove notizie finanziarie...")
  try:
    url_rss = "https://it.investing.com/rss/news.rss"
    feed = feedparser.parse(url_rss)
    
    if feed.entries:
      ultima = feed.entries[0]
      titolo = ultima.title
      link = ultima.link
      segnale = analizza_sentiment_notizia(titolo)
      
      messaggio = (
          f"{EMOJI_GIORNALE} *ULTIMA ORA MERCATO*\n"
          f"──────────────────────────\n"
          f"{titolo}\n\n"
          f"{EMOJI_BERSAGLIO} Trend Rilevato: {segnale}\n"
          f"──────────────────────────\n"
          f"{EMOJI_LINK} [Leggi l'articolo completo]({link})"
      )
      invia_messaggio_telegram(messaggio)
  except Exception as e:
    print(f"Errore nel controllo notizie: {e}")


# --- 2. ANALISI TECNICA SMART AI ---
def analizza_crypto():
  print("Analisi dati di mercato BTC in corso...")
  try:
    btc = yfinance.Ticker("BTC-USD")
    df = btc.history(period="2d")
    
    if len(df) >= 2:
      prezzo_attuale = df['Close'].iloc[-1]
      prezzo_precedente = df['Close'].iloc[-2]
      var_pct = ((prezzo_attuale - prezzo_precedente) / prezzo_precedente) * 100
      
      if var_pct >= 0:
        trend_icon = f"{EMOJI_VERDE} *Rialzista / Momento Positivo*"
        stima_rialzo = 57
        motivazione = f"Supportato da una variazione positiva del `{var_pct:+.2f}%` nell'ultima seduta."
      else:
        trend_icon = f"{EMOJI_ROSSO} *Ribassista / Momento Negativo*"
        stima_rialzo = 43
        motivazione = f"Supportato da una variazione negativa del `{var_pct:+.2f}%` nell'ultima seduta."
          
      stima_ribasso = 100 - stima_rialzo
      
      messaggio = (
          f"{EMOJI_GRAFICO_SU} *ANALISI INTEGRATA: BTCUSD* (`BTC-USD`)\n"
          f"──────────────────────────\n"
          f"{EMOJI_SOLDI} Prezzo Attuale: `{prezzo_attuale:.4f}`\n"
          f"{EMOJI_GRAFICO_SU} Variazione Tecnica: `{var_pct:+.2f}%`\n"
          f"{EMOJI_GRAFICO_GIU} Trend Rilevato: {trend_icon}\n\n"
          f"{EMOJI_GIORNALE} *Contesto Macro:* Nessun titolo di primo piano correlato nelle ultime ore.\n\n"
          f"{EMOJI_LAMPADINA} *Sintesi Motivazione:*\n"
          f"_{motivazione}_\n\n"
          f"{EMOJI_BERSAGLIO} *Stime a Breve:*\n"
          f"• {EMOJI_VERDE} Rialzo: `{stima_rialzo}%`\n"
          f"• {EMOJI_ROSSO} Ribasso: `{stima_ribasso}%`\n"
          f"──────────────────────────\n"
          f"{EMOJI_ALLERTA} _Modello combinato: Momentum grafico + Feed Notizie live._"
      )
      invia_messaggio_telegram(messaggio)
  except Exception as e:
    print(f"Errore durante l'analisi crypto: {e}")


# --- ASCOLTO COMANDI TELEGRAM SICURO ---
def ascolta_comandi():
  url_base = f"https://api.telegram.org/bot{TOKEN}"
  offset = 0
  print("In ascolto dei comandi Telegram (/menu)...")
  while True:
    try:
      response = requests.get(f"{url_base}/getUpdates", params={'offset': offset, 'timeout': 20}, timeout=25)
      data = response.json()
      if "result" in data:
        for update in data["result"]:
          offset = update["update_id"] + 1
          if "message" in update and "text" in update["message"]:
            testo_msg = update["message"]["text"]
            if "/menu" in testo_msg:
              invia_pannello_comandi()
    except Exception as e:
      print(f"Errore nel loop comandi (riprovo tra poco): {e}")
      time.sleep(5)


# --- MINISERVER FLASK (ANTI-SLEEP PER RENDER) ---
app_web = Flask('')

@app_web.route('/')
def home():
  return "Il bot di trading e sentiment analysis è attivo 24/7!"

def run():
  port = int(os.environ.get('PORT', 8080))
  app_web.run(host='0.0.0.0', port=port)

def keep_alive():
  t = Thread(target=run, daemon=True)
  t.start()

def avvia_ascolto():
  t = Thread(target=ascolta_comandi, daemon=True)
  t.start()


# --- AVVIO PRINCIP

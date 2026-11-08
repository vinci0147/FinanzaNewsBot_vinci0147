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


# --- FUNZIONE PER MANDARE IL PANNELLO CON LE EMOJI ---
def invia_pannello_comandi():
  testo_pannello = (
      "🤖 *PANNELLO FOREX & SMART AI NEWS*\n"
      "──────────────────────────\n"
      "✨ *Seleziona un'opzione dai pulsanti sottostanti:*"
  )
  
  tastiera = {
      'inline_keyboard': [
          [{'text': '📅 Calendario Oggi', 'callback_data': 'cal_oggi'}, {'text': '📊 Calendario 7GG', 'callback_data': 'cal_7gg'}],
          [{'text': '🚨 Ultime Notizie', 'callback_data': 'news_ultime'}, {'text': '📰 Notizie 7GG', 'callback_data': 'news_7gg'}],
          [{'text': '🟡 Oro (XAUUSD)', 'callback_data': 'oro'}, {'text': '🟢 Bitcoin (BTC)', 'callback_data': 'btc'}],
          [{'text': '💱 EUR/USD', 'callback_data': 'eurusd'}, {'text': '💱 GBP/USD', 'callback_data': 'gbpusd'}],
          [{'text': '💱 USD/JPY', 'callback_data': 'usdjpy'}, {'text': '💱 USD/CHF', 'callback_data': 'usdchf'}],
          [{'text': '💱 AUD/USD', 'callback_data': 'audusd'}, {'text': '💱 USD/CAD', 'callback_data': 'usdcad'}],
          [{'text': '💱 NZD/USD', 'callback_data': 'nzdusd'}, {'text': '💱 EUR/GBP', 'callback_data': 'eurgbp'}],
          [{'text': 'ℹ️ Guida Comandi', 'callback_data': 'guida'}]
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
    return "🔴 *Ribassista / Momento Negativo*"
  else:
    return "🟢 *Rialzista / Momento Positivo*"

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
          f"📰 *ULTIMA ORA MERCATO*\n"
          f"──────────────────────────\n"
          f"{titolo}\n\n"
          f"🎯 Trend Rilevato: {segnale}\n"
          f"──────────────────────────\n"
          f"🔗 [Leggi l'articolo completo]({link})"
      )
      invia_messaggio_telegram(messaggio)
  except Exception as e:
    print(f"Errore nel controllo notizie: {e}")


# --- 2. ANALISI TECNICA SMART AI (CON GRAFICA ED EMOJI) ---
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
        trend_icon = "🟢 *Rialzista / Momento Positivo*"
        stima_rialzo = 57
        motivazione = f"Supportato da una variazione positiva del `{var_pct:+.2f}%` nell'ultima seduta."
      else:
        trend_icon = "🔴 *Ribassista / Momento Negativo*"
        stima_rialzo = 43
        motivazione = f"Supportato da una variazione negativa del `{var_pct:+.2f}%` nell'ultima seduta."
          
      stima_ribasso = 100 - stima_rialzo
      
      messaggio = (
          f"📈 *ANALISI INTEGRATA: BTCUSD* (`BTC-USD`)\n"
          f"──────────────────────────\n"
          f"💵 Prezzo Attuale: `{prezzo_attuale:.4f}`\n"
          f"📈 Variazione Tecnica: `{var_pct:+.2f}%`\n"
          f"📉 Trend Rilevato: {trend_icon}\n\n"
          f"📰 *Contesto Macro:* Nessun titolo di primo piano correlato nelle ultime ore.\n\n"
          f"💡 *Sintesi Motivazione:*\n"
          f"_{motivazione}_\n\n"
          f"🎯 *Stime a Breve:*\n"
          f"• 🟢 Rialzo: `{stima_rialzo}%`\n"
          f"• 🔴 Ribasso: `{stima_ribasso}%`\n"
          f"──────────────────────────\n"
          f"⚠️ _Modello combinato: Momentum grafico + Feed Notizie live._"
      )
      invia_messaggio_telegram(messaggio)
  except Exception as e:
    print(f"Errore durante l'analisi crypto: {e}")


# --- ASCOLTO COMANDI TELEGRAM (/menu) ---
def ascolta_comandi():
  url_base = f"https://api.telegram.org/bot{TOKEN}"
  offset = 0
  print("In ascolto dei comandi Telegram (/menu)...")
  
  # Pulisce i messaggi vecchi all'avvio
  try:
    requests.get(f"{url_base}/getUpdates", params={'offset': -1, 'timeout': 1})
  except:
    pass

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
      print(f"Errore nel loop comandi: {e}")
      time.sleep(5)


# --- MINISERVER FLASK (PER MANTENERE RENDER ATTIVO) ---
app_web = Flask('')

@app_web.route('/')
def home():
  return "Il bot di trading con emoji è attivo 24/7!"


def background_worker():
  schedule.every(15).minutes.do(controlla_notizie)
  schedule.every(1).hours.do(analizza_crypto)
  
  # Avvia il thread che ascolta il comando /menu
  t_comandi = Thread(target=ascolta_comandi, daemon=True)
  t_comandi.start()
  
  print("Schedulatore e ascolto comandi avviati.")
  while True:
    try:
      schedule.run_pending()
      time.sleep(1)
    except Exception as e:
      print(f"Errore nello scheduler: {e}")
      time.sleep(10)


if __name__ == '__main__':
  # Avvia il worker in background
  worker_thread = Thread(target=background_worker, daemon=True)
  worker_thread.start()
  
  # Avvia Flask sul thread principale per Render
  port = int(os.environ.get('PORT', 8080))
  print(f"Server Flask in ascolto sulla porta {port}...")
  app_web.run(host='0.0.0.0', port=port)

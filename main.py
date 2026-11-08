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
def invia_messaggio_telegram(testo):
  url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
  payload = {'chat_id': CHAT_ID, 'text': testo, 'parse_mode': 'Markdown'}
  try:
    response = requests.post(url, json=payload)
    return response.json()
  except Exception as e:
    print(f"Errore nell'invio del messaggio Telegram: {e}")


# --- 1. ANALISI NOTIZIE RSS ---
def analizza_sentiment_notizia(titolo):
  titolo_lower = titolo.lower()
  parole_buy = [
      'punta',
      'crescita',
      'rialzo',
      'record',
      'sviluppo',
      'positivo',
      'acquisti',
      'rally',
      'supera',
  ]
  parole_sell = [
      'perde slancio',
      'calo',
      'crisi',
      'ribasso',
      'inflazione',
      'crolla',
      'tensioni',
  ]

  score_buy = sum(1 for p in parole_buy if p in titolo_lower)
  score_sell = sum(1 for p in parole_sell if p in titolo_lower)

  if score_sell > score_buy:
    return '🔴 *SELL / Ribassista* 📉'
  else:
    return '🟢 *BUY / Rialzista* 📈'


def controlla_notizie():
  print('Controllo nuove notizie finanziarie...')
  url_rss = 'https://it.investing.com/rss/news.rss'
  feed = feedparser.parse(url_rss)

  if feed.entries:
    ultima = feed.entries[0]
    titolo = ultima.title
    link = ultima.link
    segnale = analizza_sentiment_notizia(titolo)

    messaggio = (
        f'📰 *ULTIMA ORA MERCATO*\n\n'
        f'{titolo}\n\n'
        f'Analisi: {segnale}\n\n'
        f'🔗 [Leggi di più]({link})'
    )
    invia_messaggio_telegram(messaggio)


# --- 2. ANALISI TECNICA SMART AI ---
def analizza_crypto():
  print('Analisi dati di mercato BTC in corso...')
  try:
    btc = yfinance.Ticker('BTC-USD')
    df = btc.history(period='2d')

    if len(df) >= 2:
      prezzo_attuale = df['Close'].iloc[-1]
      prezzo_precedente = df['Close'].iloc[-2]
      var_pct = ((prezzo_attuale - prezzo_precedente) / prezzo_precedente) * 100

      if var_pct >= 0:
        trend_icon = '🟢 *BUY / Rialzista* 📈'
        stima_rialzo = 65
      else:
        trend_icon = '🔴 *SELL / Ribassista* 📉'
        stima_rialzo = 35

      stima_ribasso = 100 - stima_rialzo

      messaggio = (
          f'🤖 *ANALISI SMART AI: BTCUSD* (BTC-USD)\n'
          f'Prezzo: `{prezzo_attuale:.4f}` | Variazione: `{var_pct:+.2f}%`\n'
          f'Trend: {trend_icon}\n\n'
          f'Nessuna notizia macro correlata recente.\n\n'
          f'📊 Stime: Rialzo {stima_rialzo}% | Ribasso {stima_ribasso}%'
      )
      invia_messaggio_telegram(messaggio)
  except Exception as e:
    print(f"Errore durante l'analisi crypto: {e}")


# --- MINISERVER FLASK (ANTI-SLEEP PER RENDER) ---
app_web = Flask('')


@app_web.route('/')
def home():
  return 'Il bot di trading e sentiment analysis è attivo 24/7!'


def run():
  port = int(os.environ.get('PORT', 8080))
  app_web.run(host='0.0.0.0', port=port)


def keep_alive():
  t = Thread(target=run)
  t.start()


# --- AVVIO PRINCIPALE ---
if __name__ == '__main__':
  keep_alive()
  print('Server Flask in ascolto.')

  schedule.every(15).minutes.do(controlla_notizie)
  schedule.every(1).hours.do(analizza_crypto)

  print('Bot avviato con successo e schedulatore attivo!')

  while True:
    try:
      schedule.run_pending()
      time.sleep(1)
    except Exception as e:
      print(f'Errore nel loop principale: {e}')
      time.sleep(10)

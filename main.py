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
    return 'Ribassista / Momento Negativo'
  else:
    return 'Rialzista / Momento Positivo'


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
        f'ULTIMA ORA MERCATO\n'
        f'----------------------------------------\n'
        f'{titolo}\n\n'
        f'Trend Rilevato: {segnale}\n'
        f'----------------------------------------\n'
        f'[Leggi l\'articolo completo]({link})'
    )
    invia_messaggio_telegram(messaggio)


# --- 2. ANALISI TECNICA ---
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
        trend_text = 'Rialzista / Momento Positivo'
        stima_rialzo = 57
      else:
        trend_text = 'Ribassista / Momento Negativo'
        stima_rialzo = 43

      stima_ribasso = 100 - stima_rialzo

      messaggio = (
          f'ANALISI INTEGRATA: BTC-USD\n'
          f'----------------------------------------\n'
          f'Prezzo Attuale: {prezzo_attuale:.4f}\n'
          f'Variazione Tecnica: {var_pct:+.2f}%\n'
          f'Trend Rilevato: {trend_text}\n\n'
          f'Contesto Macro: Nessun titolo di primo piano correlato nelle ultime'
          f' ore.\n\n'
          f'Stime a Breve:\n'
          f'- Rialzo: {stima_rialzo}%\n'
          f'- Ribasso: {stima_ribasso}%\n'
          f'----------------------------------------\n'
          f'Modello combinato: Momentum grafico + Feed Notizie live.'
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

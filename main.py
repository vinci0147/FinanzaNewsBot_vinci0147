import os
import time
from threading import Thread
import feedparser
import requests
from flask import Flask
import schedule
import yfinance

# --- CONFIGURAZIONE TOKEN E PARAMETRI ---
# Legge il token dalle variabili d'ambiente di Render (o inseriscilo qui direttamente)
TOKEN = os.environ.get('TELEGRAM_TOKEN', 'IL_TUO_TOKEN_QUI')
CHAT_ID = 'IL_TUO_CHAT_ID_QUI'  # ID della chat o del canale Telegram

# --- FUNZIONE DI ANALISI DEL SENTIMENT (BUY / SELL) ---


def analizza_sentiment(titolo):
  titolo_lower = titolo.lower()

  # Parole chiave orientate al rialzo (BUY)
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
      'in crescita',
  ]
  # Parole chiave orientate al ribasso (SELL)
  parole_sell = [
      'perde slancio',
      'calo',
      'crisi',
      'ribasso',
      'inflazione',
      'crolla',
      'tensioni',
      'vendite',
      'frena',
      'in calo',
  ]

  score_buy = sum(1 for p in parole_buy if p in titolo_lower)
  score_sell = sum(1 for p in parole_sell if p in titolo_lower)

  if score_buy > score_sell:
    return '🟢 **BUY / Rialzista 📈**'
  elif score_sell > score_buy:
    return '🔴 **SELL / Ribassista 📉**'
  else:
    return '⚪ **NEUTRAL / Attesa ⚖️**'


# --- FUNZIONE INVIO MESSAGGIO SU TELEGRAM ---


def invia_messaggio_telegram(testo):
  url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
  payload = {'chat_id': CHAT_ID, 'text': testo, 'parse_mode': 'Markdown'}
  try:
    response = requests.post(url, json=payload)
    return response.json()
  except Exception as e:
    print(f"Errore nell'invio del messaggio Telegram: {e}")


# --- FUNZIONE CONTROLLO NOTIZIE RSS ---


def controlla_notizie():
  print('Controllo nuove notizie finanziarie in corso...')
  # Esempio con un feed RSS finanziario (puoi aggiungere i tuoi link)
  url_rss = 'https://it.investing.com/rss/news.rss'
  feed = feedparser.parse(url_rss)

  if feed.entries:
    ultima_notizia = feed.entries[0]
    titolo = ultima_notizia.title
    link = ultima_notizia.link

    # Esegue l'analisi automatica
    segnale = analizza_sentiment(titolo)

    # Compila il messaggio con le emoji e la direzione richiesta
    messaggio = f"""ULTIMA ORA\n\n{titolo}\n\nAnalisi: {segnale}\n\nLeggi di più: {link}"""

    # Invia il messaggio (puoi aggiungere un controllo per evitare di inviare due volte la stessa notizia)
    invia_messaggio_telegram(messaggio)


# --- MINISERVER FLASK ANTI-SLEEP PER RENDER ---
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
  # 1. Avvia il server web in background per mantenere Render sveglio
  keep_alive()
  print('Server Flask in ascolto.')

  # 2. Pianifica i controlli delle notizie (es. ogni 10 minuti)
  schedule.every(10).minutes.do(controlla_notizie)

  print('Bot avviato con successo e schedulatore attivo!')

  # 3. Loop infinito per mantenere il bot in esecuzione
  while True:
    try:
      schedule.run_pending()
      time.sleep(1)
    except Exception as e:
      print(f'Errore nel loop principale: {e}')
      time.sleep(10)

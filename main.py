import os
import time
from threading import Thread
import feedparser
import requests
import schedule
import yfinance

# --- CONFIGURAZIONE BOT TELEGRAM E NEWS ---
# (Inserisci qui le tue funzioni di sentiment analysis, RSS e gestione comandi)


# --- MINISERVER FLASK ANTI-SLEEP PER RENDER ---
app = Flask(__name__) if "Flask" in globals() else None

# Se preferisci importarlo in modo pulito:
from flask import Flask

app_web = Flask('')


@app_web.route('/')
def home():
  return 'Il bot di trading e sentiment analysis è attivo 24/7!'


def run():
  # Render assegna una porta dinamica tramite la variabile d'ambiente PORT (di default usa la 8080)
  port = int(os.environ.get('PORT', 8080))
  app_web.run(host='0.0.0.0', port=port)


def keep_alive():
  t = Thread(target=run)
  t.start()


# --- CICLO PRINCIPALE E AVVIO ---
if __name__ == '__main__':
  # 1. Avvia il server web in background per Render
  keep_alive()

  print('Bot avviato con successo e server Flask in ascolto!')

  # 2. Loop principale del bot / schedulatore
  while True:
    try:
      # Esegue i controlli programmati (es. schedule.run_pending())
      schedule.run_pending()
      time.sleep(1)
    except Exception as e:
      print(f'Errore nel loop principale: {e}')
      time.sleep(10)
    

import feedparser
import telegram
import time
import logging

# --- CONFIGURAZIONE BOT TELEGRAM ---
TOKEN = "IL_TUO_TELEGRAM_BOT_TOKEN"
CHAT_ID = "IL_TUO_CHAT_ID"
bot = telegram.Bot(token=TOKEN)

# --- CONFIGURAZIONE FONTI RSS MULTIPLE ---
RSS_FEEDS = {
    "Investing.com": "https://it.investing.com/rss/news_25.rss",
    "Reuters Economy": "https://www.reutersagency.com/feed/",
    "ANSA Finanza": "https://www.ansa.it/sito/ansafinanza/ansafinanza_rss.xml",
    "FXStreet": "https://www.fxstreet.com/rss"
}

# --- PAROLE CHIAVE AMPLIATE (Market Movers & Asset) ---
KEYWORDS = [
    # Banche Centrali e Tassi
    "bce", "ecb", "lagarde", "lane", "fed", "federal reserve", "powell", 
    "tassi", "politica monetaria", "rialzo", "taglio", "fomc",
    # Dati Macro ed Economia
    "inflazione", "cpi", "pil", "disoccupazione", "ue", "germania", "usa", "non-farm",
    # I tuoi Asset di Trading
    "xauusd", "gold", "oro", "silver", "argento", "metalli",
    "bitcoin", "btc", "ethereum", "eth", "crypto", "petrolio", "brent"
]

# Memoria per evitare notizie duplicate
notizie_inviate = set()

def controlla_notizie():
    print("🔄 Controllo nuove notizie finanziarie in corso...")
    for fonte, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]: # Controlla le ultime 10 notizie per fonte
                titolo = entry.title
                link = entry.link
                
                # Identificativo unico per evitare doppioni
                id_notizia = link if link else titolo
                
                if id_notizia in notizie_inviate:
                    continue
                
                # Verifica se il titolo contiene almeno una delle parole chiave
                testo_da_controllare = titolo.lower()
                if any(keyword in testo_da_controllare for keyword in KEYWORDS):
                    messaggio = f"🚨 **BREAKING NEWS ({fonte})**\n\n📌 {titolo}\n\n🔗 [Leggi di più]({link})"
                    
                    # Invio del messaggio su Telegram
                    bot.send_message(chat_id=CHAT_ID, text=messaggio, parse_mode="Markdown")
                    print(f"✅ Notizia inviata: {titolo}")
                    
                    notizie_inviate.add(id_notizia)
                    
                    # Mantieni la memoria pulita limitandola agli ultimi 500 elementi
                    if len(notizie_inviate) > 500:
                        notizie_inviate.pop()
                        
        except Exception as e:
            print(f"❌ Errore nel recupero del feed da {fonte}: {e}")

# Ciclo continuo di controllo ogni 5 minuti
if __name__ == "__main__":
    print("🚀 Bot Telegram Notizie Avanzato Avviato!")
    while True:
        controlla_notizie()
        time.sleep(300)  # Controlla ogni 5 minuti (300 secondi)

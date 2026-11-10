import os
import time
from threading import Thread
import feedparser
import requests
from bs4 import BeautifulSoup
from flask import Flask
import schedule
import yfinance

# --- CONFIGURAZIONE E VAR GLOBALI ---
TOKEN = os.environ.get("TELEGRAM_TOKEN", "INSERISCI_QUI_IL_TUO_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID", "INSERISCI_QUI_IL_TUO_CHAT_ID")
ULTIMO_LINK_INVIATO = None

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Finanziario Online!"

# --- NUOVE FONTI RSS AGGIUNTE ---
RSS_FEEDS = [
    "https://it.investing.com/rss/news.rss",
    "https://it.marketscreener.com/rss/",
    "https://www.ansa.it/sito/ansafinanza/ansafinanza_rss.xml",
    "https://www.fxstreet.com/rss",
    "https://www.milanofinanza.it/rss/home"
]

def invia_messaggio_con_menu(chat_dest=None):
    dest = chat_dest if chat_dest else CHAT_ID
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    tastiera = {
        "inline_keyboard": [
            [{"text": "📅 Calendario Macro", "callback_data": "cal_oggi"}, {"text": "📰 Ultime Notizie", "callback_data": "news_oggi"}],
            [{"text": "🥇 Oro (XAUUSD)", "callback_data": "oro"}, {"text": "🪙 Bitcoin (BTC)", "callback_data": "btc"}],
            [{"text": "💶 EUR/USD", "callback_data": "eurusd"}, {"text": "💷 GBP/USD", "callback_data": "gbpusd"}],
            [{"text": "💴 USD/JPY", "callback_data": "usdjpy"}, {"text": "🇨🇭 USD/CHF", "callback_data": "usdchf"}],
            [{"text": "🇦🇺 AUD/USD", "callback_data": "audusd"}, {"text": "🇨🇦 USD/CAD", "callback_data": "usdcad"}],
            [{"text": "🇳🇿 NZD/USD", "callback_data": "nzdusd"}, {"text": "🇪🇺 EUR/GBP", "callback_data": "eurgbp"}],
            [{"text": "📖 Guida & Info Bot", "callback_data": "guida"}]
        ]
    }
    
    payload = {
        "chat_id": dest,
        "text": "📈 **PANNELLO FOREX, CRYPTO & MACRO NEWS** 📉\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n💡 Seleziona un'opzione dai pulsanti sottostanti: 🔥",
        "reply_markup": tastiera,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Errore invio menu: {e}")

def invia_messaggio(testo, chat_dest=None):
    dest = chat_dest if chat_dest else CHAT_ID
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": dest, "text": testo, "parse_mode": "Markdown", "disable_web_page_preview": False}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Errore invio Telegram: {e}")

# --- FILTRO NOTIZIE POTENZIATO CON NUOVE PAROLE CHIAVE MACRO ---
def analizza_impatto_notizia(titolo):
    t = titolo.lower()
    
    # 1. Scarto immediato dello spam su singole aziende/utili a meno che non tocchino macro o asset target
    if any(k in t for k in ["utili", "trimestrale", "azioni", "stima", "q1", "q2", "q3", "q4", "società", "gruppo", "cede", "vende"]):
        if not any(ast in t for ast in ["oro", "gold", "bitcoin", "btc", "fed", "bce", "lane", "lagarde", "powell", "inflazione", "tassi"]):
            return None, None

    # 2. Rilevamento Sentiment
    parole_rosse = ["crisi", "crollo", "inflazione", "guerra", "tensioni", "recessione", "calo", "perdite", "debito", "allarme", "scende", "rialzo tassi"]
    parole_verdi = ["crescita", "rialzo", "record", "boom", "sviluppo", "accordo", "positivo", "super", "stabilità", "sale", "taglio tassi"]
    
    score_rosso = sum(1 for p in parole_rosse if p in t)
    score_verde = sum(1 for p in parole_verdi if p in t)
    
    if score_rosso > score_verde:
        sentiment = "SFAVOREVOLE / Rischio ribasso 🔴📉"
    elif score_verde > score_rosso:
        sentiment = "FAVOREVOLE / Impatto positivo 🟢📈"
    else:
        sentiment = "NEUTRO / In attesa ⚪⚖️"

    # 3. Mappatura completa degli Asset e Macro Movers (Inclusi Lane, BCE, Tassi, FED)
    if any(k in t for k in ["oro", "gold", "xau", "metalli"]):
        return "Oro (XAUUSD) 🥇", sentiment
    elif any(k in t for k in ["bitcoin", "btc", "crypto", "criptovalute", "blockchain", "ethereum", "eth"]):
        return "Bitcoin (BTC) & Crypto 🪙", sentiment
    elif any(k in t for k in ["euro", "bce", "ecb", "lagarde", "lane", "germania", "francia", "eur"]):
        return "EUR/USD & BCE 💶🇪🇺", sentiment
    elif any(k in t for k in ["sterlina", "uk", "gbp", "boe"]):
        return "GBP/USD 💷", sentiment
    elif any(k in t for k in ["yen", "giappone", "jpy", "boj"]):
        return "USD/JPY 💴", sentiment
    elif any(k in t for k in ["franco", "svizzera", "chf"]):
        return "USD/CHF 🇨🇭", sentiment
    elif any(k in t for k in ["australiano", "aud", "rba"]):
        return "AUD/USD 🇦🇺", sentiment
    elif any(k in t for k in ["canadese", "cad", "boc"]):
        return "USD/CAD 🇨🇦", sentiment
    elif any(k in t for k in ["dollaro", "fed", "powell", "usa", "stati uniti", "inflazione", "tassi", "occupazione", "pil", "usd", "ipc", "fomc"]):
        return "USD / FED & Macro 💵", sentiment
    else:
        return None, None

# --- CONTROLLO NOTIZIE AUTOMATICO (MULTI-FONTE) ---
def controlla_notizie(chat_dest=None):
    global ULTIMO_LINK_INVIATO
    try:
        for feed_url in RSS_FEEDS:
            feed = feedparser.parse(feed_url)
            if feed.entries:
                for entry in feed.entries[:5]:
                    asset_target, sentiment = analizza_impatto_notizia(entry.title)
                    if asset_target is not None:
                        if chat_dest is None and entry.link == ULTIMO_LINK_INVIATO:
                            return
                        
                        msg = (
                            f"🚨 **NOTIZIA TARGET: {asset_target}** 🚨\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"📌 *Titolo:* {entry.title}\n\n"
                            f"⚡ *Impatto:* {sentiment}\n\n"
                            f"🔗 [👉 Leggi l'articolo completo]({entry.link})"
                        )
                        invia_messaggio(msg, chat_dest)
                        
                        if chat_dest is None:
                            ULTIMO_LINK_INVIATO = entry.link
                        break
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
            soup = BeautifulSoup(response.text, 'html.parser')
            eventi = soup.find_all('tr', id=lambda x: x and x.startswith('eventRowId_'))
            
            msg = "📅 **CALENDARIO ECONOMICO UFFICIALE** 🎯\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            contatore = 0
            
            for ev in eventi:
                if contatore >= 8:
                    break
                
                time_td = ev.find('td', class_='time')
                curr_td = ev.find('td', class_='flagCur')
                title_td = ev.find('td', class_='event')
                
                ora = time_td.get_text(strip=True) if time_td else "--:--"
                valuta = curr_td.get_text(strip=True) if curr_td else ""
                titolo = title_td.get_text(strip=True) if title_td else ""
                
                if titolo:
                    contatore += 1
                    msg += f"⏰ *{ora}* [{valuta}]\n📌 {titolo}\n\n"
            
            if contatore == 0:
                msg += "🟢 *Nessun evento imminente o widget in aggiornamento.*"
                
            msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            invia_messaggio(msg, chat_dest)
        else:
            invia_messaggio("⚠️ Impossibile caricare il widget del calendario in questo momento.", chat_dest)
    except Exception as e:
        print(f"Errore widget calendario: {e}")

def notizie_sette_giorni(chat_dest=None):
    try:
        msg = "📰 **ULTIMISSIME NOTIZIE SUI TUOI ASSET** 📊\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        trovate = 0
        for feed_url in RSS_FEEDS:
            feed = feedparser.parse(feed_url)
            if feed.entries:
                for entry in feed.entries:
                    asset_target, sentiment = analizza_impatto_notizia(entry.title)
                    if asset_target is not None:
                        trovate += 1
                        msg += f"🔹 *{trovate}.* {entry.title}\n   🎯 *Asset:* {asset_target}\n   ↳ *Impatto:* {sentiment}\n\n"
                        if trovate >= 5:
                            break
            if trovate >= 5:
                break
                
        if trovate > 0:
            invia_messaggio(msg, chat_dest)
        else:
            invia_messaggio("🟢 Nessuna notizia spazzatura filtrata; monitoraggio attivo solo sui tuoi asset.", chat_dest)
    except Exception as e:
        print(f"Errore notizie 7 giorni: {e}")

# --- CALENDARIO MACRO PRINCIPALE ---
def invia_calendario(tipo, chat_dest=None):
    msg = (
        "📅 **CALENDARIO ECONOMICO CHIAVE** 🎯\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🇺🇸 **DOMANI 10 NOVEMBRE - Ore 14:30 (CET):**\n"
        "🔹 Indice dei Prezzi al Consumo (IPC m/m & a/a)\n"
        "🔹 IPC Core m/m & a/a\n"
        "   🎯 *Interessa:* USD / Oro (XAUUSD) / Bitcoin / Forex 💵🥇🪙\n"
        "   ⚡ *Impatto:* MASSIMO (Il market mover più atteso della settimana)\n\n"
        "📌 *Filtro Attivo:* Il bot scarta in automatico ogni notizia aziendale o non inerente ai tuoi asset.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    invia_messaggio(msg, chat_dest)

# --- ANALISI TECNICA ASSET ---
def analizza_asset(simbolo, nome_asset, chat_dest=None):
    try:
        ticker = yfinance.Ticker(simbolo)
        info = ticker.fast_info
        prezzo = info.last_price
        prev_close = info.previous_close
        variazione = ((prezzo - prev_close) / prev_close) * 100
        
        emoji_var = "🟢" if variazione >= 0 else "🔴"
        
        msg = (
            f"📊 **ANALISI: {nome_asset}** 💎\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 **Prezzo:** {prezzo:.4f}\n"
            f"{emoji_var} **Variazione 24h:** {variazione:+.2f}%\n"
            f"🤖 **Stato Bot Grid:** Operativo in Demo\n"
            f"⚙️ **Strategia:** Multi-TP & Break-Even attivo\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        invia_messaggio(msg, chat_dest)
    except Exception as e:
        print(f"Errore analisi asset {simbolo}: {e}")
        invia_messaggio(f"⚠️ Impossibile recuperare la quotazione di {nome_asset}.", chat_dest)

# --- TELEGRAM POLLING COMANDI ---
def ascolta_comandi():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset}&timeout=10"
            resp = requests.get(url, timeout=15).json()
            
            if resp.get("ok"):
                for result in resp.get("result", []):
                    offset = result["update_id"] + 1
                    
                    if "message" in result:
                        msg = result["message"]
                        chat_id = msg["chat"]["id"]
                        text = msg.get("text", "")
                        
                        if text in ["/start", "/menu"]:
                            invia_messaggio_con_menu(chat_id)
                            
                    elif "callback_query" in result:
                        query = result["callback_query"]
                        chat_id = query["message"]["chat"]["id"]
                        data_callback = query["data"]

                        callback_url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
                        requests.post(callback_url, json={"callback_query_id": query["id"], "text": "⚡ Elaborazione..."})

                        if data_callback == "btc":
                            analizza_asset("BTC-USD", "BITCOIN (BTC)", chat_id)
                        elif data_callback == "oro":
                            analizza_asset("GC=F", "ORO (XAUUSD)", chat_id)
                        elif data_callback == "eurusd":
                            analizza_asset("EURUSD=X", "EUR/USD", chat_id)
                        elif data_callback == "gbpusd":
                            analizza_asset("GBPUSD=X", "GBP/USD", chat_id)
                        elif data_callback == "usdjpy":
                            analizza_asset("JPY=X", "USD/JPY", chat_id)
                        elif data_callback == "usdchf":
                            analizza_asset("CHF=X", "USD/CHF", chat_id)
                        elif data_callback == "audusd":
                            analizza_asset("AUDUSD=X", "AUD/USD", chat_id)
                        elif data_callback == "usdcad":
                            analizza_asset("CAD=X", "USD/CAD", chat_id)
                        elif data_callback == "nzdusd":
                            analizza_asset("NZDUSD=X", "NZD/USD", chat_id)
                        elif data_callback == "eurgbp":
                            analizza_asset("EURGBP=X", "EUR/GBP", chat_id)
                        elif data_callback == "news_oggi":
                            controlla_notizie(chat_id)
                            notizie_sette_giorni(chat_id)
                        elif data_callback == "cal_oggi" or data_callback == "cal_7gg":
                            scarica_calendario_live(chat_id)
                            invia_calendario("oggi", chat_id)
                        elif data_callback == "guida":
                            invia_messaggio("📖 *GUIDA BOT:* Filtro anti-spazzatura aziendale attivo.", chat_id)

        except Exception as e:
            print(f"Errore ascolto: {e}")
        time.sleep(1)

# --- WORKER BACKGROUND ---
def worker():
    time.sleep(5)
    invia_messaggio("🚀 *SERVER ONLINE:* Filtro anti-spazzatura aziendale attivato con fonti Macro estese! 🟢🔥")
    Thread(target=ascolta_comandi, daemon=True).start()
    schedule.every(15).minutes.do(lambda: controlla_notizie())
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    Thread(target=worker, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

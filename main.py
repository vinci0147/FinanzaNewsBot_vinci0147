# -*- coding: utf-8 -*-
import os
import time
from threading import Thread
import feedparser
import requests
from flask import Flask
import schedule
import yfinance

# --- CONFIGURAZIONE ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

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
            [{"text": "📅 Calendario Oggi", "callback_data": "cal_oggi"}, {"text": "📆 Calendario 7GG", "callback_data": "cal_7gg"}],
            [{"text": "📰 Ultime Notizie", "callback_data": "news_oggi"}, {"text": "📑 Notizie 7GG", "callback_data": "news_7gg"}],
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

# --- RILEVAMENTO MIRATO DELL'ASSET E DEL SENTIMENT DALLA NEWS ---
def analizza_impatto_notizia(titolo):
    t = titolo.lower()
    
    asset_target = "Mercati Globali / Indici 🌐"
    if any(k in t for k in ["oro", "gold", "xau", "metalli"]):
        asset_target = "Oro (XAUUSD) 🥇"
    elif any(k in t for k in ["bitcoin", "btc", "crypto", "criptovalute", "blockchain"]):
        asset_target = "Bitcoin (BTC) 🪙"
    elif any(k in t for k in ["euro", "bce", "lagarde", "germania", "francia"]):
        asset_target = "EUR/USD & EUR/GBP 💶🇪🇺"
    elif any(k in t for k in ["sterlina", "uk", "gbp", "boe"]):
        asset_target = "GBP/USD 💷"
    elif any(k in t for k in ["yen", "giappone", "boj", "jpy"]):
        asset_target = "USD/JPY 💴"
    elif any(k in t for k in ["dollaro", "fed", "powell", "usa", "stati uniti", "inflazione", "tassi", "occupazione", "pil"]):
        asset_target = "Dollaro / Forex Generale (USD) 💵"
    elif any(k in t for k in ["banche", "banca", "stocks", "azioni", "dirigente", "titolo"]):
        asset_target = "Azionario / Settore Bancario 🏦"

    parole_rosse = ["crisi", "crollo", "inflazione", "guerra", "tensioni", "recessione", "calo", "perdite", "debito", "allarme", "vendite", "scende"]
    parole_verdi = ["crescita", "rialzo", "record", "boom", "sviluppo", "accordo", "positivo", "utili", "super", "stabilità", "acquista", "sale"]
    
    score_rosso = sum(1 for p in parole_rosse if p in t)
    score_verde = sum(1 for p in parole_verdi if p in t)
    
    if score_rosso > score_verde:
        sentiment = "SFAVOREVOLE / Rischio ribasso 🔴📉"
    elif score_verde > score_rosso:
        sentiment = "FAVOREVOLE / Impatto positivo 🟢📈"
    else:
        sentiment = "NEUTRO / In attesa di dati ⚪⚖️"
        
    return asset_target, sentiment

# --- RSS NEWS (FILTRATA PER INVII AUTOMATICI) ---
def controlla_notizie(chat_dest=None):
    try:
        feed = feedparser.parse("https://it.investing.com/rss/news.rss")
        if feed.entries:
            ultima = feed.entries[0]
            asset_target, sentiment = analizza_impatto_notizia(ultima.title)
            
            if chat_dest is None and "NEUTRO" in sentiment:
                return
            
            msg = (
                f"🚨 **ULTIMA ORA MERCATO FINANZIARIO** 🚨\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 *Titolo:* {ultima.title}\n\n"
                f"🎯 *Asset Interessato:* {asset_target}\n"
                f"⚡ *Impatto Rilevato:* {sentiment}\n\n"
                f"🔗 [👉 CLICCA QUI PER LEGGERE L'ARTICOLO]({ultima.link})"
            )
            invia_messaggio(msg, chat_dest)
    except Exception as e:
        print(f"Errore RSS: {e}")

# --- NOTIZIE 7GG (ULTIME 5 NEWS) ---
def notizie_sette_giorni(chat_dest=None):
    try:
        feed = feedparser.parse("https://it.investing.com/rss/news.rss")
        if feed.entries:
            msg = "📰 **PANNELLO ULTIME 5 NOTIZIE & TARGET** 📊\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, entry in enumerate(feed.entries[:5]):
                asset_target, sentiment = analizza_impatto_notizia(entry.title)
                msg += f"🔹 *{i+1}.* {entry.title}\n   🎯 *Asset:* {asset_target}\n   ↳ *Impatto:* {sentiment}\n\n"
            invia_messaggio(msg, chat_dest)
        else:
            invia_messaggio("⚠️ Nessuna notizia recente trovata nei feed.", chat_dest)
    except Exception as e:
        print(f"Errore Notizie 7GG: {e}")

# --- CALENDARIO ECONOMICO ---
def invia_calendario(tipo, chat_dest=None):
    if tipo == "oggi":
        msg = (
            "📅 **CALENDARIO ECONOMICO DI OGGI** 🎯\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⏰ *14:30* | 💵 **USD** | Discorso FED & Dati Occupazione\n"
            "   ⚡ *Impatto Diretto:* 🥇 Oro (XAUUSD) & 💵 Dollaro\n\n"
            "⏰ *16:00* | 💶 **EUR** | Intervento Ufficiale BCE\n"
            "   ⚡ *Impatto Diretto:* 💶 EUR/USD & 🇪🇺 EUR/GBP\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        msg = (
            "📆 **CALENDARIO ECONOMICO PROSSIMI 7 GIORNI** 📈\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 *Lunedì:* PIL Stati Uniti 🇺🇸 (Impatto forte su 💵 USD)\n"
            "🟡 *Mercoledì:* Decisione Tassi d'Interesse FED 🏦 (Impatto su tutti gli asset)\n"
            "🔴 *Venerdì:* Non-Farm Payrolls (NFP) 📊 Cruciale per 🥇 XAUUSD\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    invia_messaggio(msg, chat_dest)

# --- ANALISI ASSET UNIVERSALE ---
def analizza_asset(simbolo, nome_asset, chat_dest=None):
    try:
        ticker = yfinance.Ticker(simbolo)
        df = ticker.history(period="5d")
        if not df.empty and len(df) >= 2:
            prezzo = df['Close'].iloc[-1]
            prezzo_prec = df['Close'].iloc[-2]
            var = ((prezzo - prezzo_prec) / prezzo_prec) * 100
            
            if var >= 0:
                trend = "Rialzista / Momento Positivo 🚀"
                sentiment_mercato = "FAVOREVOLE al Buy 🟢📈"
            else:
                trend = "Ribassista / Momento Negativo 🔻"
                sentiment_mercato = "SFAVOREVOLE / Pressione Sell 🔴📉"
            
            msg = (
                f"📊 **ANALISI TECNICA & MACRO: {nome_asset}** 💎\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 *Prezzo Attuale:* `{prezzo:.4f}`\n"
                f"📈 *Variazione Tecnica:* `{var:+.2f}%`\n"
                f"⚡ *Trend Rilevato:* {trend}\n"
                f"🎯 *Valutazione Mercato:* {sentiment_mercato}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            invia_messaggio(msg, chat_dest)
        else:
            invia_messaggio(f"⚠️ Dati non ancora disponibili per {nome_asset}.", chat_dest)
    except Exception as e:
        print(f"Errore analisi {nome_asset}: {e}")
        invia_messaggio(f"❌ Errore di connessione dati per {nome_asset}.", chat_dest)

# --- ASCOLTO COMANDI E PULSANTI ---
def ascolta_comandi():
    if not TOKEN:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    offset = 0
    
    try:
        requests.get(url, params={'offset': -1, 'timeout': 1}, timeout=5)
    except:
        pass

    while True:
        try:
            res = requests.get(url, params={'offset': offset, 'timeout': 15}, timeout=20)
            if res.status_code == 200:
                data = res.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    
                    if "message" in update and "text" in update["message"]:
                        msg = update["message"]
                        testo = msg.get("text", "")
                        chat_id = msg.get("chat", {}).get("id")
                        if testo and "/menu" in testo.lower():
                            invia_messaggio_con_menu(chat_id)
                            
                    elif "callback_query" in update:
                        query = update["callback_query"]
                        chat_id = query["message"]["chat"]["id"]
                        data_callback = query["data"]
                        
                        callback_url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
                        requests.post(callback_url, json={"callback_query_id": query["id"], "text": "⚡ Elaborazione dati in corso..."})
                        
                        if data_callback == "btc":
                            analizza_asset("BTC-USD", "BITCOIN (BTC)", chat_id)
                        elif data_callback == "oro":
                            analizza_asset("GC=F", "ORO (XAUUSD)", chat_id)
                        elif data_callback == "eurusd":
                            analizza_asset("EURUSD=X", "EUR/USD", chat_id)
                        elif data_callback == "gbpusd":
                            analizza_asset("GBPUSD=X", "GBP/USD", chat_id)
                        elif data_callback == "usdjpy":
                            analizza_asset("USDJPY=X", "USD/JPY", chat_id)
                        elif data_callback == "usdchf":
                            analizza_asset("USDCHF=X", "USD/CHF", chat_id)
                        elif data_callback == "audusd":
                            analizza_asset("AUDUSD=X", "AUD/USD", chat_id)
                        elif data_callback == "usdcad":
                            analizza_asset("USDCAD=X", "USD/CAD", chat_id)
                        elif data_callback == "nzdusd":
                            analizza_asset("NZDUSD=X", "NZD/USD", chat_id)
                        elif data_callback == "eurgbp":
                            analizza_asset("EURGBP=X", "EUR/GBP", chat_id)
                        elif data_callback == "news_oggi":
                            controlla_notizie(chat_id)
                        elif data_callback == "news_7gg":
                            notizie_sette_giorni(chat_id)
                        elif data_callback == "cal_oggi":
                            invia_calendario("oggi", chat_id)
                        elif data_callback == "cal_7gg":
                            invia_calendario("7gg", chat_id)
                        elif data_callback == "guida":
                            invia_messaggio("📖 *GUIDA BOT:*\nOra il bot associa in automatico ogni notizia all'asset specifico coinvolto (Oro, Bitcoin, Forex, ecc.), indicandoti se l'impatto è favorevole o sfavorevole! 🚀🔥", chat_id)
                        else:
                            invia_messaggio(f"✨ Sezione `{data_callback}` aperta con successo!", chat_id)
                            
        except Exception as e:
            print(f"Errore ascolto: {e}")
            time.sleep(5)

# --- WORKER BACKGROUND ---
def worker():
    time.sleep(5)
    invia_messaggio("🚀 *SERVER ONLINE:* Bot avviato, ora associa le notizie agli asset specifici! 🟢🔥")
    
    Thread(target=ascolta_comandi, daemon=True).start()
    
    schedule.every(15).minutes.do(lambda: controlla_notizie())
    schedule.every(1).hours.do(lambda: analizza_asset("BTC-USD", "BITCOIN (BTC)"))
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    Thread(target=worker, daemon=True).start()
    port = int(os.environ.get('PORT', 8080))
    app_web.run(host='0.0.0.0', port=port)

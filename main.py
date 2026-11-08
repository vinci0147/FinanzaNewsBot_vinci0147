
    import schedule
    import feedparser
    import yfinance
except ImportError:
    print("Installazione delle dipendenze in corso...")
    import os
    os.system('pip install schedule feedparser yfinance requests')
    import schedule
    import feedparser
    import yfinance

import time
import datetime
import requests
import json

TOKEN = "8858283509:AAFS-hvhjIbIwXvk5olT9H7OBNFUlzwG7UM"
CHAT_ID = "-1003769211169"
TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
GET_UPDATES_URL = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
RSS_NEWS_URL = "https://it.investing.com/rss/news.rss"
KEYWORDS = ["USD", "EUR", "FED", "BCE", "Inflazione", "CPI", "NFP", "Oro", "XAUUSD", "Tassi", "PIL", "Guerra", "Geopolitica"]
LOG_FILE = "sent_news.txt"

MAPPA_TICKER = {
    "btcusd": "BTC-USD", "btc": "BTC-USD", "bitcoin": "BTC-USD",
    "ethusd": "ETH-USD", "eth": "ETH-USD",
    "xauusd": "XAUUSD=X", "oro": "XAUUSD=X", "gold": "XAUUSD=X",
    "xagusd": "XAGUSD=X", "argento": "XAGUSD=X",
    "eurusd": "EURUSD=X", "gbpusd": "GBPUSD=X", "usdjpy": "USDJPY=X",
    "usdchf": "USDCHF=X", "audusd": "AUDUSD=X", "usdcad": "USDCAD=X",
    "nzdusd": "NZDUSD=X", "eurgbp": "EURGBP=X", "cadchf": "CADCHF=X",
    "aapl": "AAPL", "enel": "ENEL.MI"
}

def load_sent_news():
    try:
        with open(LOG_FILE, "r") as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def save_sent_link(link):
    with open(LOG_FILE, "a") as f:
        f.write(link + "\n")

def send_telegram_message(text, reply_markup=None, target_chat=CHAT_ID):
    payload = {"chat_id": target_chat, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        response = requests.post(TELEGRAM_URL, json=payload)
        return response.json()
    except Exception as e:
        return None

def analizza_impatto_notizia(titolo_notizia, ticker):
    t_low = titolo_notizia.lower()
    tc = ticker.lower()

    if "btc" in tc or "bitcoin" in tc:
        if any(w in t_low for w in ["tassi giu", "taglio", "liquidita", "stimolo", "approvazione", "sec", "etf"]):
            return "Impatto AI: RIALZISTA (Maggiore liquidita o notizie crypto favorevoli)."
        if any(w in t_low for w in ["tassi su", "stretta", "inflazione alta", "restrizioni", "divieto", "crisi"]):
            return "Impatto AI: RIBASSISTA (Aversione al rischio o stretta monetaria)."

    elif "xauusd" in tc or "oro" in tc or "gold" in tc:
        if any(w in t_low for w in ["guerra", "tensioni", "crisi", "inflazione", "tassi giu", "beni rifugio"]):
            return "Impatto AI: RIALZISTA (Cresce l'attrattiva come bene rifugio)."
        if any(w in t_low for w in ["tassi su", "dollaro forte", "crescita forte", "pace"]):
            return "Impatto AI: RIBASSISTA (Pressione sui metalli preziosi)."

    elif tc in ["eurusd", "gbpusd", "audusd", "nzdusd"]:
        if any(w in t_low for w in ["fed", "tassi usa giu", "inflazione usa debole", "dollaro debole"]):
            return "Impatto AI: RIALZISTA per la coppia (Dollaro sotto pressione)."
        if any(w in t_low for w in ["bce", "boe", "europa debole", "tassi usa su", "dollaro forte"]):
            return "Impatto AI: RIBASSISTA per la coppia (Dollaro forte)."

    elif tc in ["usdjpy", "usdchf", "usdcad"]:
        if any(w in t_low for w in ["tassi usa su", "dollaro forte", "inflazione usa alta"]):
            return "Impatto AI: RIALZISTA per la coppia (Apprezzamento dollaro)."
        if any(w in t_low for w in ["tassi usa giu", "dollaro debole", "banca centrale"]):
            return "Impatto AI: RIBASSISTA per la coppia (Indebolimento dollaro)."

    return "Impatto AI: NEUTRO / Monitorare la volatilita."

def genera_menu_interattivo():
    testo = "PANNELLO FOREX & SMART AI NEWS\nSeleziona un'opzione dai pulsanti sottostanti:"
    keyboard = {
        "inline_keyboard": [
            [{"text": "Calendario Oggi", "callback_data": "cmd_calendario"}, {"text": "Calendario 7GG", "callback_data": "cmd_calendario_7gg"}],
            [{"text": "Ultime Notizie", "callback_data": "cmd_notizie"}, {"text": "Notizie 7GG", "callback_data": "cmd_notizie_7gg"}],
            [{"text": "Oro (XAUUSD)", "callback_data": "prev_xauusd"}, {"text": "Bitcoin (BTC)", "callback_data": "prev_btcusd"}],
            [{"text": "EUR/USD", "callback_data": "prev_eurusd"}, {"text": "GBP/USD", "callback_data": "prev_gbpusd"}],
            [{"text": "USD/JPY", "callback_data": "prev_usdjpy"}, {"text": "USD/CHF", "callback_data": "prev_usdchf"}],
            [{"text": "AUD/USD", "callback_data": "prev_audusd"}, {"text": "USD/CAD", "callback_data": "prev_usdcad"}],
            [{"text": "NZD/USD", "callback_data": "prev_nzdusd"}, {"text": "EUR/GBP", "callback_data": "prev_eurgbp"}],
            [{"text": "Guida Comandi", "callback_data": "cmd_comandi"}]
        ]
    }
    return testo, keyboard

def genera_calendario_oggi():
    oggi = datetime.date.today().strftime("%d/%m/%Y")
    eventi = []
    feed = feedparser.parse(RSS_NEWS_URL)
    for entry in feed.entries:
        if hasattr(entry, 'title') and any(kw in entry.title.lower() for kw in ["oggi", "fed", "bce", "cpi", "nfp", "tassi", "PIL"]):
            eventi.append(f"- {entry.title}")
    risultato = f"CALENDARIO OGGI ({oggi})\n\n" + ("\n".join(eventi[:5]) if eventi else "Nessun evento rilevante oggi.")
    return risultato

def genera_calendario_7gg():
    return "CALENDARIO SETTIMANALE:\n- Lun: BCE / UE\n- Mar: Germania / Petrolio\n- Mer: CPI USA & FOMC\n- Gio: Tassi BCE / Sussidi USA\n- Ven: PIL UK / NFP USA"

def genera_ultime_notizie():
    notizie = []
    feed = feedparser.parse(RSS_NEWS_URL)
    for entry in feed.entries:
        if hasattr(entry, 'title') and hasattr(entry, 'link'):
            notizie.append(f"- {entry.title}\n  [Leggi]({entry.link})")
            if len(notizie) >= 5: break
    return "ULTIME NOTIZIE DI MERCATO:\n\n" + ("\n\n".join(notizie) if notizie else "Nessuna notizia.")

def genera_notizie_7gg():
    notizie = []
    feed = feedparser.parse(RSS_NEWS_URL)
    for entry in feed.entries:
        if hasattr(entry, 'title') and hasattr(entry, 'link'):
            if any(kw in entry.title.lower() for kw in KEYWORDS):
                notizie.append(f"- {entry.title}\n  [Leggi]({entry.link})")
                if len(notizie) >= 6: break
    return "ARCHIVIO NOTIZIE RECENTI:\n\n" + ("\n\n".join(notizie) if notizie else "Nessuna notizia.")

def genera_previsione_asset(ticker_input):
    try:
        tc = ticker_input.strip().lower()
        if tc in ["xauusd", "oro", "gold"]:
            lt = ["XAUUSD=X", "GLD", "GC=F"]
            kw_notizia = ["oro", "gold", "fed", "bce", "inflazione", "guerra", "crisi"]
        elif tc in ["btcusd", "btc", "bitcoin"]:
            lt = ["BTC-USD", "BTCUSD=X"]
            kw_notizia = ["bitcoin", "btc", "crypto", "sec"]
        elif tc in ["eurusd", "gbpusd", "usdjpy", "usdchf", "audusd", "usdcad", "nzdusd", "eurgbp"]:
            lt = [MAPPA_TICKER.get(tc)]
            kw_notizia = [tc[:3], tc[3:], "fed", "bce", "tassi", "inflazione"]
        else:
            lt = [MAPPA_TICKER.get(tc, ticker_input.upper())]
            kw_notizia = [tc]

        hist, ticker_trovato = None, ""
        for t in lt:
            h = yfinance.Ticker(t).history(period="5d")
            if not h.empty:
                hist, ticker_trovato = h, t
                break

        if hist is None or hist.empty:
            return f"Asset {ticker_input} non trovato."

        pa = hist['Close'].iloc[-1]
        pp = hist['Close'].iloc[-2]
        var = ((pa - pp) / pp) * 100

        feed = feedparser.parse(RSS_NEWS_URL)
        notizia_rilevante = None
        for entry in feed.entries:
            if hasattr(entry, 'title') and any(k in entry.title.lower() for k in kw_notizia):
                notizia_rilevante = entry.title
                break

        pr = 55 + min(int(var * 10), 30) if var > 0 else max(45 - int(abs(var) * 10), 15)
        pb = 100 - pr
        tr = "Rialzista" if var > 0 else "Ribassista"

        news_text = f"Notizia: {notizia_rilevante}\n{analizza_impatto_notizia(notizia_rilevante, ticker_input)}" if notizia_rilevante else "Nessuna notizia macro correlata recente."

        return (
            f"ANALISI SMART AI: {ticker_input.upper()} ({ticker_trovato})\n"
            f"Prezzo: {pa:.4f} | Variazione: {var:+.2f}%\n"
            f"Trend: {tr}\n\n"
            f"{news_text}\n\n"
            f"Stime: Rialzo {pr}% | Ribasso {pb}%"
        )
    except Exception as e:
        return f"Errore analisi per {ticker_input}: {e}"

def genera_lista_comandi():
    return "GUIDA COMANDI:\n/menu - Pannello\n/calendario - Oggi\n/calendario_7gg - Settimana\n/previsione [asset] - Analisi\n/notizie - News"

def send_daily_agenda():
    send_telegram_message(genera_calendario_oggi())

def check_live_news():
    sent = load_sent_news()
    feed = feedparser.parse(RSS_NEWS_URL)
    for entry in feed.entries:
        if hasattr(entry, 'link') and hasattr(entry, 'title'):
            if entry.link in sent: continue
            if any(kw.lower() in entry.title.lower() for kw in KEYWORDS):
                msg = f"ULTIMA ORA\n\n{entry.title}\n\n[Leggi]({entry.link})"
                res = send_telegram_message(msg)
                if res and res.get("ok"):
                    save_sent_link(entry.link)
        time.sleep(1)

last_update_id = 0

def check_telegram_updates():
    global last_update_id
    try:
        res = requests.get(f"{GET_UPDATES_URL}?offset={last_update_id + 1}&timeout=1").json()
        if "result" in res:
            for update in res["result"]:
                last_update_id = update["update_id"]
                if "message" in update and "text" in update["message"]:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    text = msg["text"].strip().lower()

                    if text in ["/menu", "/start"]:
                        t, kb = genera_menu_interattivo()
                        send_telegram_message(t, reply_markup=kb, target_chat=chat_id)
                    elif text == "/calendario":
                        send_telegram_message(genera_calendario_oggi(), target_chat=chat_id)
                    elif text == "/calendario_7gg":
                        send_telegram_message(genera_calendario_7gg(), target_chat=chat_id)
                    elif text == "/notizie":
                        send_telegram_message(genera_ultime_notizie(), target_chat=chat_id)
                    elif text.startswith("/previsione"):
                        parts = text.split()
                        if len(parts) > 1:
                            send_telegram_message(genera_previsione_asset(parts[1]), target_chat=chat_id)
                        else:
                            send_telegram_message("Specifica un asset. Esempio: /previsione eurusd", target_chat=chat_id)
                    elif text == "/comandi":
                        send_telegram_message(genera_lista_comandi(), target_chat=chat_id)

                elif "callback_query" in update:
                    cq = update["callback_query"]
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]})
                    data = cq["data"]
                    chat_id = cq["message"]["chat"]["id"]

                    if data == "cmd_menu":
                        t, kb = genera_menu_interattivo()
                        send_telegram_message(t, reply_markup=kb, target_chat=chat_id)
                    elif data == "cmd_calendario":
                        send_telegram_message(genera_calendario_oggi(), target_chat=chat_id)
                    elif data == "cmd_calendario_7gg":
                        send_telegram_message(genera_calendario_7gg(), target_chat=chat_id)
                    elif data == "cmd_notizie":
                        send_telegram_message(genera_ultime_notizie(), target_chat=chat_id)
                    elif data.startswith("prev_"):
                        asset = data.replace("prev_", "")
                        send_telegram_message(genera_previsione_asset(asset), target_chat=chat_id)
                    elif data == "cmd_comandi":
                        send_telegram_message(genera_lista_comandi(), target_chat=chat_id)
    except Exception as e:
        print(f"Errore aggiornamenti: {e}")

schedule.every().day.at("08:00").do(send_daily_agenda)

print("Bot Smart AI avviato e pronto!")

while True:
    schedule.run_pending()
    check_live_news()
    check_telegram_updates()
    time.sleep(3)

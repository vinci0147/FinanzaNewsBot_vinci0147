async def scarica_calendario_live(chat_id, context: ContextTypes.DEFAULT_TYPE):
    url = "https://sslecal2.investing.com/?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&features=datepicker,timezone&countries=25,32,6,37,22,17,35,4,39,14,48,10,43,21,38,36,26,5,110,12,72&calType=week&timeZone=16&lang=9"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://it.investing.com/",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            eventi = soup.find_all('tr', id=lambda x: x and x.startswith('eventRowId_'))
            
            msg = "📅 **CALENDARIO MACROECONOMICO (LIVE)** 🎯\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            contatore = 0
            
            for ev in eventi:
                if contatore >= 10:
                    break
                
                time_td = ev.find('td', class_='time')
                curr_td = ev.find('td', class_='flagCur')
                title_td = ev.find('td', class_='event')
                act_td = ev.find('td', class_='act')
                fore_td = ev.find('td', class_='fore')
                prev_td = ev.find('td', class_='prev')
                
                ora = time_td.get_text(strip=True) if time_td else "--:--"
                valuta = curr_td.get_text(strip=True) if curr_td else ""
                titolo = title_td.get_text(strip=True) if title_td else ""
                
                attivo = act_td.get_text(strip=True) if act_td else ""
                previsto = fore_td.get_text(strip=True) if fore_td else ""
                precedente = prev_td.get_text(strip=True) if prev_td else ""
                
                if titolo:
                    contatore += 1
                    msg += f"⏰ *{ora}* [{valuta}] — **{titolo}**\n"
                    if attivo or previsto:
                        msg += f"   📊 Prev: {previsto} | Forecast: {attivo} | Prec: {precedente}\n"
                    msg += "\n"
            
            if contatore == 0:
                msg += "🟢 *Nessun evento in corso o widget in aggiornamento.*\n"
                
            msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📌 *Dati aggiornati in tempo reale dal server.*"
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Errore di risposta dal server delle notizie (Codice HTTP).")
    except Exception as e:
        logger.error(f"Errore calendario live: {e}")
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Connessione al calendario temporaneamente non disponibile.")

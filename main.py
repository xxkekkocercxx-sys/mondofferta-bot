"""
FORWARDER MULTI-CANALE -> @Mondofferta
Versione UNIFORME - tutti i messaggi uguali + multi-sorgente + bottone Invita personalizzato
"""
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import re
import threading
from flask import Flask
import os

# ========= CONFIG =========
api_id = 37196582
api_hash = "7d9e857155940f4a67517f588dce69d"

# LISTA CANALI SORGENTE - tutti i tuoi canali Amazon
source_channels = [
    "@ScontiShark",
    "@CAVALIERIDELRISPARMIO",
    "@OFFROG",
    "@SCONTOMATTO1",
    "@OFFERTEOGNIORA",
    "@MAXI_OFFERTE",
    "@OCCHIO_ALLO_SCONTO",
    "@SUPER_PREZZO",
]

dest_channel_input = "@Mondofferta"
il_mio_tag = "sconticoup04c-21"
mio_link_canale = "https://t.me/Mondofferta"
# ==========================

app = Flask(__name__)

@app.route('/')
def home():
    canali = ", ".join(source_channels)
    return f"BOT MONDOFFERTA ATTIVO - Sorgenti: {canali} -> {dest_channel_input}"

def sostituisci_tag(text):
    if not text:
        return text
    nuovo_tag = f'tag={il_mio_tag}'
    text = re.sub(r'tag=[^&\s]+', nuovo_tag, text)
    text = re.sub(r'tag%3D[^&\s%]+', f'tag%3D{il_mio_tag}', text, flags=re.IGNORECASE)
    if 'amazon.' in text.lower() and 'tag=' not in text.lower() and 'tag%3d' not in text.lower():
        if '?' in text:
            text = text + f'&{nuovo_tag}'
        else:
            if 'amzn.to' not in text:
                text = text + f'?{nuovo_tag}'
    return text

def estrai_link_amazon(testo, bottoni):
    pattern = r'https?://[^\s]+(?:amazon\.[^\s]+|amzn\.to/[^\s]+|link\.amazon/[^\s]+)'
    match = re.search(pattern, testo, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    if bottoni:
        for row in bottoni:
            for btn in row:
                if hasattr(btn, 'url') and btn.url and ('amazon' in btn.url.lower() or 'amzn.to' in btn.url.lower() or 'link.amazon' in btn.url.lower()):
                    return btn.url
    return None

def estrai_info_prodotto(testo):
    righe = [r.strip() for r in testo.split('\n') if r.strip()]
    titolo = ""
    prezzo_riga = ""
    sconto_riga = ""
    for r in righe:
        low = r.lower()
        if 'invita un amico' in low or '#affiliate' in low or 'prendi ora' in low or 'apri su amazon' in low:
            continue
        if 'amzlinks.in' in low or 'finisce presto' in low:
            continue
        if 'http' in low:
            continue
        if '€' in r and (prezzo_riga == ""):
            if any(x in low for x in ['da ', 'invece di', 'a ', '€']):
                prezzo_riga = r
                continue
        if ('sconto' in low or '%' in r) and sconto_riga == "":
            if '%' in r:
                sconto_riga = r
                continue
        if len(r) > 10 and '€' not in r and '%' not in r and titolo == "":
            if not r.startswith('👉') and not r.startswith('💰'):
                titolo = r
    if not titolo:
        for r in righe:
            if len(r) > 20 and '€' not in r and 'http' not in r.lower() and 'sconto' not in r.lower():
                titolo = r
                break
    return titolo, prezzo_riga, sconto_riga

def crea_messaggio_uniforme(testo_originale, titolo, prezzo, sconto):
    titolo = titolo.strip()
    if not titolo:
        titolo = "OFFERTA AMAZON"
    parti = []
    parti.append(f"🔥 {titolo}")
    parti.append("")
    if prezzo and '€' in prezzo:
        parti.append(f"💰 {prezzo}")
    if sconto and ('sconto' in sconto.lower() or '%' in sconto):
        if not sconto.strip().startswith('🏷'):
            parti.append(f"🏷️ {sconto}")
        else:
            parti.append(sconto)
    parti.append("")
    parti.append("⏰ Finisce presto!")
    parti.append("")
    parti.append("👇 Clicca qui sotto per l'offerta")
    return "\n".join(parti)

session_str = os.environ.get("SESSION_STRING")
client = None

if session_str:
    session_str = session_str.strip().replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "")
    print(f"Trovata SESSION_STRING (lunghezza: {len(session_str)})")
    print(f"Canali sorgente configurati: {source_channels}")
    try:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)

        @client.on(events.NewMessage)
        async def handler(event):
            try:
                chat = await event.get_chat()
                chat_username = getattr(chat, 'username', None)
                chat_title = getattr(chat, 'title', 'N/A')
                chat_id = event.chat_id
                chat_username_clean = (chat_username or "").lower()
                chat_title_clean = (chat_title or "").lower()
                is_source = False
                for src in source_channels:
                    src_clean = src.replace("@","").lower()
                    if src_clean in chat_username_clean or src_clean in chat_title_clean:
                        is_source = True
                        break
                    if str(chat_id) == src:
                        is_source = True
                        break
                if not is_source:
                    return
                print(f"[MATCH] Messaggio da @{chat_username} ({chat_title}) ID:{chat_id}")
                messaggio = event.message
                testo_originale = messaggio.text or messaggio.message or ""
                link_amazon_originale = estrai_link_amazon(testo_originale, messaggio.buttons)
                if link_amazon_originale:
                    link_amazon_mio = sostituisci_tag(link_amazon_originale)
                    print(f"[AMAZON LINK] {link_amazon_originale} -> {link_amazon_mio}")
                else:
                    link_amazon_mio = None
                    print("[AMAZON LINK] Nessun link trovato")
                    link_amazon_mio = sostituisci_tag(testo_originale)
                titolo, prezzo, sconto = estrai_info_prodotto(testo_originale)
                print(f"[INFO] Titolo: {titolo[:80]} | Prezzo: {prezzo} | Sconto: {sconto}")
                testo_uniforme = crea_messaggio_uniforme(testo_originale, titolo, prezzo, sconto)
                testo_uniforme = sostituisci_tag(testo_uniforme)
                print(f"[TESTO UNIFORME]\n{testo_uniforme[:500]}")
                bottoni_uniformi = []
                if link_amazon_originale:
                    bottoni_uniformi.append([Button.url("🛒 Apri su Amazon", link_amazon_mio)])
                else:
                    testo_con_tag = sostituisci_tag(testo_originale)
                    link_fallback = estrai_link_amazon(testo_con_tag, None)
                    if link_fallback:
                        bottoni_uniformi.append([Button.url("🛒 Apri su Amazon", link_fallback)])
                    else:
                        bottoni_uniformi.append([Button.url("🛒 Apri su Amazon", "https://www.amazon.it/")])
                bottoni_uniformi.append([Button.url("✉️ Invita un amico", mio_link_canale)])
                print(f"[BOTTONI UNIFORMI] {bottoni_uniformi}")
                try:
                    if messaggio.media:
                        print(f"[INVIO] Con media verso {dest_channel_input} - TEMPLATE UNIFORME")
                        await client.send_message(dest_channel_input, testo_uniforme, file=messaggio.media, buttons=bottoni_uniformi, link_preview=False)
                    else:
                        print(f"[INVIO] Solo testo verso {dest_channel_input} - TEMPLATE UNIFORME")
                        await client.send_message(dest_channel_input, testo_uniforme, buttons=bottoni_uniformi, link_preview=False)
                    print(f"[OK] Inoltrato UNIFORME su {dest_channel_input} con tag {il_mio_tag}")
                except Exception as e:
                    print(f"[ERRORE INVIO] {e}")
                    import traceback
                    traceback.print_exc()
            except Exception as e:
                print(f"[ERRORE HANDLER] {e}")
                import traceback
                traceback.print_exc()
    except Exception as e:
        print(f"ERRORE SESSION_STRING: {e}")
        client = None
else:
    print("ATTENZIONE: SESSION_STRING non trovata!")

def avvia_bot():
    if client is None:
        print("BOT NON AVVIATO - SESSION_STRING mancante!")
        return
    print(f"Avvio bot {source_channels} -> {dest_channel_input}")
    try:
        client.start()
        print("Client avviato correttamente!")
        client.run_until_disconnected()
    except Exception as e:
        print(f"Errore avvio: {e}")

threading.Thread(target=avvia_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

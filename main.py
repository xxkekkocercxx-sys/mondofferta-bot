"""
FORWARDER MULTI-CANALE -> @Mondofferta
Versione PROFESSIONALE + ANTEPRIMA AMAZON UFFICIALE
- No immagini copiate, solo anteprima ufficiale Amazon
- Template pulito e professionale
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

MOSTRA_ANTEPRIMA_AMAZON = True  # Anteprima ufficiale Amazon
# ==========================

app = Flask(__name__)

@app.route('/')
def home():
    return f"BOT PROFESSIONALE ATTIVO - Anteprima Amazon: {MOSTRA_ANTEPRIMA_AMAZON} -> {dest_channel_input}"

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
    pattern = r'https?://[^\s\)]+(?:amazon\.[^\s\)]+|amzn\.to/[^\s\)]+|link\.amazon[^\s\)]+)'
    match = re.search(pattern, testo, re.IGNORECASE)
    if match:
        return match.group(0).strip().rstrip('.,)!"\'')
    if bottoni:
        for row in bottoni:
            for btn in row:
                if hasattr(btn, 'url') and btn.url:
                    low = btn.url.lower()
                    if 'amazon' in low or 'amzn.to' in low or 'link.amazon' in low:
                        return btn.url.strip()
    return None

def estrai_info_prodotto(testo):
    righe = [r.strip() for r in testo.split('\n') if r.strip()]
    titolo = ""
    prezzo_attuale = ""
    prezzo_vecchio = ""
    sconto = ""
    
    for r in righe:
        low = r.lower()
        # Salta righe inutili
        if any(x in low for x in ['invita un amico', '#affiliate', 'prendi ora', 'apri su amazon', 'clicca qui', 'finisce presto', 'amzlinks.in']):
            continue
        if 'http' in low:
            continue
            
        # Cerca pattern "19,99€ invece di 24,99€" o "19,99€ - 24,99€"
        match_prezzi = re.search(r'(\d+[.,]\d+\s*€).*?(\d+[.,]\d+\s*€)', r)
        if match_prezzi and not prezzo_attuale:
            prezzo_attuale = match_prezzi.group(1).strip()
            prezzo_vecchio = match_prezzi.group(2).strip()
            continue
            
        # Prezzo singolo
        if '€' in r and not prezzo_attuale and len(r) < 50:
            # Prende solo il prezzo
            m = re.search(r'\d+[.,]\d+\s*€', r)
            if m:
                prezzo_attuale = m.group(0)
                # Se la riga contiene "invece di" ma non abbiamo preso il secondo prezzo
                if 'invece' in low or 'listino' in low:
                    # già gestito sopra
                    pass
                continue
        
        # Sconto
        if ('%' in r or 'sconto' in low) and not sconto and len(r) < 60:
            if '%' in r:
                m = re.search(r'-?\d+\s*%', r)
                if m:
                    sconto = m.group(0)
                else:
                    sconto = r
                continue
        
        # Titolo - prima riga lunga senza € e senza %
        if len(r) > 15 and '€' not in r and '%' not in r and not titolo:
            if not r.startswith(('👉','💰','🔥','🔗','📦','✅','⏰','💶')):
                # Pulisci emoji iniziali
                r_clean = re.sub(r'^[\W_]+', '', r)
                if len(r_clean) > 15:
                    titolo = r_clean

    if not titolo:
        for r in righe:
            if len(r) > 25 and '€' not in r and 'http' not in r.lower() and 'sconto' not in r.lower():
                titolo = re.sub(r'^[\W_]+', '', r)
                break
                
    return titolo, prezzo_attuale, prezzo_vecchio, sconto

def crea_messaggio_professionale(titolo, prezzo_attuale, prezzo_vecchio, sconto, link_amazon):
    titolo = titolo.strip() if titolo else "Offerta Amazon"
    # Rendi titolo più leggibile - prima lettera maiuscola
    if len(titolo) > 5:
        titolo = titolo[0].upper() + titolo[1:]
    
    parti = []
    # Header professionale - meno emoji, più pulito
    parti.append(f"📦 {titolo}")
    parti.append("")
    
    # Sezione prezzo - professionale
    if prezzo_attuale and prezzo_vecchio:
        parti.append(f"💰 Prezzo: {prezzo_attuale} invece di {prezzo_vecchio}")
    elif prezzo_attuale:
        parti.append(f"💰 Prezzo: {prezzo_attuale}")
    
    if sconto:
        # Normalizza sconto
        sconto_clean = sconto.strip()
        if '%' in sconto_clean and 'sconto' not in sconto_clean.lower():
            parti.append(f"🏷️ Sconto: {sconto_clean}")
        else:
            parti.append(f"🏷️ {sconto_clean}")
    
    parti.append("")
    parti.append("✅ Offerta verificata | Prime disponibile")
    parti.append("⏳ Disponibilità limitata")
    parti.append("")
    
    # Link - sarà quello che genera l'anteprima Amazon ufficiale
    if link_amazon:
        parti.append(f"{link_amazon}")
    
    return "\n".join(parti)

session_str = os.environ.get("SESSION_STRING")
client = None

if session_str:
    session_str = session_str.strip().replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "")
    print(f"SESSION_STRING OK - Modalità PROFESSIONALE + Anteprima Amazon")
    try:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)

        @client.on(events.NewMessage)
        async def handler(event):
            try:
                chat = await event.get_chat()
                chat_username = getattr(chat, 'username', None)
                chat_title = getattr(chat, 'title', 'N/A')
                chat_username_clean = (chat_username or "").lower()
                chat_title_clean = (chat_title or "").lower()

                is_source = False
                for src in source_channels:
                    src_clean = src.replace("@","").lower()
                    if src_clean in chat_username_clean or src_clean in chat_title_clean:
                        is_source = True
                        break
                if not is_source:
                    return

                print(f"[MATCH] {chat_username}")
                msg = event.message
                testo_orig = msg.text or msg.message or ""

                link_orig = estrai_link_amazon(testo_orig, msg.buttons)
                link_mio = sostituisci_tag(link_orig) if link_orig else "https://www.amazon.it/"

                titolo, prezzo_att, prezzo_vecchio, sconto = estrai_info_prodotto(testo_orig)
                testo_pro = crea_messaggio_professionale(titolo, prezzo_att, prezzo_vecchio, sconto, link_mio)

                print(f"[PRO] {titolo[:60]} | {prezzo_att} | {sconto}")

                if not link_mio.startswith("http"):
                    link_mio = "https://www.amazon.it/"

                bottoni = [
                    [Button.url("🛒 Acquista su Amazon", link_mio)],
                    [Button.url("✉️ Invita un amico", mio_link_canale)]
                ]

                await client.send_message(
                    dest_channel_input,
                    testo_pro,
                    buttons=bottoni,
                    link_preview=MOSTRA_ANTEPRIMA_AMAZON
                )
                print(f"[OK] Inviato professionale")

            except Exception as e:
                print(f"[ERRORE] {e}")
                import traceback
                traceback.print_exc()
    except Exception as e:
        print(f"ERRORE SESSION: {e}")
        client = None
else:
    print("SESSION_STRING mancante!")

def avvia_bot():
    if client is None:
        return
    try:
        client.start()
        print("Bot professionale avviato!")
        client.run_until_disconnected()
    except Exception as e:
        print(f"Errore: {e}")

threading.Thread(target=avvia_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

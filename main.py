"""
FORWARDER ScontiShark -> @Mondofferta
Versione FINALE con supporto BOTTONI + DEBUG
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
source_channel_input = "@ScontiShark"
dest_channel_input = "@Mondofferta"
il_mio_tag = "sconticoup04c-21"
# ==========================

app = Flask(__name__)

@app.route('/')
def home():
    return "BOT MONDOFFERTA ATTIVO - @ScontiShark -> @Mondofferta con bottoni"

def sostituisci_tag(text):
    if not text:
        return text
    nuovo_tag = f'tag={il_mio_tag}'
    # Sostituisce sia tag= che tag%3D (url encoded)
    text = re.sub(r'tag=[^&\s]+', nuovo_tag, text)
    text = re.sub(r'tag%3D[^&\s%]+', f'tag%3D{il_mio_tag}', text, flags=re.IGNORECASE)
    # Se non c'e' nessun tag ma c'e' un link amazon, aggiungilo
    # Per amazon.it / amazon.com
    if 'amazon.' in text.lower() and 'tag=' not in text.lower() and 'tag%3d' not in text.lower():
        # Se ha gia' ?, aggiungi &
        if '?' in text:
            text = text + f'&{nuovo_tag}'
        else:
            # Per link corti amzn.to non aggiungere, tanto si risolve
            if 'amzn.to' not in text:
                text = text + f'?{nuovo_tag}'
    return text

session_str = os.environ.get("SESSION_STRING")
client = None

if session_str:
    session_str = session_str.strip().replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "")
    print(f"Trovata SESSION_STRING (lunghezza: {len(session_str)})")
    try:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)

        @client.on(events.NewMessage)
        async def handler(event):
            try:
                chat = await event.get_chat()
                chat_username = getattr(chat, 'username', None)
                chat_title = getattr(chat, 'title', 'N/A')
                chat_id = event.chat_id

                source_clean = source_channel_input.replace("@","").lower()
                chat_username_clean = (chat_username or "").lower()
                
                # Filtro solo ScontiShark
                is_source = source_clean in chat_username_clean or source_clean in chat_title.lower() or str(chat_id) == source_channel_input
                
                if not is_source:
                    return

                print(f"[MATCH] Messaggio da @{chat_username} ({chat_title}) ID:{chat_id}")
                messaggio = event.message
                testo_originale = messaggio.text or messaggio.message or ""
                testo_nuovo = sostituisci_tag(testo_originale)
                
                print(f"[TESTO] {testo_originale[:300]}")
                print(f"[NUOVO TESTO] {testo_nuovo[:300]}")

                # Gestione bottoni
                nuovi_bottoni = None
                if messaggio.buttons:
                    nuovi_bottoni = []
                    print(f"[BOTTONI] Trovati {len(messaggio.buttons)} righe di bottoni")
                    for row in messaggio.buttons:
                        nuova_riga = []
                        for btn in row:
                            try:
                                # btn.text e btn.url
                                if hasattr(btn, 'url') and btn.url:
                                    vecchio_url = btn.url
                                    nuovo_url = sostituisci_tag(vecchio_url)
                                    print(f"  [BOTTONE URL] '{btn.text}': {vecchio_url} -> {nuovo_url}")
                                    nuova_riga.append(Button.url(btn.text, nuovo_url))
                                elif hasattr(btn, 'text'):
                                    # Bottone senza url (tipo callback) lo copiamo
                                    nuova_riga.append(btn)
                            except Exception as be:
                                print(f"  [ERRORE BOTTONE] {be}")
                                nuova_riga.append(btn)
                        nuovi_bottoni.append(nuova_riga)
                else:
                    print("[BOTTONI] Nessun bottone inline")

                # Invio
                try:
                    if messaggio.media:
                        print(f"[INVIO] Con media verso {dest_channel_input}")
                        await client.send_message(dest_channel_input, testo_nuovo, file=messaggio.media, buttons=nuovi_bottoni, link_preview=False)
                    else:
                        print(f"[INVIO] Solo testo verso {dest_channel_input}")
                        await client.send_message(dest_channel_input, testo_nuovo, buttons=nuovi_bottoni, link_preview=False)
                    print(f"[OK] Inoltrato su {dest_channel_input} con tag {il_mio_tag}")
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
    print(f"Avvio bot {source_channel_input} -> {dest_channel_input}")
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

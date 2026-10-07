"""
FORWARDER ScontiShark -> @Mondofferta
Versione per Render FREE - con SESSION_STRING
"""
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import re
import threading
from flask import Flask
import os

# ========= CONFIG =========
api_id = 37196582
api_hash = "7d9e857155940f4a67517f588dce69d"
source_channel = "@ScontiShark"
dest_channel = "@Mondofferta"
il_mio_tag = "sconticoup04c-21"
# ==========================

app = Flask(__name__)

@app.route('/')
def home():
    return "BOT MONDOFFERTA ATTIVO - In ascolto su @ScontiShark -> @Mondofferta"

def sostituisci_tag(text):
    if not text:
        return text
    nuovo_tag = f'tag={il_mio_tag}'
    text = re.sub(r'tag=[^&\s]+', nuovo_tag, text)
    text = re.sub(r'tag%3D[^&\s%]+', f'tag%3D{il_mio_tag}', text)
    return text

# Usa la sessione dalle variabili ambiente di Render
session_str = os.environ.get("SESSION_STRING")

if session_str:
    print("Trovata SESSION_STRING, uso quella!")
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
else:
    print("ATTENZIONE: SESSION_STRING non trovata, mettila nelle Environment Variables di Render!")
    # fallback per non crashare
    client = TelegramClient(StringSession(), api_id, api_hash)

@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    print(f"Nuovo messaggio da ScontiShark ricevuto!")
    messaggio = event.message
    testo_originale = messaggio.text or messaggio.message or ""
    testo_nuovo = sostituisci_tag(testo_originale)
    try:
        if messaggio.media:
            await client.send_message(dest_channel, testo_nuovo, file=messaggio.media)
        else:
            await client.send_message(dest_channel, testo_nuovo)
        print(f"Inoltrato su @Mondofferta con tag {il_mio_tag}")
    except Exception as e:
        print(f"Errore: {e}")

def avvia_bot():
    print(f"Avvio in corso... In ascolto su {source_channel} -> {dest_channel}")
    client.start()
    client.run_until_disconnected()

threading.Thread(target=avvia_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

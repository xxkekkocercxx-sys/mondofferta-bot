"""
FORWARDER MULTI-CANALE -> @Mondofferta
Versione PROFESSIONALE FINALE + ANTI-DUPLICATI
- Link nascosto "Apri su Amazon"
- Prezzo originale + scontato
- Anteprima Amazon ufficiale
- Controllo duplicati via ASIN + titolo (evita stesso prodotto da canali diversi)
"""
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import re
import threading
from flask import Flask
import os
import json
import time
from datetime import datetime, timedelta

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

MOSTRA_ANTEPRIMA_AMAZON = True
CACHE_ORE = 24  # Non ripostare stesso prodotto per 24 ore
CACHE_FILE = "seen_products.json"

app = Flask(__name__)

# ===== CACHE ANTI-DUPLICATI =====
cache_lock = threading.Lock()
seen_cache = {}  # {asin_or_title_hash: timestamp}

def load_cache():
    global seen_cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                seen_cache = data
                print(f"[CACHE] Caricati {len(seen_cache)} prodotti già visti")
                # Pulisci vecchi
                pulisci_cache()
    except Exception as e:
        print(f"[CACHE] Errore caricamento: {e}")
        seen_cache = {}

def save_cache():
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(seen_cache, f)
    except Exception as e:
        print(f"[CACHE] Errore salvataggio: {e}")

def pulisci_cache():
    global seen_cache
    now = time.time()
    limite = CACHE_ORE * 3600
    to_remove = []
    for key, ts in seen_cache.items():
        if now - ts > limite:
            to_remove.append(key)
    for key in to_remove:
        del seen_cache[key]
    if to_remove:
        print(f"[CACHE] Puliti {len(to_remove)} vecchi prodotti (>{CACHE_ORE}h)")

def estrai_asin(link):
    if not link:
        return None
    # Pattern ASIN: 10 caratteri alfanumerici maiuscoli
    patterns = [
        r'/dp/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
        r'/product/([A-Z0-9]{10})',
        r'amazon\.[^/]+/.*([A-Z0-9]{10})',
        r'/d/([A-Z0-9]{10})',
    ]
    for pat in patterns:
        m = re.search(pat, link, re.IGNORECASE)
        if m:
            asin = m.group(1).upper()
            # Verifica che sia plausibile (10 char, contiene almeno un numero e lettera)
            if len(asin) == 10:
                return asin
    return None

def normalizza_titolo(titolo):
    if not titolo:
        return ""
    # Lowercase, rimuovi emoji, spazi doppi, punteggiatura
    t = titolo.lower()
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    # Prendi prime 8 parole significative come hash
    parole = t.split()[:8]
    return " ".join(parole)

def is_duplicato(asin, titolo):
    global seen_cache
    now = time.time()
    
    # Chiave primaria: ASIN se disponibile
    if asin:
        key = f"ASIN:{asin}"
        with cache_lock:
            if key in seen_cache:
                diff = now - seen_cache[key]
                if diff < CACHE_ORE * 3600:
                    ore = int((CACHE_ORE*3600 - diff)/3600)
                    print(f"[DUPLICATO] ASIN {asin} già postato {int(diff/60)}min fa, salto (mancano {ore}h)")
                    return True
            # Non è duplicato, aggiungilo
            seen_cache[key] = now
            save_cache()
            print(f"[CACHE] Nuovo ASIN aggiunto: {asin}")
            return False
    else:
        # Fallback su titolo normalizzato
        titolo_norm = normalizza_titolo(titolo)
        if not titolo_norm or len(titolo_norm) < 10:
            return False
        key = f"TITLE:{titolo_norm}"
        with cache_lock:
            if key in seen_cache:
                diff = now - seen_cache[key]
                if diff < CACHE_ORE * 3600:
                    print(f"[DUPLICATO] Titolo simile già postato: '{titolo_norm[:40]}...' {int(diff/60)}min fa")
                    return True
            seen_cache[key] = now
            save_cache()
            print(f"[CACHE] Nuovo titolo aggiunto: {titolo_norm[:40]}")
            return False

# Carica cache all'avvio
load_cache()

# ===== FUNZIONI ORIGINALI =====
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
    titolo = ""; prezzo_attuale = ""; prezzo_vecchio = ""; sconto = ""
    for r in righe:
        low = r.lower()
        if any(x in low for x in ['invita un amico', '#affiliate', 'prendi ora', 'apri su amazon', 'clicca qui', 'finisce presto', 'amzlinks.in']):
            continue
        if 'http' in low:
            continue
        match_doppio = re.search(r'(\d+[.,]\d+\s*€)[^\d€]{0,20}(\d+[.,]\d+\s*€)', r)
        if match_doppio and not prezzo_attuale:
            p1 = match_doppio.group(1).strip()
            p2 = match_doppio.group(2).strip()
            if 'invece' in low or 'listino' in low or 'anzich' in low:
                prezzo_attuale = p1
                prezzo_vecchio = p2
            else:
                try:
                    v1 = float(p1.replace('€','').replace(',','.').strip())
                    v2 = float(p2.replace('€','').replace(',','.').strip())
                    if v1 < v2:
                        prezzo_attuale = p1
                        prezzo_vecchio = p2
                    else:
                        prezzo_attuale = p2
                        prezzo_vecchio = p1
                except:
                    prezzo_attuale = p1
                    prezzo_vecchio = p2
            continue
        if '€' in r and not prezzo_attuale and len(r) < 80:
            m = re.findall(r'\d+[.,]\d+\s*€', r)
            if m:
                prezzo_attuale = m[0]
                if len(m) > 1 and not prezzo_vecchio:
                    prezzo_vecchio = m[1]
                continue
        if ('%' in r or 'sconto' in low) and not sconto and len(r) < 80:
            if '%' in r:
                m = re.search(r'-?\d+\s*%', r)
                if m:
                    sconto = m.group(0)
                continue
        if len(r) > 15 and '€' not in r and '%' not in r and not titolo:
            if not r.startswith(('👉','💰','🔥','🔗','📦','✅','⏰','💶','💥','❌','🏷️')):
                r_clean = re.sub(r'^[\W_]+', '', r)
                if len(r_clean) > 15:
                    titolo = r_clean
    if not titolo:
        for r in righe:
            if len(r) > 25 and '€' not in r and 'http' not in r.lower():
                titolo = re.sub(r'^[\W_]+', '', r)
                break
    return titolo, prezzo_attuale, prezzo_vecchio, sconto

def crea_messaggio_professionale(titolo, prezzo_attuale, prezzo_vecchio, sconto, link_amazon):
    titolo = titolo.strip() if titolo else "Offerta Amazon"
    if len(titolo) > 5:
        titolo = titolo[0].upper() + titolo[1:]
    parti = []
    parti.append(f"📦 {titolo}")
    parti.append("")
    if prezzo_attuale and prezzo_vecchio:
        parti.append(f"💥 Prezzo Scontato: {prezzo_attuale}")
        parti.append(f"💶 Prezzo Originale: {prezzo_vecchio}")
    elif prezzo_attuale:
        parti.append(f"💰 Prezzo: {prezzo_attuale}")
    else:
        parti.append(f"💰 Offerta attiva su Amazon")
    if sconto:
        sconto_clean = sconto.strip()
        if '%' in sconto_clean and not sconto_clean.startswith('-') and sconto_clean[0].isdigit():
            sconto_clean = f"-{sconto_clean}"
        parti.append(f"🏷️ Risparmi: {sconto_clean}")
    parti.append("")
    parti.append("✅ Offerta verificata | Prime disponibile")
    parti.append("⏳ Disponibilità limitata")
    parti.append("")
    if link_amazon:
        parti.append(f"👉 [Apri su Amazon]({link_amazon})")
    return "\n".join(parti)

session_str = os.environ.get("SESSION_STRING")
client = None

@app.route('/')
def home():
    with cache_lock:
        count = len(seen_cache)
    return f"BOT ANTI-DUPLICATI ATTIVO - {count} prodotti in cache ({CACHE_ORE}h) -> {dest_channel_input}"

@app.route('/cache')
def cache_status():
    with cache_lock:
        items = list(seen_cache.items())[-20:]
    html = f"<h3>Cache Anti-duplicati ({len(seen_cache)} totali)</h3><ul>"
    for k, ts in reversed(items):
        dt = datetime.fromtimestamp(ts).strftime("%H:%M:%S %d/%m")
        html += f"<li>{k} - {dt}</li>"
    html += "</ul>"
    return html

@app.route('/clear_cache')
def clear_cache():
    global seen_cache
    with cache_lock:
        seen_cache = {}
        save_cache()
    return "Cache pulita!"

if session_str:
    session_str = session_str.strip().replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "")
    print(f"SESSION_STRING OK - Anti-duplicati {CACHE_ORE}h attivo")
    try:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)

        @client.on(events.NewMessage)
        async def handler(event):
            try:
                chat = await event.get_chat()
                chat_username = getattr(chat, 'username', None)
                chat_username_clean = (chat_username or "").lower()
                chat_title = getattr(chat, 'title', 'N/A')
                chat_title_clean = (chat_title or "").lower()

                is_source = False
                for src in source_channels:
                    src_clean = src.replace("@","").lower()
                    if src_clean in chat_username_clean or src_clean in chat_title_clean:
                        is_source = True
                        break
                if not is_source:
                    return

                print(f"[MATCH] Da @{chat_username}")
                msg = event.message
                testo_orig = msg.text or msg.message or ""

                link_orig = estrai_link_amazon(testo_orig, msg.buttons)
                link_mio = sostituisci_tag(link_orig) if link_orig else "https://www.amazon.it/"

                # Estrai ASIN per controllo duplicati
                asin = estrai_asin(link_orig or link_mio)
                titolo, prezzo_att, prezzo_vecchio, sconto = estrai_info_prodotto(testo_orig)

                # CONTROLLO DUPLICATO - se già visto, salta
                if is_duplicato(asin, titolo):
                    print(f"[SKIP] Prodotto duplicato non inviato")
                    return

                print(f"[PREZZI] Scontato: {prezzo_att} | Originale: {prezzo_vecchio} | ASIN: {asin}")
                testo_pro = crea_messaggio_professionale(titolo, prezzo_att, prezzo_vecchio, sconto, link_mio)

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
                print(f"[OK] Inviato - ASIN:{asin} | Scontato {prezzo_att}")

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
        print(f"Bot anti-duplicati avviato! Cache {CACHE_ORE}h")
        client.run_until_disconnected()
    except Exception as e:
        print(f"Errore: {e}")

threading.Thread(target=avvia_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

"""
FORWARDER MULTI-CANALE -> @Mondofferta
Versione FINALE PULITA Opzione 1 - Foto Amazon + Logo grande alto sx
"""
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import re, threading, os, json, time
from flask import Flask
from PIL import Image
import requests

api_id = 37196582
api_hash = "7d9e857155940f4a67517f588dce69d"
source_channels = ["@ScontiShark","@CAVALIERIDELRISPARMIO","@OFFROG","@SCONTOMATTO1","@OFFERTEOGNIORA","@MAXI_OFFERTE","@OCCHIO_ALLO_SCONTO","@SUPER_PREZZO"]
dest_channel_input = "@Mondofferta"
il_mio_tag = "sconticoup04c-21"
mio_link_canale = "https://t.me/Mondofferta"
CACHE_ORE = 24
CACHE_FILE = "seen_products.json"
LOGO_CANDIDATI = ["logo.png","logo.jpg","/mnt/data/logo.png","/mnt/data/logo.jpg","./logo.png"]

app = Flask(__name__)
cache_lock = threading.Lock()
seen_cache = {}

def load_cache():
    global seen_cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                seen_cache = json.load(f)
    except:
        seen_cache = {}

def save_cache():
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(seen_cache, f)
    except:
        pass

def estrai_asin(link):
    if not link:
        return None
    for pat in [r'/dp/([A-Z0-9]{10})',r'/gp/product/([A-Z0-9]{10})',r'/product/([A-Z0-9]{10})',r'/d/([A-Z0-9]{10})']:
        m = re.search(pat, link, re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return None

def normalizza_titolo(t):
    t = t.lower()
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return " ".join(t.split()[:8])

def is_duplicato(asin, titolo):
    global seen_cache
    now = time.time()
    key = f"ASIN:{asin}" if asin else f"TITLE:{normalizza_titolo(titolo)}"
    if len(key) < 15:
        return False
    with cache_lock:
        if key in seen_cache and now - seen_cache[key] < CACHE_ORE*3600:
            return True
        seen_cache[key] = now
        save_cache()
        return False

load_cache()

def sostituisci_tag(text):
    if not text:
        return text
    nuovo_tag = f'tag={il_mio_tag}'
    text = re.sub(r'tag=[^&\s]+', nuovo_tag, text)
    text = re.sub(r'tag%3D[^&\s%]+', f'tag%3D{il_mio_tag}', text, flags=re.IGNORECASE)
    if 'amazon.' in text.lower() and 'tag=' not in text.lower() and 'tag%3d' not in text.lower():
        text = text + (f'&{nuovo_tag}' if '?' in text else f'?{nuovo_tag}')
    return text

def estrai_link_amazon(testo, bottoni):
    pattern = r'https?://[^\s\)]+(?:amazon\.[^\s\)]+|amzn\.to/[^\s\)]+|link\.amazon[^\s\)]+)'
    m = re.search(pattern, testo, re.IGNORECASE)
    if m:
        return m.group(0).strip().rstrip('.,)!"\'')
    if bottoni:
        for row in bottoni:
            for btn in row:
                if hasattr(btn, 'url') and btn.url and ('amazon' in btn.url.lower() or 'amzn.to' in btn.url.lower()):
                    return btn.url.strip()
    return None

def estrai_info_prodotto(testo):
    righe = [r.strip() for r in testo.split('\n') if r.strip()]
    tutti_prezzi = re.findall(r'\d+[.,]\d+\s*€', testo)
    prezzi = []
    for p in tutti_prezzi:
        if p not in prezzi:
            prezzi.append(p)
    prezzo_att = ""
    prezzo_vecchio = ""
    if len(prezzi) >= 2:
        for r in righe:
            if 'invece' in r.lower() or 'listino' in r.lower():
                mm = re.findall(r'\d+[.,]\d+\s*€', r)
                if len(mm) >= 2:
                    prezzo_att = mm[0]
                    prezzo_vecchio = mm[1]
                    break
        if not prezzo_att:
            try:
                def to_f(p): return float(re.search(r'\d+[.,]\d+', p).group(0).replace(',', '.'))
                pf = sorted([(to_f(p), p) for p in prezzi[:4]], key=lambda x: x[0])
                prezzo_att = pf[0][1]
                prezzo_vecchio = pf[-1][1]
            except:
                prezzo_att = prezzi[0]
                prezzo_vecchio = prezzi[1]
    elif len(prezzi) == 1:
        prezzo_att = prezzi[0]
    sconto = ""
    mm = re.search(r'(\d+)\s*%', testo)
    if mm:
        sconto = f"{mm.group(1)}%"
    candidati = []
    for r in righe:
        low = r.lower()
        if any(x in low for x in ['http','amazon','apri su','offerta attiva','offerta verificata','disponibilità','invita','prime','www.']):
            continue
        if '€' in r or '%' in r:
            continue
        if len(r) < 15:
            continue
        rc = re.sub(r'^[\W_]+', '', r).strip()
        if len(rc) > 15:
            candidati.append(rc)
    titolo = max(candidati, key=len) if candidati else (righe[0] if righe else "Offerta Amazon")
    return titolo, prezzo_att, prezzo_vecchio, sconto

def trova_logo():
    for p in LOGO_CANDIDATI:
        if os.path.exists(p):
            return p
    for f in os.listdir("/mnt/data"):
        if "logo" in f.lower() and f.lower().endswith(('.png','.jpg','.jpeg')):
            return f"/mnt/data/{f}"
    return None

def get_amazon_image_url(asin, amazon_link):
    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36','Accept-Language':'it-IT,it;q=0.9'}
    urls = []
    if asin:
        urls.append(f"https://www.amazon.it/dp/{asin}")
    if amazon_link and 'amazon.' in amazon_link.lower():
        urls.append(amazon_link)
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code != 200:
                continue
            html = r.text
            patterns = [r'"hiRes":"(https://[^"]+m\.media-amazon\.com[^"]+)"',r'"large":"(https://[^"]+m\.media-amazon\.com[^"]+)"',r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"',r'(https://m\.media-amazon\.com/images/I/[^"\s]+\.jpg)']
            for pat in patterns:
                m = re.search(pat, html, re.IGNORECASE)
                if m:
                    img_url = m.group(1).replace('\\u002F','/').replace('\\/','/')
                    if 'm.media-amazon.com' in img_url:
                        return img_url
        except:
            continue
    return None

def scarica_immagine(url, path="/tmp/amazon.jpg"):
    try:
        headers = {'User-Agent':'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15, stream=True)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            return path
    except:
        pass
    return None

def crea_immagine_pulita(asin, amazon_link):
    img_url = get_amazon_image_url(asin, amazon_link)
    prod_path = None
    if img_url:
        prod_path = scarica_immagine(img_url, "/tmp/prod_amazon.jpg")
    if not prod_path or not os.path.exists(prod_path) or os.path.getsize(prod_path) < 5000:
        return None
    try:
        W, H = 1080, 1080
        canvas = Image.new('RGB', (W, H), (255,255,255))
        prod_img = Image.open(prod_path).convert("RGBA")
        prod_img.thumbnail((900, 900), Image.LANCZOS)
        px = (W - prod_img.width)//2
        py = (H - prod_img.height)//2
        canvas.paste(prod_img, (px, py), prod_img if prod_img.mode == 'RGBA' else None)
        logo_path = trova_logo()
        if logo_path:
            try:
                logo = Image.open(logo_path).convert("RGBA")
                logo.thumbnail((280, 280), Image.LANCZOS)
                shadow = Image.new('RGBA', (logo.width+6, logo.height+6), (0,0,0,25))
                canvas.paste(shadow, (28, 28), shadow)
                canvas.paste(logo, (25, 25), logo)
            except:
                pass
        out_path = f"/tmp/pulita_{int(time.time())}.jpg"
        canvas.save(out_path, "JPEG", quality=95)
        try:
            os.remove(prod_path)
        except:
            pass
        return out_path
    except:
        return None

def crea_messaggio(titolo, prezzo_att, prezzo_vecchio, sconto, link):
    titolo = titolo.strip() if titolo else "Offerta Amazon"
    if len(titolo) > 5:
        titolo = titolo[0].upper() + titolo[1:]
    parti = []
    parti.append(f"📦 {titolo}")
    parti.append("")
    if prezzo_att and prezzo_vecchio:
        parti.append(f"💥 Prezzo Scontato: {prezzo_att}")
        parti.append(f"💶 Prezzo Originale: {prezzo_vecchio}")
    elif prezzo_att:
        parti.append(f"💰 Prezzo: {prezzo_att}")
    else:
        parti.append(f"💰 Offerta attiva su Amazon")
    if sconto:
        sc = sconto.strip()
        if '%' in sc and not sc.startswith('-') and sc[0].isdigit():
            sc = f"-{sc}"
        parti.append(f"🏷️ Risparmi: {sc}")
    parti.append("")
    parti.append("✅ Offerta verificata | Prime disponibile")
    parti.append("⏳ Disponibilità limitata")
    parti.append("")
    if link:
        parti.append(f"👉 [Apri su Amazon]({link})")
    return "\n".join(parti)

session_str = os.environ.get("SESSION_STRING")
client = None

@app.route('/')
def home():
    with cache_lock:
        c = len(seen_cache)
    logo = trova_logo()
    return f"BOT PULITO PRO Opzione1 - Foto Amazon + Logo grande alto sx - {c} cache - Logo: {bool(logo)}"

@app.route('/clear_cache')
def clear_cache_route():
    global seen_cache
    with cache_lock:
        seen_cache = {}
        save_cache()
    return "Cache pulita!"

if session_str:
    session_str = session_str.strip().replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "")
    print("SESSION_STRING OK - Pulito Pro Opzione1")
    try:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)
        @client.on(events.NewMessage)
        async def handler(event):
            try:
                chat = await event.get_chat()
                chat_username = getattr(chat, 'username', None)
                chat_username_clean = (chat_username or "").lower()
                chat_title_clean = getattr(chat, 'title', '').lower()
                is_source = False
                for src in source_channels:
                    if src.replace("@","").lower() in chat_username_clean or src.replace("@","").lower() in chat_title_clean:
                        is_source = True
                        break
                if not is_source:
                    return
                print(f"[MATCH] {chat_username}")
                msg = event.message
                testo_orig = msg.text or msg.message or ""
                link_orig = estrai_link_amazon(testo_orig, msg.buttons)
                link_mio = sostituisci_tag(link_orig) if link_orig else "https://www.amazon.it/"
                asin = estrai_asin(link_orig or link_mio)
                titolo, prezzo_att, prezzo_vecchio, sconto = estrai_info_prodotto(testo_orig)
                if is_duplicato(asin, titolo):
                    print("[SKIP] Duplicato")
                    return
                print(f"[PREZZI] {prezzo_att} | {prezzo_vecchio} | {sconto} | {asin}")
                testo_msg = crea_messaggio(titolo, prezzo_att, prezzo_vecchio, sconto, link_mio)
                if not link_mio.startswith("http"):
                    link_mio = "https://www.amazon.it/"
                bottoni = [[Button.url("🛒 Acquista su Amazon", link_mio)],[Button.url("✉️ Invita un amico", mio_link_canale)]]
                img_path = None
                if asin:
                    img_path = crea_immagine_pulita(asin, link_mio)
                if img_path and os.path.exists(img_path):
                    await client.send_message(dest_channel_input, testo_msg, file=img_path, buttons=bottoni, link_preview=False)
                    print(f"[OK] Pulita Pro - {asin}")
                    try:
                        os.remove(img_path)
                    except:
                        pass
                else:
                    await client.send_message(dest_channel_input, testo_msg, buttons=bottoni, link_preview=False)
                    print(f"[OK] Solo testo - {asin}")
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
        print("Bot pulito pro avviato!")
        client.run_until_disconnected()
    except Exception as e:
        print(f"Errore: {e}")

threading.Thread(target=avvia_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

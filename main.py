"""
FORWARDER MULTI-CANALE -> @Mondofferta
VERSIONE V3 - PREZZI REALI DA AMAZON + FIX IMMAGINI
"""
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import re, threading, os, json, time
from flask import Flask
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
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
    try:
        if os.path.exists("/mnt/data"):
            for f in os.listdir("/mnt/data"):
                if "logo" in f.lower() and f.lower().endswith(('.png','.jpg','.jpeg')):
                    return f"/mnt/data/{f}"
    except:
        pass
    return None

def pulisci_prezzo(txt):
    if not txt:
        return ""
    txt = txt.strip()
    m = re.search(r'(\d+[.,]\d+)', txt)
    if not m:
        return txt
    num = m.group(1).replace('.', ',')
    if '€' not in txt:
        return f"{num} €"
    txt = re.sub(r'\s*€', ' €', txt)
    return txt.replace('  ', ' ').strip()

def get_amazon_details(asin, amazon_link):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'it-IT,it;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    urls = []
    if asin:
        urls.append(f"https://www.amazon.it/dp/{asin}")
    if amazon_link and 'amazon.' in amazon_link.lower():
        urls.append(amazon_link)
    if not urls:
        return None, None, None, None, None

    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                continue
            html = r.text

            titolo = None
            img_url = None
            prezzo_att = None
            prezzo_old = None
            sconto = None

            # TITOLO
            m = re.search(r'<span[^>]*id="productTitle"[^>]*>\s*(.*?)\s*</span>', html, re.DOTALL | re.IGNORECASE)
            if m:
                titolo = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                titolo = re.sub(r'\s+', ' ', titolo).strip()

            # IMMAGINE - priorita hiRes
            patterns_img = [
                r'"hiRes":"(https://[^"]+m\.media-amazon\.com[^"]+)"',
                r'"large":"(https://[^"]+m\.media-amazon\.com[^"]+)"',
                r'"mainImageUrl":"(https://[^"]+m\.media-amazon\.com[^"]+)"',
                r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"',
            ]
            for pat in patterns_img:
                mm = re.search(pat, html, re.IGNORECASE)
                if mm:
                    cand = mm.group(1).replace('\\u002F','/').replace('\\/','/')
                    # Filtra immagini piccole / logo
                    if 'm.media-amazon.com' in cand and 'SS40' not in cand and 'logo' not in cand.lower():
                        img_url = cand
                        break
            # Fallback: prendi prima immagine grande
            if not img_url:
                all_imgs = re.findall(r'(https://m\.media-amazon\.com/images/I/[^"\s]+\.jpg)', html)
                for cand in all_imgs:
                    if '._SS' not in cand and len(cand) > 50:
                        img_url = cand
                        break

            # PREZZI - cerca tutti gli a-offscreen
            offscreen = re.findall(r'<span[^>]*class="[^"]*a-offscreen[^"]*"[^>]*>([^<]+)</span>', html)
            prezzi_trovati = []
            for p in offscreen:
                p = p.strip()
                if '€' in p and re.search(r'\d', p):
                    # Evita prezzi tipo "€ 0,00" o duplicati
                    if p not in prezzi_trovati:
                        prezzi_trovati.append(p.strip())

            # Se troviamo prezzi
            if prezzi_trovati:
                # Rimuovi duplicati e pulisci
                uniq = []
                for p in prezzi_trovati:
                    pp = pulisci_prezzo(p)
                    if pp not in uniq and len(pp) > 3:
                        uniq.append(pp)
                prezzi_trovati = uniq

                # Logica: primo prezzo = attuale, secondo (se esiste e piu alto) = vecchio
                if len(prezzi_trovati) >= 1:
                    prezzo_att = prezzi_trovati[0]
                if len(prezzi_trovati) >= 2:
                    try:
                        def to_f(s):
                            mm = re.search(r'(\d+[.,]\d+)', s)
                            return float(mm.group(1).replace(',', '.')) if mm else 0
                        # Se secondo e piu alto del primo, e il vecchio
                        if to_f(prezzi_trovati[1]) > to_f(prezzi_trovati[0]) * 1.05:
                            prezzo_old = prezzi_trovati[1]
                    except:
                        pass

            # Cerca vecchio prezzo specifico barrato
            if not prezzo_old:
                m = re.search(r'<span[^>]*class="[^"]*a-price a-text-price[^"]*"[^>]*>.*?<span[^>]*class="[^"]*a-offscreen[^"]*"[^>]*>([^<]+)</span>', html, re.DOTALL | re.IGNORECASE)
                if m:
                    prezzo_old = pulisci_prezzo(m.group(1))

            # Cerca sconto
            m = re.search(r'savingsPercentage[^>]*>([^<]*?(\d+)\s*%[^<]*)', html, re.IGNORECASE)
            if m:
                sconto = f"{m.group(2)}%"
            else:
                m = re.search(r'Risparmi[^<]*?(\d+)\s*%', html, re.IGNORECASE)
                if m:
                    sconto = f"{m.group(1)}%"
                else:
                    m = re.search(r'-\s*(\d+)\s*%\s*</span>\s*[^<]*offerta', html, re.IGNORECASE)
                    if m:
                        sconto = f"{m.group(1)}%"

            # Calcola sconto se manca
            if not sconto and prezzo_att and prezzo_old:
                try:
                    def to_f(s):
                        mm = re.search(r'(\d+[.,]\d+)', s)
                        return float(mm.group(1).replace(',', '.')) if mm else 0
                    fa = to_f(prezzo_att)
                    fo = to_f(prezzo_old)
                    if fa > 0 and fo > fa:
                        perc = int(round((1 - fa/fo)*100))
                        if 5 <= perc <= 90:
                            sconto = f"{perc}%"
                except:
                    pass

            if prezzo_att:
                print(f"[AMAZON OK] {asin} | {prezzo_att} | old:{prezzo_old} | -{sconto} | img:{bool(img_url)}")
                return titolo, pulisci_prezzo(prezzo_att), pulisci_prezzo(prezzo_old) if prezzo_old else None, sconto, img_url

        except Exception as e:
            print(f"[AMAZON ERR] {e}")
            continue

    return None, None, None, None, None

def scarica_immagine(url, path="/tmp/amazon.jpg"):
    try:
        headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(url, headers=headers, timeout=15, stream=True)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            # Verifica che sia immagine valida >5KB e non placeholder
            if os.path.getsize(path) > 5000:
                return path
    except:
        pass
    return None

def crea_immagine_pulita(asin, amazon_link, img_url_gia=None):
    if not PIL_AVAILABLE:
        return None
    img_url = img_url_gia
    if not img_url:
        _, _, _, _, img_url = get_amazon_details(asin, amazon_link)
    prod_path = None
    if img_url:
        prod_path = scarica_immagine(img_url, "/tmp/prod_amazon.jpg")
    if not prod_path or not os.path.exists(prod_path):
        return None
    try:
        W, H = 1080, 1080
        canvas = Image.new('RGB', (W, H), (255,255,255))
        prod_img = Image.open(prod_path).convert("RGBA")
        # Verifica dimensioni minime
        if prod_img.width < 100 or prod_img.height < 100:
            return None
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
    except Exception as e:
        print(f"[IMG ERR] {e}")
        return None

def crea_messaggio(titolo, prezzo_att, prezzo_vecchio, sconto, link):
    titolo = titolo.strip() if titolo else "Offerta Amazon"
    if len(titolo) > 5:
        titolo = titolo[0].upper() + titolo[1:]
    # Taglia titolo lungo
    if len(titolo) > 100:
        titolo = titolo[:100].rsplit(' ', 1)[0] + "..."
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
    return f"BOT PREZZI REALI V3 - {c} cache - Logo: {bool(logo)} - PIL: {PIL_AVAILABLE}"

@app.route('/clear_cache')
def clear_cache_route():
    global seen_cache
    with cache_lock:
        seen_cache = {}
        save_cache()
    return "Cache pulita!"

if session_str:
    session_str = session_str.strip().replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "")
    print("SESSION_STRING OK - Prezzi Reali V3")
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

                titolo_msg, prezzo_att_msg, prezzo_vecchio_msg, sconto_msg = estrai_info_prodotto(testo_orig)

                if is_duplicato(asin, titolo_msg):
                    print("[SKIP] Duplicato")
                    return

                # PREZZI REALI DA AMAZON
                titolo_amz, prezzo_att_amz, prezzo_old_amz, sconto_amz, img_url_amz = get_amazon_details(asin, link_mio) if asin else (None, None, None, None, None)

                titolo_finale = titolo_amz if titolo_amz and len(titolo_amz) > 15 else titolo_msg
                prezzo_att = prezzo_att_amz if prezzo_att_amz else prezzo_att_msg
                prezzo_vecchio = prezzo_old_amz if prezzo_old_amz else prezzo_vecchio_msg
                sconto = sconto_amz if sconto_amz else sconto_msg

                print(f"[PREZZI MSG] {prezzo_att_msg} | {prezzo_vecchio_msg} | {sconto_msg}")
                print(f"[PREZZI AMZ] {prezzo_att} | {prezzo_vecchio} | {sconto} | {asin}")

                testo_msg = crea_messaggio(titolo_finale, prezzo_att, prezzo_vecchio, sconto, link_mio)
                if not link_mio.startswith("http"):
                    link_mio = "https://www.amazon.it/"
                bottoni = [[Button.url("🛒 Acquista su Amazon", link_mio)],[Button.url("✉️ Invita un amico", mio_link_canale)]]
                img_path = None
                if asin:
                    img_path = crea_immagine_pulita(asin, link_mio, img_url_amz)
                if img_path and os.path.exists(img_path):
                    await client.send_message(dest_channel_input, testo_msg, file=img_path, buttons=bottoni, link_preview=False)
                    print(f"[OK] V3 Prezzo Reale - {asin} - {prezzo_att}")
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
        print("Bot V3 prezzi reali avviato!")
        client.run_until_disconnected()
    except Exception as e:
        print(f"Errore: {e}")

threading.Thread(target=avvia_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

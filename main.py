"""
FORWARDER MULTI-CANALE -> @Mondofferta
VERSIONE V11 - DOPPIO CONTROLLO + FORMATO UNIFORME + ANTI-DUPLICATO 7 GIORNI
"""
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import re, threading, os, json, time, random, html
from flask import Flask
try:
    from PIL import Image
    PIL_AVAILABLE = True
except:
    PIL_AVAILABLE = False
    Image = None
import requests

api_id = 37196582
api_hash = "7d9e857155940f4a67517f588dce69d"
source_channels = ["@ScontiShark","@CAVALIERIDELRISPARMIO","@OFFROG","@SCONTOMATTO1","@OFFERTEOGNIORA","@MAXI_OFFERTE","@OCCHIO_ALLO_SCONTO","@SUPER_PREZZO"]
dest_channel_input = "@Mondofferta"
il_mio_tag = "sconticoup04c-21"
mio_link_canale = "https://t.me/Mondofferta"
CACHE_ORE = 168  # 7 giorni anti-duplicato
CACHE_FILE = "seen_products.json"
CACHE_FILE_TMP = "/tmp/seen_products.json"
LOGO_CANDIDATI = ["logo.png","logo.jpg","/mnt/data/logo.png","/mnt/data/logo.jpg","./logo.png"]

app = Flask(__name__)
cache_lock = threading.Lock()
seen_cache = {}

def load_cache():
    global seen_cache
    for cf in [CACHE_FILE, CACHE_FILE_TMP]:
        try:
            if os.path.exists(cf):
                with open(cf,'r',encoding='utf-8') as f:
                    data = json.load(f)
                    if data:
                        seen_cache = data
                        print(f"[CACHE] Caricati {len(seen_cache)} da {cf}")
                        return
        except:
            continue
    seen_cache = {}
    print("[CACHE] Nuova")

def save_cache():
    try:
        for cf in [CACHE_FILE, CACHE_FILE_TMP]:
            try:
                with open(cf,'w',encoding='utf-8') as f:
                    json.dump(seen_cache,f)
            except:
                pass
    except:
        pass

def pulisci_cache_vecchia():
    global seen_cache
    now = time.time()
    limite = CACHE_ORE*3600
    vecchie = [k for k,ts in seen_cache.items() if now - ts > limite]
    for k in vecchie:
        del seen_cache[k]
    if vecchie:
        print(f"[CACHE] Pulite {len(vecchie)} vecchie")
        save_cache()

def estrai_asin(link):
    if not link:
        return None
    for pat in [r'/dp/([A-Z0-9]{10})',r'/gp/product/([A-Z0-9]{10})',r'/product/([A-Z0-9]{10})',r'/d/([A-Z0-9]{10})']:
        m = re.search(pat, link, re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return None

def normalizza_titolo(t):
    if not t:
        return ""
    t = t.lower()
    t = re.sub(r'\b\d+\s*(eu|us|uk|cm|mm|ml|l|kg|g)\b',' ',t)
    t = re.sub(r'[^a-z0-9\s]',' ',t)
    t = re.sub(r'\s+',' ',t).strip()
    parole = [p for p in t.split() if len(p)>2][:10]
    return " ".join(parole)

def is_duplicato(asin,titolo):
    global seen_cache
    now = time.time()
    if random.random() < 0.1:
        pulisci_cache_vecchia()
    if asin:
        key = f"ASIN:{asin}"
        with cache_lock:
            if key in seen_cache and now - seen_cache[key] < CACHE_ORE*3600:
                ore = int((now - seen_cache[key])/3600)
                print(f"[DUPLICATO ASIN] {asin} gia {ore}h fa - BLOCCO")
                return True
            seen_cache[key]=now
            if titolo:
                kt = f"TITLE:{normalizza_titolo(titolo)}"
                if len(kt)>=15:
                    seen_cache[kt]=now
            save_cache()
            return False
    if titolo:
        kt = f"TITLE:{normalizza_titolo(titolo)}"
        if len(kt)<15:
            return False
        with cache_lock:
            if kt in seen_cache and now - seen_cache[kt] < CACHE_ORE*3600:
                print(f"[DUPLICATO TITLE] {titolo[:40]}")
                return True
            seen_cache[kt]=now
            save_cache()
            return False
    return False

load_cache()

def correggi_testo(testo):
    if not testo:
        return "Offerta Amazon"
    t = testo
    t = html.unescape(t)
    t = html.unescape(t)
    t = t.replace('&#39;',"'" ).replace('&#x27;',"'").replace('&amp;','&').replace('&quot;','"').replace('&#34;','"')
    t = re.sub(r'\s*e\.{2,}\s*$','',t)
    t = re.sub(r'\s*…\s*$','',t)
    t = re.sub(r'\s*\*{2,}\s*$','',t)
    t = re.sub(r'\s*\*{2,}\s*',' ',t)
    t = re.sub(r'https?://\S+','',t)
    t = re.sub(r'\s+',' ',t).strip()
    t = t.strip(' .,;:!*')
    if len(t)>5:
        t = t[0].upper()+t[1:]
    return t[:200] if len(t)>200 else t

def valida_testo_finale(titolo):
    if not titolo:
        return None
    t = correggi_testo(titolo)
    if len(t)<10:
        return None
    if 'http' in t.lower() or 'www.' in t.lower():
        return None
    if '&#' in t or '&amp;' in t:
        t = html.unescape(t)
    t = re.sub(r'\*{2,}','',t).strip()
    if len(t)<10:
        return None
    return t

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
    titolo = correggi_testo(titolo)
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

def valida_prezzi_finali(prezzo_att, prezzo_vecchio):
    att = pulisci_prezzo(prezzo_att) if prezzo_att else ""
    vec = pulisci_prezzo(prezzo_vecchio) if prezzo_vecchio else ""
    if att and vec:
        try:
            def to_f(s):
                mm = re.search(r'(\d+[.,]\d+)', s)
                return float(mm.group(1).replace(',', '.')) if mm else 0
            fa = to_f(att)
            fv = to_f(vec)
            if fa>0 and fv>0 and fa>fv:
                att, vec = vec, att
        except:
            pass
    return att, vec

def calcola_sconto_finale(prezzo_att, prezzo_vecchio, sconto_esistente=""):
    if sconto_esistente and re.search(r'\d+%', sconto_esistente):
        return sconto_esistente.strip()
    if not prezzo_att or not prezzo_vecchio:
        return ""
    try:
        def to_f(s):
            mm = re.search(r'(\d+[.,]\d+)', s)
            return float(mm.group(1).replace(',', '.')) if mm else 0
        fa = to_f(prezzo_att)
        fv = to_f(prezzo_vecchio)
        if fa>0 and fv>fa:
            perc = int(round((1 - fa/fv)*100))
            if 1 <= perc <= 90:
                return f"-{perc}%"
        elif fv>0 and fa>fv:
            perc = int(round((1 - fv/fa)*100))
            if 1 <= perc <= 90:
                return f"-{perc}%"
    except:
        pass
    return ""

def valida_immagine_finale(path):
    if not path or not os.path.exists(path):
        return False
    try:
        size = os.path.getsize(path)
        if size < 4000:
            return False
        if PIL_AVAILABLE:
            from PIL import Image
            im = Image.open(path)
            if im.width < 80 or im.height < 80:
                return False
        return True
    except:
        return False

def get_amazon_details(asin, amazon_link):
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    ]
    session = requests.Session()
    urls = []
    if asin:
        urls.append(f"https://www.amazon.it/dp/{asin}")
        urls.append(f"https://www.amazon.com/dp/{asin}")
    if amazon_link and 'amazon.' in amazon_link.lower():
        clean = amazon_link.split('?')[0]
        if asin and asin not in clean:
            clean = f"https://www.amazon.it/dp/{asin}"
        if clean not in urls:
            urls.append(clean)
    if not urls:
        return None, None, None, None, None
    try:
        session.get("https://www.amazon.it/", timeout=8, headers={'User-Agent': USER_AGENTS[0]})
    except:
        pass
    for attempt in range(2):
        headers = {
            'User-Agent': USER_AGENTS[attempt % len(USER_AGENTS)],
            'Accept-Language': 'it-IT,it;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Referer': 'https://www.amazon.it/',
        }
        for url in urls:
            try:
                r = session.get(url, headers=headers, timeout=15)
                if r.status_code != 200:
                    continue
                html_page = r.text
                if len(html_page) < 8000:
                    continue
                if 'captcha' in html_page.lower()[:5000] and 'sp-cc' in html_page.lower():
                    time.sleep(0.5)
                    continue
                titolo = None
                img_url = None
                prezzo_att = None
                prezzo_old = None
                sconto = None
                m = re.search(r'<span[^>]*id="productTitle"[^>]*>\s*(.*?)\s*</span>', html_page, re.DOTALL | re.IGNORECASE)
                if m:
                    titolo = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                    titolo = re.sub(r'\s+', ' ', titolo).strip()
                    titolo = correggi_testo(titolo)
                # Immagine
                mm = re.search(r'id="landingImage"[^>]+data-old-hires="([^"]+)"', html_page)
                if mm:
                    img_url = mm.group(1)
                if not img_url:
                    mm = re.search(r'"colorImages"\s*:\s*\{[^}]*"initial"\s*:\s*\[\s*\{[^}]*"hiRes"\s*:\s*"(https://[^"]+)"', html_page, re.DOTALL)
                    if mm:
                        img_url = mm.group(1).replace('\\u002F','/').replace('\\/','/')
                if not img_url:
                    mm = re.search(r'data-a-dynamic-image="([^"]+)"', html_page)
                    if mm:
                        dyn = mm.group(1).replace('&quot;', '"')
                        imgs = re.findall(r'"(https://m\.media-amazon\.com/images/I/[^"]+)"\s*:\s*\[(\d+),', dyn)
                        imgs_sorted = sorted(imgs, key=lambda x: int(x[1]), reverse=True)
                        for cand_url, sz in imgs_sorted:
                            cand_url = cand_url.replace('\\u002F','/').replace('\\/','/')
                            if any(b in cand_url for b in ['_SS40_', '_SS60_', '_US40_', 'play-icon']):
                                continue
                            if len(cand_url) > 50:
                                img_url = cand_url
                                break
                if not img_url:
                    for pat in [r'"hiRes":"(https://[^"]+m\.media-amazon\.com[^"]+)"', r'"large":"(https://[^"]+m\.media-amazon\.com[^"]+)"']:
                        mm = re.search(pat, html_page)
                        if mm:
                            cand = mm.group(1).replace('\\u002F','/').replace('\\/','/')
                            if 'm.media-amazon.com' in cand and len(cand) > 40:
                                img_url = cand
                                break
                if not img_url:
                    all_imgs = re.findall(r'https://m\.media-amazon\.com/images/I/[^"\s]+\.(?:jpg|jpeg)', html_page)
                    best = None
                    best_score = -1
                    for cand in all_imgs:
                        if any(b in cand for b in ['_SS40_', '_SS60_', '_SS100_', '_US40_', 'play-icon', '_CR', 'overlay', '_UX']):
                            continue
                        if len(cand) < 60:
                            continue
                        score = 1000
                        if '._AC_SL1500_' in cand:
                            score = 1500
                        if score > best_score:
                            best_score = score
                            best = cand
                    if best:
                        img_url = best
                if img_url:
                    img_url = img_url.replace('http://','https://')
                    if '._SS' in img_url or '._SX' in img_url or '._SY' in img_url:
                        base = img_url.split('._')[0]
                        img_url = base + '._AC_SL1500_.jpg'
                # Prezzi
                core_block = ""
                m_core = re.search(r'id="corePriceDisplay[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', html_page, re.DOTALL | re.IGNORECASE)
                if m_core:
                    core_block = m_core.group(1)
                else:
                    core_block = html_page[:70000]
                for pat in [r'id="priceblock_dealprice"[^>]*>([^<]+)', r'id="priceblock_ourprice"[^>]*>([^<]+)']:
                    mm = re.search(pat, html_page)
                    if mm:
                        prezzo_att = pulisci_prezzo(mm.group(1))
                        break
                if not prezzo_att and core_block:
                    mm = re.search(r'class="[^"]*priceToPay[^"]*"[^>]*>.*?<span[^>]*class="[^"]*a-offscreen[^"]*"[^>]*>([^<]+)</span>', core_block, re.DOTALL)
                    if mm:
                        prezzo_att = pulisci_prezzo(mm.group(1))
                    else:
                        mm = re.search(r'<span[^>]*class="[^"]*a-offscreen[^"]*"[^>]*>([^<]*€[^<]*)</span>', core_block)
                        if mm:
                            prezzo_att = pulisci_prezzo(mm.group(1))
                mm = re.search(r'<span[^>]*class="[^"]*a-price a-text-price[^"]*"[^>]*>.*?<span[^>]*class="[^"]*a-offscreen[^"]*"[^>]*>([^<]+)</span>', html_page, re.DOTALL)
                if mm:
                    prezzo_old = pulisci_prezzo(mm.group(1))
                if prezzo_att and prezzo_old:
                    try:
                        def to_f(s):
                            mmm = re.search(r'(\d+[.,]\d+)', s)
                            return float(mmm.group(1).replace(',', '.')) if mmm else 0
                        fa = to_f(prezzo_att)
                        fo = to_f(prezzo_old)
                        if fa>0 and fo>0 and fa>fo:
                            prezzo_att, prezzo_old = prezzo_old, prezzo_att
                    except:
                        pass
                mm = re.search(r'savingsPercentage[^>]*>\s*-?\s*(\d+)\s*%', html_page, re.IGNORECASE)
                if mm:
                    sconto = f"{mm.group(1)}%"
                else:
                    mm = re.search(r'Risparmi[^<]*?(\d+)\s*%', html_page, re.IGNORECASE)
                    if mm:
                        sconto = f"{mm.group(1)}%"
                if not sconto and prezzo_att and prezzo_old:
                    sconto = calcola_sconto_finale(prezzo_att, prezzo_old, "")
                if img_url or prezzo_att:
                    print(f"[AMAZON V11 OK] {asin} | {prezzo_att} | {prezzo_old} | {sconto} | img:{bool(img_url)}")
                    return titolo, prezzo_att, prezzo_old, sconto, img_url
            except Exception as e:
                print(f"[AMAZON V11 ERR] {e}")
                continue
    print(f"[AMAZON V11 FAIL] {asin}")
    return None, None, None, None, None

def scarica_immagine(url, path="/tmp/amazon.jpg"):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36','Referer': 'https://www.amazon.it/'}
        r = requests.get(url, headers=headers, timeout=20, stream=True)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            size = os.path.getsize(path)
            if size > 4000:
                return path
            else:
                os.remove(path)
    except:
        pass
    return None

def crea_immagine_pulita(asin, amazon_link, img_url_gia=None):
    if not PIL_AVAILABLE:
        return None
    img_url = img_url_gia
    if not img_url and asin:
        _, _, _, _, img_url = get_amazon_details(asin, amazon_link)
    if not img_url:
        return None
    prod_path = scarica_immagine(img_url, "/tmp/prod_amazon.jpg")
    if not prod_path or not os.path.exists(prod_path):
        return None
    try:
        W, H = 1080, 1080
        canvas = Image.new('RGB', (W, H), (255,255,255))
        prod_img = Image.open(prod_path).convert("RGBA")
        if prod_img.width < 80 or prod_img.height < 80:
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
                canvas.paste(logo, (25, 25), logo)
            except:
                pass
        out_path = f"/tmp/pulita_{int(time.time())}_{random.randint(100,999)}.jpg"
        canvas.save(out_path, "JPEG", quality=95)
        try:
            os.remove(prod_path)
        except:
            pass
        if valida_immagine_finale(out_path):
            return out_path
        else:
            return None
    except:
        import traceback
        traceback.print_exc()
        return None

def crea_messaggio(titolo, prezzo_att, prezzo_vecchio, sconto, link):
    titolo = valida_testo_finale(titolo) or "Offerta Amazon"
    if len(titolo) > 5:
        titolo = titolo[0].upper() + titolo[1:]
    if len(titolo) > 100:
        titolo = titolo[:100].rsplit(' ', 1)[0] + "..."
    prezzo_att, prezzo_vecchio = valida_prezzi_finali(prezzo_att, prezzo_vecchio)
    sconto = calcola_sconto_finale(prezzo_att, prezzo_vecchio, sconto)
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
    return f"BOT V11 DOPPIO CONTROLLO + ANTI-DUPLICATO 7GG - {c} cache - Logo: {bool(logo)} - PIL: {PIL_AVAILABLE}"

@app.route('/clear_cache')
def clear_cache_route():
    global seen_cache
    with cache_lock:
        seen_cache = {}
        save_cache()
    return "Cache pulita! Anti-duplicato resettato"

if session_str:
    session_str = session_str.strip().replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "")
    print("SESSION_STRING OK - V11")
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
                print(f"[MATCH] {chat_username} - {getattr(chat, 'title', '')}")
                msg = event.message
                testo_orig = msg.text or msg.message or ""
                link_orig = estrai_link_amazon(testo_orig, msg.buttons)
                link_mio = sostituisci_tag(link_orig) if link_orig else "https://www.amazon.it/"
                asin = estrai_asin(link_orig or link_mio)
                titolo_msg, prezzo_att_msg, prezzo_vecchio_msg, sconto_msg = estrai_info_prodotto(testo_orig)

                # ANTI-DUPLICATO V11 - DOPPIO CONTROLLO
                if is_duplicato(asin, titolo_msg):
                    print(f"[SKIP DUPLICATO] {asin} - {titolo_msg[:30]}")
                    return

                # PREZZI + IMMAGINE + DOPPIO CONTROLLO
                titolo_amz, prezzo_att_amz, prezzo_old_amz, sconto_amz, img_url_amz = get_amazon_details(asin, link_mio) if asin else (None, None, None, None, None)

                # DOPPIO CONTROLLO TITOLO
                titolo_finale = titolo_amz if titolo_amz and len(titolo_amz) > 15 else titolo_msg
                titolo_finale = valida_testo_finale(titolo_finale) or titolo_msg
                titolo_finale = correggi_testo(titolo_finale)

                # DOPPIO CONTROLLO PREZZI
                prezzo_att = prezzo_att_amz if prezzo_att_amz else prezzo_att_msg
                prezzo_vecchio = prezzo_old_amz if prezzo_old_amz else prezzo_vecchio_msg
                prezzo_att, prezzo_vecchio = valida_prezzi_finali(prezzo_att, prezzo_vecchio)

                # DOPPIO CONTROLLO SCONTO - SEMPRE CALCOLATO
                sconto = sconto_amz if sconto_amz else sconto_msg
                sconto = calcola_sconto_finale(prezzo_att, prezzo_vecchio, sconto)

                print(f"[PREZZI MSG] {prezzo_att_msg} | {prezzo_vecchio_msg} | {sconto_msg}")
                print(f"[PREZZI AMZ] {prezzo_att} | {prezzo_vecchio} | {sconto} | {asin} | img:{bool(img_url_amz)}")

                testo_msg = crea_messaggio(titolo_finale, prezzo_att, prezzo_vecchio, sconto, link_mio)
                if not link_mio.startswith("http"):
                    link_mio = "https://www.amazon.it/"
                bottoni = [[Button.url("🛒 Acquista su Amazon", link_mio)],[Button.url("✉️ Invita un amico", mio_link_canale)]]
                
                # DOPPIO CONTROLLO IMMAGINE
                img_path = None
                if asin:
                    img_path = crea_immagine_pulita(asin, link_mio, img_url_amz)
                
                # FALLBACK: foto originale pulita
                if (not img_path or not valida_immagine_finale(img_path)) and (msg.photo or msg.media):
                    try:
                        print(f"[FALLBACK FOTO] Pulizia originale per {asin}")
                        orig_path = await msg.download_media(file="/tmp/original_fallback.jpg")
                        if orig_path and os.path.exists(orig_path) and PIL_AVAILABLE:
                            try:
                                im = Image.open(orig_path).convert("RGB")
                                W, H = im.size
                                l = int(W*0.06); t = int(H*0.06); r = int(W*0.94); b = int(H*0.94)
                                im_crop = im.crop((l, t, r, b))
                                canvas = Image.new('RGB', (1080,1080), (255,255,255))
                                im_crop.thumbnail((900,900), Image.LANCZOS)
                                px = (1080-im_crop.width)//2; py = (1080-im_crop.height)//2
                                canvas.paste(im_crop, (px, py))
                                lp = trova_logo()
                                if lp:
                                    try:
                                        lg = Image.open(lp).convert("RGBA")
                                        lg.thumbnail((280,280), Image.LANCZOS)
                                        canvas.paste(lg, (25,25), lg)
                                    except:
                                        pass
                                fb_path = f"/tmp/fallback_{int(time.time())}.jpg"
                                canvas.save(fb_path, "JPEG", quality=95)
                                if valida_immagine_finale(fb_path):
                                    img_path = fb_path
                                    print(f"[FALLBACK OK] {img_path}")
                            except Exception as e:
                                print(f"[FALLBACK CROP ERR] {e}")
                            try:
                                os.remove(orig_path)
                            except:
                                pass
                    except Exception as e:
                        print(f"[FALLBACK ERR] {e}")

                if img_path and valida_immagine_finale(img_path):
                    await client.send_message(dest_channel_input, testo_msg, file=img_path, buttons=bottoni, link_preview=False)
                    print(f"[OK] V11 con foto - {asin} - {prezzo_att} - {sconto}")
                    try:
                        os.remove(img_path)
                    except:
                        pass
                else:
                    await client.send_message(dest_channel_input, testo_msg, buttons=bottoni, link_preview=False)
                    print(f"[OK] V11 Solo testo - {asin} - {prezzo_att} - {sconto} - no foto validata")
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
        print("Bot V11 doppio controllo + anti-duplicato 7gg avviato!")
        client.run_until_disconnected()
    except Exception as e:
        print(f"Errore: {e}")

threading.Thread(target=avvia_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

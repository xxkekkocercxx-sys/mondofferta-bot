"""
FORWARDER MULTI-CANALE -> @Mondofferta
VERSIONE V8 - CORREZIONE TESTO AUTOMATICA
SOLO IMMAGINI AMAZON PULITE (no loghi altri canali)
"""
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import re, threading, os, json, time, random, html
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


def correggi_testo(testo):
    """
    V8 - CORREGGE TESTO CON ERRORI: HTML entities, troncamenti, encoding rotto
    """
    if not testo:
        return testo
    
    # 1) Decodifica HTML entities (anche doppia codifica)
    # &#39; -> ', &amp; -> &, &quot; -> ", ecc
    testo = html.unescape(testo)
    testo = html.unescape(testo)  # Seconda passata per doppia codifica tipo &amp;#39;
    
    # Fix manuali comuni se unescape non basta
    testo = testo.replace("&#39;", "'").replace("&#x27;", "'").replace("&apos;", "'")
    testo = testo.replace("&quot;", '"').replace("&#34;", '"').replace("&amp;", "&")
    testo = testo.replace("&lt;", "<").replace("&gt;", ">")
    testo = testo.replace("&#x2F;", "/").replace("&#47;", "/")
    
    # 2) Rimuove troncamenti tipo "e..." o "e…" alla fine (come da screenshot cassaforte)
    # Pattern: " e..." o " e…" o " ..."
    testo = re.sub(r'\s+e\.\.\.\s*$', '', testo, flags=re.IGNORECASE)
    testo = re.sub(r'\s+e…\s*$', '', testo, flags=re.IGNORECASE)
    testo = re.sub(r'\s+…\s*$', '', testo)
    # Se finisce con " e" singolo (troncato), rimuove
    testo = re.sub(r'\s+e\s*$', '', testo, flags=re.IGNORECASE)
    
    # 3) Pulisce caratteri strani e encoding rotto
    testo = testo.replace('�', '').replace('\x00', '').replace('\r', ' ')
    
    # 4) Normalizza spazi e trattini
    testo = re.sub(r'\s+', ' ', testo)  # Spazi multipli -> singolo
    testo = re.sub(r'\s*–\s*', ' - ', testo)  # En dash
    testo = re.sub(r'\s*—\s*', ' - ', testo)  # Em dash
    testo = testo.strip()
    
    # 5) Fix maiuscole/minuscole basilare se tutto maiuscolo
    # Se titolo è TUTTO MAIUSCOLO, lo rende Title Case
    if testo.isupper() and len(testo) > 10:
        testo = testo.title()
    
    # 6) Rimuove doppie virgolette strane o spazi prima di punteggiatura
    testo = re.sub(r'\s+,', ',', testo)
    testo = re.sub(r'\s+\.', '.', testo)
    testo = re.sub(r'\s+!', '!', testo)
    testo = re.sub(r'\s+\?', '?', testo)
    
    # 7) Se titolo finisce con "-" o "," troncato, rimuove
    testo = re.sub(r'[\-,]\s*$', '', testo).strip()
    
    return testo

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

def get_amazon_details(asin, amazon_link):
    """
    V6 - FIX IMMAGINE PRINCIPALE + PREZZI INVERTITI + SCONTO MANCANTE
    - Immagine: landingImage data-old-hires o colorImages.initial[0].hiRes (main)
    - Prezzi: priceToPay per attuale, a-text-price per vecchio, fix inversione
    - Sconto: sempre calcolato se manca
    """
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    ]
    
    urls = []
    if asin:
        urls.append(f"https://www.amazon.it/dp/{asin}")
    if amazon_link and 'amazon.' in amazon_link.lower():
        clean_link = amazon_link.split('?')[0]
        if asin and asin not in clean_link:
            clean_link = f"https://www.amazon.it/dp/{asin}"
        urls.append(clean_link)
    
    if not urls:
        return None, None, None, None, None

    for attempt in range(2):
        headers = {
            'User-Agent': USER_AGENTS[attempt % len(USER_AGENTS)],
            'Accept-Language': 'it-IT,it;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Referer': 'https://www.amazon.it/',
        }
        
        for url in urls:
            try:
                r = requests.get(url, headers=headers, timeout=15)
                if r.status_code != 200:
                    continue
                html = r.text
                
                if 'captcha' in html.lower() and 'api-services-support@amazon' in html.lower():
                    time.sleep(0.5)
                    continue

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
                    titolo = correggi_testo(titolo)

                # ===== IMMAGINE PRINCIPALE V6 =====
                # 1) landingImage data-old-hires = immagine principale assoluta
                m = re.search(r'id="landingImage"[^>]+data-old-hires="([^"]+)"', html)
                if m:
                    img_url = m.group(1)
                
                # 2) colorImages initial[0].hiRes = prima immagine galleria (main)
                if not img_url:
                    m = re.search(r'"colorImages"\s*:\s*\{[^}]*"initial"\s*:\s*\[\s*\{[^}]*"hiRes"\s*:\s*"(https://[^"]+)"', html, re.DOTALL)
                    if m:
                        img_url = m.group(1).replace('\\u002F','/').replace('\\/','/')
                
                # 3) mainImageUrl
                if not img_url:
                    m = re.search(r'"mainImageUrl"\s*:\s*"(https://[^"]+m\.media-amazon\.com[^"]+)"', html)
                    if m:
                        img_url = m.group(1).replace('\\u002F','/').replace('\\/','/')
                
                # 4) Primo hiRes (main di solito)
                if not img_url:
                    m = re.search(r'"hiRes":"(https://[^"]+m\.media-amazon\.com[^"]+)"', html)
                    if m:
                        cand = m.group(1).replace('\\u002F','/').replace('\\/','/')
                        if 'm.media-amazon.com' in cand and len(cand) > 50:
                            # Escludi immagini lifestyle con testo tipo ECCELLENTE (spesso hanno _UX o _CR)
                            if not any(x in cand for x in ['_UX', '_CR0', '_CR1']):
                                img_url = cand

                # 5) Fallback: prima I/ valida
                if not img_url:
                    all_imgs = re.findall(r'https://m\.media-amazon\.com/images/I/[^"\s]+\.(?:jpg|jpeg)', html)
                    for cand in all_imgs:
                        if any(bad in cand for bad in ['_SS40_', '_SS60_', '_SS100_', '_US40_', 'play-icon', '_CR', 'overlay', '_UX']):
                            continue
                        if len(cand) < 60:
                            continue
                        img_url = cand
                        break

                # ===== PREZZI V6 FIX INVERSIONE =====
                # Cerca blocco corePriceDisplay
                core_block = ""
                m_core = re.search(r'id="corePriceDisplay[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL | re.IGNORECASE)
                if m_core:
                    core_block = m_core.group(1)
                else:
                    core_block = html[:60000]

                # Prezzo attuale: dealprice > ourprice > priceToPay
                m = re.search(r'id="priceblock_dealprice"[^>]*>([^<]+)', html)
                if m:
                    prezzo_att = pulisci_prezzo(m.group(1))
                
                if not prezzo_att:
                    m = re.search(r'id="priceblock_ourprice"[^>]*>([^<]+)', html)
                    if m:
                        prezzo_att = pulisci_prezzo(m.group(1))
                
                if not prezzo_att and core_block:
                    # Cerca in priceToPay
                    m = re.search(r'class="[^"]*priceToPay[^"]*"[^>]*>.*?<span[^>]*class="[^"]*a-offscreen[^"]*"[^>]*>([^<]+)</span>', core_block, re.DOTALL)
                    if m:
                        prezzo_att = pulisci_prezzo(m.group(1))
                    else:
                        m = re.search(r'<span[^>]*class="[^"]*a-offscreen[^"]*"[^>]*>([^<]*€[^<]*)</span>', core_block)
                        if m:
                            prezzo_att = pulisci_prezzo(m.group(1))

                # Prezzo vecchio (barrato) - a-text-price
                m = re.search(r'<span[^>]*class="[^"]*a-price a-text-price[^"]*"[^>]*>.*?<span[^>]*class="[^"]*a-offscreen[^"]*"[^>]*>([^<]+)</span>', html, re.DOTALL)
                if m:
                    prezzo_old = pulisci_prezzo(m.group(1))
                
                if not prezzo_old:
                    m = re.search(r'id="listPrice"[^>]*>([^<]+)', html)
                    if m:
                        prezzo_old = pulisci_prezzo(m.group(1))
                    else:
                        m = re.search(r'"listPrice"\s*:\s*"([^"]+)"', html)
                        if m:
                            prezzo_old = pulisci_prezzo(m.group(1))

                # FIX INVERSIONE: se attuale > vecchio, scambia
                if prezzo_att and prezzo_old:
                    try:
                        def to_f(s):
                            mm = re.search(r'(\d+[.,]\d+)', s)
                            return float(mm.group(1).replace(',', '.')) if mm else 0
                        fa = to_f(prezzo_att)
                        fo = to_f(prezzo_old)
                        if fa > 0 and fo > 0 and fa > fo:
                            prezzo_att, prezzo_old = prezzo_old, prezzo_att
                            print(f"[FIX INV] Scambiati: att={prezzo_att} old={prezzo_old}")
                    except:
                        pass

                # SCONTO
                m = re.search(r'savingsPercentage[^>]*>\s*-?\s*(\d+)\s*%', html, re.IGNORECASE)
                if m:
                    sconto = f"{m.group(1)}%"
                else:
                    m = re.search(r'Risparmi[^<]*?(\d+)\s*%', html, re.IGNORECASE)
                    if m:
                        sconto = f"{m.group(1)}%"
                
                # Calcola sconto sempre se manca
                if not sconto and prezzo_att and prezzo_old:
                    try:
                        def to_f(s):
                            mm = re.search(r'(\d+[.,]\d+)', s)
                            return float(mm.group(1).replace(',', '.')) if mm else 0
                        fa = to_f(prezzo_att)
                        fo = to_f(prezzo_old)
                        if fa > 0 and fo > fa:
                            perc = int(round((1 - fa/fo)*100))
                            if 1 <= perc <= 90:
                                sconto = f"{perc}%"
                    except:
                        pass

                if img_url or prezzo_att:
                    print(f"[AMAZON V6 OK] {asin} | Att:{prezzo_att} | Old:{prezzo_old} | Sconto:{sconto} | Img:{bool(img_url)}")
                    return titolo, prezzo_att, prezzo_old, sconto, img_url

            except Exception as e:
                print(f"[AMAZON V6 ERR] {e}")
                continue

    print(f"[AMAZON V6 FAIL] {asin}")
    return None, None, None, None, None

def scarica_immagine(url, path="/tmp/amazon.jpg"):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.amazon.it/'
        }
        r = requests.get(url, headers=headers, timeout=20, stream=True)
        if r.status_code == 200:
            content_type = r.headers.get('content-type', '')
            if 'image' not in content_type and 'octet-stream' not in content_type:
                # Controlla comunque, a volte Amazon non manda content-type corretto
                pass
            with open(path, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            size = os.path.getsize(path)
            if size > 5000:  # Abbassato a 5KB per prodotti piccoli come cassaforte
                print(f"[IMG DOWNLOAD] OK {size} bytes da {url[:60]}")
                return path
            else:
                print(f"[IMG DOWNLOAD] Troppo piccola {size} bytes")
                os.remove(path)
    except Exception as e:
        print(f"[IMG DOWNLOAD ERR] {e}")
    return None

def crea_immagine_pulita(asin, amazon_link, img_url_gia=None):
    """
    SOLO IMMAGINE AMAZON PULITA + LOGO - MAI da altri canali
    """
    if not PIL_AVAILABLE:
        print("[IMG] PIL non disponibile")
        return None
    
    img_url = img_url_gia
    # Se non abbiamo URL, prova a recuperarlo
    if not img_url and asin:
        _, _, _, _, img_url = get_amazon_details(asin, amazon_link)
    
    if not img_url:
        print(f"[IMG] Nessun URL immagine per {asin}")
        return None

    prod_path = scarica_immagine(img_url, "/tmp/prod_amazon.jpg")
    if not prod_path or not os.path.exists(prod_path):
        print(f"[IMG] Download fallito per {asin}")
        return None
    
    try:
        W, H = 1080, 1080
        canvas = Image.new('RGB', (W, H), (255,255,255))
        prod_img = Image.open(prod_path).convert("RGBA")
        
        # Verifica che non sia immagine corrotta (abbassato per compatibilità)
        if prod_img.width < 80 or prod_img.height < 80:
            print(f"[IMG] Immagine troppo piccola {prod_img.width}x{prod_img.height}")
            return None
        
        # Verifica che non sia completamente bianca/trasparente (captcha)
        # (semplice check)
        
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
            except Exception as e:
                print(f"[LOGO ERR] {e}")
                pass
        
        out_path = f"/tmp/pulita_{int(time.time())}_{random.randint(100,999)}.jpg"
        canvas.save(out_path, "JPEG", quality=95)
        try:
            os.remove(prod_path)
        except:
            pass
        print(f"[IMG OK] Creata {out_path}")
        return out_path
    except Exception as e:
        print(f"[IMG ERR] {e}")
        import traceback
        traceback.print_exc()
        return None

def crea_messaggio(titolo, prezzo_att, prezzo_vecchio, sconto, link):
    titolo = correggi_testo(titolo.strip()) if titolo else "Offerta Amazon"
    if len(titolo) > 5:
        titolo = titolo[0].upper() + titolo[1:]
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
    return f"BOT V8 CORREZIONE TESTO - {c} cache - Logo: {bool(logo)} - PIL: {PIL_AVAILABLE}"

@app.route('/clear_cache')
def clear_cache_route():
    global seen_cache
    with cache_lock:
        seen_cache = {}
        save_cache()
    return "Cache pulita!"

if session_str:
    session_str = session_str.strip().replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "")
    print("SESSION_STRING OK - V8 Correzione Testo")
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

                if is_duplicato(asin, titolo_msg):
                    print("[SKIP] Duplicato")
                    return

                # PREZZI + IMMAGINE SOLO DA AMAZON
                titolo_amz, prezzo_att_amz, prezzo_old_amz, sconto_amz, img_url_amz = get_amazon_details(asin, link_mio) if asin else (None, None, None, None, None)

                titolo_finale = titolo_amz if titolo_amz and len(titolo_amz) > 15 else titolo_msg
                prezzo_att = prezzo_att_amz if prezzo_att_amz else prezzo_att_msg
                prezzo_vecchio = prezzo_old_amz if prezzo_old_amz else prezzo_vecchio_msg
                sconto = sconto_amz if sconto_amz else sconto_msg

                print(f"[PREZZI MSG] {prezzo_att_msg} | {prezzo_vecchio_msg} | {sconto_msg}")
                print(f"[PREZZI AMZ] {prezzo_att} | {prezzo_vecchio} | {sconto} | {asin} | img:{bool(img_url_amz)}")

                testo_msg = crea_messaggio(titolo_finale, prezzo_att, prezzo_vecchio, sconto, link_mio)
                if not link_mio.startswith("http"):
                    link_mio = "https://www.amazon.it/"
                bottoni = [[Button.url("🛒 Acquista su Amazon", link_mio)],[Button.url("✉️ Invita un amico", mio_link_canale)]]
                
                # SOLO IMMAGINE AMAZON PULITA
                img_path = None
                if asin:
                    img_path = crea_immagine_pulita(asin, link_mio, img_url_amz)
                
                if img_path and os.path.exists(img_path):
                    await client.send_message(dest_channel_input, testo_msg, file=img_path, buttons=bottoni, link_preview=False)
                    print(f"[OK] V5 Amazon Pulito con foto - {asin} - {prezzo_att}")
                    try:
                        os.remove(img_path)
                    except:
                        pass
                else:
                    # Se non riusciamo a prendere immagine Amazon, manda SOLO TESTO (mai foto altri canali!)
                    await client.send_message(dest_channel_input, testo_msg, buttons=bottoni, link_preview=False)
                    print(f"[OK] V6 Solo testo (no foto altri canali) - {asin} - Motivo: immagine Amazon non trovata")
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
        print("Bot V8 correzione testo automatica avviato!")
        client.run_until_disconnected()
    except Exception as e:
        print(f"Errore: {e}")

threading.Thread(target=avvia_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

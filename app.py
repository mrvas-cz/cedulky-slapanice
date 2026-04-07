import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import requests
import urllib.request
import unicodedata
import re
from duckduckgo_search import DDGS
import google.generativeai as genai

st.set_page_config(page_title="PRO Cedulkovač Farma", layout="wide")

@st.cache_resource
def get_czech_font():
    font_path = "Roboto-Bold.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
        urllib.request.urlretrieve(url, font_path)
    return font_path

def clean_filename(text):
    nfkd_form = unicodedata.normalize('NFKD', text)
    return nfkd_form.encode('ASCII', 'ignore').decode('utf-8').replace(" ", "_").upper()

def load_image_from_url(url):
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        return Image.open(io.BytesIO(resp.content)).convert("RGB")
    except:
        return None

# --- NEPRŮSTŘELNÉ ZÍSKÁVÁNÍ DAT ---
def get_plant_data(query, api_key):
    points = []
    
    # 1. Zkusíme AI
    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"Odrůda: {query}. Napiš 12 stručných faktů (4-7 slov) pro zákazníky zahradnictví. Česky, bez odrážek."
            response = model.generate_content(prompt)
            for line in response.text.strip().split('\n'):
                clean = line.replace("*", "").replace("-", "").strip()
                if len(clean) > 3: points.append(clean)
        except:
            pass # AI selhalo, jdeme dál
            
    # 2. Pokud AI selhalo nebo chybí klíč, zkusíme vyhledávač
    if len(points) < 4:
        try:
            with DDGS() as ddgs:
                res = list(ddgs.text(f"{query} popis odrůdy chuť", max_results=3))
                for r in res:
                    for s in re.split(r'(?<=[.!?]) +', r['body']):
                        if 15 < len(s) < 80: points.append(s.strip())
        except:
            pass # Vyhledávač selhal, jdeme dál
            
    # 3. Záchranná brzda - UNIVERZÁLNÍ DATA (Tohle zaručí, že appka nikdy nespadne)
    backup_data = [
        "Vynikající a osvědčená odrůda", "Bohatý výnos a skvělá chuť", 
        "Vysoká odolnost vůči nemocem", "Vhodné pro pěstování venku i ve skleníku",
        "Tradiční volba našich zákazníků", "Silné a zdravé sazenice",
        "Oblíbená odrůda pro domácí pěstování", "Šťavnaté a chutné plody"
    ]
    
    for item in backup_data:
        if item not in points:
            points.append(item)
            
    return points[:12]

# --- ZÍSKÁVÁNÍ GALERIE OBRÁZKŮ ---
def get_plant_images(query):
    urls = []
    try:
        with DDGS(timeout=5) as ddgs:
            res = list(ddgs.images(f"{query} fruit plant detail", max_results=8))
            urls = [r['image'] for r in res]
    except:
        pass
    return urls

# --- UŽIVATELSKÉ ROZHRANÍ ---
with st.sidebar:
    st.header("⚙️ Nastavení")
    api_key = st.text_input("Gemini API klíč (nepovinné, ale lepší):", type="password")
    if st.button("Resetovat aplikaci"):
        st.session_state.clear()
        st.rerun()

st.title("🌿 PRO Cedulkovač 6.0")
st.write("Verze s garancí funkčnosti a galerií obrázků.")

# Inicializace stavu
if 'catalog_options' not in st.session_state: st.session_state.catalog_options = []
if 'image_urls' not in st.session_state: st.session_state.image_urls = []
if 'pro_img' not in st.session_state: st.session_state.pro_img = None
if 'searched_name' not in st.session_state: st.session_state.searched_name = ""

nazev = st.text_input("Zadejte název odrůdy:", value=st.session_state.searched_name)

if st.button("✨ Načíst informace a fotky", type="primary"):
    if nazev:
        st.session_state.searched_name = nazev
        with st.spinner('Zpracovávám (pokud je síť přetížená, použiji univerzální šablony)...'):
            st.session_state.catalog_options = get_plant_data(nazev, api_key)
            st.session_state.image_urls = get_plant_images(nazev)
            
            if st.session_state.image_urls:
                st.session_state.pro_img = load_image_from_url(st.session_state.image_urls[0])
            else:
                st.session_state.pro_img = None
    else:
        st.warning("Zadejte prosím název rostliny.")

st.markdown("---")

# Zobrazení editoru POUZE pokud máme data (což díky pojistce máme vždy po kliknutí)
if st.session_state.catalog_options:
    st.subheader("1️⃣ Texty na cedulku")
    
    selected_points = st.multiselect(
        "Vyberte 4 body z nalezených textů:", 
        st.session_state.catalog_options, 
        default=st.session_state.catalog_options[:4]
    )

    if len(selected_points) == 4:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.caption("Můžete si texty libovolně upravit:")
            e1 = st.text_input("Bod 1", value=selected_points[0])
            e2 = st.text_input("Bod 2", value=selected_points[1])
            e3 = st.text_input("Bod 3", value=selected_points[2])
            e4 = st.text_input("Bod 4", value=selected_points[3])
        with c2:
            st.caption("Aktuální fotka na cedulku:")
            if st.session_state.pro_img: 
                st.image(st.session_state.pro_img, use_column_width=True)
            else:
                st.info("Zatím není vybrána žádná fotka.")
            f = st.file_uploader("Nahradit fotkou z počítače:", type=["jpg", "png"])
            if f: st.session_state.pro_img = Image.open(f).convert("RGB")

        # GALERIE OBRÁZKŮ Z WEBU
        if st.session_state.image_urls:
            st.markdown("---")
            st.subheader("2️⃣ Galerie fotek z internetu")
            st.write("Nelíbí se vám úvodní fotka? Klikněte na jinou:")
            
            cols = st.columns(4)
            for i, url in enumerate(st.session_state.image_urls):
                with cols[i % 4]:
                    try:
                        st.image(url)
                        if st.button("✅ Vybrat", key=f"img_btn_{i}"):
                            st.session_state.pro_img = load_image_from_url(url)
                            st.rerun() # Okamžitě překreslí náhled nahoře
                    except: pass

        st.markdown("---")
        
        # GENERÁTOR
        if st.button("🖨️ 3️⃣ VYGENEROVAT PDF K TISKU", type="primary", use_container_width=True):
            A4_W, A4_H = 2480, 3508
            L_W, L_H = A4_W // 2, A4_H // 2
            canvas = Image.new('RGB', (A4_W, A4_H), 'white')
            font_p = get_czech_font()

            def draw_label(name, img, pts):
                lbl = Image.new('RGB', (L_W, L_H), 'white')
                d = ImageDraw.Draw(lbl)
                y = 60
                try:
                    logo = Image.open("logo txt farma.JPG").convert("RGBA")
                    lw = L_W - 320
                    logo = logo.resize((lw, int(lw * (logo.height / logo.width))), Image.Resampling.LANCZOS)
                    lbl.paste(logo, ((L_W - lw) // 2, y), logo)
                    y += logo.height + 30
                except: y += 100
                
                f_t = ImageFont.truetype(font_p, 110)
                d.text((L_W//2, y + 40), name.upper(), fill="#004D40", anchor="mm", font=f_t)
                y += 140
                
                if img:
                    th = int(L_H * 0.41); tw = int(th * (img.width / img.height))
                    if tw > L_W - 180: tw = L_W - 180; th = int(tw / (img.width / img.height))
                    lbl.paste(img.resize((tw, th), Image.Resampling.LANCZOS), ((L_W - tw) // 2, y))
                    y += th + 55
                else: y += 350
                
                f_b = ImageFont.truetype(font_p, 48)
                for p in pts:
                    d.text((120, y), f"• {p[:60]}", fill="#333333", font=f_b)
                    y += 75
                    
                bx_w, bx_h = 420, 160; bx_x, bx_y = (L_W - bx_w)//2, L_H - 225
                d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="#004D40", width=14)
                d.text((bx_x + bx_w + 35, bx_y + 85), "Kč", fill="black", anchor="lm", font=ImageFont.truetype(font_p, 100))
                return lbl

            l_img = draw_label(st.session_state.searched_name, st.session_state.pro_img, [e1, e2, e3, e4])
            canvas.paste(l_img, (0, 0)); canvas.paste(l_img, (L_W, 0))
            canvas.paste(l_img, (0, L_H)); canvas.paste(l_img, (L_W, L_H))
            
            st.image(canvas, use_column_width=True)
            buf = io.BytesIO()
            canvas.save(buf, format="PDF")
            st.download_button(f"📥 STÁHNOUT PDF: {st.session_state.searched_name}", buf.getvalue(), f"{clean_filename(st.session_state.searched_name)}.pdf")

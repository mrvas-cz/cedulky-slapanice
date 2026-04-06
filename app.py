import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import requests
import urllib.request
import unicodedata
import re
from duckduckgo_search import DDGS

st.set_page_config(page_title="Cedulkovač Šlapanice", layout="wide")

@st.cache_resource
def get_czech_font():
    font_path = "Roboto-Bold.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
        urllib.request.urlretrieve(url, font_path)
    return font_path

def get_fitting_font(text, max_width, initial_size, font_path):
    size = initial_size
    font = ImageFont.truetype(font_path, size)
    while font.getlength(text) > (max_width - 140) and size > 35:
        size -= 4
        font = ImageFont.truetype(font_path, size)
    return font

def clean_filename(text):
    nfkd_form = unicodedata.normalize('NFKD', text)
    only_ascii = nfkd_form.encode('ASCII', 'ignore').decode('utf-8')
    return only_ascii.replace(" ", "_").upper()

# --- CHYTRÉ DOHLEDÁVÁNÍ FAKTŮ ---
def fetch_smart_plant_data(query):
    facts = []
    img_url = None
    
    try:
        with DDGS() as ddgs:
            # 1. HLEDÁNÍ TEXTU (hledáme konkrétně "pěstování" a "vlastnosti")
            search_results = list(ddgs.text(f"{query} vlastnosti pěstování využití", max_results=5))
            
            seen_sentences = set()
            for r in search_results:
                snippet = r['body']
                # Rozdělení na věty
                sentences = re.split(r'(?<=[.!?]) +', snippet)
                for s in sentences:
                    s = s.strip().replace("...", "")
                    # FILTR: Hledáme věcné informace (klíčová slova)
                    keywords = ["chuť", "aroma", "slunce", "půda", "vitamín", "výnos", "odolná", "plod", "léčiv", "vhodné", "využití"]
                    if any(key in s.lower() for key in keywords) and len(s) < 80 and len(s) > 15:
                        # Očištění od balastu
                        clean_s = re.sub(r'http\S+', '', s)
                        if clean_s not in seen_sentences:
                            facts.append(clean_s)
                            seen_sentences.add(clean_s)
            
            # 2. HLEDÁNÍ OBRÁZKU
            img_results = list(ddgs.images(f"{query} sazenice plod detail", max_results=1))
            if img_results:
                img_url = img_results[0]['image']
    except:
        pass

    # ZÁCHRANNÁ BRZDA: Pokud internet nic rozumného nenašel, nabídneme profi univerzální body
    placeholders = [
        "Vynikající chuť a bohaté aroma",
        "Silná sazenice s bohatým kořenem",
        "Vhodné pro záhony i do truhlíků",
        "Vypěstováno lokálně bez chemie",
        "Vysoký obsah vitamínů a minerálů",
        "Odolná odrůda pro české zahrady"
    ]
    
    while len(facts) < 8:
        facts.append(placeholders[len(facts) % len(placeholders)])
        
    return facts, img_url

# --- APLIKACE ---
st.title("🚜 Šlapanický Cedulkovač – Profi Faktograf")
st.write("Aplikace dohledá věcné informace o chuti, pěstování a využití rostliny.")

if 'all_options' not in st.session_state: st.session_state.all_options = []
if 'img_found' not in st.session_state: st.session_state.img_found = None

nazev = st.text_input("Zadejte název sazenice:", placeholder="Např. Celer řapíkatý")

if st.button("🔍 Najít věcné informace"):
    if nazev:
        with st.spinner('Analyzuji odborné weby...'):
            options, img = fetch_smart_plant_data(nazev)
            st.session_state.all_options = options
            if img:
                try:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    resp = requests.get(img, headers=headers, timeout=5)
                    st.session_state.img_found = Image.open(io.BytesIO(resp.content)).convert("RGB")
                except: st.session_state.img_found = None
    else: st.warning("Napište název!")

st.markdown("---")

if st.session_state.all_options:
    st.subheader("📋 Vyberte 4 nejdůležitější informace pro zákazníka")
    st.info("Zde jsou fakta o chuti, nárocích a využití. Vyberte ty nejlepší.")
    
    selected = st.multiselect("Vyberte z nabídky:", st.session_state.all_options, max_selections=4)
    
    if len(selected) == 4:
        col1, col2 = st.columns(2)
        with col1:
            # Možnost finální editace (zkrácení, úprava)
            f1 = st.text_input("Bod 1:", value=selected[0][:50])
            f2 = st.text_input("Bod 2:", value=selected[1][:50])
            f3 = st.text_input("Bod 3:", value=selected[2][:50])
            f4 = st.text_input("Bod 4:", value=selected[3][:50])
        
        with col2:
            if st.session_state.img_found:
                st.image(st.session_state.img_found, width=200)
            up = st.file_uploader("Nahrát vlastní fotku:", type=["jpg", "png"])
            if up: st.session_state.img_found = Image.open(up).convert("RGB")

        if st.button("✨ VYTVOŘIT PROFI CEDULKY"):
            A4_W, A4_H = 2480, 3508
            LABEL_W, LABEL_H = A4_W // 2, A4_H // 2
            canvas = Image.new('RGB', (A4_W, A4_H), 'white')
            font_p = get_czech_font()

            def create_label(name, img, bullets):
                lbl = Image.new('RGB', (LABEL_W, LABEL_H), 'white')
                d = ImageDraw.Draw(lbl)
                y = 50
                # Logo
                try:
                    logo = Image.open("logo txt farma.JPG").convert("RGBA")
                    lw = LABEL_W - 300
                    lh = int(lw * (logo.height / logo.width))
                    logo = logo.resize((lw, lh), Image.Resampling.LANCZOS)
                    lbl.paste(logo, ((LABEL_W - lw) // 2, y), logo)
                    y += lh + 25
                except: y += 110
                # Název
                f_t = get_fitting_font(name.upper(), LABEL_W, 120, font_p)
                d.text((LABEL_W//2, y + 45), name.upper(), fill="#1B5E20", anchor="mm", font=f_t)
                y += 140
                # Fotka
                if img:
                    th = int(LABEL_H * 0.40)
                    asp = img.width / img.height
                    tw = int(th * asp)
                    if tw > LABEL_W - 160: tw = LABEL_W - 160; th = int(tw / asp)
                    res = img.resize((tw, th), Image.Resampling.LANCZOS)
                    lbl.paste(res, ((LABEL_W - tw) // 2, y))
                    y += th + 50
                else: y += 320
                # Body
                f_b = ImageFont.truetype(font_p, 50)
                for b in bullets:
                    if b:
                        d.text((115, y), f"• {b}", fill="#333333", font=f_b)
                        y += 75
                # Cena
                bx_w, bx_h = 420, 155
                bx_x, bx_y = (LABEL_W - bx_w)//2, LABEL_H - 225
                d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="#1B5E20", width=12)
                d.text((bx_x + bx_w + 35, bx_y + 80), "Kč", fill="black", anchor="lm", font=ImageFont.truetype(font_p, 100))
                d.rectangle([0, 0, LABEL_W-2, LABEL_H-2], outline="#EEEEEE", width=4)
                return lbl

            final_label = create_label(nazev, st.session_state.img_found, [f1, f2, f3, f4])
            canvas.paste(final_label, (0, 0)); canvas.paste(final_label, (LABEL_W, 0))
            canvas.paste(final_label, (0, LABEL_H)); canvas.paste(final_label, (LABEL_W, LABEL_H))
            st.image(canvas, use_column_width=True)
            buf = io.BytesIO()
            canvas.save(buf, format="PDF")
            st.download_button(f"📥 STÁHNOUT PDF {nazev.upper()}", buf.getvalue(), f"cedulky_{clean_filename(nazev)}.pdf", "application/pdf")

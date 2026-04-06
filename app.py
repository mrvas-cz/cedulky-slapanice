import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import requests
import urllib.request
import unicodedata
import wikipedia
import re
from duckduckgo_search import DDGS

# Nastavení češtiny pro Wikipedii
wikipedia.set_lang("cs")

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

# --- FUNKCE PRO DOHLEDÁNÍ INFORMACÍ ---
def fetch_plant_info(query):
    points = []
    img_url = None
    
    # 1. Hledání textu na Wikipedii
    try:
        summary = wikipedia.summary(query, sentences=3)
        # Rozdělení na věty a vyčištění
        sentences = re.split(r'[.!?]', summary)
        for s in sentences:
            s = s.strip()
            if len(s) > 5:
                # Ořezání na max 5-6 slov pro stručnost
                words = s.split()[:5]
                points.append(" ".join(words))
            if len(points) >= 4: break
    except:
        points = ["Kvalitní odrůda", "Zdravá sazenice", "Místní původ", "Připraveno k sadbě"]

    # Doplnění bodů, pokud jich je málo
    while len(points) < 4:
        points.append("Vypěstováno u nás")

    # 2. Hledání fotky
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(f"{query} sazenice", max_results=1))
            if results: img_url = results[0]['image']
    except: pass
    
    return points[:4], img_url

# --- HLAVNÍ ROZHRANÍ ---
st.title("🚜 Šlapanický Cedulkovač – Inteligentní automat")

# Inicializace paměti (session_state)
if 'found_points' not in st.session_state:
    st.session_state.found_points = ["", "", "", ""]
if 'found_img' not in st.session_state:
    st.session_state.found_img = None

nazev = st.text_input("Zadejte název sazenice:", placeholder="Např. Celer řapíkatý")

if st.button("🔍 Najít informace a fotku"):
    if nazev:
        with st.spinner('Prohledávám zdroje...'):
            points, img_url = fetch_plant_info(nazev)
            st.session_state.found_points = points
            
            if img_url:
                try:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    resp = requests.get(img_url, headers=headers, timeout=5)
                    st.session_state.found_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                except:
                    st.session_state.found_img = None
    else:
        st.warning("Nejdříve napište název.")

st.markdown("---")

# --- EDITAČNÍ SEKCE ---
st.subheader("📝 Kontrola a úprava informací")
st.write("Zde můžete upravit, co aplikace našla, než to vytisknete:")

col1, col2 = st.columns(2)

with col1:
    edit_b1 = st.text_input("Bod 1 (max 5 slov):", value=st.session_state.found_points[0])
    edit_b2 = st.text_input("Bod 2 (max 5 slov):", value=st.session_state.found_points[1])
    edit_b3 = st.text_input("Bod 3 (max 5 slov):", value=st.session_state.found_points[2])
    edit_b4 = st.text_input("Bod 4 (max 5 slov):", value=st.session_state.found_points[3])

with col2:
    if st.session_state.found_img:
        st.image(st.session_state.found_img, caption="Dohledaná fotka", width=200)
    else:
        st.write("Fotka nenalezena.")
    
    uploaded_file = st.file_uploader("Nahrát jinou fotku:", type=["jpg", "png"])
    if uploaded_file:
        st.session_state.found_img = Image.open(uploaded_file).convert("RGB")

# --- GENEROVÁNÍ PDF ---
if st.button("✨ VYTVOŘIT FINÁLNÍ CEDULKY"):
    if not nazev:
        st.error("Chybí název sazenice!")
    else:
        with st.spinner('Generuji PDF...'):
            A4_W, A4_H = 2480, 3508
            LABEL_W, LABEL_H = A4_W // 2, A4_H // 2
            canvas = Image.new('RGB', (A4_W, A4_H), 'white')
            font_p = get_czech_font()

            def create_label(p_name, image, bullets):
                lbl = Image.new('RGB', (LABEL_W, LABEL_H), 'white')
                d = ImageDraw.Draw(lbl)
                
                # 1. LOGO
                curr_y = 50
                try:
                    logo = Image.open("logo txt farma.JPG").convert("RGBA")
                    lw = LABEL_W - 280
                    lh = int(lw * (logo.height / logo.width))
                    logo = logo.resize((lw, lh), Image.Resampling.LANCZOS)
                    lbl.paste(logo, ((LABEL_W - lw) // 2, curr_y), logo)
                    curr_y += lh + 25
                except: curr_y += 110

                # 2. NÁZEV
                f_t = get_fitting_font(p_name.upper(), LABEL_W, 125, font_p)
                d.text((LABEL_W//2, curr_y + 45), p_name.upper(), fill="#1B5E20", anchor="mm", font=f_t)
                curr_y += 140

                # 3. FOTKA
                if image:
                    target_h = int(LABEL_H * 0.40)
                    asp = image.width / image.height
                    tw = int(target_h * asp)
                    if tw > LABEL_W - 160:
                        tw = LABEL_W - 160
                        target_h = int(tw / asp)
                    img_res = image.resize((tw, target_h), Image.Resampling.LANCZOS)
                    lbl.paste(img_res, ((LABEL_W - tw) // 2, curr_y))
                    curr_y += target_h + 45
                else: curr_y += 320

                # 4. EDITOVANÉ BODY
                f_b = ImageFont.truetype(font_p, 55)
                for b in bullets:
                    if b.strip():
                        d.text((110, curr_y), f"• {b}", fill="#333333", font=f_b)
                        curr_y += 75

                # 5. CENA
                bx_w, bx_h = 420, 150
                bx_x, bx_y = (LABEL_W - bx_w)//2, LABEL_H - 220
                d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="#1B5E20", width=12)
                f_kc = ImageFont.truetype(font_p, 100)
                d.text((bx_x + bx_w + 35, bx_y + 75), "Kč", fill="black", anchor="lm", font=f_kc)
                
                d.rectangle([0, 0, LABEL_W-2, LABEL_H-2], outline="#EEEEEE", width=4)
                return lbl

            current_bullets = [edit_b1, edit_b2, edit_b3, edit_b4]
            final_lbl = create_label(nazev, st.session_state.found_img, current_bullets)
            
            canvas.paste(final_lbl, (0, 0))
            canvas.paste(final_lbl, (LABEL_W, 0))
            canvas.paste(final_lbl, (0, LABEL_H))
            canvas.paste(final_lbl, (LABEL_W, LABEL_H))

            st.image(canvas, use_column_width=True)
            buf = io.BytesIO()
            canvas.save(buf, format="PDF")
            
            safe_name = clean_filename(nazev)
            st.download_button(
                label=f"📥 STÁHNOUT PDF (cedulky_{safe_name}.pdf)",
                data=buf.getvalue(),
                file_name=f"cedulky_{safe_name}.pdf",
                mime="application/pdf"
            )

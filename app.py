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

# Nastavení češtiny
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

# --- FUNKCE PRO DOHLEDÁNÍ VELKÉHO MNOŽSTVÍ INFO ---
def fetch_lots_of_info(query):
    all_sentences = []
    img_url = None
    
    try:
        # Získáme delší text z Wikipedie
        page = wikipedia.page(query, auto_suggest=True)
        content = page.summary + " " + page.section("Popis") if page.section("Popis") else page.summary
        
        # Rozsekání na věty (hledáme tečky, ale pozor na zkratky)
        raw_sentences = re.split(r'(?<=[.!?]) +', content)
        
        for s in raw_sentences:
            s = re.sub(r'\(.*?\)', '', s).strip() # Odstranění textu v závorkách
            if len(s) > 10 and len(s) < 150: # Bereme jen rozumně dlouhé věty
                all_sentences.append(s)
            if len(all_sentences) >= 15: break # Chceme zásobu cca 15 vět
    except:
        all_sentences = [
            "Kvalitní odrůda pro vaši zahradu", "Bohatá úroda zaručena", 
            "Odolná sazenice z naší farmy", "Pěstováno bez chemických hnojiv",
            "Tradiční šlapanická kvalita", "Vhodné pro pěstování v nádobách",
            "Výborná chuť a aroma", "Sazenice s pevným balem"
        ]

    try:
        with DDGS() as ddgs:
            res = list(ddgs.images(f"{query} plod detail", max_results=1))
            if res: img_url = res[0]['image']
    except: pass
    
    return all_sentences, img_url

# --- STRUKTURA APLIKACE ---
st.title("🚜 Šlapanický Cedulkovač – Inteligentní výběr")

if 'all_options' not in st.session_state: st.session_state.all_options = []
if 'img_found' not in st.session_state: st.session_state.img_found = None

nazev = st.text_input("Zadejte název sazenice (např. Paprika ranná):")

if st.button("🔍 Prohledat internet a nabídnout možnosti"):
    if nazev:
        with st.spinner('Pracuji jako včelička...'):
            options, img = fetch_lots_of_info(nazev)
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
    st.subheader("📋 1. Vyberte právě 4 informace pro cedulku")
    # Multiselect s limitem
    selected = st.multiselect("Vyberte z nabídky:", st.session_state.all_options, max_selections=4)
    
    if len(selected) == 4:
        st.success("Skvěle! Teď je můžete v případě potřeby naposledy upravit:")
        col1, col2 = st.columns(2)
        
        with col1:
            # Finální editační políčka
            f1 = st.text_input("Bod 1:", value=selected[0])
            f2 = st.text_input("Bod 2:", value=selected[1])
            f3 = st.text_input("Bod 3:", value=selected[2])
            f4 = st.text_input("Bod 4:", value=selected[3])
        
        with col2:
            if st.session_state.img_found:
                st.image(st.session_state.img_found, width=250, caption="Náhled fotky")
            uploaded = st.file_uploader("Nahrát jinou fotku?", type=["jpg", "png"])
            if uploaded: st.session_state.img_found = Image.open(uploaded).convert("RGB")

        # --- GENERÁTOR ---
        if st.button("✨ VYTVOŘIT CEDULKY"):
            A4_W, A4_H = 2480, 3508
            LABEL_W, LABEL_H = A4_W // 2, A4_H // 2
            canvas = Image.new('RGB', (A4_W, A4_H), 'white')
            font_p = get_czech_font()

            def create_label(name, img, bullets):
                lbl = Image.new('RGB', (LABEL_W, LABEL_H), 'white')
                d = ImageDraw.Draw(lbl)
                
                # Logo
                y = 50
                try:
                    logo = Image.open("logo txt farma.JPG").convert("RGBA")
                    lw = LABEL_W - 280
                    lh = int(lw * (logo.height / logo.width))
                    logo = logo.resize((lw, lh), Image.Resampling.LANCZOS)
                    lbl.paste(logo, ((LABEL_W - lw) // 2, y), logo)
                    y += lh + 25
                except: y += 110

                # Název
                f_t = get_fitting_font(name.upper(), LABEL_W, 125, font_p)
                d.text((LABEL_W//2, y + 45), name.upper(), fill="#1B5E20", anchor="mm", font=f_t)
                y += 135

                # Fotka
                if img:
                    th = int(LABEL_H * 0.40)
                    asp = img.width / img.height
                    tw = int(th * asp)
                    if tw > LABEL_W - 160:
                        tw = LABEL_W - 160
                        th = int(tw / asp)
                    res = img.resize((tw, th), Image.Resampling.LANCZOS)
                    lbl.paste(res, ((LABEL_W - tw) // 2, y))
                    y += th + 45
                else: y += 320

                # Body
                f_b = ImageFont.truetype(font_p, 52)
                for b in bullets:
                    if b.strip():
                        # Ořezání na řádek, aby to nepřečuhovalo
                        clean_b = b[:55] + "..." if len(b) > 55 else b
                        d.text((110, y), f"• {clean_b}", fill="#333333", font=f_b)
                        y += 75

                # Cena
                bx_w, bx_h = 420, 150
                bx_x, bx_y = (LABEL_W - bx_w)//2, LABEL_H - 220
                d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="#1B5E20", width=12)
                d.text((bx_x + bx_w + 35, bx_y + 75), "Kč", fill="black", anchor="lm", font=ImageFont.truetype(font_p, 100))
                
                d.rectangle([0, 0, LABEL_W-2, LABEL_H-2], outline="#EEEEEE", width=4)
                return lbl

            final_bullets = [f1, f2, f3, f4]
            label_img = create_label(nazev, st.session_state.img_found, final_bullets)
            
            canvas.paste(label_img, (0, 0))
            canvas.paste(label_img, (LABEL_W, 0))
            canvas.paste(label_img, (0, LABEL_H))
            canvas.paste(label_img, (LABEL_W, LABEL_H))

            st.image(canvas, use_column_width=True)
            buf = io.BytesIO()
            canvas.save(buf, format="PDF")
            st.download_button(f"📥 STÁHNOUT PDF ({nazev})", buf.getvalue(), f"cedulky_{clean_filename(nazev)}.pdf", "application/pdf")
    else:
        st.info("Vyberte prosím přesně 4 body z nabídky výše.")

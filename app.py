import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import requests
import urllib.request
import unicodedata
import re
import time
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

# --- ZÁCHRANNÉ DOHLEDÁVÁNÍ (Když AI vyčerpá limit) ---
def get_web_fallback(query):
    findings = []
    try:
        with DDGS() as ddgs:
            res = list(ddgs.text(f"{query} popis odrůdy pěstování", max_results=5))
            for r in res:
                sentences = re.split(r'(?<=[.!?]) +', r['body'])
                for s in sentences:
                    if 15 < len(s) < 80 and any(k in s.lower() for k in ["chuť", "plod", "výnos", "odol"]):
                        findings.append(s.strip())
    except: pass
    return findings[:12]

# --- AI FUNKCE (Pamatuje si výsledky) ---
@st.cache_data(show_spinner=False)
def get_ai_plant_data(query, api_key):
    ai_points = []
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Odrůda: {query}. Napiš 12 stručných faktů (4-7 slov) pro zákazníky. Česky, bez odrážek."
        response = model.generate_content(prompt)
        
        lines = response.text.strip().split('\n')
        for line in lines:
            clean_l = line.replace("*", "").replace("-", "").strip()
            if len(clean_l) > 5: ai_points.append(clean_l)
            
    except Exception as e:
        if "429" in str(e):
            st.warning("⚠️ Limit AI vyčerpán. Přepínám na záložní vyhledávání...")
            return get_web_fallback(query)
        else:
            return get_web_fallback(query)

    return ai_points[:12]

# --- GALERIE OBRÁZKŮ ---
@st.cache_data(show_spinner=False)
def get_plant_images(query):
    urls = []
    try:
        with DDGS(timeout=10) as ddgs:
            # Najdeme až 8 obrázků pro výběr
            img_res = list(ddgs.images(f"{query} fruit detail", max_results=8))
            urls = [r['image'] for r in img_res]
    except: pass
    return urls

# --- UŽIVATELSKÉ ROZHRANÍ ---
with st.sidebar:
    st.header("⚙️ Nastavení")
    api_key = st.text_input("Gemini API klíč:", type="password")
    if st.button("Vymazat paměť hledání"):
        st.cache_data.clear()
        st.success("Paměť vymazána.")

st.title("🌿 Profesionální Cedulkovač 5.0 (S Galerií)")

# Udržování stavu
if 'catalog_options' not in st.session_state: st.session_state.catalog_options = []
if 'image_urls' not in st.session_state: st.session_state.image_urls = []
if 'pro_img' not in st.session_state: st.session_state.pro_img = None

nazev = st.text_input("Zadejte název odrůdy (např. Rajče San Marzano):")

if st.button("✨ Načíst informace a fotky"):
    if not api_key:
        st.error("Nejprve vložte API klíč v levém menu!")
    elif nazev:
        with st.spinner('Analyzuji data a stahuji fotky...'):
            # Texty
            st.session_state.catalog_options = get_ai_plant_data(nazev, api_key)
            # Fotky
            st.session_state.image_urls = get_plant_images(nazev)
            # Automaticky nastavíme první fotku jako výchozí
            if st.session_state.image_urls:
                st.session_state.pro_img = load_image_from_url(st.session_state.image_urls[0])
            else:
                st.session_state.pro_img = None
    else: st.warning("Zadejte název sazenice.")

st.markdown("---")

# Pokud máme data, zobrazíme editor
if st.session_state.catalog_options:
    st.subheader("📋 1. Výběr textů na cedulku")
    selected_points = st.multiselect(
        "Vyberte 4 body:", 
        st.session_state.catalog_options, 
        default=st.session_state.catalog_options[:4] if len(st.session_state.catalog_options)>=4 else None
    )

    if len(selected_points) == 4:
        c1, c2 = st.columns([2, 1])
        with c1:
            e = [st.text_input(f"Bod {i+1}", value=selected_points[i]) for i in range(4)]
        with c2:
            st.write("**Aktuálně vybraná fotka:**")
            if st.session_state.pro_img: 
                st.image(st.session_state.pro_img, use_column_width=True)
            f = st.file_uploader("Nebo nahrát vlastní foto z PC:", type=["jpg", "png"])
            if f: st.session_state.pro_img = Image.open(f).convert("RGB")

        # --- GALERIE ---
        if st.session_state.image_urls:
            st.markdown("---")
            st.subheader("🖼️ 2. Výběr fotky z internetu")
            st.write("Klikněte na 'Použít fotku' pod obrázkem, který se vám nejvíce líbí.")
            
            # Vytvoření mřížky 4 sloupců
            cols = st.columns(4)
            for i, url in enumerate(st.session_state.image_urls):
                with cols[i % 4]:
                    try:
                        st.image(url, use_column_width=True)
                        if st.button("✅ Použít fotku", key=f"img_btn_{i}"):
                            with st.spinner("Měním fotku..."):
                                st.session_state.pro_img = load_image_from_url(url)
                    except:
                        pass # Pokud odkaz z internetu nefunguje, přeskočí se

        st.markdown("---")
        
        # --- GENERÁTOR PDF ---
        if st.button("🖨️ 3. GENEROVAT FINÁLNÍ PDF", type="primary"):
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

            l_img = draw_label(nazev, st.session_state.pro_img, e)
            canvas.paste(l_img, (0, 0)); canvas.paste(l_img, (L_W, 0))
            canvas.paste(l_img, (0, L_H)); canvas.paste(l_img, (L_W, L_H))
            st.image(canvas, use_column_width=True)
            buf = io.BytesIO()
            canvas.save(buf, format="PDF")
            st.download_button(f"📥 STÁHNOUT PDF: {nazev}", buf.getvalue(), f"{clean_filename(nazev)}.pdf")

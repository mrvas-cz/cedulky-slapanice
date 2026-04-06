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

# --- FUNKCE PRO ZÁCHRANNÉ HLEDÁNÍ (Když AI nejede) ---
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

# --- AI FUNKCE S CACHOVÁNÍM A ODOLNOSTÍ ---
@st.cache_data(show_spinner=False)
def get_ai_plant_data(query, api_key):
    ai_points = []
    
    try:
        genai.configure(api_key=api_key)
        # Preferujeme 1.5-flash, má stabilnější kvóty pro Free Tier
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"Odrůda: {query}. Napiš 12 stručných faktů (4-7 slov) pro zákazníky v zahradnictví. Česky, bez odrážek."
        response = model.generate_content(prompt)
        
        lines = response.text.strip().split('\n')
        for line in lines:
            clean_l = line.replace("*", "").replace("-", "").strip()
            if len(clean_l) > 5: ai_points.append(clean_l)
            
    except Exception as e:
        if "429" in str(e):
            st.warning("⚠️ Limit AI vyčerpán. Přepínám na záložní vyhledávání v katalozích...")
            return get_web_fallback(query)
        else:
            st.error(f"Chyba AI: {e}")
            return get_web_fallback(query)

    return ai_points[:12]

# --- FOTKA (Samostatně kvůli limitům) ---
@st.cache_data(show_spinner=False)
def get_plant_image(query):
    try:
        with DDGS(timeout=10) as ddgs:
            img_res = list(ddgs.images(f"{query} fruit detail", max_results=1))
            if img_res: return img_res[0]['image']
    except: return None
    return None

# --- UI ---
with st.sidebar:
    st.header("⚙️ Nastavení")
    api_key = st.text_input("Gemini API klíč:", type="password")
    if st.button("Vymazat paměť hledání"):
        st.cache_data.clear()
        st.success("Paměť vymazána.")

st.title("🌿 Profesionální Cedulkovač 4.0")

if 'catalog_options' not in st.session_state: st.session_state.catalog_options = []
if 'pro_img' not in st.session_state: st.session_state.pro_img = None

nazev = st.text_input("Zadejte název odrůdy:")

if st.button("✨ Načíst informace"):
    if not api_key:
        st.error("Chybí API klíč v nastavení!")
    elif nazev:
        with st.spinner('Získávám data...'):
            # Získání textu (AI nebo Web)
            st.session_state.catalog_options = get_ai_plant_data(nazev, api_key)
            # Získání obrázku
            img_url = get_plant_image(nazev)
            if img_url:
                try:
                    resp = requests.get(img_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                    st.session_state.pro_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                except: st.session_state.pro_img = None
    else: st.warning("Napište název.")

st.markdown("---")

if st.session_state.catalog_options:
    st.subheader("📋 Výběr na cedulku")
    selected_points = st.multiselect("Vyberte 4 body:", st.session_state.catalog_options, 
                                     default=st.session_state.catalog_options[:4] if len(st.session_state.catalog_options)>=4 else None)

    if len(selected_points) == 4:
        c1, c2 = st.columns([2, 1])
        with c1:
            e = [st.text_input(f"Bod {i+1}", value=selected_points[i]) for i in range(4)]
        with c2:
            if st.session_state.pro_img: st.image(st.session_state.pro_img, use_column_width=True)
            f = st.file_uploader("Nahrát vlastní foto:", type=["jpg", "png"])
            if f: st.session_state.pro_img = Image.open(f).convert("RGB")

        if st.button("🖨️ GENEROVAT PDF"):
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
            st.download_button(f"📥 PDF {nazev}", buf.getvalue(), f"{clean_filename(nazev)}.pdf")

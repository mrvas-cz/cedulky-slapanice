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

st.set_page_config(page_title="PRO Cedulkovač Farma + AI", layout="wide")

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

# --- GEMINI AI PRO TEXTY & DUCKDUCKGO PRO FOTKU ---
def get_ai_plant_data(query, api_key):
    img_url = None
    ai_points = []
    
    # 1. ZÍSKÁNÍ TEXTU PŘES GOOGLE GEMINI
    try:
        genai.configure(api_key=api_key)
        # Používáme rychlý a levný model (zdarma)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Jsi profesionální zahradník, šlechtitel a marketingový expert.
        Pro rostlinu nebo specifickou odrůdu '{query}' mi napiš přesně 12 faktů, 
        které zajímají zákazníky (chuť, výnos, odolnost, nároky na slunce, ranost, atd.).
        
        PRAVIDLA:
        1. Každý bod musí být extrémně stručný, maximálně 4 až 7 slov.
        2. Piš pouze česky.
        3. Piš každý bod na nový řádek.
        4. Nepoužívej žádné odrážky (pomlčky, hvězdičky), číslování, ani žádný úvodní nebo závěrečný text. Jen čisté věty.
        """
        
        response = model.generate_content(prompt)
        # Rozsekání odpovědi na řádky a vyčištění
        lines = response.text.strip().split('\n')
        for line in lines:
            clean_line = line.replace("*", "").replace("-", "").strip()
            if len(clean_line) > 5:
                ai_points.append(clean_line)
                
    except Exception as e:
        st.error(f"Chyba při komunikaci s umělou inteligencí. Zkontrolujte API klíč. Detail: {e}")
        return [], None

    # 2. ZÍSKÁNÍ FOTKY PŘES DUCKDUCKGO
    try:
        with DDGS(timeout=10) as ddgs:
            img_results = list(ddgs.images(f"{query} plant fruit detail high quality", max_results=1))
            if img_results: img_url = img_results[0]['image']
    except:
        st.warning("Fotku se nepodařilo najít. Můžete nahrát vlastní.")

    return ai_points[:12], img_url

# --- STREAMLIT UI ---
# Postranní panel pro API klíč
with st.sidebar:
    st.header("⚙️ Nastavení AI")
    api_key = st.text_input("Zadejte váš Google Gemini API klíč:", type="password")
    st.markdown("[Získat API klíč zdarma zde](https://aistudio.google.com/app/apikey)")
    st.info("Klíč je potřeba k tomu, aby aplikace mohla používat chytrou umělou inteligenci pro psaní textů.")

st.title("🤖 PRO Cedulkovač: Poháněno umělou inteligencí")
st.write("Díky Google Gemini získáte přesné, české a odborné informace k jakékoliv zahraniční i tuzemské odrůdě.")

if 'catalog_options' not in st.session_state: st.session_state.catalog_options = []
if 'pro_img' not in st.session_state: st.session_state.pro_img = None

nazev = st.text_input("Zadejte název sazenice/odrůdy (např. Paprika Kápia, Rajče Sungold F1):")

if st.button("✨ Vygenerovat data přes AI"):
    if not api_key:
        st.error("Nejprve vlevo vložte svůj Gemini API klíč!")
    elif nazev:
        with st.spinner('Umělá inteligence analyzuje odrůdu a píše texty...'):
            options, img = get_ai_plant_data(nazev, api_key)
            if options:
                st.session_state.catalog_options = options
            if img:
                try:
                    resp = requests.get(img, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                    st.session_state.pro_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                except: st.session_state.pro_img = None
    else: st.warning("Zadejte název.")

st.markdown("---")

if st.session_state.catalog_options:
    st.subheader("📋 Výběr AI bodů na cedulku")
    
    default_sel = st.session_state.catalog_options[:4] if len(st.session_state.catalog_options) >=4 else st.session_state.catalog_options
    selected_points = st.multiselect("Zde jsou data z AI. Vyberte 4 nejlepší:", st.session_state.catalog_options, default=default_sel)

    if len(selected_points) == 4:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.caption("Finální úprava textů (můžete cokoliv přepsat):")
            e1 = st.text_input("1. bod", value=selected_points[0])
            e2 = st.text_input("2. bod", value=selected_points[1])
            e3 = st.text_input("3. bod", value=selected_points[2])
            e4 = st.text_input("4. bod", value=selected_points[3])
        
        with c2:
            if st.session_state.pro_img:
                st.image(st.session_state.pro_img, use_column_width=True)
            new_img = st.file_uploader("Nahradit fotkou z počítače:", type=["jpg", "png"])
            if new_img: st.session_state.pro_img = Image.open(new_img).convert("RGB")

        if st.button("🖨️ GENEROVAT AI PDF"):
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

                f_size = 120
                f_t = ImageFont.truetype(font_p, f_size)
                while d.textlength(name.upper(), font=f_t) > (L_W - 140):
                    f_size -= 5
                    f_t = ImageFont.truetype(font_p, f_size)
                d.text((L_W//2, y + 40), name.upper(), fill="#004D40", anchor="mm", font=f_t)
                y += 140

                if img:
                    th = int(L_H * 0.41)
                    tw = int(th * (img.width / img.height))
                    if tw > L_W - 180: tw = L_W - 180; th = int(tw / (img.width / img.height))
                    lbl.paste(img.resize((tw, th), Image.Resampling.LANCZOS), ((L_W - tw) // 2, y))
                    y += th + 55
                else: y += 350

                f_b = ImageFont.truetype(font_p, 48)
                for p in pts:
                    d.text((120, y), f"• {p[:60]}", fill="#333333", font=f_b)
                    y += 75

                bx_w, bx_h = 420, 160
                bx_x, bx_y = (L_W - bx_w)//2, L_H - 230
                d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="#004D40", width=14)
                d.text((bx_x + bx_w + 35, bx_y + 85), "Kč", fill="black", anchor="lm", font=ImageFont.truetype(font_p, 100))
                return lbl

            final = draw_label(nazev, st.session_state.pro_img, [e1, e2, e3, e4])
            canvas.paste(final, (0, 0)); canvas.paste(final, (L_W, 0))
            canvas.paste(final, (0, L_H)); canvas.paste(final, (L_W, L_H))
            st.image(canvas, use_column_width=True)
            buf = io.BytesIO()
            canvas.save(buf, format="PDF")
            st.download_button(f"📥 STÁHNOUT PDF: {nazev}", buf.getvalue(), f"{clean_filename(nazev)}.pdf")

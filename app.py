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

# --- ODOLNÉ DOHLEDÁVÁNÍ DAT ---
def get_scored_catalog_data(query):
    all_findings = []
    img_url = None
    
    try:
        with DDGS(timeout=10) as ddgs:
            # 1. Hledání textu
            search_query = f"{query} popis odrůdy pěstování"
            results = list(ddgs.text(search_query, max_results=5))
            time.sleep(0.5) # Malá pauza proti limitům
            
            for r in results:
                sentences = re.split(r'(?<=[.!?]) +', r['body'])
                for s in sentences:
                    s = s.strip().replace("...", "")
                    if 15 < len(s) < 95:
                        score = 0
                        pro_keywords = {"výnos": 5, "rezist": 8, "chuť": 6, "aroma": 6, "F1": 10, "SHU": 10, "raná": 7}
                        for kw, val in pro_keywords.items():
                            if kw in s.lower(): score += val
                        if any(char.isdigit() for char in s): score += 3
                        if score > 2:
                            all_findings.append({"text": s, "score": score})

            # 2. Hledání obrázku (samostatný try-except blok)
            try:
                time.sleep(0.5) # Další pauza
                img_results = list(ddgs.images(f"{query} plod detail", max_results=1))
                if img_results: img_url = img_results[0]['image']
            except Exception as e:
                st.warning("Obrázek se nepodařilo automaticky dohledat (limit vyhledávače).")
    
    except Exception as e:
        st.error(f"Vyhledávač je dočasně přetížen. Použijte prosím univerzální body nebo zkuste to za chvíli.")

    # Seřazení a filtrace
    unique_findings = []
    seen = set()
    for item in sorted(all_findings, key=lambda x: x['score'], reverse=True):
        clean_s = item['text'][:65]
        if clean_s.lower() not in seen:
            unique_findings.append(clean_s)
            seen.add(clean_s.lower())
    
    # Záložní profesionální body (aby aplikace nikdy nezůstala prázdná)
    backups = [
        "Špičková odrůda s vysokou výtěžností",
        "Vynikající chuťové vlastnosti a aroma",
        "Odolná sazenice s pevným kořenovým balem",
        "Vhodné pro profesionální i hobby pěstitele",
        "Tradiční kvalita z našich skleníků",
        "Bohatý zdroj vitamínů a minerálů"
    ]
    while len(unique_findings) < 10:
        unique_findings.append(backups[len(unique_findings) % len(backups)])
            
    return unique_findings[:12], img_url

# --- STREAMLIT UI ---
st.title("🌿 Profesionální generátor cedulek 3.0")

if 'catalog_options' not in st.session_state: st.session_state.catalog_options = []
if 'pro_img' not in st.session_state: st.session_state.pro_img = None

nazev = st.text_input("Zadejte název odrůdy:", placeholder="Např. Rajče Bejbino F1")

if st.button("🔍 Provést analýzu"):
    if nazev:
        with st.spinner('Prohledávám databáze...'):
            options, img = get_scored_catalog_data(nazev)
            st.session_state.catalog_options = options
            if img:
                try:
                    resp = requests.get(img, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                    st.session_state.pro_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                except: st.session_state.pro_img = None
    else: st.error("Zadejte název.")

st.markdown("---")

if st.session_state.catalog_options:
    st.subheader("📋 Parametry cedulky")
    
    default_sel = st.session_state.catalog_options[:4]
    selected_points = st.multiselect("Vyberte 4 body:", st.session_state.catalog_options, default=default_sel)

    if len(selected_points) == 4:
        c1, c2 = st.columns([2, 1])
        with c1:
            e1 = st.text_input("1.", value=selected_points[0])
            e2 = st.text_input("2.", value=selected_points[1])
            e3 = st.text_input("3.", value=selected_points[2])
            e4 = st.text_input("4.", value=selected_points[3])
        
        with c2:
            if st.session_state.pro_img:
                st.image(st.session_state.pro_img, use_column_width=True)
            new_img = st.file_uploader("Nahrát vlastní foto:", type=["jpg", "png"])
            if new_img: st.session_state.pro_img = Image.open(new_img).convert("RGB")

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
            st.download_button(f"📥 PDF {nazev}", buf.getvalue(), f"{clean_filename(nazev)}.pdf")

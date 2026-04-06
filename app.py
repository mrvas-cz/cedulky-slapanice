import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import requests
import urllib.request
import unicodedata
import re
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

# --- PROFESIONÁLNÍ ANALÝZA DAT ---
def get_scored_catalog_data(query):
    all_findings = []
    img_url = None
    
    with DDGS() as ddgs:
        # Hledáme v katalozích a odborných popisech
        search_query = f"{query} popis odrůdy charakteristika pěstování"
        results = list(ddgs.text(search_query, max_results=8))
        
        for r in results:
            snippet = r['body']
            # Rozdělení na věty a čištění
            sentences = re.split(r'(?<=[.!?]) +', snippet)
            for s in sentences:
                s = s.strip().replace("...", "")
                if len(s) < 15 or len(s) > 90: continue
                
                # Bodování relevance (profesionální klíčová slova)
                score = 0
                pro_keywords = {
                    "výnos": 5, "rezistentní": 8, "odrůda": 4, "chuť": 6, "aroma": 6,
                    "raná": 7, "pozdní": 7, "výška": 5, "plod": 4, "F1": 10, "SHU": 10,
                    "přímý konzum": 5, "skladovatelnost": 6, "stanoviště": 4, "silice": 7
                }
                for kw, value in pro_keywords.items():
                    if kw in s.lower(): score += value
                
                # Bonus za čísla (technické parametry)
                if any(char.isdigit() for char in s): score += 3
                
                if score > 2:
                    all_findings.append({"text": s, "score": score})

        # Hledání kvalitní fotografie (plod/detail)
        img_results = list(ddgs.images(f"{query} odrůda plod", max_results=1))
        if img_results: img_url = img_results[0]['image']

    # Seřazení podle skóre a odstranění duplicit
    unique_findings = []
    seen = set()
    for item in sorted(all_findings, key=lambda x: x['score'], reverse=True):
        short_text = item['text'][:60] # Prevence přetečení
        if short_text.lower() not in seen:
            unique_findings.append(short_text)
            seen.add(short_text.lower())
            
    return unique_findings[:12], img_url

# --- STREAMLIT UI ---
st.title("🌿 Profesionální generátor cedulek")
st.write("Automatizovaný sběr dat z odborných katalogů a šlechtitelských webů.")

if 'catalog_options' not in st.session_state: st.session_state.catalog_options = []
if 'pro_img' not in st.session_state: st.session_state.pro_img = None

nazev = st.text_input("Zadejte přesný název odrůdy/rostliny:", placeholder="Např. Rajče Bejbino F1")

if st.button("🔍 Provést odbornou analýzu"):
    if nazev:
        with st.spinner('Prohledávám šlechtitelské databáze...'):
            options, img = get_scored_catalog_data(nazev)
            st.session_state.catalog_options = options
            if img:
                try:
                    resp = requests.get(img, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                    st.session_state.pro_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                except: st.session_state.pro_img = None
    else: st.error("Zadejte název pro analýzu.")

st.markdown("---")

if st.session_state.catalog_options:
    st.subheader("📋 Výběr parametrů pro zákazníka")
    st.info("První 4 jsou vybrány jako nejrelevantnější. Můžete je libovolně zaměnit.")
    
    # Automatický výběr prvních 4
    default_selection = st.session_state.catalog_options[:4]
    selected_points = st.multiselect(
        "Vyberte/Změňte body (celkem 4):", 
        options=st.session_state.catalog_options,
        default=default_selection
    )

    if len(selected_points) == 4:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write("🖋️ **Finální korekce textu:**")
            edit1 = st.text_input("1. bod", value=selected_points[0])
            edit2 = st.text_input("2. bod", value=selected_points[1])
            edit3 = st.text_input("3. bod", value=selected_points[2])
            edit4 = st.text_input("4. bod", value=selected_points[3])
        
        with col2:
            if st.session_state.pro_img:
                st.image(st.session_state.pro_img, caption="Katalogové foto", use_column_width=True)
            new_img = st.file_uploader("Vlastní foto (nahradí vyhledané):", type=["jpg", "png"])
            if new_img: st.session_state.pro_img = Image.open(new_img).convert("RGB")

        if st.button("🖨️ GENEROVAT PROFESIONÁLNÍ PDF"):
            # Parametry A4 a fonty
            A4_W, A4_H = 2480, 3508
            L_W, L_H = A4_W // 2, A4_H // 2
            canvas = Image.new('RGB', (A4_W, A4_H), 'white')
            font_p = get_czech_font()

            def draw_pro_label(name, img, points):
                lbl = Image.new('RGB', (L_W, L_H), 'white')
                d = ImageDraw.Draw(lbl)
                
                # Logo Farmy
                y = 60
                try:
                    logo = Image.open("logo txt farma.JPG").convert("RGBA")
                    lw = L_W - 320
                    lh = int(lw * (logo.height / logo.width))
                    logo = logo.resize((lw, lh), Image.Resampling.LANCZOS)
                    lbl.paste(logo, ((L_W - lw) // 2, y), logo)
                    y += lh + 30
                except: y += 100

                # Název (Bold, tmavě zelená)
                f_size = 120
                f_t = ImageFont.truetype(font_p, f_size)
                while d.textlength(name.upper(), font=f_t) > (L_W - 140):
                    f_size -= 5
                    f_t = ImageFont.truetype(font_p, f_size)
                d.text((L_W//2, y + 40), name.upper(), fill="#004D40", anchor="mm", font=f_t)
                y += 130

                # Fotka
                if img:
                    th = int(L_H * 0.42)
                    asp = img.width / img.height
                    tw = int(th * asp)
                    if tw > L_W - 180: tw = L_W - 180; th = int(tw / asp)
                    res = img.resize((tw, th), Image.Resampling.LANCZOS)
                    lbl.paste(res, ((L_W - tw) // 2, y))
                    y += th + 50
                else: y += 350

                # Textové body
                f_b = ImageFont.truetype(font_p, 48)
                for p in points:
                    d.text((120, y), f"• {p}", fill="#333333", font=f_b)
                    y += 75

                # Cenový blok
                bx_w, bx_h = 420, 160
                bx_x, bx_y = (L_W - bx_w)//2, L_H - 230
                d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="#004D40", width=14)
                d.text((bx_x + bx_w + 35, bx_y + 85), "Kč", fill="black", anchor="lm", font=ImageFont.truetype(font_p, 100))
                
                d.rectangle([0, 0, L_W-2, L_H-2], outline="#E0E0E0", width=2)
                return lbl

            final_label = draw_pro_label(nazev, st.session_state.pro_img, [edit1, edit2, edit3, edit4])
            canvas.paste(final_label, (0, 0)); canvas.paste(final_label, (L_W, 0))
            canvas.paste(final_label, (0, L_H)); canvas.paste(final_label, (L_W, L_H))
            
            st.image(canvas, use_column_width=True)
            buf = io.BytesIO()
            canvas.save(buf, format="PDF")
            st.download_button(f"📥 STÁHNOUT PDF: {nazev}", buf.getvalue(), f"{clean_filename(nazev)}.pdf")
    else:
        st.warning("Pro generování PDF musíte mít vybrány přesně 4 body.")

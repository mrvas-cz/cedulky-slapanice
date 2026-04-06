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
from deep_translator import GoogleTranslator

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

# --- MEZINÁRODNÍ DOHLEDÁVÁNÍ DAT S PŘEKLADEM ---
def get_scored_catalog_data(query):
    all_findings = []
    img_url = None
    translator = GoogleTranslator(source='auto', target='cs')
    
    try:
        with DDGS(timeout=10) as ddgs:
            # 1. ČESKÉ HLEDÁNÍ
            cz_query = f"{query} popis odrůdy vlastnosti pěstování"
            cz_results = list(ddgs.text(cz_query, max_results=3))
            time.sleep(0.5)
            
            # 2. MEZINÁRODNÍ HLEDÁNÍ (Nizozemí, Německo, Itálie přes globální EN výrazy)
            en_query = f"{query} variety characteristics yield resistance seed"
            en_results = list(ddgs.text(en_query, max_results=4))
            time.sleep(0.5)
            
            combined_results = cz_results + en_results
            
            for r in combined_results:
                sentences = re.split(r'(?<=[.!?]) +', r['body'])
                for s in sentences:
                    s = s.strip().replace("...", "")
                    if 15 < len(s) < 120:
                        score = 0
                        # Klíčová slova: CZ + EN + DE (univerzální kořeny)
                        pro_keywords = {
                            "výnos": 5, "yield": 5, "ertrag": 5,
                            "rezist": 8, "resist": 8, 
                            "chuť": 6, "flavor": 6, "geschmack": 6, "taste": 6,
                            "aroma": 6, "f1": 10, "shu": 10, "brix": 8,
                            "raná": 7, "early": 7, "früh": 7,
                            "odol": 6, "tolerant": 6
                        }
                        
                        s_lower = s.lower()
                        for kw, val in pro_keywords.items():
                            if kw in s_lower: score += val
                        if any(char.isdigit() for char in s): score += 3
                        
                        if score > 2:
                            all_findings.append({"text": s, "score": score})

            # 3. HLEDÁNÍ MEZINÁRODNÍHO OBRÁZKU
            try:
                time.sleep(0.5)
                img_results = list(ddgs.images(f"{query} variety fruit detail", max_results=1))
                if img_results: img_url = img_results[0]['image']
            except: pass
            
    except Exception as e:
        st.error("Vyhledávač narazil na limit. Nabízím univerzální šlechtitelská data.")

    # Seřazení podle skóre
    sorted_findings = sorted(all_findings, key=lambda x: x['score'], reverse=True)
    
    unique_findings = []
    seen = set()
    
    # Překlad a čištění (jen u těch nejlepších, abychom šetřili čas)
    for item in sorted_findings:
        if len(unique_findings) >= 12: break
        
        original_text = item['text']
        try:
            # Automatický překlad do CZ (pokud to už není česky, pozná si to sám)
            cz_text = translator.translate(original_text)
        except:
            cz_text = original_text # Záchrana při selhání překladače
            
        clean_s = cz_text[:65].strip()
        if clean_s.lower() not in seen and len(clean_s) > 10:
            unique_findings.append(clean_s)
            seen.add(clean_s.lower())
    
    # Záložní data z katalogů, pokud se nic nenajde
    backups = [
        "Špičková mezinárodní odrůda s vysokým výnosem",
        "Vynikající chuťový profil a stabilní kvalita",
        "Silná rezistence vůči běžným chorobám",
        "Výborná adaptabilita pro naše klimatické podmínky",
        "Raná a spolehlivá sklizeň plodů",
        "Osvědčená genetika od profesionálních šlechtitelů"
    ]
    while len(unique_findings) < 10:
        unique_findings.append(backups[len(unique_findings) % len(backups)])
            
    return unique_findings[:12], img_url

# --- STREAMLIT UI ---
st.title("🌍 PRO Cedulkovač: Zahraniční katalogy")
st.write("Automatizovaný sběr dat z evropských šlechtitelských databází s překladem do češtiny.")

if 'catalog_options' not in st.session_state: st.session_state.catalog_options = []
if 'pro_img' not in st.session_state: st.session_state.pro_img = None

nazev = st.text_input("Zadejte název odrůdy (např. San Marzano, Gourmansun F1):")

if st.button("🔍 Prohledat mezinárodní weby"):
    if nazev:
        with st.spinner('Analyzuji weby a překládám data do češtiny...'):
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
    st.subheader("📋 Přeložené parametry odrůdy")
    
    default_sel = st.session_state.catalog_options[:4]
    selected_points = st.multiselect("Vyberte 4 body na cedulku:", st.session_state.catalog_options, default=default_sel)

    if len(selected_points) == 4:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.caption("Texty jsou přeloženy automatem. Zde je můžete učesat:")
            e1 = st.text_input("1. bod", value=selected_points[0])
            e2 = st.text_input("2. bod", value=selected_points[1])
            e3 = st.text_input("3. bod", value=selected_points[2])
            e4 = st.text_input("4. bod", value=selected_points[3])
        
        with c2:
            if st.session_state.pro_img:
                st.image(st.session_state.pro_img, use_column_width=True)
            new_img = st.file_uploader("Nahradit fotkou z počítače:", type=["jpg", "png"])
            if new_img: st.session_state.pro_img = Image.open(new_img).convert("RGB")

        if st.button("🖨️ GENEROVAT PDF TISKOVÁ DATA"):
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
                    # Rychlé odstranění zbytků případných cizích znaků z překladu
                    clean_p = p[:60].replace("&#39;", "'").replace("&amp;", "&")
                    d.text((120, y), f"• {clean_p}", fill="#333333", font=f_b)
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

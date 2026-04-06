import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import requests
import urllib.request
import re

# Knihovna pro vyhledávání obrázků (DuckDuckGo je zdarma a spolehlivý)
from duckduckgo_search import DDGS

st.set_page_config(page_title="Cedulkovač Šlapanice", layout="centered")

st.title("🚜 Šlapanický Cedulkovač 2.0")
st.write("Napište název sazenice a já prohledám weby šlechtitelů a zahradníků pro nejlepší fotku!")

@st.cache_resource
def get_czech_font():
    font_path = "Roboto-Bold.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
        urllib.request.urlretrieve(url, font_path)
    return font_path

# --- INTELIGENTNÍ VYHLEDÁVÁNÍ FOTEK A INFO ---
def search_web_data(query):
    img_url = None
    # Zkusíme najít fotku přes DuckDuckGo (hledá na webech zahradnictví)
    try:
        with DDGS() as ddgs:
            # Hledáme obrázek - přidáme klíčová slova pro lepší výsledek
            search_query = f"{query} sazenice plod detail"
            results = list(ddgs.images(search_query, max_results=1))
            if results:
                img_url = results[0]['image']
    except Exception as e:
        st.error(f"Chyba při hledání obrázku: {e}")

    # Jednoduché univerzální body pro sazenice (pokud chceme automatiku)
    # Pro trh je lepší mít tyto fixní body, které sedí na 90% sazenic
    bullets = [
        "• Kvalitní šlechtěná odrůda",
        "• Silný kořenový systém",
        "• Určeno pro okamžitou výsadbu",
        "• Vypěstováno s láskou u nás"
    ]
    
    return bullets, img_url

# --- ROZHRANÍ ---
nazev_produktu = st.text_input("Zadej název (např. Rajče Tornado, Paprika PCR, Máta):", "")

if nazev_produktu:
    with st.spinner('🔍 Prohledávám weby šlechtitelů...'):
        bullets, img_url = search_web_data(nazev_produktu)
        
        uploaded_img = None
        if img_url:
            try:
                # Ošetření proti blokování botů
                headers = {'User-Agent': 'Mozilla/5.0'}
                resp = requests.get(img_url, headers=headers, timeout=10)
                uploaded_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            except:
                st.warning("Obrázek ze šlechtitelského webu se nepodařilo přímo načíst.")

        if not uploaded_img:
            st.info("Nahrajte prosím fotku ručně, pokud se mi ji nepodařilo najít.")
            f = st.file_uploader("Vložit vlastní fotku:", type=["jpg", "png"])
            if f: uploaded_img = Image.open(f).convert("RGB")

        if uploaded_img:
            A4_W, A4_H = 2480, 3508
            LABEL_W, LABEL_H = A4_W // 2, A4_H // 2
            canvas = Image.new('RGB', (A4_W, A4_H), 'white')
            font_p = get_czech_font()

            def create_label():
                lbl = Image.new('RGB', (LABEL_W, LABEL_H), 'white')
                d = ImageDraw.Draw(lbl)
                
                # 1. LOGO FARMY
                try:
                    logo = Image.open("logo txt farma.JPG").convert("RGBA")
                    lw = LABEL_W - 150
                    lh = int(lw * (logo.height / logo.width))
                    logo = logo.resize((lw, lh), Image.Resampling.LANCZOS)
                    lbl.paste(logo, ((LABEL_W - lw) // 2, 30), logo)
                    y = 30 + lh + 30
                except:
                    y = 120

                # 2. NÁZEV (Zvýrazněný)
                f_t = ImageFont.truetype(font_p, 120)
                d.text((LABEL_W//2, y + 50), nazev_produktu.upper(), fill="#2E7D32", anchor="mm", font=f_t)
                y += 130

                # 3. FOTKA
                target_h = int(LABEL_H * 0.38)
                asp = uploaded_img.width / uploaded_img.height
                tw = int(target_h * asp)
                if tw > LABEL_W - 100:
                    tw = LABEL_W - 100
                    target_h = int(tw / asp)
                
                img_res = uploaded_img.resize((tw, target_h), Image.Resampling.LANCZOS)
                lbl.paste(img_res, ((LABEL_W - tw) // 2, y))
                y += target_h + 40

                # 4. BODY (4 body, max 5 slov)
                f_b = ImageFont.truetype(font_p, 55)
                for b in bullets:
                    d.text((80, y), b, fill="#444444", font=f_b)
                    y += 70

                # 5. RÁMEČEK NA CENU (DOLE)
                bx_w, bx_h = 420, 160
                bx_x, bx_y = (LABEL_W - bx_w)//2, LABEL_H - 220
                d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="black", width=8)
                d.text((bx_x + bx_w + 20, bx_y + 80), "Kč", fill="black", anchor="lm", font=f_t)
                
                d.rectangle([0, 0, LABEL_W-2, LABEL_H-2], outline="#DDDDDD", width=2)
                return lbl

            final_lbl = create_label()
            canvas.paste(final_lbl, (0, 0))
            canvas.paste(final_lbl, (LABEL_W, 0))
            canvas.paste(final_lbl, (0, LABEL_H))
            canvas.paste(final_lbl, (LABEL_W, LABEL_H))

            st.image(canvas, use_column_width=True)
            buf = io.BytesIO()
            canvas.save(buf, format="PDF")
            st.download_button("📥 STÁHNOUT PDF K TISKU", buf.getvalue(), "cedulky.pdf", "application/pdf")

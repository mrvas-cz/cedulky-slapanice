import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import requests
import urllib.request
from duckduckgo_search import DDGS

st.set_page_config(page_title="Cedulkovač Šlapanice", layout="centered")

# --- STYLIZACE ---
st.markdown("""
    <style>
    .main { background-color: #f9f9f9; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #2E7D32; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚜 Šlapanický Cedulkovač 2.1")
st.info("Tip: Nejlepší cedulky jsou z vlastních fotek. Pokud fotku nemáte, zkusím ji najít.")

@st.cache_resource
def get_czech_font():
    font_path = "Roboto-Bold.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
        urllib.request.urlretrieve(url, font_path)
    return font_path

def search_image(query):
    try:
        with DDGS() as ddgs:
            # Hledáme konkrétnější dotaz pro zahradnictví
            search_query = f"{query} rostlina sazenice"
            results = list(ddgs.images(search_query, max_results=1))
            if results:
                return results[0]['image']
    except:
        return None
    return None

# --- VSTUPY ---
nazev_produktu = st.text_input("1. Zadejte název sazenice (např. Celer listový):", "")
uploaded_file = st.file_uploader("2. Nahrajte vlastní fotku (volitelné, doporučeno):", type=["jpg", "jpeg", "png"])

if nazev_produktu:
    img_to_use = None
    
    # Rozhodnutí o fotce
    if uploaded_file:
        img_to_use = Image.open(uploaded_file).convert("RGB")
    else:
        with st.spinner('🔍 Hledám nejlepší fotku na webu...'):
            img_url = search_image(nazev_produktu)
            if img_url:
                try:
                    # Předstíráme prohlížeč, abychom nedostali 403
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                    resp = requests.get(img_url, headers=headers, timeout=5)
                    img_to_use = Image.open(io.BytesIO(resp.content)).convert("RGB")
                except:
                    st.warning("Nepodařilo se automaticky stáhnout fotku z webu. Zkuste ji nahrát ručně.")

    if st.button("Vytvořit profesionální cedulky"):
        A4_W, A4_H = 2480, 3508
        LABEL_W, LABEL_H = A4_W // 2, A4_H // 2
        canvas = Image.new('RGB', (A4_W, A4_H), 'white')
        font_p = get_czech_font()

        def create_label(product_name, image):
            lbl = Image.new('RGB', (LABEL_W, LABEL_H), 'white')
            d = ImageDraw.Draw(lbl)
            
            # 1. LOGO
            curr_y = 40
            try:
                logo = Image.open("logo txt farma.JPG").convert("RGBA")
                lw = LABEL_W - 200
                lh = int(lw * (logo.height / logo.width))
                logo = logo.resize((lw, lh), Image.Resampling.LANCZOS)
                lbl.paste(logo, ((LABEL_W - lw) // 2, curr_y), logo)
                curr_y += lh + 40
            except:
                curr_y += 100

            # 2. NÁZEV
            f_t = ImageFont.truetype(font_p, 130)
            d.text((LABEL_W//2, curr_y + 40), product_name.upper(), fill="#1B5E20", anchor="mm", font=f_t)
            curr_y += 140

            # 3. FOTKA (pokud je)
            if image:
                target_h = int(LABEL_H * 0.4)
                asp = image.width / image.height
                tw = int(target_h * asp)
                if tw > LABEL_W - 140:
                    tw = LABEL_W - 140
                    target_h = int(tw / asp)
                img_res = image.resize((tw, target_h), Image.Resampling.LANCZOS)
                lbl.paste(img_res, ((LABEL_W - tw) // 2, curr_y))
                curr_y += target_h + 40
            else:
                curr_y += 300 # Místo pro text bez fotky

            # 4. BODY
            bullets = ["• Špičková šlapanická kvalita", "• Silná a zdravá sazenice", "• Připraveno k okamžité výsadbě", "• Vypěstováno bez chemie"]
            f_b = ImageFont.truetype(font_p, 60)
            for b in bullets:
                d.text((100, curr_y), b, fill="#333333", font=f_b)
                curr_y += 85

            # 5. CENA
            bx_w, bx_h = 450, 160
            bx_x, bx_y = (LABEL_W - bx_w)//2, LABEL_H - 230
            d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="black", width=10)
            d.text((bx_x + bx_w + 30, bx_y + 80), "Kč", fill="black", anchor="lm", font=f_t)
            
            d.rectangle([0, 0, LABEL_W-2, LABEL_H-2], outline="#EEEEEE", width=4)
            return lbl

        final_lbl = create_label(nazev_produktu, img_to_use)
        canvas.paste(final_lbl, (0, 0))
        canvas.paste(final_lbl, (LABEL_W, 0))
        canvas.paste(final_lbl, (0, LABEL_H))
        canvas.paste(final_lbl, (LABEL_W, LABEL_H))

        st.image(canvas, use_column_width=True)
        buf = io.BytesIO()
        canvas.save(buf, format="PDF")
        st.download_button("📥 STÁHNOUT PDF (4 CEDULKY NA A4)", buf.getvalue(), f"cedulky_{nazev_produktu}.pdf", "application/pdf")

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import requests
import urllib.request
import unicodedata
from duckduckgo_search import DDGS

st.set_page_config(page_title="Cedulkovač Šlapanice", layout="centered")

st.title("🚜 Šlapanický Cedulkovač 2.3")
st.info("Verze s automatickým pojmenováním souboru PDF.")

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
    while font.getlength(text) > (max_width - 120) and size > 40:
        size -= 5
        font = ImageFont.truetype(font_path, size)
    return font

def clean_filename(text):
    """Převede název na bezpečné jméno souboru bez háčků a mezer."""
    nfkd_form = unicodedata.normalize('NFKD', text)
    only_ascii = nfkd_form.encode('ASCII', 'ignore').decode('utf-8')
    return only_ascii.replace(" ", "_").upper()

def search_image(query):
    try:
        with DDGS() as ddgs:
            search_query = f"{query} rostlina sazenice"
            results = list(ddgs.images(search_query, max_results=1))
            if results: return results[0]['image']
    except: return None
    return None

# --- VSTUPY ---
nazev_produktu = st.text_input("1. Název sazenice:", "")
uploaded_file = st.file_uploader("2. Nahrajte vlastní fotku (volitelné):", type=["jpg", "jpeg", "png"])

if nazev_produktu:
    img_to_use = None
    if uploaded_file:
        img_to_use = Image.open(uploaded_file).convert("RGB")
    else:
        with st.spinner('🔍 Hledám fotku...'):
            img_url = search_image(nazev_produktu)
            if img_url:
                try:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    resp = requests.get(img_url, headers=headers, timeout=5)
                    img_to_use = Image.open(io.BytesIO(resp.content)).convert("RGB")
                except: pass

    if st.button("Vytvořit cedulky"):
        A4_W, A4_H = 2480, 3508
        LABEL_W, LABEL_H = A4_W // 2, A4_H // 2
        canvas = Image.new('RGB', (A4_W, A4_H), 'white')
        font_p = get_czech_font()

        def create_label(product_name, image):
            lbl = Image.new('RGB', (LABEL_W, LABEL_H), 'white')
            d = ImageDraw.Draw(lbl)
            product_name = product_name.upper()
            
            curr_y = 40
            try:
                logo = Image.open("logo txt farma.JPG").convert("RGBA")
                lw = LABEL_W - 250
                lh = int(lw * (logo.height / logo.width))
                logo = logo.resize((lw, lh), Image.Resampling.LANCZOS)
                lbl.paste(logo, ((LABEL_W - lw) // 2, curr_y), logo)
                curr_y += lh + 30
            except: curr_y += 100

            f_t = get_fitting_font(product_name, LABEL_W, 130, font_p)
            d.text((LABEL_W//2, curr_y + 50), product_name, fill="#1B5E20", anchor="mm", font=f_t)
            curr_y += 140

            if image:
                target_h = int(LABEL_H * 0.38)
                asp = image.width / image.height
                tw = int(target_h * asp)
                if tw > LABEL_W - 150:
                    tw = LABEL_W - 150
                    target_h = int(tw / asp)
                img_res = image.resize((tw, target_h), Image.Resampling.LANCZOS)
                lbl.paste(img_res, ((LABEL_W - tw) // 2, curr_y))
                curr_y += target_h + 40
            else: curr_y += 300

            bullets = ["• Špičková šlapanická kvalita", "• Silná a zdravá sazenice", "• Připraveno k výsadbě", "• Vypěstováno s láskou"]
            f_b = ImageFont.truetype(font_p, 55)
            for b in bullets:
                d.text((100, curr_y), b, fill="#333333", font=f_b)
                curr_y += 75

            bx_w, bx_h = 420, 150
            bx_x, bx_y = (LABEL_W - bx_w)//2, LABEL_H - 220
            d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="black", width=10)
            f_kc = ImageFont.truetype(font_p, 100)
            d.text((bx_x + bx_w + 30, bx_y + 75), "Kč", fill="black", anchor="lm", font=f_kc)
            
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
        
        # --- DYNAMICKÝ NÁZEV SOUBORU ---
        safe_name = clean_filename(nazev_produktu)
        st.download_button(
            label=f"📥 STÁHNOUT PDF (cedulky_{safe_name}.pdf)",
            data=buf.getvalue(),
            file_name=f"cedulky_{safe_name}.pdf",
            mime="application/pdf"
        )

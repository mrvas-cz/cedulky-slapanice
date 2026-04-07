import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request
import unicodedata
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

# --- AI VYHLEDÁVÁNÍ PODLE VAŠÍ STRUKTURY ---
def get_structured_ai_info(query):
    try:
        with DDGS() as ddgs:
            prompt = f"""
            Jsi expert na zahradnictví. Vyhledej informace o odrůdě: {query}.
            Vytvoř výstup přesně v těchto 4 řádcích (pokud údaj neexistuje, napiš "dle odrůdy"):
            
            Řádek 1: Stanoviště (slunce/stín) | Zálivka (malá/střední/velká)
            Řádek 2: Spon (např. 40x50 cm) | Výška (cm)
            Řádek 3: Plod (barva, chuť) | Hmotnost (g)
            Řádek 4: Použití (kuchyně/přímý konzum) | Zajímavost/účinky/tip
            
            Jako bonus přidej jeden odstavec s podrobným popisem odrůdy.
            Piš česky.
            """
            response = ddgs.chat(prompt, model='gpt-4o-mini')
            return response if isinstance(response, str) else "".join(list(response))
    except:
        return "Chyba připojení k AI. Zadejte prosím údaje ručně nebo zkuste znovu."

# --- UI ---
st.title("🌿 PRO Cedulkovač 7.0 (Strukturovaný)")

if 'ai_raw' not in st.session_state: st.session_state.ai_raw = ""
if 'pro_img' not in st.session_state: st.session_state.pro_img = None

nazev = st.text_input("Název odrůdy:", placeholder="např. Rajče Bejbino F1")

if st.button("🔍 Vyhledat technické parametry", type="primary"):
    if nazev:
        with st.spinner('AI dohledává stanoviště, spon a plody...'):
            st.session_state.ai_raw = get_structured_ai_info(nazev)
    else:
        st.warning("Zadejte název.")

st.markdown("---")

if st.session_state.ai_raw:
    col_a, col_b = st.columns([1, 1])
    
    with col_a:
        st.subheader("📖 Výsledek hledání")
        st.text_area("Informace od AI (zkopírujte do polí níže):", value=st.session_state.ai_raw, height=300)
        
    with col_b:
        st.subheader("🖼️ Fotografie")
        search_query = nazev.replace(" ", "+")
        st.markdown(f"👉 [Otevřít **Google Obrázky**] (https://www.google.com/search?tbm=isch&q={search_query}+plod+detail)")
        uploaded_file = st.file_uploader("Nahrát fotku:", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            st.session_state.pro_img = Image.open(uploaded_file).convert("RGB")

    st.markdown("---")
    st.subheader("📝 Editace cedulky")
    
    # Rozdělení do vašich 4 řádků
    c1, c2 = st.columns(2)
    with c1:
        row1 = st.text_input("Řádek 1 (Stanoviště | Zálivka)", value="Stanoviště: | Zálivka: ")
        row2 = st.text_input("Řádek 2 (Spon | Výška)", value="Spon: | Výška: ")
    with c2:
        row3 = st.text_input("Řádek 3 (Plod | Hmotnost)", value="Plod: | Hmotnost: ")
        row4 = st.text_input("Řádek 4 (Použití | Zajímavost/Tip)", value="Použití: | Tip: ")

    if st.button("🖨️ GENEROVAT PDF", use_container_width=True):
        if not st.session_state.pro_img:
            st.error("Nezapomeňte nahrát fotku!")
        else:
            A4_W, A4_H = 2480, 3508
            L_W, L_H = A4_W // 2, A4_H // 2
            canvas = Image.new('RGB', (A4_W, A4_H), 'white')
            font_p = get_czech_font()

            def draw_label(name, img, lines):
                lbl = Image.new('RGB', (L_W, L_H), 'white')
                d = ImageDraw.Draw(lbl)
                # Logo
                try:
                    logo = Image.open("logo txt farma.JPG").convert("RGBA")
                    lw = L_W - 320
                    logo = logo.resize((lw, int(lw * (logo.height / logo.width))), Image.Resampling.LANCZOS)
                    lbl.paste(logo, ((L_W - lw) // 2, 60), logo)
                    y = 60 + logo.height + 30
                except: y = 160
                
                # Název
                f_t = ImageFont.truetype(font_p, 110)
                d.text((L_W//2, y + 40), name.upper(), fill="#004D40", anchor="mm", font=f_t)
                y += 140
                
                # Fotka
                th = int(L_H * 0.41); tw = int(th * (img.width / img.height))
                if tw > L_W - 180: tw = L_W - 180; th = int(tw / (img.width / img.height))
                lbl.paste(img.resize((tw, th), Image.Resampling.LANCZOS), ((L_W - tw) // 2, y))
                y += th + 50
                
                # Technické parametry (Vaše 4 řádky)
                f_b = ImageFont.truetype(font_p, 42)
                for line in lines:
                    d.text((100, y), f"• {line[:70]}", fill="#333333", font=f_b)
                    y += 65
                
                # Cena
                bx_w, bx_h = 420, 160; bx_x, bx_y = (L_W - bx_w)//2, L_H - 225
                d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="#004D40", width=14)
                d.text((bx_x + bx_w + 35, bx_y + 85), "Kč", fill="black", anchor="lm", font=ImageFont.truetype(font_p, 100))
                return lbl

            final_label = draw_label(nazev, st.session_state.pro_img, [row1, row2, row3, row4])
            canvas.paste(final_label, (0, 0)); canvas.paste(final_label, (L_W, 0))
            canvas.paste(final_label, (0, L_H)); canvas.paste(final_label, (L_W, L_H))
            
            st.image(canvas, use_column_width=True)
            buf = io.BytesIO()
            canvas.save(buf, format="PDF")
            st.download_button(f"📥 Stáhnout PDF {nazev}", buf.getvalue(), f"{clean_filename(nazev)}.pdf")

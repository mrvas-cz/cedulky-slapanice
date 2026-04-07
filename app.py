import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import requests
import urllib.request
import unicodedata
import re
import google.generativeai as genai

st.set_page_config(page_title="PRO Cedulkovač Farma AI", layout="wide")

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

# --- CHYTRÉ ZÍSKÁVÁNÍ DAT PŘES GEMINI ---
def get_detailed_ai_info(query, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Jsi expert na zahradnictví. Vyhledej detailní informace o odrůdě: {query}.
        Zaměř se na tyto parametry (pokud existují):
        1. U ZELENINY (rajčata, papriky): gramáž plodu (g), typ vzrůstu (tyčkové/keřové/nízké), tvar, barva, chuť, ranost, odolnost.
        2. U BYLINEK: využití v kuchyni, léčivé účinky, zda je to trvalka/letnička, mrazuvzdornost, nároky na slunce.
        3. U OKRASNÝCH: výška, barva květu, doba kvetení.
        
        Vytvoř výstup ve dvou částech:
        ČÁST A: 12 velmi krátkých úderných odrážek (max 6 slov) pro prodejní cedulku.
        ČÁST B: Podrobný odstavec textu o této odrůdě.
        Piš česky.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Chyba AI: {e}"

# --- UI ---
with st.sidebar:
    st.header("⚙️ Nastavení")
    api_key = st.text_input("Vložte váš Gemini API klíč:", type="password")
    st.info("Klíč získáte zdarma na: aistudio.google.com/app/apikey")

st.title("🌿 Inteligentní Cedulkovač s Google Gemini")

if 'full_info' not in st.session_state: st.session_state.full_info = ""
if 'pro_img' not in st.session_state: st.session_state.pro_img = None

nazev = st.text_input("Zadejte přesný název rostliny/odrůdy:", placeholder="např. Rajče Bejbino F1 nebo Máta peprná")

if st.button("🔍 Vyhledat vše o rostlině", type="primary"):
    if not api_key:
        st.error("Chybí API klíč v bočním panelu!")
    elif nazev:
        with st.spinner('Gemini dohledává technické parametry...'):
            st.session_state.full_info = get_detailed_ai_info(nazev, api_key)
    else:
        st.warning("Zadejte název.")

st.markdown("---")

if st.session_state.full_info:
    col_a, col_b = st.columns([1, 1])
    
    with col_a:
        st.subheader("📖 Co AI zjistila (Náhled dat)")
        # Zobrazení všeho, co AI našla, aby to uživatel mohl jen zkopírovat
        st.text_area("Kompletní informace od Gemini:", value=st.session_state.full_info, height=400)
        
    with col_b:
        st.subheader("🖼️ Odkazy na fotografie")
        st.write("Klikněte na odkaz, vyberte nejhezčí fotku, uložte ji a nahrajte níže:")
        
        # Generování odkazů na vyhledávače
        search_query = nazev.replace(" ", "+")
        st.markdown(f"👉 [Hledat na **Google Images**](https://www.google.com/search?tbm=isch&q={search_query}+fruit+detail)")
        st.markdown(f"👉 [Hledat na **Bing Images**](https://www.bing.com/images/search?q={search_query}+plant)")
        st.markdown(f"👉 [Hledat na **Pinterestu**](https://www.pinterest.com/search/pins/?q={search_query})")
        
        st.markdown("---")
        uploaded_file = st.file_uploader("Nahrát vybranou fotku:", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            st.session_state.pro_img = Image.open(uploaded_file).convert("RGB")
            st.image(st.session_state.pro_img, caption="Nahraná fotka", width=200)

    st.markdown("---")
    st.subheader("📝 3. Finalizace textů na cedulku")
    st.info("Z výše uvedeného náhledu od AI si sem přepište/zkopírujte 4 nejdůležitější body.")
    
    c1, c2 = st.columns(2)
    with c1:
        e1 = st.text_input("Bod 1 (např. Tyčkové, plody 20-30g)", value="")
        e2 = st.text_input("Bod 2 (např. Extrémně sladká chuť)", value="")
    with c2:
        e3 = st.text_input("Bod 3 (např. Odolné k praskání)", value="")
        e4 = st.text_input("Bod 4 (např. Raná, výnosná odrůda)", value="")

    if st.button("🖨️ GENEROVAT PDF K TISKU", use_container_width=True):
        if not st.session_state.pro_img:
            st.error("Před generováním nahrajte prosím obrázek!")
        else:
            A4_W, A4_H = 2480, 3508
            L_W, L_H = A4_W // 2, A4_H // 2
            canvas = Image.new('RGB', (A4_W, A4_H), 'white')
            font_p = get_czech_font()

            def draw_label(name, img, pts):
                lbl = Image.new('RGB', (L_W, L_H), 'white')
                d = ImageDraw.Draw(lbl)
                y = 60
                # Logo
                try:
                    logo = Image.open("logo txt farma.JPG").convert("RGBA")
                    lw = L_W - 320
                    logo = logo.resize((lw, int(lw * (logo.height / logo.width))), Image.Resampling.LANCZOS)
                    lbl.paste(logo, ((L_W - lw) // 2, y), logo)
                    y += logo.height + 30
                except: y += 100
                
                # Název
                f_t = ImageFont.truetype(font_p, 110)
                d.text((L_W//2, y + 40), name.upper(), fill="#004D40", anchor="mm", font=f_t)
                y += 140
                
                # Fotka
                if img:
                    th = int(L_H * 0.41); tw = int(th * (img.width / img.height))
                    if tw > L_W - 180: tw = L_W - 180; th = int(tw / (img.width / img.height))
                    lbl.paste(img.resize((tw, th), Image.Resampling.LANCZOS), ((L_W - tw) // 2, y))
                    y += th + 55
                
                # Body
                f_b = ImageFont.truetype(font_p, 48)
                for p in pts:
                    if p:
                        d.text((120, y), f"• {p[:60]}", fill="#333333", font=f_b)
                        y += 75
                
                # Cena box
                bx_w, bx_h = 420, 160; bx_x, bx_y = (L_W - bx_w)//2, L_H - 225
                d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="#004D40", width=14)
                d.text((bx_x + bx_w + 35, bx_y + 85), "Kč", fill="black", anchor="lm", font=ImageFont.truetype(font_p, 100))
                return lbl

            final_label = draw_label(nazev, st.session_state.pro_img, [e1, e2, e3, e4])
            canvas.paste(final_label, (0, 0)); canvas.paste(final_label, (L_W, 0))
            canvas.paste(final_label, (0, L_H)); canvas.paste(final_label, (L_W, L_H))
            
            st.image(canvas, use_column_width=True)
            buf = io.BytesIO()
            canvas.save(buf, format="PDF")
            st.download_button(f"📥 STÁHNOUT PDF: {nazev}", buf.getvalue(), f"{clean_filename(nazev)}.pdf")

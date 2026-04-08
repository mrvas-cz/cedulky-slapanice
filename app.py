import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request
import unicodedata
import re

st.set_page_config(page_title="PRO Cedulkovač - Smart Import", layout="wide")

@st.cache_resource
def get_czech_font():
    font_path = "Roboto-Bold.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
            urllib.request.urlretrieve(url, font_path)
        except: return None
    return font_path

def clean_filename(text):
    nfkd_form = unicodedata.normalize('NFKD', text)
    return nfkd_form.encode('ASCII', 'ignore').decode('utf-8').replace(" ", "_").upper()

# --- HLAVNÍ ROZHRANÍ ---
st.title("🌿 PRO Cedulkovač - Smart AI Import")
st.write("Stabilní verze bez výpadků. Využijte svou oblíbenou AI (Gemini/ChatGPT) a vložte hotová data.")

col_ai, col_app = st.columns([1.2, 1])

with col_ai:
    st.subheader("1. Získejte data z vaší AI")
    st.info("Zkopírujte tento text, doplňte název rostliny a vložte ho do svého Gemini nebo ChatGPT:")
    
    # Šablona pro uživatele ke zkopírování
    prompt_template = """Jsi expert na zahradnictví. Potřebuji údaje pro prodejní cedulku odrůdy: [DOPLŇTE NÁZEV].
Vypiš mi POUZE tyto 4 řádky přesně v tomto formátu, nic víc nepiš:

Ř1: Stanoviště: ... | Zálivka: ...
Ř2: Spon: ... | Výška: ...
Ř3: Plod: ... | Hmotnost: ...
Ř4: Použití: ... | Tip: ..."""
    
    st.code(prompt_template, language="text")
    
    st.markdown("---")
    st.subheader("2. Vložte výsledek z AI a fotku")
    ai_input = st.text_area("Sem vložte odpověď od Gemini/ChatGPT:", height=150, placeholder="Sem vložte ty 4 řádky...")
    
    uploaded_file = st.file_uploader("Nahrajte fotku plodu/rostliny:", type=["jpg", "png", "jpeg"])

with col_app:
    st.subheader("3. Automatický výcuc na cedulku")
    st.caption("Aplikace si z vloženého textu sama roztřídí data. Zde je můžete ještě upravit.")
    
    # Základní hodnoty
    r1 = "Stanoviště: | Zálivka: "
    r2 = "Spon: | Výška: "
    r3 = "Plod: | Hmotnost: "
    r4 = "Použití: | Tip: "
    nazev_z_textu = ""

    # Chytré parsování vloženého textu
    if ai_input:
        lines = ai_input.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("Ř1:"): r1 = line.replace("Ř1: ", "")
            elif line.startswith("Ř2:"): r2 = line.replace("Ř2: ", "")
            elif line.startswith("Ř3:"): r3 = line.replace("Ř3: ", "")
            elif line.startswith("Ř4:"): r4 = line.replace("Ř4: ", "")

    nazev = st.text_input("Název odrůdy (nadpis cedulky):", placeholder="Např. Rajče Bejbino F1")
    
    # Předvyplněná políčka, která může uživatel ručně přepsat
    edit_r1 = st.text_input("Řádek 1:", value=r1)
    edit_r2 = st.text_input("Řádek 2:", value=r2)
    edit_r3 = st.text_input("Řádek 3:", value=r3)
    edit_r4 = st.text_input("Řádek 4:", value=r4)

    st.write("---")
    if st.button("🖨️ GENEROVAT PDF K TISKU", type="primary", use_container_width=True):
        if not uploaded_file:
            st.error("❌ Chybí fotka! Nahrajte ji prosím vlevo.")
        elif not nazev:
            st.error("❌ Chybí název odrůdy!")
        else:
            img = Image.open(uploaded_file).convert("RGB")
            A4_W, A4_H = 2480, 3508
            L_W, L_H = A4_W // 2, A4_H // 2
            canvas = Image.new('RGB', (A4_W, A4_H), 'white')
            font_p = get_czech_font()

            def draw_label(name, img_plant, lines):
                lbl = Image.new('RGB', (L_W, L_H), 'white')
                d = ImageDraw.Draw(lbl)
                y = 60
                
                # Logo
                try:
                    logo = Image.open("logo txt farma.JPG").convert("RGBA")
                    lw = L_W - 350
                    logo = logo.resize((lw, int(lw * (logo.height / logo.width))), Image.Resampling.LANCZOS)
                    lbl.paste(logo, ((L_W - lw) // 2, y), logo)
                    y += logo.height + 30
                except: y += 100
                
                # Název
                f_t = ImageFont.truetype(font_p, 115) if font_p else ImageFont.load_default()
                d.text((L_W//2, y + 40), name.upper(), fill="#004D40", anchor="mm", font=f_t)
                y += 150
                
                # Fotka
                max_th = int(L_H * 0.42)
                max_tw = L_W - 200
                w, h = img_plant.size
                ratio = min(max_tw/w, max_th/h)
                new_size = (int(w*ratio), int(h*ratio))
                resized_img = img_plant.resize(new_size, Image.Resampling.LANCZOS)
                lbl.paste(resized_img, ((L_W - new_size[0]) // 2, y))
                y += new_size[1] + 60
                
                # Parametry
                f_b = ImageFont.truetype(font_p, 45) if font_p else ImageFont.load_default()
                for line in lines:
                    d.text((120, y), f"• {line}", fill="#333333", font=f_b)
                    y += 75
                
                # Cena
                bx_w, bx_h = 420, 160; bx_x, bx_y = (L_W - bx_w)//2, L_H - 220
                d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="#004D40", width=12)
                d.text((bx_x + bx_w + 40, bx_y + 80), "Kč", fill="black", anchor="lm", font=ImageFont.truetype(font_p, 100))
                
                return lbl

            label = draw_label(nazev, img, [edit_r1, edit_r2, edit_r3, edit_r4])
            canvas.paste(label, (0, 0)); canvas.paste(label, (L_W, 0))
            canvas.paste(label, (0, L_H)); canvas.paste(label, (L_W, L_H))
            
            buf = io.BytesIO()
            canvas.save(buf, format="PDF")
            st.download_button(f"📥 Stáhnout PDF {nazev}", buf.getvalue(), f"{clean_filename(nazev)}.pdf")
            st.success("PDF úspěšně vygenerováno!")

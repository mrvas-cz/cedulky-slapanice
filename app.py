import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request
import unicodedata
import textwrap
import json
import shutil

# --- KONFIGURACE ---
DB_DIR = "archiv_cedulek"
KATEGORIE = ["Papriky - Sladké", "Papriky - Pálivé", "Rajčata", "Sadba", "Bylinky", "Ostatní"]
if not os.path.exists(DB_DIR): os.makedirs(DB_DIR)

st.set_page_config(page_title="Farma Systém PRO", page_icon="🌿", layout="wide")

# --- POMOCNÉ FUNKCE ---
@st.cache_resource
def get_czech_font(font_type="Bold"):
    file_name = f"Roboto-{font_type}.ttf"
    if not os.path.exists(file_name):
        try:
            url = f"https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-{font_type}.ttf"
            urllib.request.urlretrieve(url, file_name)
        except: return None
    return file_name

def clean_filename(text):
    if not text: return "BEZ_NAZVU"
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8').replace(" ", "_").upper()

# --- GRAFIKA (Zalamování textu) ---
def draw_text_box(draw, text, pos, max_width, max_height, font_path, start_font_size):
    current_font_size = start_font_size
    lines = []
    while current_font_size > 22:
        font = ImageFont.truetype(font_path, current_font_size) if font_path else ImageFont.load_default()
        lines = []
        raw_lines = text.split('\n')
        for raw_line in raw_lines:
            if not raw_line.strip(): continue
            avg_char_width = draw.textlength("a", font=font)
            chars_per_line = max(1, int(max_width / avg_char_width))
            wrapped = textwrap.wrap(raw_line, width=chars_per_line)
            for i, w_line in enumerate(wrapped):
                lines.append(f"• {w_line}" if i == 0 else f"  {w_line}")
        if len(lines) * (current_font_size * 1.3) <= max_height: break
        current_font_size -= 2
    
    font = ImageFont.truetype(font_path, current_font_size)
    y_text = pos[1]
    for line in lines:
        draw.text((pos[0], y_text), line, fill="#333333", font=font)
        y_text += current_font_size * 1.3

def draw_label(name, img_plant, lines_text, font_bold, font_reg):
    A4_W, A4_H = 2480, 3508
    L_W, L_H = A4_W // 2, A4_H // 2
    lbl = Image.new('RGB', (L_W, L_H), 'white')
    d = ImageDraw.Draw(lbl)
    
    y = 60
    try:
        logo = Image.open("logo txt farma.JPG").convert("RGBA")
        lw = L_W - 400
        logo = logo.resize((lw, int(lw * (logo.height / logo.width))), Image.Resampling.LANCZOS)
        lbl.paste(logo, ((L_W - lw) // 2, y), logo)
        y += logo.height + 40
    except: y += 100
    
    f_t = ImageFont.truetype(font_bold, 115)
    d.text((L_W//2, y), name.upper(), fill="#004D40", anchor="mt", font=f_t)
    y += 180
    
    if img_plant:
        max_th, max_tw = int(L_H * 0.38), L_W - 200
        w, h = img_plant.size
        ratio = min(max_tw/w, max_th/h)
        new_size = (int(w*ratio), int(h*ratio))
        resized_img = img_plant.resize(new_size, Image.Resampling.LANCZOS)
        lbl.paste(resized_img, ((L_W - new_size[0]) // 2, y))
        y += new_size[1] + 60
    
    draw_text_box(d, "\n".join(lines_text), (100, y), L_W - 200, (L_H-250)-y, font_reg, 48)
    d.rectangle([(L_W-420)//2, L_H-220, (L_W+420)//2, L_H-60], outline="#004D40", width=12)
    d.text(((L_W+420)//2 + 40, L_H-140), "Kč", fill="black", anchor="lm", font=ImageFont.truetype(font_bold, 100))
    d.rectangle([0, 0, L_W-1, L_H-1], outline="#EEEEEE", width=3)
    return lbl

# --- SESSION STATE (PAMĚŤ) ---
if 'form_name' not in st.session_state: st.session_state.form_name = ""
if 'form_r1' not in st.session_state: st.session_state.form_r1 = "Stanoviště: | Zálivka: "
if 'form_r2' not in st.session_state: st.session_state.form_r2 = "Spon: | Výška: "
if 'form_r3' not in st.session_state: st.session_state.form_r3 = "Plod: | Hmotnost: "
if 'form_r4' not in st.session_state: st.session_state.form_r4 = "Použití: | Tip: "
if 'form_img' not in st.session_state: st.session_state.form_img = None
if 'form_cat' not in st.session_state: st.session_state.form_cat = "Ostatní"

# --- UI ---
tab1, tab2 = st.tabs(["🖌️ Editor & Tisk", "🗃️ Archiv"])

with tab1:
    col_l, col_r = st.columns([1, 1.2], gap="large")
    
    with col_l:
        st.header("1. Zadání")
        nazev = st.text_input("Název odrůdy:", key="form_name")
        
        if nazev:
            # Kontrola duplicity
            fname = clean_filename(nazev)
            if os.path.exists(os.path.join(DB_DIR, fname)) and nazev != st.session_state.get('loaded_now'):
                st.warning("⚠️ Odrůda již existuje.")
                if st.button("📂 Načíst existující"):
                    with open(os.path.join(DB_DIR, fname, "data.json"), "r", encoding="utf-8") as f:
                        d = json.load(f)
                    st.session_state.form_name = d['name']
                    st.session_state.form_r1 = d['r1']
                    st.session_state.form_r2 = d['r2']
                    st.session_state.form_r3 = d['r3']
                    st.session_state.form_r4 = d['r4']
                    st.session_state.form_cat = d.get('cat', 'Ostatní')
                    img_p = os.path.join(DB_DIR, fname, "photo.jpg")
                    st.session_state.form_img = Image.open(img_p) if os.path.exists(img_p) else None
                    st.session_state.loaded_now = d['name']
                    st.rerun()

            st.info("🤖 **AI Prompt:**")
            st.code(f"Jsi odborník. Najdi o odrůdě {nazev} tyto údaje: Ř1: Stanoviště: ... | Zálivka: ... Ř2: Spon: ... | Výška: ... Ř3: Plod: ... | Hmotnost: ... Ř4: Použití: ... | Tip: ...", language="text")
            q = nazev.replace(" ", "+")
            st.markdown(f"🔍 [Obrázky Google](https://google.cz/search?tbm=isch&q={q}+fruit+macro) | [Technická data IT](https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+varieta+peso)")

        st.selectbox("Kategorie:", KATEGORIE, key="form_cat")
        up_file = st.file_uploader("📸 Fotka:", type=["jpg", "png", "jpeg"])
        if up_file:
            st.session_state.form_img = Image.open(up_file).convert("RGB")
        
        if st.session_state.form_img:
            st.image(st.session_state.form_img, width=150)

    with col_r:
        st.header("2. Obsah")
        ai_txt = st.text_area("Vložit text z AI:", placeholder="Sem vložte Ř1 až Ř4...")
        if ai_txt:
            for line in ai_txt.split('\n'):
                if "Ř1:" in line: st.session_state.form_r1 = line.split("Ř1:")[1].strip()
                if "Ř2:" in line: st.session_state.form_r2 = line.split("Ř2:")[1].strip()
                if "Ř3:" in line: st.session_state.form_r3 = line.split("Ř3:")[1].strip()
                if "Ř4:" in line: st.session_state.form_r4 = line.split("Ř4:")[1].strip()
            st.rerun()

        st.text_input("Řádek 1:", key="form_r1")
        st.text_input("Řádek 2:", key="form_r2")
        st.text_input("Řádek 3:", key="form_r3")
        st.text_input("Řádek 4:", key="form_r4")

        c1, c2 = st.columns(2)
        if c1.button("💾 ULOŽIT", use_container_width=True, type="primary"):
            if st.session_state.form_name and st.session_state.form_img:
                p = os.path.join(DB_DIR, clean_filename(st.session_state.form_name))
                if not os.path.exists(p): os.makedirs(p)
                d = {"name": st.session_state.form_name, "cat": st.session_state.form_cat, "r1": st.session_state.form_r1, "r2": st.session_state.form_r2, "r3": st.session_state.form_r3, "r4": st.session_state.form_r4}
                with open(os.path.join(p, "data.json"), "w", encoding="utf-8") as f: json.dump(d, f)
                st.session_state.form_img.save(os.path.join(p, "photo.jpg"), "JPEG")
                st.success("Uloženo!")
            else: st.error("Chybí název nebo fotka!")
        
        if c2.button("🔄 NOVÁ / VYMAZAT", use_container_width=True):
            st.session_state.form_name = ""
            st.session_state.form_r1 = "Stanoviště: | Zálivka: "
            st.session_state.form_r2 = "Spon: | Výška: "
            st.session_state.form_r3 = "Plod: | Hmotnost: "
            st.session_state.form_r4 = "Použití: | Tip: "
            st.session_state.form_img = None
            st.rerun()

    # --- NÁHLED ---
    if st.session_state.form_name and st.session_state.form_img:
        st.markdown("---")
        fb, fr = get_czech_font("Bold"), get_czech_font("Regular")
        lbl = draw_label(st.session_state.form_name, st.session_state.form_img, [st.session_state.form_r1, st.session_state.form_r2, st.session_state.form_r3, st.session_state.form_r4], fb, fr)
        canvas = Image.new('RGB', (2480, 3508), 'white')
        for pos in [(0,0), (1240,0), (0,1754), (1240,1754)]: canvas.paste(lbl, pos)
        st.image(canvas, use_column_width=True)
        pdf_b = io.BytesIO()
        canvas.save(pdf_b, format="PDF")
        st.download_button("📥 STÁHNOUT PDF", pdf_b.getvalue(), f"{st.session_state.form_name}.pdf", type="primary")

with tab2:
    all_f = [f for f in os.listdir(DB_DIR) if os.path.isdir(os.path.join(DB_DIR, f))]
    for kat in KATEGORIE:
        items = []
        for f in all_f:
            with open(os.path.join(DB_DIR, f, "data.json"), "r", encoding="utf-8") as file:
                info = json.load(file)
                if info.get("cat", "Ostatní") == kat: items.append((f, info))
        if items:
            with st.expander(f"📂 {kat} ({len(items)})"):
                for f_name, info in items:
                    c1, c2, c3 = st.columns([1, 3, 1])
                    img_p = os.path.join(DB_DIR, f_name, "photo.jpg")
                    if os.path.exists(img_p): c1.image(img_p, width=100)
                    c2.write(f"**{info['name']}**")
                    if c3.button("✏️", key=f"ed_{f_name}"):
                        st.session_state.form_name = info['name']
                        st.session_state.form_r1 = info['r1']
                        st.session_state.form_r2 = info['r2']
                        st.session_state.form_r3 = info['r3']
                        st.session_state.form_r4 = info['r4']
                        st.session_state.form_cat = info.get('cat', 'Ostatní')
                        st.session_state.form_img = Image.open(img_p) if os.path.exists(img_p) else None
                        st.rerun()

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request
import unicodedata
import textwrap
import json
import shutil

# --- 1. KONFIGURACE ---
DB_DIR = "archiv_cedulek"
KATEGORIE = ["Papriky - Sladké", "Papriky - Pálivé", "Rajčata", "Sadba", "Bylinky", "Ostatní"]

if not os.path.exists(DB_DIR): os.makedirs(DB_DIR)

st.set_page_config(page_title="Farma Systém - Cedulky", page_icon="🌿", layout="wide")

# CSS pro design
st.markdown("""
    <style>
    .stButton>button { border-radius: 8px; font-weight: bold; }
    .stTextArea textarea { background-color: #f0f8f4; }
    div[data-testid="stMetricValue"] { color: #004D40; }
    </style>
""", unsafe_allow_html=True)

# --- 2. FUNKCE ---
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
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8').replace(" ", "_").upper()

def save_to_archive(name, cat, r1, r2, r3, r4, image):
    folder_name = clean_filename(name)
    path = os.path.join(DB_DIR, folder_name)
    if not os.path.exists(path): os.makedirs(path)
    data = {"name": name, "cat": cat, "r1": r1, "r2": r2, "r3": r3, "r4": r4}
    with open(os.path.join(path, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    if image: image.save(os.path.join(path, "photo.jpg"), "JPEG")

def load_label_data(folder_name):
    path = os.path.join(DB_DIR, folder_name)
    with open(os.path.join(path, "data.json"), "r", encoding="utf-8") as f: data = json.load(f)
    img_path = os.path.join(path, "photo.jpg")
    img = Image.open(img_path) if os.path.exists(img_path) else None
    return data, img

# --- 3. KRESLENÍ (DYNAMICKÉ ZALOMENÍ) ---
def draw_text_box(draw, text, pos, max_width, max_height, font_path, start_font_size):
    current_font_size = start_font_size
    lines = []
    while current_font_size > 22:
        font = ImageFont.truetype(font_path, current_font_size) if font_path else ImageFont.load_default()
        lines = []
        raw_lines = text.split('\n')
        for raw_line in raw_lines:
            if not raw_line.strip(): continue
            avg_char_width = draw.textlength("a", font=font) if font_path else 10
            chars_per_line = max(1, int(max_width / avg_char_width))
            wrapped = textwrap.wrap(raw_line, width=chars_per_line)
            for i, w_line in enumerate(wrapped):
                lines.append(f"• {w_line}" if i == 0 else f"  {w_line}")
        line_height = current_font_size * 1.3
        if len(lines) * line_height <= max_height: break
        current_font_size -= 2
    
    font = ImageFont.truetype(font_path, current_font_size) if font_path else ImageFont.load_default()
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
    f_t = ImageFont.truetype(font_bold, 115) if font_bold else ImageFont.load_default()
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
    bx_w, bx_h, bx_y = 420, 160, L_H - 220
    d.rectangle([(L_W-bx_w)//2, bx_y, (L_W+bx_w)//2, bx_y+bx_h], outline="#004D40", width=12)
    f_p = ImageFont.truetype(font_bold, 100) if font_bold else ImageFont.load_default()
    d.text(((L_W+bx_w)//2 + 40, bx_y + 80), "Kč", fill="black", anchor="lm", font=f_p)
    d.rectangle([0, 0, L_W-1, L_H-1], outline="#EEEEEE", width=3)
    return lbl

# --- 4. APLIKACE ---
if 'edit_data' not in st.session_state:
    st.session_state.edit_data = {"name": "", "cat": "Ostatní", "r1": "", "r2": "", "r3": "", "r4": "", "img": None}

st.title("🌿 Farmářský Systém: Generátor Cedulek")
tab1, tab2 = st.tabs(["🖌️ Editor & Tisk", "🗃️ Sklad / Archiv"])

with tab1:
    col_search, col_data = st.columns([1, 1.2], gap="large")
    
    with col_search:
        st.header("1. Zadání a Rešerše")
        # Načtení dat ze session state
        ed = st.session_state.edit_data
        nazev_input = st.text_input("Název odrůdy (vyhledá se i prompt):", value=ed.get("name", ""))
        
        # KONTROLA DUPLICITY
        folder_check = clean_filename(nazev_input)
        if nazev_input and os.path.exists(os.path.join(DB_DIR, folder_check)) and nazev_input != ed.get("loaded_name"):
            st.warning(f"⚠️ Odrůda '{nazev_input}' již existuje!")
            if st.button("📂 Otevřít existující"):
                d, img = load_label_data(folder_check)
                st.session_state.edit_data = {**d, "img": img, "loaded_name": nazev_input}
                st.rerun()

        # PROMPT PRO AI (To co chybělo)
        if nazev_input:
            st.info("🤖 **Prompt pro AI (zkopírujte):**")
            ai_prompt = f"Jsi odborník. Najdi o odrůdě {nazev_input} tyto údaje a vypiš je přesně takto:\nŘ1: Stanoviště: ... | Zálivka: ...\nŘ2: Spon: ... | Výška: ...\nŘ3: Plod: ... | Hmotnost: ...\nŘ4: Použití: ... | Tip: ..."
            st.code(ai_prompt, language="text")
            
            st.markdown("🔍 **Odkazy pro rešerši:**")
            q = nazev_input.replace(" ", "+")
            st.markdown(f"👉 [Obrázky Google] (https://google.cz/search?tbm=isch&q={q}+fruit+macro+white+background)")
            st.markdown(f"👉 [Itálie (Technická data)] (https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+varieta+peso)")
            st.markdown(f"👉 [Holandsko (Katalogy)] (https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+ras+kenmerken)")

        selected_cat = st.selectbox("Kategorie:", KATEGORIE, index=KATEGORIE.index(ed.get("cat", "Ostatní")))
        
        uploaded_file = st.file_uploader("📸 Nahrát fotku:", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            st.session_state.edit_data["img"] = Image.open(uploaded_file).convert("RGB")
        elif ed.get("img"):
            st.image(ed.get("img"), width=150)

    with col_data:
        st.header("2. Obsah Cedulky")
        ai_import = st.text_area("Vložit výsledek z AI:", height=100)
        
        if ai_import:
            for line in ai_import.split('\n'):
                if "Ř1:" in line: st.session_state.edit_data["r1"] = line.split("Ř1:")[1].strip()
                elif "Ř2:" in line: st.session_state.edit_data["r2"] = line.split("Ř2:")[1].strip()
                elif "Ř3:" in line: st.session_state.edit_data["r3"] = line.split("Ř3:")[1].strip()
                elif "Ř4:" in line: st.session_state.edit_data["r4"] = line.split("Ř4:")[1].strip()
            st.rerun()

        curr = st.session_state.edit_data
        r1 = st.text_input("Řádek 1:", value=curr.get("r1") if curr.get("r1") else "Stanoviště: | Zálivka: ")
        r2 = st.text_input("Řádek 2:", value=curr.get("r2") if curr.get("r2") else "Spon: | Výška: ")
        r3 = st.text_input("Řádek 3:", value=curr.get("r3") if curr.get("r3") else "Plod: | Hmotnost: ")
        r4 = st.text_input("Řádek 4:", value=curr.get("r4") if curr.get("r4") else "Použití: | Tip: ")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 ULOŽIT", use_container_width=True, type="primary"):
                if nazev_input and st.session_state.edit_data.get("img"):
                    save_to_archive(nazev_input, selected_cat, r1, r2, r3, r4, st.session_state.edit_data["img"])
                    st.success("Uloženo!")
                else: st.error("Chybí název/fotka")
        with col2:
            if st.button("🔄 NOVÁ", use_container_width=True):
                st.session_state.edit_data = {"name": "", "cat": "Ostatní", "r1": "", "r2": "", "r3": "", "r4": "", "img": None}
                st.rerun()

    if nazev_input and st.session_state.edit_data.get("img"):
        st.markdown("---")
        f_b, f_r = get_czech_font("Bold"), get_czech_font("Regular")
        lbl = draw_label(nazev_input, st.session_state.edit_data["img"], [r1, r2, r3, r4], f_b, f_r)
        canvas = Image.new('RGB', (2480, 3508), 'white')
        for pos in [(0,0), (1240,0), (0,1754), (1240,1754)]: canvas.paste(lbl, pos)
        st.image(canvas, use_column_width=True)
        buf = io.BytesIO()
        canvas.save(buf, format="PDF")
        st.download_button("📥 STÁHNOUT PDF", buf.getvalue(), f"{clean_filename(nazev_input)}.pdf", type="primary")

with tab2:
    all_f = [f for f in os.listdir(DB_DIR) if os.path.isdir(os.path.join(DB_DIR, f))]
    st.header(f"📊 Sklad ({len(all_f)} položek)")
    for kat in KATEGORIE:
        kat_items = []
        for f in all_f:
            p = os.path.join(DB_DIR, f, "data.json")
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as file:
                    info = json.load(file)
                    if info.get("cat", "Ostatní") == kat: kat_items.append((f, info))
        if kat_items:
            with st.expander(f"📂 {kat} ({len(kat_items)})"):
                for f_name, info in kat_items:
                    c1, c2, c3 = st.columns([1, 3, 1])
                    with c1: 
                        im_p = os.path.join(DB_DIR, f_name, "photo.jpg")

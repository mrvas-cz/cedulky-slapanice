import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request
import unicodedata
import textwrap
import json
import shutil

# --- 1. ZÁKLADNÍ KONFIGURACE A STYLY ---
DB_DIR = "archiv_cedulek"
KATEGORIE = ["Papriky - Sladké", "Papriky - Pálivé", "Rajčata", "Sadba", "Bylinky", "Ostatní"]

if not os.path.exists(DB_DIR): os.makedirs(DB_DIR)

st.set_page_config(page_title="Farma Systém - Cedulky", page_icon="🌿", layout="wide")

# Vlastní CSS pro hezčí design
st.markdown("""
    <style>
    .stButton>button { border-radius: 8px; font-weight: bold; }
    div[data-testid="stMetricValue"] { color: #004D40; }
    .css-1d391kg { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

# --- 2. POMOCNÉ FUNKCE (ZÁKULISÍ) ---
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

# --- 3. GRAFICKÝ ENGINE (TVORBA PDF) ---
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
    f_price = ImageFont.truetype(font_bold, 100) if font_bold else ImageFont.load_default()
    d.text(((L_W+bx_w)//2 + 40, bx_y + 80), "Kč", fill="black", anchor="lm", font=f_price)
    
    d.rectangle([0, 0, L_W-1, L_H-1], outline="#EEEEEE", width=3)
    return lbl

# --- 4. HLAVNÍ APLIKACE A UI ---
if 'edit_data' not in st.session_state:
    st.session_state.edit_data = {"name": "", "cat": "Ostatní", "r1": "", "r2": "", "r3": "", "r4": "", "img": None}

st.title("🌿 Farmářský Systém: Generátor Cedulek")

tab1, tab2 = st.tabs(["🖌️ Editor & Tisk", "🗃️ Sklad / Archiv"])

# --- ZÁLOŽKA 1: EDITOR ---
with tab1:
    col_search, col_data = st.columns([1, 1.2], gap="large")
    
    with col_search:
        st.header("1. Zadání a Rešerše")
        nazev_input = st.text_input("Název odrůdy:", value=st.session_state.edit_data["name"], placeholder="Např. Rajče Bejbino")
        
        folder_check = clean_filename(nazev_input)
        is_duplicate = nazev_input and os.path.exists(os.path.join(DB_DIR, folder_check)) and nazev_input != st.session_state.edit_data.get("loaded_name")
        
        if is_duplicate:
            st.warning(f"⚠️ Pozor: Odrůda '{nazev_input}' již ve skladu existuje!")
            if st.button("📂 Otevřít existující z archivu"):
                d, img = load_label_data(folder_check)
                st.session_state.edit_data = {**d, "img": img, "loaded_name": nazev_input}
                st.rerun()

        selected_cat = st.selectbox("Kategorie pro uložení:", KATEGORIE, index=KATEGORIE.index(st.session_state.edit_data["cat"]))
        
        if nazev_input:
            st.markdown("🔍 **Zahraniční katalogy (s překladem):**")
            q = nazev_input.replace(" ", "+")
            c1, c2 = st.columns(2)
            c1.markdown(f"👉 [Google Obrázky](https://google.cz/search?tbm=isch&q={q}+fruit+macro)\n\n👉 [Holandsko (Osiva)](https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+ras+kenmerken)")
            c2.markdown(f"👉 [Itálie (Rajčata/Papriky)](https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+varieta+peso)\n\n👉 [Německo (Bylinky)](https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+sorte+anbau)")

        uploaded_file = st.file_uploader("📸 Nahrát staženou fotku:", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            st.session_state.edit_data["img"] = Image.open(uploaded_file).convert("RGB")
            st.success("Fotka nahrána!")
        elif st.session_state.edit_data["img"]:
            st.image(st.session_state.edit_data["img"], width=150, caption="Aktuální fotka")

    with col_data:
        st.header("2. Obsah Cedulky")
        ai_import = st.text_area("Vložit strukturovaný text z AI (volitelné):", height=100, placeholder="Sem vložte výsledek z ChatGPT/Gemini...")
        
        if ai_import:
            for line in ai_import.split('\n'):
                if "Ř1:" in line: st.session_state.edit_data["r1"] = line.split("Ř1:")[1].strip()
                elif "Ř2:" in line: st.session_state.edit_data["r2"] = line.split("Ř2:")[1].strip()
                elif "Ř3:" in line: st.session_state.edit_data["r3"] = line.split("Ř3:")[1].strip()
                elif "Ř4:" in line: st.session_state.edit_data["r4"] = line.split("Ř4:")[1].strip()

        r1 = st.text_input("Řádek 1 (Stanoviště/Zálivka):", value=st.session_state.edit_data["r1"] if st.session_state.edit_data["r1"] else "Stanoviště: | Zálivka: ")
        r2 = st.text_input("Řádek 2 (Spon/Výška):", value=st.session_state.edit_data["r2"] if st.session_state.edit_data["r2"] else "Spon: | Výška: ")
        r3 = st.text_input("Řádek 3 (Plod/Hmotnost):", value=st.session_state.edit_data["r3"] if st.session_state.edit_data["r3"] else "Plod: | Hmotnost: ")
        r4 = st.text_input("Řádek 4 (Použití/Tip):", value=st.session_state.edit_data["r4"] if st.session_state.edit_data["r4"] else "Použití: | Tip: ")

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("💾 ULOŽIT DO SKLADU", use_container_width=True, type="primary"):
                if nazev_input and st.session_state.edit_data["img"]:
                    save_to_archive(nazev_input, selected_cat, r1, r2, r3, r4, st.session_state.edit_data["img"])
                    st.success("✅ Úspěšně uloženo do databáze!")
                else: st.error("❌ Chybí název nebo fotografie!")
        with col_btn2:
            if st.button("🔄 NOVÁ / VYČISTIT", use_container_width=True):
                st.session_state.edit_data = {"name": "", "cat": "Ostatní", "r1": "", "r2": "", "r3": "", "r4": "", "img": None}
                st.rerun()

    # Náhled a Tisk (Generuje se pouze pokud je název a fotka)
    if nazev_input and st.session_state.edit_data["img"]:
        st.markdown("---")
        st.subheader("🖨️ Náhled a Tisk (A4)")
        with st.spinner("Vykresluji tiskový arch..."):
            f_b = get_czech_font("Bold")
            f_r = get_czech_font("Regular")
            
            # Filtrování prázdných vzorových řádků
            lines = [r for r in [r1, r2, r3, r4] if r.strip() and not r.endswith(": | ")]
            if not lines: lines = [r1, r2, r3, r4] # Fallback
            
            single_lbl = draw_label(nazev_input, st.session_state.edit_data["img"], lines, f_b, f_r)
            
            canvas = Image.new('RGB', (2480, 3508), 'white')
            canvas.paste(single_lbl, (0, 0))
            canvas.paste(single_lbl, (1240, 0))
            canvas.paste(single_lbl, (0, 1754))
            canvas.paste(single_lbl, (1240, 1754))
            
            col_img, col_dl = st.columns([1, 2])
            with col_img:
                st.image(canvas, use_column_width=True, caption="Náhled formátu A4")
            with col_dl:
                st.write("**Tiskový arch je připraven.** Obsahuje 4 stejné cedulky. PDF stáhnete tlačítkem níže a vytisknete běžným způsobem bez okrajů.")
                pdf_buf = io.BytesIO()
                canvas.save(pdf_buf, format="PDF")
                st.download_button("📥 STÁHNOUT PDF K TISKU", pdf_buf.getvalue(), f"{clean_filename(nazev_input)}_A4.pdf", mime="application/pdf", type="primary")

# --- ZÁLOŽKA 2: ARCHIV / SKLAD ---
with tab2:
    all_folders = [f for f in os.listdir(DB_DIR) if os.path.isdir(os.path.join(DB_DIR, f))]
    
    # Rychlý Dashboard
    st.header("📊 Přehled skladu")
    m_cols = st.columns(len(KATEGORIE) + 1)
    m_cols[0].metric("Celkem druhů", len(all_folders))
    
    # Procházení archivu a počítání metrik
    archive_data = {kat: [] for kat in KATEGORIE}
    for f in all_folders:
        path = os.path.join(DB_DIR, f, "data.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as file:
                info = json.load(file)
                cat = info.get("cat", "Ostatní")
                if cat in archive_data: archive_data[cat].append((f, info))

    for i, kat in enumerate(KATEGORIE):
        m_cols[i+1].metric(kat, len(archive_data[kat]))
        
    st.markdown("---")

    # Zobrazení podle kategorií
    for kat in KATEGORIE:
        if archive_data[kat]:
            st.subheader(f"📂 {kat}")
            for f_name, info in archive_data[kat]:
                with st.expander(f"🌿 {info['name']}"):
                    c1, c2, c3 = st.columns([1, 3, 1])
                    img_p = os.path.join(DB_DIR, f_name, "photo.jpg")
                    with c1:
                        if os.path.exists(img_p): st.image(img_p, width=120)
                    with c2:
                        st.markdown(f"**{info['name']}**")
                        st.caption(f"{info['r1']}  \n{info['r2']}  \n{info['r3']}  \n{info['r4']}")
                    with c3:
                        if st.button("✏️ Otevřít v Editoru", key=f"load_{f_name}"):
                            d, img = load_label_data(f_name)
                            st.session_state.edit_data = {**d, "img": img, "loaded_name": info['name']}
                            st.success("✅ Načteno! Přepněte se do první záložky 'Editor & Tisk'.")
                        if st.button("🗑️ Smazat odrůdu", key=f"del_{f_name}", type="primary"):
                            shutil.rmtree(os.path.join(DB_DIR, f_name))
                            st.rerun()

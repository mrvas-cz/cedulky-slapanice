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

st.markdown("""
    <style>
    .stButton>button { border-radius: 8px; font-weight: bold; }
    .stTextArea textarea { background-color: #f8fbfa; border: 1px solid #1B5E20; }
    </style>
""", unsafe_allow_html=True)

# --- 2. FUNKCE PRO TEXT A GRAFIKU ---
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
        if len(lines) * (current_font_size * 1.3) <= max_height: break
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

# --- 3. PAMĚŤ ---
if 'form_name' not in st.session_state: st.session_state.form_name = ""
if 'form_r1' not in st.session_state: st.session_state.form_r1 = "Stanoviště: | Zálivka: "
if 'form_r2' not in st.session_state: st.session_state.form_r2 = "Spon: | Výška: "
if 'form_r3' not in st.session_state: st.session_state.form_r3 = "Plod: | Hmotnost: "
if 'form_r4' not in st.session_state: st.session_state.form_r4 = "Použití: | Tip: "
if 'form_img' not in st.session_state: st.session_state.form_img = None
if 'ai_input_text' not in st.session_state: st.session_state.ai_input_text = ""

def process_ai_input():
    text = st.session_state.ai_input_text
    if not text: return
    clean_text = text.replace("**", "").replace("*", "")
    for line in clean_text.split('\n'):
        # Oříznutí na 65 znaků rovnou při importu, aby se text zaručeně vešel
        if "Ř1:" in line: st.session_state.form_r1 = line.split("Ř1:")[1].strip()[:65]
        elif "Ř2:" in line: st.session_state.form_r2 = line.split("Ř2:")[1].strip()[:65]
        elif "Ř3:" in line: st.session_state.form_r3 = line.split("Ř3:")[1].strip()[:65]
        elif "Ř4:" in line: st.session_state.form_r4 = line.split("Ř4:")[1].strip()[:65]

def reset_form():
    st.session_state.form_name = ""
    st.session_state.form_r1 = "Stanoviště: | Zálivka: "
    st.session_state.form_r2 = "Spon: | Výška: "
    st.session_state.form_r3 = "Plod: | Hmotnost: "
    st.session_state.form_r4 = "Použití: | Tip: "
    st.session_state.form_img = None
    st.session_state.ai_input_text = ""

# --- 4. APLIKACE A UI ---
st.title("🌿 Farmářský Systém: Generátor Cedulek")
tab1, tab2 = st.tabs(["🖌️ Editor & Tisk", "🗃️ Sklad / Archiv"])

with tab1:
    col_search, col_data = st.columns([1, 1.2], gap="large")
    
    with col_search:
        st.header("1. Zadání a Rešerše")
        current_name = st.text_input("Název odrůdy:", key="form_name")
        folder_check = clean_filename(current_name)
        
        if current_name and os.path.exists(os.path.join(DB_DIR, folder_check)):
            st.warning("⚠️ Odrůda již v archivu existuje!")
        
        if current_name:
            st.info("🤖 **Prompt pro AI (Zkopírujte):**")
            # Upravený agresivní prompt
            ai_prompt = f"""Jsi odborník. Najdi o odrůdě {current_name} tyto údaje.
!!! KRITICKÉ PRAVIDLO: PIŠ EXTRÉMNĚ STRUČNĚ, POUZE HESLA. KAŽDÝ ŘÁDEK SMÍ MÍT MAXIMÁLNĚ 6 AŽ 7 SLOV CELKEM !!!
Vypiš je přesně takto:
Ř1: Stanoviště: ... | Zálivka: ...
Ř2: Spon: ... | Výška: ...
Ř3: Plod: ... | Hmotnost: ...
Ř4: Použití: ... | Tip: ..."""
            st.code(ai_prompt, language="text")
            
            q = current_name.replace(" ", "+")
            st.markdown(f"🔍 [Obrázky Google](https://google.cz/search?tbm=isch&q={q}+fruit+macro) | [Data Itálie](https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+varieta+peso) | [Data Nizozemí](https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+ras+kenmerken)")

        selected_cat = st.selectbox("Kategorie pro uložení:", KATEGORIE)
        
        uploaded_file = st.file_uploader("📸 Nahrát staženou fotku:", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            st.session_state.form_img = Image.open(uploaded_file).convert("RGB")
            st.success("Fotka načtena!")
            
        if st.session_state.form_img:
            st.image(st.session_state.form_img, width=180, caption="Aktuální fotka na cedulku")

    with col_data:
        st.header("2. Obsah Cedulky (Max 6-7 slov)")
        
        st.text_area("Vložit výsledek z AI (automaticky ořízne přebytek):", key="ai_input_text", on_change=process_ai_input, height=120, placeholder="Vložte zkopírovaný text z Gemini sem a klikněte mimo toto pole...")
        
        # Omezení znaků přímo na inputech (max_chars=65 garantuje čitelnost na cedulce)
        st.text_input("Řádek 1 (Stanoviště/Zálivka):", key="form_r1", max_chars=65)
        st.text_input("Řádek 2 (Spon/Výška):", key="form_r2", max_chars=65)
        st.text_input("Řádek 3 (Plod/Hmotnost):", key="form_r3", max_chars=65)
        st.text_input("Řádek 4 (Použití/Tip):", key="form_r4", max_chars=65)

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("💾 ULOŽIT DO SKLADU", use_container_width=True, type="primary"):
                if st.session_state.form_name and st.session_state.form_img:
                    p = os.path.join(DB_DIR, clean_filename(st.session_state.form_name))
                    if not os.path.exists(p): os.makedirs(p)
                    
                    d = {"name": st.session_state.form_name, "cat": selected_cat, 
                         "r1": st.session_state.form_r1, "r2": st.session_state.form_r2, 
                         "r3": st.session_state.form_r3, "r4": st.session_state.form_r4}
                         
                    with open(os.path.join(p, "data.json"), "w", encoding="utf-8") as f:
                        json.dump(d, f, ensure_ascii=False)
                        
                    st.session_state.form_img.save(os.path.join(p, "photo.jpg"), "JPEG")
                    st.success("✅ Uloženo do databáze!")
                else: 
                    st.error("❌ Chybí název nebo fotka!")
                    
        with col_btn2:
            st.button("🔄 NOVÁ (VYČISTIT)", use_container_width=True, on_click=reset_form)

    # NÁHLED A TISK
    if st.session_state.form_name and st.session_state.form_img:
        st.markdown("---")
        st.subheader("🖨️ Náhled a Tisk (A4)")
        with st.spinner("Generuji arch..."):
            f_b, f_r = get_czech_font("Bold"), get_czech_font("Regular")
            
            lines = [st.session_state.form_r1, st.session_state.form_r2, st.session_state.form_r3, st.session_state.form_r4]
            valid_lines = [r for r in lines if r.strip() and not r.endswith(": | ")]
            if not valid_lines: valid_lines = lines
            
            single_lbl = draw_label(st.session_state.form_name, st.session_state.form_img, valid_lines, f_b, f_r)
            
            canvas = Image.new('RGB', (2480, 3508), 'white')
            canvas.paste(single_lbl, (0, 0))
            canvas.paste(single_lbl, (1240, 0))
            canvas.paste(single_lbl, (0, 1754))
            canvas.paste(single_lbl, (1240, 1754))
            
            c_img, c_dl = st.columns([1, 2])
            c_img.image(canvas, use_column_width=True)
            
            pdf_buf = io.BytesIO()
            canvas.save(pdf_buf, format="PDF")
            c_dl.download_button("📥 STÁHNOUT PDF K TISKU", pdf_buf.getvalue(), f"{clean_filename(st.session_state.form_name)}_A4.pdf", mime="application/pdf", type="primary")

# --- ZÁLOŽKA 2: ARCHIV ---
with tab2:
    all_folders = [f for f in os.listdir(DB_DIR) if os.path.isdir(os.path.join(DB_DIR, f))]
    st.header(f"📊 Přehled skladu ({len(all_folders)} druhů)")
    
    for kat in KATEGORIE:
        kat_items = []
        for f in all_folders:
            path = os.path.join(DB_DIR, f, "data.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as file:
                    info = json.load(file)
                    if info.get("cat", "Ostatní") == kat: kat_items.append((f, info))
        
        if kat_items:
            with st.expander(f"📂 {kat} ({len(kat_items)})"):
                for f_name, info in kat_items:
                    c1, c2, c3 = st.columns([1, 3, 1])
                    img_p = os.path.join(DB_DIR, f_name, "photo.jpg")
                    if os.path.exists(img_p): c1.image(img_p, width=120)
                    
                    c2.markdown(f"**{info.get('name', 'Neznámý')}**")
                    c2.caption(f"{info.get('r1', '')} \n{info.get('r2', '')}")
                    
                    if c3.button("✏️ Načíst do editoru", key=f"load_{f_name}"):
                        st.session_state.form_name = info.get('name', '')
                        st.session_state.form_r1 = info.get('r1', '')[:65]
                        st.session_state.form_r2 = info.get('r2', '')[:65]
                        st.session_state.form_r3 = info.get('r3', '')[:65]
                        st.session_state.form_r4 = info.get('r4', '')[:65]
                        st.session_state.form_img = Image.open(img_p) if os.path.exists(img_p) else None
                        st.success("Načteno! Přepněte se do první záložky.")
                        
                    if c3.button("🗑️ Smazat", key=f"del_{f_name}", type="primary"):
                        shutil.rmtree(os.path.join(DB_DIR, f_name))
                        st.rerun()

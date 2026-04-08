import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request
import unicodedata
import json
import shutil
import uuid
import textwrap

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

# --- 2. GRAFICKÉ FUNKCE A ZAROVNÁNÍ DO BLOKU ---
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

def load_label_data(folder_name):
    path = os.path.join(DB_DIR, folder_name)
    with open(os.path.join(path, "data.json"), "r", encoding="utf-8") as f: data = json.load(f)
    img_path = os.path.join(path, "photo.jpg")
    img = Image.open(img_path) if os.path.exists(img_path) else None
    return data, img

def draw_justified_paragraph(d, text, start_x, start_y, max_w, max_h, font_bold_path, font_reg_path):
    curr_size = 55 
    best_size = curr_size
    lines_data = []
    
    text = text.replace('|', ' | ')
    words_raw = text.split()
    if not words_raw: return

    while curr_size >= 20:
        try:
            f_b = ImageFont.truetype(font_bold_path, curr_size) if font_bold_path else ImageFont.load_default()
            f_r = ImageFont.truetype(font_reg_path, curr_size) if font_reg_path else ImageFont.load_default()
        except:
            f_b = ImageFont.load_default(); f_r = ImageFont.load_default()
            
        lines_data = []
        current_line = []
        current_w = 0
        space_w = d.textlength(" ", font=f_r)

        for word in words_raw:
            f_curr = f_b if word.endswith(':') else f_r
            w_len = d.textlength(word, font=f_curr)

            if not current_line:
                current_line.append((word, f_curr, w_len))
                current_w = w_len
            else:
                if current_w + space_w + w_len <= max_w:
                    current_line.append((word, f_curr, w_len))
                    current_w += space_w + w_len
                else:
                    lines_data.append((current_line, current_w))
                    current_line = [(word, f_curr, w_len)]
                    current_w = w_len

        if current_line:
            lines_data.append((current_line, current_w))

        line_spacing = int(curr_size * 1.5)
        total_h = len(lines_data) * line_spacing

        if total_h <= max_h:
            best_size = curr_size
            break
        curr_size -= 2

    y = start_y
    line_spacing = int(best_size * 1.5)

    for i, (line_words, line_w) in enumerate(lines_data):
        if len(line_words) == 1 or i == len(lines_data) - 1:
            x = start_x
            for word, font, w_len in line_words:
                fill = "#004D40" if word.endswith(':') else ("#AAAAAA" if word == '|' else "#222222")
                d.text((x, y), word, fill=fill, font=font)
                x += w_len + d.textlength(" ", font=font)
        else:
            total_word_w = sum(w_len for _, _, w_len in line_words)
            total_space = max_w - total_word_w
            gap = total_space / (len(line_words) - 1)

            x = start_x
            for j, (word, font, w_len) in enumerate(line_words):
                fill = "#004D40" if word.endswith(':') else ("#AAAAAA" if word == '|' else "#222222")
                d.text((x, y), word, fill=fill, font=font)
                x += w_len + gap
                
        y += line_spacing

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
    
    title_size = 90
    f_t = ImageFont.truetype(font_bold, title_size) if font_bold else ImageFont.load_default()
    while font_bold and d.textlength(name.upper(), font=f_t) > (L_W - 80) and title_size > 40:
        title_size -= 5
        f_t = ImageFont.truetype(font_bold, title_size)
        
    d.text((L_W//2, y), name.upper(), fill="#004D40", anchor="mt", font=f_t)
    y += int(title_size * 1.3) + 20 
    
    if img_plant:
        max_th, max_tw = int(L_H * 0.42), L_W - 160 
        w, h = img_plant.size
        ratio = min(max_tw/w, max_th/h)
        new_size = (int(w*ratio), int(h*ratio))
        resized_img = img_plant.resize(new_size, Image.Resampling.LANCZOS)
        
        img_x = (L_W - new_size[0]) // 2
        img_y = y
        pad = 12
        d.rectangle([img_x - pad, img_y - pad, img_x + new_size[0] + pad, img_y + new_size[1] + pad], outline="#004D40", width=4)
        lbl.paste(resized_img, (img_x, img_y))
        y += new_size[1] + 50 
        
    valid_lines = [r.strip() for r in lines_text if r.strip() and not r.endswith(": | ")]
    combined_text = " ".join(valid_lines)
    
    price_y_start = L_H - 220
    max_text_height = price_y_start - y - 20 
    
    draw_justified_paragraph(d, combined_text, 100, y, L_W - 200, max_text_height, font_bold, font_reg)
        
    bx_w, bx_h, bx_y = 420, 160, price_y_start
    d.rectangle([(L_W-bx_w)//2, bx_y, (L_W+bx_w)//2, bx_y+bx_h], outline="#004D40", width=12)
    f_p = ImageFont.truetype(font_bold, 100) if font_bold else ImageFont.load_default()
    d.text(((L_W+bx_w)//2 + 40, bx_y + 80), "Kč", fill="black", anchor="lm", font=f_p)
    d.rectangle([0, 0, L_W-1, L_H-1], outline="#EEEEEE", width=3)
    return lbl

# --- 3. EXTRÉMNĚ BEZPEČNÁ PAMĚŤ ---
if 'form_key' not in st.session_state: st.session_state.form_key = str(uuid.uuid4())
if 'd' not in st.session_state:
    st.session_state.d = {
        "name": "", "cat": "Ostatní", "img": None,
        "r1": "Stanoviště: | Zálivka: ", "r2": "Spon: | Výška: ",
        "r3": "Plod: | Hmotnost: ", "r4": "Použití: | Tip: ", "last_ai": "",
        "last_name_check": ""
    }
if 'show_load_msg' not in st.session_state: st.session_state.show_load_msg = False

def c_key(field): return f"{field}_{st.session_state.form_key}"
def get_current(field): return st.session_state.get(c_key(field), st.session_state.d.get(field, ""))

# --- 4. APLIKACE A UI ---
st.title("🌿 Farmářský Systém: Generátor Cedulek")

if st.session_state.show_load_msg:
    st.success("✅ Cedulka úspěšně načtena! Vše je v Editoru připraveno k tisku nebo úpravám.")
    st.session_state.show_load_msg = False

tab1, tab2 = st.tabs(["🖌️ Editor & Tisk", "🗃️ Sklad / Archiv"])

with tab1:
    col_search, col_data = st.columns([1, 1.2], gap="large")

    with col_search:
        st.header("1. Zadání a Rešerše")
        
        st.text_input("Název odrůdy:", value=st.session_state.d["name"], key=c_key("name"), placeholder="Např. rajče start")
        curr_name = get_current("name")
        
        # CHYTRÁ AUTO-KATEGORIZACE PODLE ZADANÉHO SLOVA
        if curr_name != st.session_state.d.get("last_name_check", ""):
            ln = curr_name.lower()
            if "rajče" in ln or "rajčata" in ln or "rajcata" in ln:
                st.session_state.d["cat"] = "Rajčata"
            elif "paprika" in ln or "papriky" in ln:
                st.session_state.d["cat"] = "Papriky - Sladké"
            elif "bazalka" in ln or "pažitka" in ln or "bylink" in ln or "máta" in ln:
                st.session_state.d["cat"] = "Bylinky"
            st.session_state.d["last_name_check"] = curr_name
        
        folder_check = clean_filename(curr_name)
        if curr_name and os.path.exists(os.path.join(DB_DIR, folder_check)):
            st.warning("⚠️ Odrůda již v archivu existuje!")
            if st.button("📂 Načíst existující data z archivu", type="primary"):
                loaded_d, loaded_img = load_label_data(folder_check)
                st.session_state.d.update(loaded_d)
                if st.session_state.d.get("cat") not in KATEGORIE: st.session_state.d["cat"] = "Ostatní"
                st.session_state.d["img"] = loaded_img
                st.session_state.d["last_ai"] = ""
                st.session_state.form_key = str(uuid.uuid4())
                st.session_state.show_load_msg = True
                st.rerun()

        if curr_name:
            st.info("🤖 **Prompt pro AI (Zkopírujte):**")
            # VYLEPŠENÝ PROMPT (Auto-korekce názvu)
            ai_prompt = f"Jsi odborník. Hledáme odrůdu: {curr_name}.\n!!! KRITICKÁ PRAVIDLA:\n1. OVĚŘ A OPRAV NÁZEV: Zjisti přesný oficiální název (např. 'rajče start' -> 'Rajče Start F1'). Pokud je to zkomolenina (např. Zlatka místo Zlatava), zeptej se/upozorni.\n2. PIŠ EXTRÉMNĚ STRUČNĚ (max 6 slov na řádek).\n3. PIŠ LAICKY PRO BĚŽNÉHO SPOTŘEBITELE. VYNECH VŠECHNA CIZÍ NEBO ODBORNÁ SLOVA. !!!\nVypiš to přesně takto:\nPŘESNÝ NÁZEV: (doplň oficiální název)\nŘ1: Stanoviště: ... | Zálivka: ...\nŘ2: Spon: ... | Výška: ...\nŘ3: Plod: ... | Hmotnost: ...\nŘ4: Použití: ... | Tip: ..."
            st.code(ai_prompt, language="text")

            q = curr_name.replace(" ", "+")
            st.markdown(f"🔍 [Obrázky Google](https://google.cz/search?tbm=isch&q={q}+fruit+macro+white+background) | [Data Itálie](https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+varieta+peso) | [Data Nizozemí](https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+ras+kenmerken)")

        cat_idx = KATEGORIE.index(st.session_state.d["cat"]) if st.session_state.d["cat"] in KATEGORIE else KATEGORIE.index("Ostatní")
        st.session_state.d["cat"] = st.selectbox("Kategorie pro uložení:", KATEGORIE, index=cat_idx, key=c_key("cat"))

        up_file = st.file_uploader("📸 Nahrát staženou fotku:", type=["jpg", "png", "jpeg"], key=c_key("img_up"))
        if up_file:
            st.session_state.d["img"] = Image.open(up_file).convert("RGB")

        if st.session_state.d.get("img"):
            st.image(st.session_state.d["img"], width=180, caption="Aktuální fotka na cedulku")

    with col_data:
        st.header("2. Obsah Cedulky")

        ai_input = st.text_area("Vložit výsledek z AI:", height=120, key=c_key("ai"))
        if ai_input and ai_input != st.session_state.d.get("last_ai"):
            st.session_state.d["name"] = get_current("name")
            st.session_state.d["cat"] = get_current("cat")
            st.session_state.d["r1"] = get_current("r1")
            st.session_state.d["r2"] = get_current("r2")
            st.session_state.d["r3"] = get_current("r3")
            st.session_state.d["r4"] = get_current("r4")
            
            st.session_state.d["last_ai"] = ai_input
            clean_txt = ai_input.replace("**", "").replace("*", "")
            
            # CHYTRÉ ČTENÍ: Přečte i opravený název!
            for line in clean_txt.split('\n'):
                if "PŘESNÝ NÁZEV:" in line.upper():
                    possible_name = line.split(":", 1)[1].strip()
                    if possible_name: st.session_state.d["name"] = possible_name
                elif "Ř1:" in line: st.session_state.d["r1"] = line.split("Ř1:")[1].strip()[:65]
                elif "Ř2:" in line: st.session_state.d["r2"] = line.split("Ř2:")[1].strip()[:65]
                elif "Ř3:" in line: st.session_state.d["r3"] = line.split("Ř3:")[1].strip()[:65]
                elif "Ř4:" in line: st.session_state.d["r4"] = line.split("Ř4:")[1].strip()[:65]
            
            st.session_state.form_key = str(uuid.uuid4())
            st.rerun()

        st.text_input("Řádek 1 (Stanoviště/Zálivka):", value=st.session_state.d["r1"], max_chars=65, key=c_key("r1"))
        st.text_input("Řádek 2 (Spon/Výška):", value=st.session_state.d["r2"], max_chars=65, key=c_key("r2"))
        st.text_input("Řádek 3 (Plod/Hmotnost):", value=st.session_state.d["r3"], max_chars=65, key=c_key("r3"))
        st.text_input("Řádek 4 (Použití/Tip):", value=st.session_state.d["r4"], max_chars=65, key=c_key("r4"))

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("💾 ULOŽIT DO SKLADU", use_container_width=True, type="primary"):
                f_name = get_current("name")
                f_img = st.session_state.d.get("img")
                if f_name and f_img:
                    p = os.path.join(DB_DIR, clean_filename(f_name))
                    if not os.path.exists(p): os.makedirs(p)
                    d_out = {
                        "name": f_name, "cat": st.session_state.d["cat"],
                        "r1": get_current("r1"), "r2": get_current("r2"),
                        "r3": get_current("r3"), "r4": get_current("r4")
                    }
                    with open(os.path.join(p, "data.json"), "w", encoding="utf-8") as f:
                        json.dump(d_out, f, ensure_ascii=False)
                    f_img.save(os.path.join(p, "photo.jpg"), "JPEG")
                    st.success("✅ Uloženo do databáze!")
                else:
                    st.error("❌ Chybí název nebo fotka!")

        with col_btn2:
            if st.button("🔄 NOVÁ (VYČISTIT)", use_container_width=True):
                st.session_state.d = {
                    "name": "", "cat": "Ostatní", "img": None,
                    "r1": "Stanoviště: | Zálivka: ", "r2": "Spon: | Výška: ",
                    "r3": "Plod: | Hmotnost: ", "r4": "Použití: | Tip: ", "last_ai": "",
                    "last_name_check": ""
                }
                st.session_state.form_key = str(uuid.uuid4())
                st.rerun()

    # --- NÁHLED A TISK ---
    c_name = get_current("name")
    c_img = st.session_state.d.get("img")
    if c_name and c_img:
        st.markdown("---")
        st.subheader("🖨️ Náhled a Tisk (A4)")
        with st.spinner("Generuji arch..."):
            f_b, f_r = get_czech_font("Bold"), get_czech_font("Regular")
            lines = [get_current("r1"), get_current("r2"), get_current("r3"), get_current("r4")]
            
            valid_lines = [r for r in lines if r.strip() and not r.endswith(": | ")]
            if not valid_lines: valid_lines = lines

            single_lbl = draw_label(c_name, c_img, valid_lines, f_b, f_r)

            canvas = Image.new('RGB', (2480, 3508), 'white')
            canvas.paste(single_lbl, (0, 0))
            canvas.paste(single_lbl, (1240, 0))
            canvas.paste(single_lbl, (0, 1754))
            canvas.paste(single_lbl, (1240, 1754))

            c_img_col, c_dl = st.columns([1, 2])
            c_img_col.image(canvas, use_column_width=True)

            pdf_buf = io.BytesIO()
            canvas.save(pdf_buf, format="PDF")
            c_dl.download_button("📥 STÁHNOUT PDF K TISKU", pdf_buf.getvalue(), f"{clean_filename(c_name)}_A4.pdf", mime="application/pdf", type="primary")

# --- ZÁLOŽKA 2: ARCHIV ---
with tab2:
    all_folders = [f for f in os.listdir(DB_DIR) if os.path.isdir(os.path.join(DB_DIR, f))]
    st.header(f"📊 Přehled skladu ({len(all_folders)} položek)")

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
                        loaded_d, loaded_img = load_label_data(f_name)
                        st.session_state.d.update(loaded_d)
                        if st.session_state.d.get("cat") not in KATEGORIE: st.session_state.d["cat"] = "Ostatní"
                        st.session_state.d["img"] = loaded_img
                        st.session_state.d["last_ai"] = ""
                        st.session_state.form_key = str(uuid.uuid4())
                        st.session_state.show_load_msg = True
                        st.rerun()

                    if c3.button("🗑️ Smazat", key=f"del_{f_name}", type="primary"):
                        shutil.rmtree(os.path.join(DB_DIR, f_name))
                        st.rerun()

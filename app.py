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

def load_label_data(folder_name):
    path = os.path.join(DB_DIR, folder_name)
    with open(os.path.join(path, "data.json"), "r", encoding="utf-8") as f: data = json.load(f)
    img_path = os.path.join(path, "photo.jpg")
    img = Image.open(img_path) if os.path.exists(img_path) else None
    return data, img

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
    
    f_t = ImageFont.truetype(font_bold, 110) if font_bold else ImageFont.load_default()
    d.text((L_W//2, y), name.upper(), fill="#004D40", anchor="mt", font=f_t)
    y += 160
    
    if img_plant:
        max_th, max_tw = int(L_H * 0.38), L_W - 240
        w, h = img_plant.size
        ratio = min(max_tw/w, max_th/h)
        new_size = (int(w*ratio), int(h*ratio))
        resized_img = img_plant.resize(new_size, Image.Resampling.LANCZOS)
        
        img_x = (L_W - new_size[0]) // 2
        img_y = y
        pad = 12
        d.rectangle([img_x - pad, img_y - pad, img_x + new_size[0] + pad, img_y + new_size[1] + pad], outline="#004D40", width=4)
        lbl.paste(resized_img, (img_x, img_y))
        y += new_size[1] + 90
        
    f_b = ImageFont.truetype(font_bold, 40) if font_bold else ImageFont.load_default()
    f_r = ImageFont.truetype(font_reg, 40) if font_reg else ImageFont.load_default()
    
    for line in lines_text:
        parts = line.split('|', 1)
        x_positions = [100, int(L_W * 0.52)]
        for i, part in enumerate(parts):
            part = part.strip()
            if not part: continue
            curr_x = x_positions[i]
            if ":" in part:
                key, val = part.split(':', 1)
                d.text((curr_x, y), key.strip() + ":", fill="#004D40", font=f_b)
                curr_x += d.textlength(key.strip() + ": ", font=f_b)
                d.text((curr_x, y), val.strip(), fill="#333333", font=f_r)
            else:
                d.text((curr_x, y), part, fill="#333333", font=f_r)
        y += 85
        
    bx_w, bx_h, bx_y = 420, 160, L_H - 220
    d.rectangle([(L_W-bx_w)//2, bx_y, (L_W+bx_w)//2, bx_y+bx_h], outline="#004D40", width=12)
    f_p = ImageFont.truetype(font_bold, 100) if font_bold else ImageFont.load_default()
    d.text(((L_W+bx_w)//2 + 40, bx_y + 80), "Kč", fill="black", anchor="lm", font=f_p)
    d.rectangle([0, 0, L_W-1, L_H-1], outline="#EEEEEE", width=3)
    return lbl

# --- 3. CENTRÁLNÍ BEZPEČNÁ PAMĚŤ (BEZ VAZBY NA KLÍČE) ---
if 'active_label' not in st.session_state:
    st.session_state.active_label = {
        "name": "", "cat": "Ostatní", "img": None,
        "r1": "Stanoviště: | Zálivka: ",
        "r2": "Spon: | Výška: ",
        "r3": "Plod: | Hmotnost: ",
        "r4": "Použití: | Tip: "
    }
if 'upload_id' not in st.session_state: st.session_state.upload_id = str(uuid.uuid4())
if 'raw_ai_input' not in st.session_state: st.session_state.raw_ai_input = ""

# --- 4. APLIKACE A UI ---
st.title("🌿 Farmářský Systém: Generátor Cedulek")
tab1, tab2 = st.tabs(["🖌️ Editor & Tisk", "🗃️ Sklad / Archiv"])

with tab1:
    col_search, col_data = st.columns([1, 1.2], gap="large")

    with col_search:
        st.header("1. Zadání a Rešerše")
        
        # POUŽITÍ POUZE VALUE (Bypass Streamlit chyby)
        current_name = st.text_input("Název odrůdy:", value=st.session_state.active_label["name"])
        st.session_state.active_label["name"] = current_name

        folder_check = clean_filename(current_name)
        if current_name and os.path.exists(os.path.join(DB_DIR, folder_check)):
            st.warning("⚠️ Odrůda již v archivu existuje!")
            if st.button("📂 Načíst existující data z archivu", type="primary"):
                # Bezpečné načtení starých dat
                d, img = load_label_data(folder_check)
                st.session_state.active_label.update({
                    "name": d.get("name", ""),
                    "cat": d.get("cat", "Ostatní"),
                    "r1": d.get("r1", "Stanoviště: | Zálivka: "),
                    "r2": d.get("r2", "Spon: | Výška: "),
                    "r3": d.get("r3", "Plod: | Hmotnost: "),
                    "r4": d.get("r4", "Použití: | Tip: "),
                    "img": img
                })
                st.session_state.upload_id = str(uuid.uuid4())
                st.rerun()

        if current_name:
            st.info("🤖 **Prompt pro AI (Zkopírujte):**")
            ai_prompt = f"Jsi odborník. Najdi o odrůdě {current_name} tyto údaje.\n!!! KRITICKÁ PRAVIDLA:\n1. PIŠ EXTRÉMNĚ STRUČNĚ (max 6 slov na řádek).\n2. PIŠ LAICKY PRO BĚŽNÉHO SPOTŘEBITELE. VYNECH VŠECHNA CIZÍ NEBO ODBORNÁ SLOVA. !!!\nVypiš to přesně takto:\nŘ1: Stanoviště: ... | Zálivka: ...\nŘ2: Spon: ... | Výška: ...\nŘ3: Plod: ... | Hmotnost: ...\nŘ4: Použití: ... | Tip: ..."
            st.code(ai_prompt, language="text")

            q = current_name.replace(" ", "+")
            st.markdown(f"🔍 [Obrázky Google](https://google.cz/search?tbm=isch&q={q}+fruit+macro+white+background) | [Data Itálie](https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+varieta+peso) | [Data Nizozemí](https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+ras+kenmerken)")

        # Bezpečný výběr kategorie
        cat_safe = st.session_state.active_label["cat"] if st.session_state.active_label["cat"] in KATEGORIE else "Ostatní"
        cat_idx = KATEGORIE.index(cat_safe)
        st.session_state.active_label["cat"] = st.selectbox("Kategorie pro uložení:", KATEGORIE, index=cat_idx)

        # Fotografie
        uploaded_file = st.file_uploader("📸 Nahrát staženou fotku:", type=["jpg", "png", "jpeg"], key=st.session_state.upload_id)
        if uploaded_file:
            st.session_state.active_label["img"] = Image.open(uploaded_file).convert("RGB")

        if st.session_state.active_label["img"]:
            st.image(st.session_state.active_label["img"], width=180, caption="Aktuální fotka na cedulku")

    with col_data:
        st.header("2. Obsah Cedulky")

        # Zpracování AI textu
        new_ai_input = st.text_area("Vložit výsledek z AI:", value=st.session_state.raw_ai_input, height=120)
        if new_ai_input != st.session_state.raw_ai_input:
            st.session_state.raw_ai_input = new_ai_input
            clean_txt = new_ai_input.replace("**", "").replace("*", "")
            for line in clean_txt.split('\n'):
                if "Ř1:" in line: st.session_state.active_label["r1"] = line.split("Ř1:")[1].strip()[:65]
                elif "Ř2:" in line: st.session_state.active_label["r2"] = line.split("Ř2:")[1].strip()[:65]
                elif "Ř3:" in line: st.session_state.active_label["r3"] = line.split("Ř3:")[1].strip()[:65]
                elif "Ř4:" in line: st.session_state.active_label["r4"] = line.split("Ř4:")[1].strip()[:65]
            st.rerun()

        st.session_state.active_label["r1"] = st.text_input("Řádek 1:", value=st.session_state.active_label["r1"], max_chars=65)
        st.session_state.active_label["r2"] = st.text_input("Řádek 2:", value=st.session_state.active_label["r2"], max_chars=65)
        st.session_state.active_label["r3"] = st.text_input("Řádek 3:", value=st.session_state.active_label["r3"], max_chars=65)
        st.session_state.active_label["r4"] = st.text_input("Řádek 4:", value=st.session_state.active_label["r4"], max_chars=65)

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("💾 ULOŽIT DO SKLADU", use_container_width=True, type="primary"):
                al = st.session_state.active_label
                if al["name"] and al["img"]:
                    p = os.path.join(DB_DIR, clean_filename(al["name"]))
                    if not os.path.exists(p): os.makedirs(p)
                    d_out = {
                        "name": al["name"], "cat": al["cat"],
                        "r1": al["r1"], "r2": al["r2"], "r3": al["r3"], "r4": al["r4"]
                    }
                    with open(os.path.join(p, "data.json"), "w", encoding="utf-8") as f:
                        json.dump(d_out, f, ensure_ascii=False)
                    al["img"].save(os.path.join(p, "photo.jpg"), "JPEG")
                    st.success("✅ Úspěšně uloženo do archivu!")
                else:
                    st.error("❌ Chybí název nebo fotka!")

        with col_btn2:
            if st.button("🔄 NOVÁ (VYČISTIT)", use_container_width=True):
                st.session_state.active_label = {
                    "name": "", "cat": "Ostatní", "img": None,
                    "r1": "Stanoviště: | Zálivka: ", "r2": "Spon: | Výška: ",
                    "r3": "Plod: | Hmotnost: ", "r4": "Použití: | Tip: "
                }
                st.session_state.raw_ai_input = ""
                st.session_state.upload_id = str(uuid.uuid4())
                st.rerun()

    # --- NÁHLED A TISK ---
    al = st.session_state.active_label
    if al["name"] and al["img"]:
        st.markdown("---")
        st.subheader("🖨️ Náhled a Tisk (A4)")
        with st.spinner("Generuji arch..."):
            f_b, f_r = get_czech_font("Bold"), get_czech_font("Regular")
            lines = [al["r1"], al["r2"], al["r3"], al["r4"]]
            valid_lines = [r for r in lines if r.strip() and not r.endswith(": | ")]
            if not valid_lines: valid_lines = lines

            single_lbl = draw_label(al["name"], al["img"], valid_lines, f_b, f_r)

            canvas = Image.new('RGB', (2480, 3508), 'white')
            canvas.paste(single_lbl, (0, 0))
            canvas.paste(single_lbl, (1240, 0))
            canvas.paste(single_lbl, (0, 1754))
            canvas.paste(single_lbl, (1240, 1754))

            c_img, c_dl = st.columns([1, 2])
            c_img.image(canvas, use_column_width=True)

            pdf_buf = io.BytesIO()
            canvas.save(pdf_buf, format="PDF")
            c_dl.download_button("📥 STÁHNOUT PDF K TISKU", pdf_buf.getvalue(), f"{clean_filename(al['name'])}_A4.pdf", mime="application/pdf", type="primary")

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
                    # Zpětná kompatibilita - chybějící kategorie se hodí do "Ostatní"
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
                        d, img = load_label_data(f_name)
                        st.session_state.active_label.update({
                            "name": d.get("name", ""),
                            "cat": d.get("cat", "Ostatní"),
                            "r1": d.get("r1", "Stanoviště: | Zálivka: "),
                            "r2": d.get("r2", "Spon: | Výška: "),
                            "r3": d.get("r3", "Plod: | Hmotnost: "),
                            "r4": d.get("r4", "Použití: | Tip: "),
                            "img": img
                        })
                        st.session_state.upload_id = str(uuid.uuid4())
                        st.session_state.raw_ai_input = ""
                        st.rerun()

                    if c3.button("🗑️ Smazat", key=f"del_{f_name}", type="primary"):
                        shutil.rmtree(os.path.join(DB_DIR, f_name))
                        st.rerun()

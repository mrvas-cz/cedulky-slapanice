import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request
import unicodedata
import textwrap
import json
import shutil

# --- KONFIGURACE A CESTY ---
DB_DIR = "archiv_cedulek"
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

st.set_page_config(page_title="PRO Cedulkovač Farma - s Archivem", layout="wide")

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
    nfkd_form = unicodedata.normalize('NFKD', text)
    return nfkd_form.encode('ASCII', 'ignore').decode('utf-8').replace(" ", "_").upper()

# --- FUNKCE PRO UKLÁDÁNÍ A NAČÍTÁNÍ ---
def save_to_archive(name, r1, r2, r3, r4, image):
    folder_name = clean_filename(name)
    path = os.path.join(DB_DIR, folder_name)
    if not os.path.exists(path):
        os.makedirs(path)
    
    # Uložení textů
    data = {"name": name, "r1": r1, "r2": r2, "r3": r3, "r4": r4}
    with open(os.path.join(path, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    
    # Uložení obrázku
    if image:
        image.save(os.path.join(path, "photo.jpg"), "JPEG")
    return True

def delete_from_archive(folder_name):
    path = os.path.join(DB_DIR, folder_name)
    if os.path.exists(path):
        shutil.rmtree(path)
        return True
    return False

# --- FUNKCE KRESLENÍ (Zůstává stejná jako minule) ---
def draw_text_box(draw, text, pos, max_width, max_height, font_path, start_font_size):
    current_font_size = start_font_size
    lines = []
    while current_font_size > 22:
        font = ImageFont.truetype(font_path, current_font_size)
        lines = []
        raw_lines = text.split('\n')
        for raw_line in raw_lines:
            if not raw_line.strip(): continue
            avg_char_width = draw.textlength("a", font=font)
            chars_per_line = max(1, int(max_width / avg_char_width))
            wrapped = textwrap.wrap(raw_line, width=chars_per_line)
            for i, w_line in enumerate(wrapped):
                lines.append(f"• {w_line}" if i == 0 else f"  {w_line}")
        line_height = current_font_size * 1.3
        if len(lines) * line_height <= max_height: break
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
        max_th, max_tw = int(L_H * 0.40), L_W - 200
        w, h = img_plant.size
        ratio = min(max_tw/w, max_th/h)
        new_size = (int(w*ratio), int(h*ratio))
        resized_img = img_plant.resize(new_size, Image.Resampling.LANCZOS)
        lbl.paste(resized_img, ((L_W - new_size[0]) // 2, y))
        y += new_size[1] + 60
    
    draw_text_box(d, "\n".join(lines_text), (100, y), L_W - 200, (L_H-250)-y, font_reg, 48)
    bx_w, bx_h, bx_y = 420, 160, L_H - 220
    d.rectangle([(L_W-bx_w)//2, bx_y, (L_W+bx_w)//2, bx_y+bx_h], outline="#004D40", width=12)
    d.text(((L_W+bx_w)//2 + 40, bx_y + 80), "Kč", fill="black", anchor="lm", font=ImageFont.truetype(font_bold, 100))
    return lbl

# --- HLAVNÍ NAVIGACE ---
tab1, tab2 = st.tabs(["🆕 Vytvořit / Upravit", "🗃️ Archiv uložených cedulek"])

with tab1:
    st.title("🌿 Editor cedulek")
    
    # Pomocná funkce pro vyčištění polí
    if 'edit_data' not in st.session_state:
        st.session_state.edit_data = {"name": "", "r1": "", "r2": "", "r3": "", "r4": "", "img": None}

    col_l, col_r = st.columns([1, 1.2])
    
    with col_l:
        st.subheader("🔍 Rešerše")
        nazev_search = st.text_input("Zadejte název odrůdy:", value=st.session_state.edit_data["name"])
        if nazev_search:
            q = nazev_search.replace(" ", "+")
            st.markdown(f"🔗 [Google CZ](https://google.cz/search?q={q}) | [IT]({q}+varieta) | [NL]({q}+ras) | [Obrázky](https://google.cz/search?tbm=isch&q={q}+fruit+macro)")
            st.code(f"Jsi odborník. Najdi o odrůdě {nazev_search} tyto údaje: Ř1: Stanoviště... Ř2: Spon... Ř3: Plod... Ř4: Použití...", language="text")
        
        uploaded_file = st.file_uploader("📸 Nahrát fotku:", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            st.session_state.edit_data["img"] = Image.open(uploaded_file).convert("RGB")
        elif st.session_state.edit_data["img"]:
            st.image(st.session_state.edit_data["img"], width=150)

    with col_r:
        st.subheader("📝 Údaje cedulky")
        ai_import = st.text_area("Vložit výstřižek z AI (volitelné):")
        
        # Parsování importu
        d = st.session_state.edit_data
        if ai_import:
            for line in ai_import.split('\n'):
                if "Ř1:" in line: d["r1"] = line.split("Ř1:")[1].strip()
                elif "Ř2:" in line: d["r2"] = line.split("Ř2:")[1].strip()
                elif "Ř3:" in line: d["r3"] = line.split("Ř3:")[1].strip()
                elif "Ř4:" in line: d["r4"] = line.split("Ř4:")[1].strip()

        final_name = st.text_input("NÁZEV NA CEDULECE:", value=nazev_search)
        fr1 = st.text_input("Řádek 1:", value=d["r1"])
        fr2 = st.text_input("Řádek 2:", value=d["r2"])
        fr3 = st.text_input("Řádek 3:", value=d["r3"])
        fr4 = st.text_input("Řádek 4:", value=d["r4"])

        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 ULOŽIT DO ARCHIVU", use_container_width=True):
                if final_name and st.session_state.edit_data["img"]:
                    save_to_archive(final_name, fr1, fr2, fr3, fr4, st.session_state.edit_data["img"])
                    st.success("Uloženo!")
                else: st.error("Chybí název nebo fotka!")
        with c2:
            if st.button("🔄 NOVÁ (VYČISTIT)", use_container_width=True):
                st.session_state.edit_data = {"name": "", "r1": "", "r2": "", "r3": "", "r4": "", "img": None}
                st.rerun()

    # Náhled a PDF
    if final_name and st.session_state.edit_data["img"]:
        st.markdown("---")
        f_b, f_r = get_czech_font("Bold"), get_czech_font("Regular")
        lbl = draw_label(final_name, st.session_state.edit_data["img"], [fr1, fr2, fr3, fr4], f_b, f_r)
        
        canvas = Image.new('RGB', (2480, 3508), 'white')
        for pos in [(0,0), (1240,0), (0,1754), (1240,1754)]: canvas.paste(lbl, pos)
        
        st.image(canvas, use_column_width=True)
        pdf_buf = io.BytesIO()
        canvas.save(pdf_buf, format="PDF")
        st.download_button("📥 STÁHNOUT PDF K TISKU", pdf_buf.getvalue(), f"{clean_filename(final_name)}.pdf", type="primary")

with tab2:
    st.title("🗃️ Správa archivu")
    folders = sorted(os.listdir(DB_DIR))
    
    if not folders:
        st.info("Archiv je zatím prázdný. Vytvořte a uložte svou první cedulku.")
    
    for f in folders:
        with st.expander(f"📁 {f.replace('_', ' ')}"):
            col1, col2, col3 = st.columns([1, 3, 1])
            data_path = os.path.join(DB_DIR, f, "data.json")
            img_path = os.path.join(DB_DIR, f, "photo.jpg")
            
            if os.path.exists(data_path):
                with open(data_path, "r", encoding="utf-8") as file:
                    info = json.load(file)
                
                with col1:
                    if os.path.exists(img_path):
                        st.image(img_path, width=150)
                with col2:
                    st.write(f"**{info['name']}**")
                    st.caption(f"{info['r1']} | {info['r2']}")
                    st.caption(f"{info['r3']} | {info['r4']}")
                with col3:
                    if st.button("✏️ UPRAVIT", key=f"ed_{f}"):
                        st.session_state.edit_data = {
                            "name": info["name"], "r1": info["r1"], "r2": info["r2"], 
                            "r3": info["r3"], "r4": info["r4"], 
                            "img": Image.open(img_path) if os.path.exists(img_path) else None
                        }
                        st.rerun()
                    if st.button("🗑️ SMAZAT", key=f"del_{f}"):
                        delete_from_archive(f)
                        st.rerun()

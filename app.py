import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request
import unicodedata
import json
import shutil
import uuid

# --- 1. KONFIGURACE ---
DB_DIR = "archiv_cedulek"
KATEGORIE = ["Papriky - Sladké", "Papriky - Pálivé", "Rajčata", "Sadba", "Bylinky", "Květiny", "Ostatní"]

if not os.path.exists(DB_DIR): os.makedirs(DB_DIR)

st.set_page_config(page_title="Farma Systém - Cedulky", page_icon="🌿", layout="wide")

st.markdown("""
    <style>
    .stButton>button { border-radius: 8px; font-weight: bold; }
    .stTextArea textarea { background-color: #f8fbfa; border: 1px solid #1B5E20; }
    </style>
""", unsafe_allow_html=True)

# --- 2. GRAFICKÉ FUNKCE: VEKTOROVÉ IKONY ---
SPECIAL_CHARS = ["✿", "☀", "☁", "💧"]

def draw_inline_icon(d, char, x, y, size):
    """Kreslí vektorové ikony přímo do textu (100% garance tisku)"""
    if char == "✿":
        c = size // 2; r = size // 3
        d.ellipse([x+c-r, y+c-2*r, x+c+r, y+c], fill="#F48FB1")
        d.ellipse([x+c-r, y+c, x+c+r, y+c+2*r], fill="#F48FB1")
        d.ellipse([x+c-2*r, y+c-r, x+c, y+c+r], fill="#F48FB1")
        d.ellipse([x+c, y+c-r, x+c+2*r, y+c+r], fill="#F48FB1")
        d.ellipse([x+c-r//2, y+c-r//2, x+c+r//2, y+c+r//2], fill="#FFF59D")
    elif char == "☀":
        pad = size // 5
        d.ellipse([x+pad, y+pad, x+size-pad, y+size-pad], fill="#FFB300")
        c = size//2
        d.line([(x+c, y), (x+c, y+size)], fill="#FFB300", width=3)
        d.line([(x, y+c), (x+size, y+c)], fill="#FFB300", width=3)
    elif char == "☁":
        d.ellipse([x, y+size//2, x+size//2, y+size], fill="#90A4AE")
        d.ellipse([x+size//4, y+size//4, x+size*3//4, y+size], fill="#90A4AE")
        d.ellipse([x+size//2, y+size//2, x+size, y+size], fill="#90A4AE")
    elif char == "💧":
        c = x + size//2
        d.polygon([(c, y+size//6), (x+size//4, y+size*3//4), (x+size*3//4, y+size*3//4)], fill="#29B6F6")
        d.ellipse([x+size//4, y+size//2, x+size*3//4, y+size], fill="#29B6F6")

def draw_plant_icon(d, p_type, cx, cy, size):
    """Kreslí velký květináč a ukazuje chování kytky"""
    pot_w = size * 0.45
    pot_h = size * 0.35
    pot_y = cy + size * 0.5 
    
    # Květináč
    d.polygon([
        (cx - pot_w/2, pot_y), 
        (cx + pot_w/2, pot_y), 
        (cx + pot_w/2 - 15, pot_y + pot_h), 
        (cx - pot_w/2 + 15, pot_y + pot_h)
    ], fill="#8D6E63")
    d.rectangle([cx - pot_w/2 - 10, pot_y, cx + pot_w/2 + 10, pot_y + 15], fill="#5D4037")
    
    # Stonek a listy podle typu
    d.line([(cx, pot_y), (cx, pot_y - size*0.4)], fill="#43A047", width=12) 
    
    if p_type == "vzpřímená":
        d.ellipse([cx-40, pot_y-size*0.2, cx-5, pot_y-size*0.2+35], fill="#66BB6A")
        d.ellipse([cx+5, pot_y-size*0.3, cx+40, pot_y-size*0.3+35], fill="#66BB6A")
        d.ellipse([cx-25, pot_y-size*0.45, cx+25, pot_y-size*0.45+50], fill="#E91E63") 
    elif p_type == "převis":
        d.line([(cx, pot_y), (cx+size*0.4, pot_y-size*0.1), (cx+size*0.5, pot_y+size*0.4)], fill="#43A047", width=10)
        d.line([(cx, pot_y), (cx-size*0.4, pot_y-size*0.1), (cx-size*0.5, pot_y+size*0.5)], fill="#43A047", width=10)
        d.ellipse([cx+size*0.5-20, pot_y+size*0.2, cx+size*0.5+20, pot_y+size*0.2+40], fill="#E91E63")
        d.ellipse([cx-size*0.5-20, pot_y+size*0.3, cx-size*0.5+20, pot_y+size*0.3+40], fill="#E91E63")
    elif p_type == "polopřevis":
        d.line([(cx, pot_y), (cx+size*0.4, pot_y-size*0.1), (cx+size*0.45, pot_y+size*0.15)], fill="#43A047", width=10)
        d.line([(cx, pot_y), (cx-size*0.4, pot_y-size*0.1), (cx-size*0.45, pot_y+size*0.15)], fill="#43A047", width=10)
        d.ellipse([cx+size*0.45-20, pot_y+size*0.05, cx+size*0.45+20, pot_y+size*0.05+40], fill="#E91E63")
        d.ellipse([cx-size*0.45-20, pot_y+size*0.05, cx-size*0.45+20, pot_y+size*0.05+40], fill="#E91E63")
    else:
        d.ellipse([cx-30, pot_y-size*0.2, cx-5, pot_y-size*0.2+25], fill="#66BB6A")
        d.ellipse([cx+5, pot_y-size*0.3, cx+30, pot_y-size*0.3+25], fill="#66BB6A")

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

    # Měření s ohledem na ikony
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
            w_len = 0
            for char in word:
                if char in SPECIAL_CHARS: w_len += curr_size
                else: w_len += d.textlength(char, font=f_curr)

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

        if current_line: lines_data.append((current_line, current_w))

        line_spacing = int(curr_size * 1.5)
        if len(lines_data) * line_spacing <= max_h:
            best_size = curr_size
            break
        curr_size -= 2

    # Vykreslení s ikonami
    y = start_y
    line_spacing = int(best_size * 1.5)

    for i, (line_words, line_w) in enumerate(lines_data):
        if len(line_words) == 1 or i == len(lines_data) - 1:
            x = start_x
            for word, font, w_len in line_words:
                fill = "#004D40" if word.endswith(':') else ("#AAAAAA" if word == '|' else "#222222")
                for char in word:
                    if char in SPECIAL_CHARS:
                        draw_inline_icon(d, char, x, y + line_spacing//8, int(best_size * 0.8))
                        x += best_size
                    else:
                        d.text((x, y), char, fill=fill, font=font)
                        x += d.textlength(char, font=font)
                x += d.textlength(" ", font=font)
        else:
            total_word_w = sum(w_len for _, _, w_len in line_words)
            total_space = max_w - total_word_w
            gap = total_space / (len(line_words) - 1)

            x = start_x
            for word, font, w_len in line_words:
                fill = "#004D40" if word.endswith(':') else ("#AAAAAA" if word == '|' else "#222222")
                x_curr = x
                for char in word:
                    if char in SPECIAL_CHARS:
                        draw_inline_icon(d, char, x_curr, y + line_spacing//8, int(best_size * 0.8))
                        x_curr += best_size
                    else:
                        d.text((x_curr, y), char, fill=fill, font=font)
                        x_curr += d.textlength(char, font=font)
                x += w_len + gap
                
        y += line_spacing

def draw_label(name, img_plant, lines_text, shu_text, cat, font_bold, font_reg):
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
    
    # NÁZEV 
    title_size = 85
    f_t = ImageFont.truetype(font_bold, title_size) if font_bold else ImageFont.load_default()
    while font_bold and d.textlength(name.upper(), font=f_t) > (L_W - 80) and title_size > 40:
        title_size -= 5
        f_t = ImageFont.truetype(font_bold, title_size)
        
    d.text((L_W//2, y), name.upper(), fill="#004D40", anchor="mt", font=f_t)
    y += int(title_size * 1.3) + 10 
    
    if shu_text and shu_text.strip():
        shu_size = 70
        f_shu = ImageFont.truetype(font_bold, shu_size) if font_bold else ImageFont.load_default()
        while font_bold and d.textlength(shu_text.upper(), font=f_shu) > (L_W - 100) and shu_size > 30:
            shu_size -= 5
            f_shu = ImageFont.truetype(font_bold, shu_size)
            
        d.text((L_W//2, y), shu_text.upper(), fill="#D32F2F", anchor="mt", font=f_shu) 
        y += int(shu_size * 1.3) + 10 
    
    # SPECIÁLNÍ IKONA PRO KVĚTINY
    if cat == "Květiny" and lines_text:
        growth_line = lines_text[0].lower()
        p_type = "neznámá"
        if "polopřevis" in growth_line or "poloprevis" in growth_line: p_type = "polopřevis"
        elif "převis" in growth_line or "previs" in growth_line: p_type = "převis"
        elif "vzpřímen" in growth_line or "vzprimen" in growth_line: p_type = "vzpřímená"
        
        iw = 240 # Velikost ikony květináče
        draw_plant_icon(d, p_type, L_W//2, y, iw)
        y += iw + 20
        
        # Zbytek prvního řádku (centimetry, letnička) kompaktně pod květináč
        text_to_print = lines_text[0].replace("Vzrůst:", "").replace("Převis", "").replace("Polopřevis", "").replace("Vzpřímená", "").replace("|", "").strip()
        if text_to_print:
            f_g = ImageFont.truetype(font_bold, 45) if font_bold else ImageFont.load_default()
            d.text((L_W//2, y), text_to_print, fill="#555555", anchor="mt", font=f_g)
            y += 60
        lines_text = lines_text[1:]
    else:
        if not shu_text: y += 20 
    
    # FOTKA (U květin obří!)
    if img_plant:
        if cat == "Květiny": img_scale = 0.48
        elif shu_text and shu_text.strip(): img_scale = 0.36
        else: img_scale = 0.42
            
        max_th, max_tw = int(L_H * img_scale), L_W - 160 
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
        
    valid_lines = [r.strip() for r in lines_text if r.strip() and not r.endswith(": | ") and not r.endswith(": ")]
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
        "r3": "Plod: | Hmotnost: ", "r4": "Použití: | Tip: ", 
        "shu": "", "last_ai": "", "last_name_check": ""
    }
if 'show_load_msg' not in st.session_state: st.session_state.show_load_msg = False

def c_key(field): return f"{field}_{st.session_state.form_key}"
def get_current(field): return st.session_state.get(c_key(field), st.session_state.d.get(field, ""))

def sync_to_d():
    st.session_state.d["name"] = get_current("name")
    st.session_state.d["cat"] = get_current("cat")
    st.session_state.d["r1"] = get_current("r1")
    st.session_state.d["r2"] = get_current("r2")
    st.session_state.d["r3"] = get_current("r3")
    st.session_state.d["r4"] = get_current("r4")
    st.session_state.d["shu"] = get_current("shu")

def apply_template(cat):
    if cat == "Bylinky":
        st.session_state.d["r1"] = "Stanoviště: | Zálivka: "
        st.session_state.d["r2"] = "Spon: | Výška: "
        st.session_state.d["r3"] = "Typ: | Sběr: "
        st.session_state.d["r4"] = "Použití: | Tip: "
    elif cat == "Květiny":
        st.session_state.d["r1"] = "Vzrůst: Převis 60 cm | Letnička"
        st.session_state.d["r2"] = "✿ Květ: V-IX"
        st.session_state.d["r3"] = "☀ Stanoviště: Slunné"
        st.session_state.d["r4"] = "💧💧💧 Zálivka: Hojná"
    else:
        st.session_state.d["r1"] = "Stanoviště: | Zálivka: "
        st.session_state.d["r2"] = "Spon: | Výška: "
        st.session_state.d["r3"] = "Plod: | Hmotnost: "
        st.session_state.d["r4"] = "Použití: | Tip: "

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
        
        st.text_input("Název odrůdy:", value=st.session_state.d["name"], key=c_key("name"), placeholder="Např. surfinie červená")
        curr_name = get_current("name")
        
        if curr_name != st.session_state.d.get("last_name_check", ""):
            ln = curr_name.lower()
            matched_cat = None
            if any(x in ln for x in ["chilli", "chili", "jalape", "habanero", "páliv", "paliv"]):
                matched_cat = "Papriky - Pálivé"
            elif "rajče" in ln or "rajčata" in ln or "rajcata" in ln:
                matched_cat = "Rajčata"
            elif "paprika" in ln or "papriky" in ln:
                matched_cat = "Papriky - Sladké"
            elif any(x in ln for x in ["bazalka", "pažitka", "bylink", "máta", "koriandr", "tymián"]):
                matched_cat = "Bylinky"
            elif any(x in ln for x in ["muškát", "petúni", "surfin", "begóni", "pelargoni", "aksamitník", "afrikán", "kytka", "květin", "macešk", "lobelk", "fuchsi"]):
                matched_cat = "Květiny"
            
            st.session_state.d["last_name_check"] = curr_name
            if matched_cat and st.session_state.d.get("cat") != matched_cat:
                sync_to_d() 
                st.session_state.d["cat"] = matched_cat
                apply_template(matched_cat)
                st.session_state.form_key = str(uuid.uuid4())
                st.rerun()
        
        folder_check = clean_filename(curr_name)
        if curr_name and os.path.exists(os.path.join(DB_DIR, folder_check)):
            st.warning("⚠️ Odrůda již v archivu existuje!")
            if st.button("📂 Načíst existující data z archivu", type="primary"):
                loaded_d, loaded_img = load_label_data(folder_check)
                st.session_state.d.update(loaded_d)
                if st.session_state.d.get("cat") not in KATEGORIE: st.session_state.d["cat"] = "Ostatní"
                if "shu" not in st.session_state.d: st.session_state.d["shu"] = "" 
                st.session_state.d["img"] = loaded_img
                st.session_state.d["last_ai"] = ""
                st.session_state.form_key = str(uuid.uuid4())
                st.session_state.show_load_msg = True
                st.rerun()

        cat_idx = KATEGORIE.index(st.session_state.d["cat"]) if st.session_state.d["cat"] in KATEGORIE else KATEGORIE.index("Ostatní")
        selected_cat = st.selectbox("Kategorie pro uložení:", KATEGORIE, index=cat_idx, key=c_key("cat"))
        
        if selected_cat != st.session_state.d["cat"]:
            sync_to_d()
            st.session_state.d["cat"] = selected_cat
            apply_template(selected_cat)
            st.session_state.form_key = str(uuid.uuid4())
            st.rerun()

        if curr_name:
            st.info("🤖 **Prompt pro AI (Zkopírujte):**")
            
            cat = st.session_state.d["cat"]
            if cat == "Papriky - Pálivé":
                specifics = "Ř1: Stanoviště: ... | Zálivka: ...\nŘ2: Spon: ... | Výška: ...\nŘ3: Plod: ... | Hmotnost: ...\nŘ4: Použití: ... | Tip: ...\nŘ5: Pálivost: [Slovní popis] | SHU: [Číslo]"
            elif cat == "Bylinky":
                specifics = "Ř1: Stanoviště: ... | Zálivka: ...\nŘ2: Spon: ... | Výška: ...\nŘ3: Typ: [Trvalka/Letnička] | Sběr: [Květen - Září]\nŘ4: Použití: ... | Tip: ..."
            elif cat == "Květiny":
                specifics = "Ř1: Vzrůst: [Převis/Polopřevis/Vzpřímená] [Délka cm] | Typ: [Letnička/Trvalka]\nŘ2: ✿ Květ: [Měsíce, např. V-IX]\nŘ3: ☀ Stanoviště: [Slunné] nebo ☁ Stanoviště: [Stinné]\nŘ4: 💧💧💧 Zálivka: [Hojná] nebo 💧 Zálivka: [Mírná]"
            else:
                specifics = "Ř1: Stanoviště: ... | Zálivka: ...\nŘ2: Spon: ... | Výška: ...\nŘ3: Plod: ... | Hmotnost: ...\nŘ4: Použití: ... | Tip: ..."

            ai_prompt = f"Jsi odborník. Hledáme odrůdu: {curr_name}.\n!!! KRITICKÁ PRAVIDLA:\n1. OVĚŘ A OPRAV NÁZEV: Zjisti přesný oficiální název (např. 'rajče start' -> 'Rajče Start F1').\n2. PIŠ EXTRÉMNĚ STRUČNĚ (max 6 slov na řádek).\n3. PIŠ LAICKY PRO BĚŽNÉHO SPOTŘEBITELE. VYNECH VŠECHNA CIZÍ NEBO ODBORNÁ SLOVA. !!!\nVypiš to přesně takto:\nPŘESNÝ NÁZEV: (doplň oficiální název)\n{specifics}"
            st.code(ai_prompt, language="text")

            q = curr_name.replace(" ", "+")
            st.markdown(f"🔍 [Obrázky Google](https://google.cz/search?tbm=isch&q={q}+flower+macro+white+background) | [Data Itálie](https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+varieta+peso) | [Data Nizozemí](https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+ras+kenmerken)")

        up_file = st.file_uploader("📸 Nahrát staženou fotku:", type=["jpg", "png", "jpeg"], key=c_key("img_up"))
        if up_file:
            st.session_state.d["img"] = Image.open(up_file).convert("RGB")

        if st.session_state.d.get("img"):
            st.image(st.session_state.d["img"], width=180, caption="Aktuální fotka na cedulku")

    with col_data:
        st.header("2. Obsah Cedulky")

        ai_input = st.text_area("Vložit výsledek z AI:", height=120, key=c_key("ai"))
        if ai_input and ai_input != st.session_state.d.get("last_ai"):
            sync_to_d() 
            st.session_state.d["last_ai"] = ai_input
            clean_txt = ai_input.replace("**", "").replace("*", "")
            
            for line in clean_txt.split('\n'):
                if "PŘESNÝ NÁZEV:" in line.upper():
                    possible_name = line.split(":", 1)[1].strip()
                    if possible_name: st.session_state.d["name"] = possible_name
                elif "Ř1:" in line: st.session_state.d["r1"] = line.split("Ř1:")[1].strip()[:65]
                elif "Ř2:" in line: st.session_state.d["r2"] = line.split("Ř2:")[1].strip()[:65]
                elif "Ř3:" in line: st.session_state.d["r3"] = line.split("Ř3:")[1].strip()[:65]
                elif "Ř4:" in line: st.session_state.d["r4"] = line.split("Ř4:")[1].strip()[:65]
                elif "Ř5:" in line or "PÁLIVOST:" in line.upper(): 
                    st.session_state.d["shu"] = line.split(":", 1)[1].strip()[:65]
            
            st.session_state.form_key = str(uuid.uuid4())
            st.rerun()

        if st.session_state.d["cat"] == "Papriky - Pálivé":
            st.session_state.d["shu"] = st.text_input("🌶️ Pálivost (SHU):", value=st.session_state.d.get("shu", ""), max_chars=65, key=c_key("shu"))
        else:
            st.session_state.d["shu"] = get_current("shu")
        
        st.text_input("Řádek 1:", value=st.session_state.d["r1"], max_chars=65, key=c_key("r1"))
        st.text_input("Řádek 2:", value=st.session_state.d["r2"], max_chars=65, key=c_key("r2"))
        st.text_input("Řádek 3:", value=st.session_state.d["r3"], max_chars=65, key=c_key("r3"))
        st.text_input("Řádek 4:", value=st.session_state.d["r4"], max_chars=65, key=c_key("r4"))

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("💾 ULOŽIT DO SKLADU", use_container_width=True, type="primary"):
                sync_to_d() 
                f_name = st.session_state.d["name"]
                f_img = st.session_state.d.get("img")
                if f_name and f_img:
                    p = os.path.join(DB_DIR, clean_filename(f_name))
                    if not os.path.exists(p): os.makedirs(p)
                    d_out = {
                        "name": f_name, "cat": st.session_state.d["cat"],
                        "r1": st.session_state.d["r1"], "r2": st.session_state.d["r2"],
                        "r3": st.session_state.d["r3"], "r4": st.session_state.d["r4"],
                        "shu": st.session_state.d["shu"]
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
                    "r3": "Plod: | Hmotnost: ", "r4": "Použití: | Tip: ", 
                    "shu": "", "last_ai": "", "last_name_check": ""
                }
                st.session_state.form_key = str(uuid.uuid4())
                st.rerun()

    # --- NÁHLED A TISK ---
    c_name = get_current("name")
    c_img = st.session_state.d.get("img")
    c_shu = get_current("shu") if st.session_state.d["cat"] == "Papriky - Pálivé" else ""
    c_cat = st.session_state.d["cat"]
    
    if c_name and c_img:
        st.markdown("---")
        st.subheader("🖨️ Náhled a Tisk (A4)")
        with st.spinner("Generuji arch..."):
            f_b, f_r = get_czech_font("Bold"), get_czech_font("Regular")
            lines = [get_current("r1"), get_current("r2"), get_current("r3"), get_current("r4")]
            
            valid_lines = [r for r in lines if r.strip() and not r.endswith(": | ") and r.strip() != "✿" and r.strip() != "☀" and r.strip() != "💧"]
            if not valid_lines: valid_lines = lines

            single_lbl = draw_label(c_name, c_img, valid_lines, c_shu, c_cat, f_b, f_r)

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
                        if "shu" not in st.session_state.d: st.session_state.d["shu"] = ""
                        st.session_state.d["img"] = loaded_img
                        st.session_state.d["last_ai"] = ""
                        st.session_state.form_key = str(uuid.uuid4())
                        st.session_state.show_load_msg = True
                        st.rerun()

                    if c3.button("🗑️ Smazat", key=f"del_{f_name}", type="primary"):
                        shutil.rmtree(os.path.join(DB_DIR, f_name))
                        st.rerun()

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request
import unicodedata
import json
import shutil
import uuid
import zipfile

# --- 1. KONFIGURACE A ABSOLUTNÍ CESTA ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "archiv_cedulek")

KATEGORIE = ["Papriky - Sladké", "Papriky - Pálivé", "Rajčata", "Sadba", "Bylinky", "Květiny", "Ostatní"]

if not os.path.exists(DB_DIR): os.makedirs(DB_DIR)

st.set_page_config(page_title="Šlapánský Cedulátor 3000", page_icon="🌿", layout="wide")

# --- BOČNÍ PANEL S INFORMACEMI O SYSTÉMU ---
with st.sidebar:
    st.header("⚙️ Systémové informace")
    st.info("📂 **Cesta k vašemu archivu:**\n\n`" + DB_DIR + "`\n\n*(Zde se nacházejí všechny vaše uložené cedulky)*")

# PŘIDÁN ODPUZOVAČ PŘEKLADAČŮ A STYLOVÁNÍ OBŘÍCH ZÁLOŽEK
st.markdown("""
    <style>
    .stButton>button { border-radius: 8px; font-weight: bold; }
    .stTextArea textarea { background-color: #f8fbfa; border: 1px solid #1B5E20; }
    
    /* Vylepšení hlavních záložek (Tabs) - Obří a přehledné */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 70px;
        background-color: #f0f2f6;
        border-radius: 12px 12px 0 0;
        padding: 0 30px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e8f5e9 !important;
        border-bottom: 5px solid #1B5E20 !important;
    }
    .stTabs [data-baseweb="tab"] p {
        font-size: 26px !important;
        font-weight: 900 !important;
        color: #333333;
    }
    .stTabs [aria-selected="true"] p {
        color: #1B5E20 !important;
    }
    </style>
    <meta name="google" content="notranslate">
""", unsafe_allow_html=True)

# --- 2. GRAFICKÉ FUNKCE A VEKTOROVÉ IKONY ---
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

def draw_vector_icon(d, icon_type, x, y, size):
    if icon_type == "Květ":
        c = size // 2; r = size // 3
        d.ellipse([x+c-r, y+c-2*r, x+c+r, y+c], fill="#EC407A")
        d.ellipse([x+c-r, y+c, x+c+r, y+c+2*r], fill="#EC407A")
        d.ellipse([x+c-2*r, y+c-r, x+c, y+c+r], fill="#EC407A")
        d.ellipse([x+c, y+c-r, x+c+2*r, y+c+r], fill="#EC407A")
        d.ellipse([x+c-r//2, y+c-r//2, x+c+r//2, y+c+r//2], fill="#FFEE58")
    elif icon_type == "Slunce":
        pad = size // 5
        d.ellipse([x+pad, y+pad, x+size-pad, y+size-pad], fill="#FFA000")
        c = size//2
        d.line([(x+c, y), (x+c, y+size)], fill="#FFA000", width=4)
        d.line([(x, y+c), (x+size, y+c)], fill="#FFA000", width=4)
        d.line([(x+pad, y+pad), (x+size-pad, y+size-pad)], fill="#FFA000", width=4)
        d.line([(x+pad, y+size-pad), (x+size-pad, y+pad)], fill="#FFA000", width=4)
    elif icon_type == "Polostín":
        pad = size // 5
        d.ellipse([x+pad, y+pad, x+size-pad, y+size-pad], fill="#FFA000")
        d.pieslice([x+pad, y+pad, x+size-pad, y+size-pad], 270, 90, fill="#424242")
        c = size//2
        d.line([(x+c, y), (x+c, y+size)], fill="#FFA000", width=4) 
        d.line([(x, y+c), (x+c, y+c)], fill="#FFA000", width=4) 
        d.line([(x+c, y+c), (x+size, y+c)], fill="#424242", width=4) 
        d.line([(x+pad, y+pad), (x+c, y+c)], fill="#FFA000", width=4) 
        d.line([(x+pad, y+size-pad), (x+c, y+c)], fill="#FFA000", width=4) 
        d.line([(x+size-pad, y+pad), (x+c, y+c)], fill="#424242", width=4) 
        d.line([(x+size-pad, y+size-pad), (x+c, y+c)], fill="#424242", width=4) 
    elif icon_type == "Stín":
        pad = size // 5
        d.ellipse([x+pad, y+pad, x+size-pad, y+size-pad], fill="#424242")
        c = size//2
        d.line([(x+c, y), (x+c, y+size)], fill="#424242", width=4)
        d.line([(x, y+c), (x+size, y+c)], fill="#424242", width=4)
        d.line([(x+pad, y+pad), (x+size-pad, y+size-pad)], fill="#424242", width=4)
        d.line([(x+pad, y+size-pad), (x+size-pad, y+pad)], fill="#424242", width=4)
    elif icon_type == "Kapka":
        c = x + size//2
        d.polygon([(c, y+size//6), (x+size//4, y+size*3//4), (x+size*3//4, y+size*3//4)], fill="#29B6F6")
        d.ellipse([x+size//4, y+size//2, x+size*3//4, y+size], fill="#29B6F6")

def draw_plant_pot_bottom(d, p_type, cx, cy, size):
    pot_w = size * 0.4
    pot_h = size * 0.3
    pot_y = cy 
    
    d.polygon([
        (cx - pot_w/2, pot_y), (cx + pot_w/2, pot_y), 
        (cx + pot_w/2 - 10, pot_y + pot_h), (cx - pot_w/2 + 10, pot_y + pot_h)
    ], fill="#8D6E63")
    d.rectangle([cx - pot_w/2 - 8, pot_y, cx + pot_w/2 + 8, pot_y + 12], fill="#5D4037")
    
    if p_type == "vzpřímená":
        d.line([(cx, pot_y), (cx, pot_y - size*0.45)], fill="#4CAF50", width=12) 
        d.ellipse([cx-35, pot_y-size*0.3, cx-5, pot_y-size*0.3+30], fill="#81C784")
        d.ellipse([cx+5, pot_y-size*0.4, cx+35, pot_y-size*0.4+30], fill="#81C784")
        d.ellipse([cx-25, pot_y-size*0.6, cx+25, pot_y-size*0.6+50], fill="#D81B60") 
    elif p_type == "převis":
        d.line([(cx, pot_y), (cx+size*0.3, pot_y-size*0.1), (cx+size*0.4, pot_y+size*0.4)], fill="#4CAF50", width=10)
        d.line([(cx, pot_y), (cx-size*0.3, pot_y-size*0.1), (cx-size*0.4, pot_y+size*0.4)], fill="#4CAF50", width=10)
        d.ellipse([cx+size*0.4-20, pot_y+size*0.2, cx+size*0.4+20, pot_y+size*0.2+40], fill="#D81B60")
        d.ellipse([cx-size*0.4-20, pot_y+size*0.2, cx-size*0.4+20, pot_y+size*0.2+40], fill="#D81B60")
    elif p_type == "polopřevis":
        d.line([(cx, pot_y), (cx+size*0.3, pot_y-size*0.1), (cx+size*0.4, pot_y+size*0.1)], fill="#4CAF50", width=10)
        d.line([(cx, pot_y), (cx-size*0.3, pot_y-size*0.1), (cx-size*0.4, pot_y+size*0.1)], fill="#4CAF50", width=10)
        d.ellipse([cx+size*0.4-15, pot_y, cx+size*0.4+15, pot_y+30], fill="#D81B60")
        d.ellipse([cx-size*0.4-15, pot_y, cx-size*0.4+15, pot_y+30], fill="#D81B60")
    else: 
        d.ellipse([cx-30, pot_y-size*0.2, cx-5, pot_y-size*0.2+25], fill="#81C784")
        d.ellipse([cx+5, pot_y-size*0.3, cx+30, pot_y-size*0.3+25], fill="#81C784")

def draw_bottom_justified_paragraph(d, text, start_x, top_limit_y, bottom_y, max_w, font_bold, font_reg):
    curr_size = 45 
    best_size = curr_size
    lines_data = []
    
    text = text.replace('|', ' | ')
    words_raw = text.split()
    if not words_raw: return

    max_h = bottom_y - top_limit_y

    while curr_size >= 18:
        f_b = ImageFont.truetype(font_bold, curr_size) if font_bold else ImageFont.load_default()
        f_r = ImageFont.truetype(font_reg, curr_size) if font_reg else ImageFont.load_default()
            
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

    line_spacing = int(best_size * 1.5)
    total_h = len(lines_data) * line_spacing
    y = bottom_y - total_h
    
    f_b = ImageFont.truetype(font_bold, best_size) if font_bold else ImageFont.load_default()
    f_r = ImageFont.truetype(font_reg, best_size) if font_reg else ImageFont.load_default()

    for i, (line_words, line_w) in enumerate(lines_data):
        if len(line_words) == 1 or i == len(lines_data) - 1:
            x = start_x
            for word, _, w_len in line_words:
                font = f_b if word.endswith(':') else f_r
                fill = "#004D40" if word.endswith(':') else ("#666666" if word == '|' else "#222222")
                d.text((x, y), word, fill=fill, font=font)
                x += w_len + d.textlength(" ", font=font)
        else:
            total_word_w = sum(w_len for _, _, w_len in line_words)
            total_space = max_w - total_word_w
            gap = total_space / (len(line_words) - 1)

            x = start_x
            for j, (word, _, w_len) in enumerate(line_words):
                font = f_b if word.endswith(':') else f_r
                fill = "#004D40" if word.endswith(':') else ("#666666" if word == '|' else "#222222")
                d.text((x, y), word, fill=fill, font=font)
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
    
    if " - " in name:
        parts = name.split(" - ", 1)
        main_title = parts[0].strip()
        sub_title = parts[1].strip()
    else:
        main_title = name.strip()
        sub_title = ""

    start_title_size = 110 if cat == "Sadba" else 85
    title_size = start_title_size
    f_t = ImageFont.truetype(font_bold, title_size) if font_bold else ImageFont.load_default()
    
    while font_bold and d.textlength(main_title.upper(), font=f_t) > (L_W - 80) and title_size > 30:
        title_size -= 5
        f_t = ImageFont.truetype(font_bold, title_size)
        
    d.text((L_W//2, y), main_title.upper(), fill="#004D40", anchor="mt", font=f_t)
    y += int(title_size * 1.2) 

    if sub_title:
        sub_size = int(title_size * 0.85) 
        f_sub = ImageFont.truetype(font_bold, sub_size) if font_bold else ImageFont.load_default()
        while font_bold and d.textlength(sub_title.upper(), font=f_sub) > (L_W - 80) and sub_size > 20:
            sub_size -= 5
            f_sub = ImageFont.truetype(font_bold, sub_size)
        
        d.text((L_W//2, y), sub_title.upper(), fill="#D32F2F", anchor="mt", font=f_sub)
        y += int(sub_size * 1.3) + 10
    else:
        y += 10
    
    if cat == "Sadba":
        bottom_zone_y = L_H - 220 
        
        if img_plant:
            max_th = bottom_zone_y - y - 30 
            max_tw = L_W - 80 
            w, h = img_plant.size
            ratio = min(max_tw/w, max_th/h)
            new_size = (int(w*ratio), int(h*ratio))
            resized_img = img_plant.resize(new_size, Image.Resampling.LANCZOS)
            
            img_x = (L_W - new_size[0]) // 2
            img_y = y + (max_th - new_size[1]) // 2 
            pad = 12
            d.rectangle([img_x - pad, img_y - pad, img_x + new_size[0] + pad, img_y + new_size[1] + pad], outline="#004D40", width=4)
            lbl.paste(resized_img, (img_x, img_y))
            
        f_p = ImageFont.truetype(font_bold, 100) if font_bold else ImageFont.load_default()
        kc_w = d.textlength("Kč", font=f_p)
        bx_w, bx_h = 420, 160
        total_price_w = bx_w + 30 + kc_w
        
        bx_x = (L_W - total_price_w) // 2 
        bx_y = bottom_zone_y + 20
        
        d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="#004D40", width=12)
        d.text((bx_x + bx_w + 30, bx_y + bx_h//2), "Kč", fill="black", anchor="lm", font=f_p)

    elif cat == "Květiny":
        bottom_zone_y = L_H - 240 
        
        kvet_raw = lines_text[1].split(":")[-1].strip() if len(lines_text) > 1 else ""
        slunce_raw = lines_text[2].split(":")[-1].strip() if len(lines_text) > 2 else ""
        voda_raw = lines_text[3].split(":")[-1].strip() if len(lines_text) > 3 else ""
        
        kvet_txt = kvet_raw.replace("✿", "").strip()
        slunce_lower = slunce_raw.lower()
        has_polostin = "polost" in slunce_lower
        has_stin = ("stín" in slunce_lower or "stin" in slunce_lower) and not has_polostin
        has_slunce = "slun" in slunce_lower or "svět" in slunce_lower or "přím" in slunce_lower
        
        stan_icons = []
        if has_slunce and has_polostin: stan_icons = ["Slunce", "Polostín"]
        elif has_polostin: stan_icons = ["Polostín"]
        elif has_stin: stan_icons = ["Stín"]
        elif has_slunce: stan_icons = ["Slunce"]
        else: stan_icons = ["Slunce", "Polostín"] 
        
        slunce_txt = slunce_raw.replace("☀", "").replace("☁", "").replace("⛅", "").strip()
        
        voda_lower = voda_raw.lower()
        if any(w in voda_lower for w in ["hojn", "hodně", "vydat", "víc", "vysok", "3"]) or voda_raw.count("💧") >= 3: drops = 3
        elif any(w in voda_lower for w in ["mál", "suš", "občas", "1"]) or voda_raw.count("💧") == 1: drops = 1
        else: drops = 2 
            
        voda_txt = voda_raw.replace("💧", "").strip()
        
        items = []
        if kvet_txt: items.append(("Květ", kvet_txt, ["Květ"]))
        if slunce_txt: items.append(("Stanoviště", slunce_txt, stan_icons))
        if voda_txt: items.append(("Zálivka", voda_txt, ["Kapka"] * drops))
        
        icon_size = 55
        icon_spacing_y = 20
        total_icons_height = (icon_size * 2) + icon_spacing_y if len(items) > 1 else icon_size
        
        if img_plant:
            max_th = bottom_zone_y - y - total_icons_height - 30 
            max_tw = L_W - 120 
            w, h = img_plant.size
            ratio = min(max_tw/w, max_th/h)
            new_size = (int(w*ratio), int(h*ratio))
            resized_img = img_plant.resize(new_size, Image.Resampling.LANCZOS)
            
            img_x = (L_W - new_size[0]) // 2
            img_y = y
            pad = 12
            d.rectangle([img_x - pad, img_y - pad, img_x + new_size[0] + pad, img_y + new_size[1] + pad], outline="#004D40", width=4)
            lbl.paste(resized_img, (img_x, img_y))
            y += new_size[1] + 30 
            
        f_icon_txt = ImageFont.truetype(font_bold, 45) if font_bold else ImageFont.load_default()
        
        centers = [
            (L_W * 0.28, y), 
            (L_W * 0.72, y), 
            (L_W * 0.5, y + icon_size + icon_spacing_y)
        ]
        
        for i, (i_type, txt, icon_list) in enumerate(items):
            if i < len(centers):
                center_x, icon_y = centers[i]
                txt_w = d.textlength(txt, font=f_icon_txt)
                icons_total_w = len(icon_list) * icon_size + (len(icon_list)-1) * 10
                total_w = icons_total_w + 20 + txt_w
                start_x = int(center_x - (total_w / 2))
                
                curr_x = start_x
                for icon_name in icon_list:
                    draw_vector_icon(d, icon_name, curr_x, icon_y, icon_size)
                    curr_x += icon_size + 10
                    
                d.text((curr_x + 10, icon_y + (icon_size//2)), txt, fill="#333333", anchor="lm", font=f_icon_txt)
        
        f_p = ImageFont.truetype(font_bold, 100) if font_bold else ImageFont.load_default()
        kc_w = d.textlength("Kč", font=f_p)
        
        bx_w, bx_h = 400, 160
        total_price_w = bx_w + 30 + kc_w
        bx_x = L_W - total_price_w - 50 
        bx_y = bottom_zone_y + 30
        
        d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="#004D40", width=12)
        d.text((bx_x + bx_w + 30, bx_y + bx_h//2), "Kč", fill="black", anchor="lm", font=f_p)
        
        growth_line = lines_text[0].lower() if lines_text else ""
        p_type = "neznámá"
        if "polopřevis" in growth_line or "poloprevis" in growth_line: p_type = "polopřevis"
        elif "převis" in growth_line or "previs" in growth_line: p_type = "převis"
        elif "vzpřímen" in growth_line or "vzprimen" in growth_line: p_type = "vzpřímená"
        
        pot_size = 160
        pot_center_x = 160 
        draw_plant_pot_bottom(d, p_type, pot_center_x, bottom_zone_y + 40, pot_size)
        
        raw_growth = lines_text[0] if lines_text else ""
        parts = raw_growth.replace("Vzrůst:", "").replace("Typ:", "").replace("⤵", "").replace("⬆", "").replace("↘", "").split("|")
        part1 = parts[0].strip() if len(parts) > 0 else ""
        part2 = parts[1].strip() if len(parts) > 1 else ""
            
        text_start_x = pot_center_x + (pot_size // 2) + 20
        max_text_w = bx_x - text_start_x - 30 
        
        p1_size = 45
        f_growth = ImageFont.truetype(font_bold, p1_size) if font_bold else ImageFont.load_default()
        while font_bold and d.textlength(part1, font=f_growth) > max_text_w and p1_size > 20:
            p1_size -= 2
            f_growth = ImageFont.truetype(font_bold, p1_size)
            
        p2_size = 38
        f_type = ImageFont.truetype(font_reg, p2_size) if font_reg else ImageFont.load_default()
        while font_reg and d.textlength(part2, font=f_type) > max_text_w and p2_size > 15:
            p2_size -= 2
            f_type = ImageFont.truetype(font_reg, p2_size)
        
        text_y = bottom_zone_y + 60
        if part1:
            d.text((text_start_x, text_y), part1, fill="#222222", anchor="lt", font=f_growth)
            text_y += int(p1_size * 1.3)
        if part2:
            d.text((text_start_x, text_y), part2, fill="#555555", anchor="lt", font=f_type)

    else:
        if shu_text and shu_text.strip():
            shu_size = 70
            f_shu = ImageFont.truetype(font_bold, shu_size) if font_bold else ImageFont.load_default()
            while font_bold and d.textlength(shu_text.upper(), font=f_shu) > (L_W - 100) and shu_size > 30:
                shu_size -= 5
                f_shu = ImageFont.truetype(font_bold, shu_size)
            d.text((L_W//2, y), shu_text.upper(), fill="#D32F2F", anchor="mt", font=f_shu) 
            y += int(shu_size * 1.3) + 10 
        else:
            y += 20 
        
        bottom_zone_y = L_H - 220
        text_reserved_h = 160 
        
        if img_plant:
            max_th = bottom_zone_y - text_reserved_h - y - 10 
            max_tw = L_W - 120 
            w, h = img_plant.size
            ratio = min(max_tw/w, max_th/h)
            new_size = (int(w*ratio), int(h*ratio))
            resized_img = img_plant.resize(new_size, Image.Resampling.LANCZOS)
            
            img_x = (L_W - new_size[0]) // 2
            img_y = y
            pad = 12
            d.rectangle([img_x - pad, img_y - pad, img_x + new_size[0] + pad, img_y + new_size[1] + pad], outline="#004D40", width=4)
            lbl.paste(resized_img, (img_x, img_y))
            y += new_size[1] + 30 
            
        valid_lines = [r.strip() for r in lines_text if r.strip() and not r.endswith(": | ")]
        combined_text = " ".join(valid_lines)
        
        draw_bottom_justified_paragraph(d, combined_text, 100, y, bottom_zone_y - 10, L_W - 200, font_bold, font_reg)
            
        f_p = ImageFont.truetype(font_bold, 100) if font_bold else ImageFont.load_default()
        kc_w = d.textlength("Kč", font=f_p)
        bx_w, bx_h = 420, 160
        total_price_w = bx_w + 30 + kc_w
        
        bx_x = (L_W - total_price_w) // 2 
        bx_y = bottom_zone_y + 20
        
        d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="#004D40", width=12)
        d.text((bx_x + bx_w + 30, bx_y + bx_h//2), "Kč", fill="black", anchor="lm", font=f_p)

    d.rectangle([0, 0, L_W-1, L_H-1], outline="#EEEEEE", width=3)
    return lbl

def generate_pdfs(c_name, c_img, lines_text, c_shu, c_cat, font_bold, font_reg):
    valid_lines = [r for r in lines_text if r.strip() and not r.endswith(": | ") and r.strip() != "✿" and r.strip() != "☀" and r.strip() != "💧"]
    if not valid_lines: valid_lines = lines_text

    single_lbl = draw_label(c_name, c_img, valid_lines, c_shu, c_cat, font_bold, font_reg)

    canvas_4 = Image.new('RGB', (2480, 3508), 'white')
    canvas_4.paste(single_lbl, (0, 0))
    canvas_4.paste(single_lbl, (1240, 0))
    canvas_4.paste(single_lbl, (0, 1754))
    canvas_4.paste(single_lbl, (1240, 1754))

    pdf_buf_4 = io.BytesIO()
    canvas_4.save(pdf_buf_4, format="PDF", resolution=300, quality=100)

    canvas_2 = Image.new('RGB', (3508, 2480), 'white')
    single_lbl_a5 = single_lbl.resize((1754, 2480), Image.Resampling.LANCZOS)
    canvas_2.paste(single_lbl_a5, (0, 0))
    canvas_2.paste(single_lbl_a5, (1754, 0))

    pdf_buf_2 = io.BytesIO()
    canvas_2.save(pdf_buf_2, format="PDF", resolution=300, quality=100)

    return canvas_4, pdf_buf_4, pdf_buf_2

# --- 3. BEZPEČNÁ PAMĚŤ ---
if 'form_key' not in st.session_state: st.session_state.form_key = str(uuid.uuid4())
if 'active_print_preview' not in st.session_state: st.session_state.active_print_preview = None 
if 'd' not in st.session_state:
    st.session_state.d = {
        "name": "", "cat": "Ostatní", "img": None,
        "r1": "Stanoviště: | Zálivka: ", "r2": "Spon: | Výška: ",
        "r3": "Plod: | Hmotnost: ", "r4": "Použití: | Tip: ", 
        "shu": "", "last_ai": "", "last_name_check": "",
        "loaded_from": None
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
    current_r1 = st.session_state.d.get("r1", "")
    is_default_or_empty = current_r1 in ["", "Stanoviště: | Zálivka: ", "Vzrůst: Převis 60 cm | Typ: Letnička"]
    
    if not is_default_or_empty: return 

    if cat == "Bylinky":
        st.session_state.d["r1"] = "Stanoviště: | Zálivka: "
        st.session_state.d["r2"] = "Spon: | Výška: "
        st.session_state.d["r3"] = "Typ: | Sběr: "
        st.session_state.d["r4"] = "Použití: | Tip: "
    elif cat == "Květiny":
        st.session_state.d["r1"] = "Vzrůst: Převis 60 cm | Typ: Letnička"
        st.session_state.d["r2"] = "Květ: V-IX"
        st.session_state.d["r3"] = "Stanoviště: Slunné a Polostín"
        st.session_state.d["r4"] = "Zálivka: Hojná"
    elif cat == "Sadba":
        st.session_state.d["r1"] = ""
        st.session_state.d["r2"] = ""
        st.session_state.d["r3"] = ""
        st.session_state.d["r4"] = ""
    else:
        st.session_state.d["r1"] = "Stanoviště: | Zálivka: "
        st.session_state.d["r2"] = "Spon: | Výška: "
        st.session_state.d["r3"] = "Plod: | Hmotnost: "
        st.session_state.d["r4"] = "Použití: | Tip: "

# Vytvoření seznamu všech uložených cedulek pro navigaci šipkami v editoru
all_saved_folders = [f for f in os.listdir(DB_DIR) if os.path.isdir(os.path.join(DB_DIR, f))]
nav_items = []
for f in all_saved_folders:
    p = os.path.join(DB_DIR, f, "data.json")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as file:
            info = json.load(file)
            nav_items.append((f, info.get('name', '').lower()))
nav_items.sort(key=lambda x: x[1]) # Abecední řazení
ordered_folders = [x[0] for x in nav_items]

# --- 4. APLIKACE A UI ---
st.title("🌿 Šlapánský Cedulátor 3000")
st.markdown("#### *generátor cedulek*")

if st.session_state.show_load_msg:
    st.success("✅ Cedulka úspěšně načtena do Editoru!")
    st.session_state.show_load_msg = False

# OPRAVA: Prohození záložek (Sklad je nyní první a hlavní)
tab_sklad, tab_editor = st.tabs(["🗃️ Sklad / Archiv", "🖌️ Editor & Tisk"])

# =========================================================
# ZÁLOŽKA 1: SKLAD / ARCHIV
# =========================================================
with tab_sklad:
    c_head, c_search, c_sort = st.columns([2, 2, 1])
    with c_head:
        # OPRAVA: POUŽIT SPRÁVNÝ NÁZEV SEZNAMU
        st.header(f"📊 Přehled skladu ({len(all_saved_folders)} položek)")
    with c_search:
        search_q = st.text_input("🔍 Hledat odrůdu:", placeholder="Zadejte část názvu...").lower()
    with c_sort:
        sort_by = st.selectbox("Třídit podle:", ["Název (A-Z)", "Název (Z-A)"])

    for kat in KATEGORIE:
        kat_items = []
        for f in all_saved_folders:
            path = os.path.join(DB_DIR, f, "data.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as file:
                    info = json.load(file)
                    item_name = info.get('name', 'Neznámý').lower()
                    if info.get("cat", "Ostatní") == kat:
                        if search_q in item_name:
                            kat_items.append((f, info))

        if kat_items:
            if sort_by == "Název (A-Z)":
                kat_items.sort(key=lambda x: x[1].get('name', '').lower())
            else:
                kat_items.sort(key=lambda x: x[1].get('name', '').lower(), reverse=True)

            with st.expander(f"📂 {kat} ({len(kat_items)})", expanded=(bool(search_q))):
                
                if st.button(f"📦 Připravit celou kategorii ke stažení (ZIP)", key=f"zip_prep_{kat}", type="primary"):
                    with st.spinner(f"Balím {len(kat_items)} položek do ZIPu, vydržte..."):
                        zip_buffer = io.BytesIO()
                        f_b, f_r = get_czech_font("Bold"), get_czech_font("Regular")
                        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                            for f_name, info in kat_items:
                                img_p = os.path.join(DB_DIR, f_name, "photo.jpg")
                                if os.path.exists(img_p):
                                    p_name = info.get('name', 'Neznámý')
                                    p_cat = info.get('cat', 'Ostatní')
                                    p_shu = info.get('shu', '')
                                    p_lines = [info.get('r1', ''), info.get('r2', ''), info.get('r3', ''), info.get('r4', '')]
                                    p_img = Image.open(img_p).convert("RGB")
                                    
                                    cv4, pb4, pb2 = generate_pdfs(p_name, p_img, p_lines, p_shu, p_cat, f_b, f_r)
                                    safe_name = clean_filename(p_name.split("-")[0] if "-" in p_name else p_name)
                                    
                                    zip_file.writestr(f"{safe_name}_4x_A6.pdf", pb4.getvalue())
                                    zip_file.writestr(f"{safe_name}_2x_A5.pdf", pb2.getvalue())
                                    
                        st.session_state[f"zip_ready_{kat}"] = zip_buffer.getvalue()
                
                if st.session_state.get(f"zip_ready_{kat}"):
                    st.success("✅ ZIP je připraven!")
                    st.download_button(f"📥 STÁHNOUT ZIP ARCHIV ({kat})", data=st.session_state[f"zip_ready_{kat}"], file_name=f"Cedulky_{kat}.zip", mime="application/zip", type="secondary")
                    
                st.markdown("---")

                for f_name, info in kat_items:
                    c1, c2, c3 = st.columns([1, 2, 2.5])
                    img_p = os.path.join(DB_DIR, f_name, "photo.jpg")
                    has_img = os.path.exists(img_p)
                    if has_img: c1.image(img_p, width=120)

                    disp_name = info.get('name', 'Neznámý')
                    if " - " in disp_name:
                        disp_name = disp_name.replace(" - ", " <span style='color:red;'>- ") + "</span>"
                    c2.markdown(f"**{disp_name}**", unsafe_allow_html=True)
                    
                    if info.get('cat') != "Sadba":
                        c2.caption(f"{info.get('r1', '')} \n{info.get('r2', '')}")

                    btn_col1, btn_col2, btn_col3 = c3.columns(3)
                    
                    if btn_col1.button("✏️ Upravit v Editoru", key=f"load_{f_name}", width="stretch"):
                        loaded_d, loaded_img = load_label_data(f_name)
                        st.session_state.d.update(loaded_d)
                        if st.session_state.d.get("cat") not in KATEGORIE: st.session_state.d["cat"] = "Ostatní"
                        if "shu" not in st.session_state.d: st.session_state.d["shu"] = ""
                        st.session_state.d["img"] = loaded_img
                        st.session_state.d["last_ai"] = loaded_d.get("raw_ai", "")
                        st.session_state.d["loaded_from"] = f_name
                        st.session_state.form_key = str(uuid.uuid4())
                        st.session_state.show_load_msg = True
                        st.rerun()

                    if btn_col2.button("🖨️ Tisk", key=f"prnt_{f_name}", width="stretch"):
                        if st.session_state.active_print_preview == f_name:
                            st.session_state.active_print_preview = None
                        else:
                            st.session_state.active_print_preview = f_name
                        st.rerun()

                    if btn_col3.button("🗑️ Smazat", key=f"del_{f_name}", width="stretch"):
                        shutil.rmtree(os.path.join(DB_DIR, f_name))
                        if st.session_state.active_print_preview == f_name:
                            st.session_state.active_print_preview = None
                        st.rerun()

                    if st.session_state.active_print_preview == f_name:
                        with st.container():
                            st.markdown("---")
                            with st.spinner(f"Generuji PDF pro {disp_name}..."):
                                p_name = info.get('name', 'Neznámý')
                                p_cat = info.get('cat', 'Ostatní')
                                p_shu = info.get('shu', '')
                                p_lines = [info.get('r1', ''), info.get('r2', ''), info.get('r3', ''), info.get('r4', '')]
                                p_img = Image.open(img_p).convert("RGB") if has_img else None
                                
                                if p_img and p_name:
                                    f_b, f_r = get_czech_font("Bold"), get_czech_font("Regular")
                                    cv4, pb4, pb2 = generate_pdfs(p_name, p_img, p_lines, p_shu, p_cat, f_b, f_r)
                                    
                                    c_prev, c_dwn = st.columns([1, 1])
                                    c_prev.image(cv4, width="stretch")
                                    
                                    dwn_name = clean_filename(p_name.split("-")[0] if "-" in p_name else p_name)
                                    c_dwn.download_button("📥 STÁHNOUT 4 CEDULKY (A6)", pb4.getvalue(), f"{dwn_name}_4x_A6.pdf", mime="application/pdf", type="primary", key=f"d4_{f_name}", width="stretch")
                                    c_dwn.markdown("<br>", unsafe_allow_html=True)
                                    c_dwn.download_button("📥 STÁHNOUT 2 CEDULKY (A5)", pb2.getvalue(), f"{dwn_name}_2x_A5.pdf", mime="application/pdf", type="secondary", key=f"d2_{f_name}", width="stretch")
                                else:
                                    st.error("Chybí obrázek nebo název, nelze generovat tisk.")
                            st.markdown("---")

# =========================================================
# ZÁLOŽKA 2: EDITOR & TISK
# =========================================================
with tab_editor:
    
    # --- HORNÍ NAVIGAČNÍ PANEL PRO EDITOR ---
    c_nav1, c_nav2, c_nav3 = st.columns([1, 1.5, 1])
    
    if st.session_state.d.get("loaded_from") and st.session_state.d["loaded_from"] in ordered_folders:
        curr_idx = ordered_folders.index(st.session_state.d["loaded_from"])
        
        with c_nav1:
            if curr_idx > 0:
                if st.button("⬅️ Předchozí v archivu", width="stretch"):
                    prev_f = ordered_folders[curr_idx - 1]
                    loaded_d, loaded_img = load_label_data(prev_f)
                    st.session_state.d.update(loaded_d)
                    if "shu" not in st.session_state.d: st.session_state.d["shu"] = ""
                    st.session_state.d["img"] = loaded_img
                    st.session_state.d["last_ai"] = loaded_d.get("raw_ai", "")
                    st.session_state.d["loaded_from"] = prev_f
                    st.session_state.form_key = str(uuid.uuid4())
                    st.rerun()
        
        with c_nav3:
            if curr_idx < len(ordered_folders) - 1:
                if st.button("Další v archivu ➡️", width="stretch"):
                    next_f = ordered_folders[curr_idx + 1]
                    loaded_d, loaded_img = load_label_data(next_f)
                    st.session_state.d.update(loaded_d)
                    if "shu" not in st.session_state.d: st.session_state.d["shu"] = ""
                    st.session_state.d["img"] = loaded_img
                    st.session_state.d["last_ai"] = loaded_d.get("raw_ai", "")
                    st.session_state.d["loaded_from"] = next_f
                    st.session_state.form_key = str(uuid.uuid4())
                    st.rerun()
                    
    with c_nav2:
        if st.button("➕ Založit novou čistou cedulku", width="stretch", type="primary"):
            st.session_state.d = {
                "name": "", "cat": "Ostatní", "img": None,
                "r1": "Stanoviště: | Zálivka: ", "r2": "Spon: | Výška: ",
                "r3": "Plod: | Hmotnost: ", "r4": "Použití: | Tip: ", 
                "shu": "", "last_ai": "", "last_name_check": "",
                "loaded_from": None
            }
            st.session_state.form_key = str(uuid.uuid4())
            st.rerun()
            
    st.markdown("---")

    # --- SAMOTNÝ EDITOR ---
    col_search, col_data = st.columns([1, 1.2], gap="large")

    with col_search:
        st.header("1. Zadání a Rešerše")
        
        st.text_input("Název odrůdy:", value=st.session_state.d["name"], key=c_key("name"), placeholder="Např. Dýně goliáš - dorůstá až 50kg")
        st.caption("💡 **Tip pro profíky:** Použijte pomlčku s mezerami (` - `) pro rozdělení názvu. Text za pomlčkou bude ČERVENĚ na novém řádku!")
        
        curr_name = get_current("name")
        
        if curr_name != st.session_state.d.get("last_name_check", ""):
            ln = curr_name.lower()
            matched_cat = None
            if any(x in ln for x in ["chilli", "chili", "jalape", "habanero", "páliv", "paliv"]):
                matched_cat = "Papriky - Pálivé"
            elif any(x in ln for x in ["sazenic", "sadba", "roubovan"]):
                matched_cat = "Sadba"
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
        
        folder_check = clean_filename(curr_name.split("-")[0].strip() if "-" in curr_name else curr_name)
        if curr_name and os.path.exists(os.path.join(DB_DIR, folder_check)) and st.session_state.d.get("loaded_from") != folder_check:
            st.warning("⚠️ Odrůda s tímto názvem už ve skladu existuje!")

        cat_idx = KATEGORIE.index(st.session_state.d["cat"]) if st.session_state.d["cat"] in KATEGORIE else KATEGORIE.index("Ostatní")
        selected_cat = st.selectbox("Kategorie pro uložení:", KATEGORIE, index=cat_idx, key=c_key("cat"))
        
        if selected_cat != st.session_state.d["cat"]:
            sync_to_d()
            st.session_state.d["cat"] = selected_cat
            apply_template(selected_cat)
            st.session_state.form_key = str(uuid.uuid4())
            st.rerun()

        if curr_name:
            cat = st.session_state.d["cat"]
            if cat == "Sadba":
                st.info("💡 **Pro kategorii Sadba není potřeba text od AI.** Stačí pouze dohledat a nahrát hezkou fotku sazenice.")
            else:
                st.info("🤖 **Prompt pro AI (Zkopírujte):**")
                if cat == "Papriky - Pálivé":
                    specifics = "Ř1: Stanoviště: ... | Zálivka: ...\nŘ2: Spon: ... | Výška: ...\nŘ3: Plod: ... | Hmotnost: ...\nŘ4: Použití: ... | Tip: ...\nŘ5: Pálivost: [Slovní popis] | SHU: [Číslo]"
                elif cat == "Bylinky":
                    specifics = "Ř1: Stanoviště: ... | Zálivka: ...\nŘ2: Spon: ... | Výška: ...\nŘ3: Typ: [Trvalka/Letnička] | Sběr: [Květen - Září]\nŘ4: Použití: ... | Tip: ..."
                elif cat == "Květiny":
                    specifics = "Ř1: Vzrůst: [Klíčové slovo: Převis/Polopřevis/Vzpřímená] [Délka, např. 60 cm] | Typ: [Letnička/Trvalka]\nŘ2: Květ: [Měsíce, např. V-IX]\nŘ3: Stanoviště: [Slunné / Polostín / Stín / Slunné a Polostín]\nŘ4: Zálivka: [Hojná / Mírná / Málo]"
                else:
                    specifics = "Ř1: Stanoviště: ... | Zálivka: ...\nŘ2: Spon: ... | Výška: ...\nŘ3: Plod: ... | Hmotnost: ...\nŘ4: Použití: ... | Tip: ..."

                search_name = curr_name.split(" - ")[0].strip() if " - " in curr_name else curr_name

                ai_prompt = f"Jsi odborník. Hledáme odrůdu: {search_name}.\n!!! KRITICKÁ PRAVIDLA:\n1. OVĚŘ A OPRAV NÁZEV: Zjisti přesný oficiální název. PEČLIVĚ ZKONTROLUJ, ZDA MÁ ODRŮDA PŘÍVLASTEK 'F1' (hybrid). Pokud ano, bezpodmínečně ho přidej na konec názvu (např. 'Rajče Start F1').\n2. PIŠ EXTRÉMNĚ STRUČNĚ (max 6 slov na řádek pro řádky 1-5).\n3. PIŠ LAICKY PRO BĚŽNÉHO SPOTŘEBITELE. VYNECH CIZÍ A ODBORNÁ SLOVA. !!!\nVypiš to přesně takto:\nPŘESNÝ NÁZEV: (doplň oficiální název včetně F1, pokud to je F1)\n{specifics}\nZAJÍMAVOSTI:\n- (1. zajímavost o pěstování, původu nebo chuti)\n- (2. zajímavost)\n- (3. zajímavost)"
                st.code(ai_prompt, language="text")

            search_q = (curr_name.split(" - ")[0].strip() if " - " in curr_name else curr_name).replace(" ", "+")
            st.markdown(f"🔍 [Google Obrázky (Sazenice / Profi)](https://google.cz/search?tbm=isch&q={search_q}+plant+seedling+macro+white+background) | 🌳 [Google Obrázky (Dospělá rostlina / Botanická)](https://google.cz/search?tbm=isch&q={search_q}+latinský+název+rostlina)")

        up_file = st.file_uploader("📸 Nahrát staženou fotku:", type=["jpg", "png", "jpeg"], key=c_key("img_up"))
        if up_file:
            st.session_state.d["img"] = Image.open(up_file).convert("RGB")

        if st.session_state.d.get("img"):
            st.image(st.session_state.d["img"], width=180, caption="Aktuální fotka na cedulku")

    with col_data:
        st.header("2. Obsah Cedulky")

        if st.session_state.d["cat"] == "Sadba":
            st.success("🌱 **Režim Sadba:** Bude vytištěn pouze velký název, maximálně zvětšená fotka a cena.")
        else:
            ai_val = st.session_state.d.get("last_ai", "")
            ai_input = st.text_area("Vložit výsledek z AI (Zůstane uložen s informacemi navíc):", value=ai_val, height=150, key=c_key("ai"))
            
            if ai_input and ai_input != ai_val:
                sync_to_d() 
                st.session_state.d["last_ai"] = ai_input
                
                lines = ai_input.replace("**", "").replace("*", "").replace("\r", "\n").split('\n')
                
                for line in lines:
                    line_up = line.upper().strip()
                    
                    if line_up.startswith("PŘESNÝ NÁZEV:"):
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            possible_name = parts[1].strip()
                            if possible_name and " - " not in st.session_state.d["name"]:
                                st.session_state.d["name"] = possible_name
                    
                    elif line_up.startswith("Ř1:") or line_up.startswith("R1:"):
                        parts = line.split(":", 1)
                        if len(parts) > 1: st.session_state.d["r1"] = parts[1].strip()[:65]
                        
                    elif line_up.startswith("Ř2:") or line_up.startswith("R2:"):
                        parts = line.split(":", 1)
                        if len(parts) > 1: st.session_state.d["r2"] = parts[1].strip()[:65]
                        
                    elif line_up.startswith("Ř3:") or line_up.startswith("R3:"):
                        parts = line.split(":", 1)
                        if len(parts) > 1: st.session_state.d["r3"] = parts[1].strip()[:65]
                        
                    elif line_up.startswith("Ř4:") or line_up.startswith("R4:"):
                        parts = line.split(":", 1)
                        if len(parts) > 1: st.session_state.d["r4"] = parts[1].strip()[:65]
                        
                    elif line_up.startswith("Ř5:") or line_up.startswith("R5:") or line_up.startswith("PÁLIVOST:"):
                        parts = line.split(":", 1)
                        if len(parts) > 1: st.session_state.d["shu"] = parts[1].strip()[:65]
                
                st.session_state.form_key = str(uuid.uuid4())
                st.rerun()

            if st.session_state.d["cat"] == "Papriky - Pálivé":
                st.text_input("🌶️ Pálivost (SHU):", value=st.session_state.d.get("shu", ""), max_chars=65, key=c_key("shu"))
            
            c = st.session_state.d["cat"]
            lbl_r1 = "Řádek 1 (Vzrůst - napište Převis/Polopřevis/Vzpřímená!):" if c == "Květiny" else "Řádek 1 (Stanoviště/Zálivka):"
            lbl_r2 = "Řádek 2 (Květ):" if c == "Květiny" else "Řádek 2 (Spon/Výška):"
            lbl_r3 = "Řádek 3 (Stanoviště):" if c == "Květiny" else ("Řádek 3 (Typ/Sběr):" if c == "Bylinky" else "Řádek 3 (Plod/Hmotnost):")
            lbl_r4 = "Řádek 4 (Zálivka):" if c == "Květiny" else "Řádek 4 (Použití/Tip):"

            st.text_input(lbl_r1, value=st.session_state.d["r1"], max_chars=65, key=c_key("r1"))
            st.text_input(lbl_r2, value=st.session_state.d["r2"], max_chars=65, key=c_key("r2"))
            st.text_input(lbl_r3, value=st.session_state.d["r3"], max_chars=65, key=c_key("r3"))
            st.text_input(lbl_r4, value=st.session_state.d["r4"], max_chars=65, key=c_key("r4"))

        st.markdown("<br>", unsafe_allow_html=True)
        
        is_editing = st.session_state.d.get("loaded_from") is not None
        
        if is_editing:
            st.info("✏️ **REŽIM ÚPRAV:** Pracujete s cedulkou načtenou ze skladu.")
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("💾 PŘEPSAT PŮVODNÍ VE SKLADU", type="primary", width="stretch"):
                    sync_to_d() 
                    f_name = st.session_state.d["name"]
                    f_img = st.session_state.d.get("img")
                    if f_name and f_img:
                        save_name = f_name.split(" - ")[0].strip() if " - " in f_name else f_name
                        new_folder = clean_filename(save_name)
                        loaded_from = st.session_state.d.get("loaded_from")
                        
                        if loaded_from and loaded_from != new_folder:
                            old_p = os.path.join(DB_DIR, loaded_from)
                            if os.path.exists(old_p):
                                shutil.rmtree(old_p)
                                
                        p = os.path.join(DB_DIR, new_folder)
                        if not os.path.exists(p): os.makedirs(p)
                        
                        d_out = {
                            "name": f_name, "cat": st.session_state.d["cat"],
                            "r1": st.session_state.d["r1"], "r2": st.session_state.d["r2"],
                            "r3": st.session_state.d["r3"], "r4": st.session_state.d["r4"],
                            "shu": st.session_state.d["shu"],
                            "raw_ai": st.session_state.d.get("last_ai", "")
                        }
                        with open(os.path.join(p, "data.json"), "w", encoding="utf-8") as f:
                            json.dump(d_out, f, ensure_ascii=False)
                        f_img.save(os.path.join(p, "photo.jpg"), "JPEG", quality=100, subsampling=0)
                        
                        st.session_state.d["loaded_from"] = new_folder
                        st.success("✅ Úspěšně přepsáno!")
                    else:
                        st.error("❌ Chybí název nebo fotka!")

            with c_btn2:
                if st.button("💾 ULOŽIT JAKO NOVOU KOPII", width="stretch"):
                    sync_to_d() 
                    f_name = st.session_state.d["name"]
                    f_img = st.session_state.d.get("img")
                    if f_name and f_img:
                        save_name = f_name.split(" - ")[0].strip() if " - " in f_name else f_name
                        new_folder = clean_filename(save_name)
                        
                        p = os.path.join(DB_DIR, new_folder)
                        if not os.path.exists(p): os.makedirs(p)
                        
                        d_out = {
                            "name": f_name, "cat": st.session_state.d["cat"],
                            "r1": st.session_state.d["r1"], "r2": st.session_state.d["r2"],
                            "r3": st.session_state.d["r3"], "r4": st.session_state.d["r4"],
                            "shu": st.session_state.d["shu"],
                            "raw_ai": st.session_state.d.get("last_ai", "")
                        }
                        with open(os.path.join(p, "data.json"), "w", encoding="utf-8") as f:
                            json.dump(d_out, f, ensure_ascii=False)
                        f_img.save(os.path.join(p, "photo.jpg"), "JPEG", quality=100, subsampling=0)
                        
                        st.session_state.d["loaded_from"] = new_folder
                        st.success("✅ Uloženo do skladu jako nová cedulka!")
                    else:
                        st.error("❌ Chybí název nebo fotka!")

        else:
            if st.button("💾 ULOŽIT NOVOU DO SKLADU", type="primary", width="stretch"):
                sync_to_d() 
                f_name = st.session_state.d["name"]
                f_img = st.session_state.d.get("img")
                if f_name and f_img:
                    save_name = f_name.split(" - ")[0].strip() if " - " in f_name else f_name
                    new_folder = clean_filename(save_name)
                    p = os.path.join(DB_DIR, new_folder)
                    if not os.path.exists(p): os.makedirs(p)
                    d_out = {
                        "name": f_name, "cat": st.session_state.d["cat"],
                        "r1": st.session_state.d["r1"], "r2": st.session_state.d["r2"],
                        "r3": st.session_state.d["r3"], "r4": st.session_state.d["r4"],
                        "shu": st.session_state.d["shu"],
                        "raw_ai": st.session_state.d.get("last_ai", "")
                    }
                    with open(os.path.join(p, "data.json"), "w", encoding="utf-8") as f:
                        json.dump(d_out, f, ensure_ascii=False)
                    f_img.save(os.path.join(p, "photo.jpg"), "JPEG", quality=100, subsampling=0)
                    
                    st.session_state.d["loaded_from"] = new_folder
                    st.success("✅ Uloženo do databáze! Nyní jste v režimu úprav.")
                else:
                    st.error("❌ Chybí název nebo fotka!")

    # --- NÁHLED A TISK (EDITOR) ---
    c_name = get_current("name")
    c_img = st.session_state.d.get("img")
    c_shu = get_current("shu") if st.session_state.d["cat"] == "Papriky - Pálivé" else ""
    c_cat = st.session_state.d["cat"]
    
    if c_name and c_img:
        st.markdown("---")
        st.subheader("🖨️ Náhled a Tisk (z Editoru)")
        with st.spinner("Generuji archy..."):
            f_b, f_r = get_czech_font("Bold"), get_czech_font("Regular")
            lines = [get_current("r1"), get_current("r2"), get_current("r3"), get_current("r4")]
            
            canvas_4, pdf_buf_4, pdf_buf_2 = generate_pdfs(c_name, c_img, lines, c_shu, c_cat, f_b, f_r)

            c_img_col, c_dl_col = st.columns([1.5, 1])
            c_img_col.image(canvas_4, width="stretch")
            
            with c_dl_col:
                down_name = clean_filename(c_name.split("-")[0] if "-" in c_name else c_name)
                st.download_button("📥 STÁHNOUT PDF: 4 CEDULKY (A6)", pdf_buf_4.getvalue(), f"{down_name}_4x_A6.pdf", mime="application/pdf", type="primary", width="stretch")
                st.markdown("<br>", unsafe_allow_html=True)
                st.download_button("📥 STÁHNOUT PDF: 2 CEDULKY (A5)", pdf_buf_2.getvalue(), f"{down_name}_2x_A5.pdf", mime="application/pdf", type="secondary", width="stretch")

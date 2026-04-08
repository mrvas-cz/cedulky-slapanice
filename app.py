import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import os
import urllib.request
import unicodedata
import textwrap

st.set_page_config(page_title="PRO Cedulkovač Farma - Auto-Layout", layout="wide")

@st.cache_resource
def get_czech_font(font_type="Bold"):
    # Stáhne font Roboto Bold nebo Regular
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

# --- POMOCNÁ FUNKCE PRO KRESLENÍ ZALOMENÉHO TEXTU S DYNAMICKOU VELIKOSTÍ ---
def draw_text_box(draw, text, pos, max_width, max_height, font_path, start_font_size):
    current_font_size = start_font_size
    lines = []
    
    # Najdeme ideální velikost písma, aby se text vešel do boxu
    while current_font_size > 25: # Minimální čitelná velikost
        font = ImageFont.truetype(font_path, current_font_size)
        lines = []
        
        # Rozdělíme text podle odrážek
        raw_lines = text.split('\n')
        
        for raw_line in raw_lines:
            if not raw_line.strip(): continue
            # Zalamujeme každý řádek podle šířky cedulky
            # Odhad počtu znaků na řádek podle velikosti písma
            avg_char_width = draw.textlength("a", font=font)
            chars_per_line = int(max_width / avg_char_width)
            wrapped = textwrap.wrap(raw_line, width=chars_per_line)
            for i, w_line in enumerate(wrapped):
                if i == 0: lines.append(f"• {w_line}") # Odrážka jen u prvního zalomení
                else: lines.append(f"  {w_line}") # Odsazení u dalších řádků
        
        # Vypočítáme celkovou výšku textu
        line_height = current_font_size * 1.3
        total_height = len(lines) * line_height
        
        if total_height <= max_height:
            break # Vešli jsme se, končíme hledání velikosti
        current_font_size -= 2 # Zmenšíme písmo a zkusíme znovu

    # Vykreslíme text
    font = ImageFont.truetype(font_path, current_font_size)
    line_height = current_font_size * 1.3
    y_text = pos[1]
    
    for line in lines:
        # Použijeme barvu loga pro odrážky a černou pro text
        if line.startswith("• "):
            # Vykreslíme odrážku zeleně
            draw.text((pos[0], y_text), "•", fill="#004D40", font=font)
            # Vykreslíme text černě
            draw.text((pos[0] + draw.textlength("• ", font=font), y_text), line[2:], fill="#333333", font=font)
        else:
            draw.text((pos[0], y_text), line, fill="#333333", font=font)
        y_text += line_height

# --- CORE FUNKCE KRESLENÍ JEDNÉ CEDULKY ---
def draw_label(name, img_plant, lines_text, font_bold, font_reg):
    A4_W, A4_H = 2480, 3508
    L_W, L_H = A4_W // 2, A4_H // 2
    lbl = Image.new('RGB', (L_W, L_H), 'white')
    d = ImageDraw.Draw(lbl)
    
    # 1. LOGO
    y = 60
    try:
        logo = Image.open("logo txt farma.JPG").convert("RGBA")
        lw = L_W - 400
        logo = logo.resize((lw, int(lw * (logo.height / logo.width))), Image.Resampling.LANCZOS)
        lbl.paste(logo, ((L_W - lw) // 2, y), logo)
        y += logo.height + 40
    except: y += 100
    
    # 2. NÁZEV ODRŮDY (S dynamickým zmenšením, pokud je příliš dlouhý)
    title_font_size = 115
    f_t = ImageFont.truetype(font_bold, title_font_size)
    while d.textlength(name.upper(), font=f_t) > (L_W - 100) and title_font_size > 60:
        title_font_size -= 5
        f_t = ImageFont.truetype(font_bold, title_font_size)
        
    d.text((L_W//2, y), name.upper(), fill="#004D40", anchor="mt", font=f_t)
    y += f_t.getbbox(name.upper())[3] + 60 # Dynamická mezera podle výšky nadpisu
    
    # 3. FOTKA ROSTLINY
    max_th = int(L_H * 0.40); max_tw = L_W - 200
    if img_plant:
        w, h = img_plant.size
        ratio = min(max_tw/w, max_th/h)
        new_size = (int(w*ratio), int(h*ratio))
        resized_img = img_plant.resize(new_size, Image.Resampling.LANCZOS)
        lbl.paste(resized_img, ((L_W - new_size[0]) // 2, y))
        y += new_size[1] + 60
    else:
        y += max_th + 60 # Mezera, pokud fotka chybí

    # 4. TECHNICKÉ PARAMETRY (Zalamovaný text s auto-size)
    full_text = "\n".join(lines_text)
    # Vymezený prostor pro text (od konce fotky po začátek ceny)
    max_text_height = (L_H - 250) - y 
    draw_text_box(d, full_text, (100, y), L_W - 200, max_text_height, font_reg, 48)
    
    # 5. CENA BOX
    bx_w, bx_h = 420, 160; bx_x, bx_y = (L_W - bx_w)//2, L_H - 220
    d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="#004D40", width=12)
    d.text((bx_x + bx_w + 40, bx_y + 80), "Kč", fill="black", anchor="lm", font=ImageFont.truetype(font_bold, 100))
    
    # Přidáme jemný rámeček kolem celé cedulky pro ořez
    d.rectangle([0, 0, L_W-1, L_H-1], outline="#EEEEEE", width=2)
    
    return lbl

# --- STREAMLIT UI ---
st.title("🌿 PRO Cedulkovač Farma - Perfektní Layout")

# Inicializace stavu
if 'label_a4_preview' not in st.session_state: st.session_state.label_a4_preview = None

# 1. KROK: ZADÁNÍ NÁZVU
nazev = st.text_input("1. Zadejte název odrůdy (pro rešerši):", placeholder="např. Rajče Bejbino F1")

if nazev:
    st.markdown("---")
    col_research, col_edit = st.columns([1, 1.2])

    with col_research:
        st.subheader("🔍 Rešerše a Foto")
        q = nazev.replace(" ", "+")
        
        # Mezinárodní odkazy (přeložené)
        st.write("📖 **Technické informace (přeloženo do CZ):**")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"[🇮🇹 Itálie (Rajčata/Papriky)](https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+varieta+peso+sesto)")
            st.markdown(f"[🇳🇱 Holandsko (Osiva)](https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+ras+kenmerken+plantafstand)")
        with c2:
            st.markdown(f"[🇩🇪 Německo (Bylinky)](https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+sorte+anbau+abstand)")
            st.markdown(f"[🇭🇺 Maďarsko (Papriky)](https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={q}+fajta+termesztes+tavolsag)")
        
        st.write("---")
        st.subheader("📸 Fotografie")
        st.markdown(f"👉 [Hledat Profi Fotky na Google Images] (https://www.google.com/search?tbm=isch&q={q}+fruit+detail+macro+white+background)")
        
        uploaded_file = st.file_uploader("2. Nahrajte fotku:", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            st.image(uploaded_file, caption="Nahraný obrázek", width=200)

    with col_edit:
        st.subheader("📝 Import dat a Editace")
        st.caption("Zkopírujte do své AI (Gemini/ChatGPT):")
        prompt_text = f"Jsi odborník. Najdi o odrůdě {nazev} tyto údaje a vypiš je přesně takto:\nŘ1: Stanoviště: ... | Zálivka: ...\nŘ2: Spon: ... | Výška: ...\nŘ3: Plod: ... | Hmotnost: ...\nŘ4: Použití: ... | Tip: ..."
        st.code(prompt_text, language="text")
        
        ai_data = st.text_area("3. Vložte odpověď od AI:", height=150)
        
        # Logika automatického výcucu
        r1, r2, r3, r4 = "", "", "", ""
        if ai_data:
            lines = ai_data.split('\n')
            for line in lines:
                if "Ř1:" in line: r1 = line.split("Ř1:")[1].strip()
                elif "Ř2:" in line: r2 = line.split("Ř2:")[1].strip()
                elif "Ř3:" in line: r3 = line.split("Ř3:")[1].strip()
                elif "Ř4:" in line: r4 = line.split("Ř4:")[1].strip()

        st.write("---")
        # Finální úprava názvu (nadpis)
        edit_nazev = st.text_input("NÁZEV NA CEDULECE:", value=nazev if nazev else "")
        
        # Úprava 4 řádků technických parametrů (zde mohou být dlouhé texty)
        edit_r1 = st.text_input("Řádek 1:", value=r1 if r1 else "Stanoviště: | Zálivka: ")
        edit_r2 = st.text_input("Řádek 2:", value=r2 if r2 else "Spon: | Výška: ")
        edit_r3 = st.text_input("Řádek 3:", value=r3 if r3 else "Plod: | Hmotnost: ")
        # Zde často bývá dlouhý text (Tip, Použití)
        edit_r4 = st.text_input("Řádek 4:", value=r4 if r4 else "Použití: | Tip: ")

        st.write("---")
        btn_preview = st.button("👁️ AKTUALIZOVAT NÁHLED TISKU", use_container_width=True)

st.markdown("---")

# --- GENERÁTOR A ZOBRAZENÍ NÁHLEDU ---
if nazev and (uploaded_file or btn_preview):
    with st.spinner('Generuji náhled tiskového archu A4...'):
        # Fonty
        f_bold = get_czech_font("Bold")
        f_reg = get_czech_font("Regular")
        
        # Obrázek rostliny (ošetření pokud chybí)
        try:
            img_p = Image.open(uploaded_file).convert("RGB") if uploaded_file else None
        except: img_p = None

        # Sestavíme texty (ošetříme prázdné řádky)
        final_lines = []
        if edit_r1.strip() and edit_r1 != "Stanoviště: | Zálivka: ": final_lines.append(edit_r1)
        if edit_r2.strip() and edit_r2 != "Spon: | Výška: ": final_lines.append(edit_r2)
        if edit_r3.strip() and edit_r3 != "Plod: | Hmotnost: ": final_lines.append(edit_r3)
        if edit_r4.strip() and edit_r4 != "Použití: | Tip: ": final_lines.append(edit_r4)
        
        # Pokud uživatel nic nevyplnil, dáme tam vzor
        if not final_lines: final_lines = [edit_r1, edit_r2, edit_r3, edit_r4]

        # Vytvoření jedné dokonalé cedulky
        single_label = draw_label(edit_nazev, img_p, final_lines, f_bold, f_reg)
        
        # Vytvoření A4 archu
        A4_W, A4_H = 2480, 3508
        L_W, L_H = A4_W // 2, A4_H // 2
        canvas = Image.new('RGB', (A4_W, A4_H), 'white')
        
        # Rozmístění 4 cedulek
        canvas.paste(single_label, (0, 0))
        canvas.paste(single_label, (L_W, 0))
        canvas.paste(single_label, (0, L_H))
        canvas.paste(single_label, (L_W, L_H))
        
        # Uložíme náhled do session state
        st.session_state.label_a4_preview = canvas

# Zobrazení náhledu, pokud existuje
if st.session_state.label_a4_preview:
    st.subheader("🖼️ Náhled tiskového archu A4")
    st.image(st.session_state.label_a4_preview, use_column_width=True, caption="Takto bude vypadat vytištěná stránka.")
    
    # Tlačítko pro stažení PDF
    buf = io.BytesIO()
    st.session_state.label_a4_preview.save(buf, format="PDF")
    
    st.download_button(
        label=f"📥 STÁHNOUT PDF K TISKU ({edit_nazev})",
        data=buf.getvalue(),
        file_name=f"{clean_filename(edit_nazev)}_A4.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True
    )

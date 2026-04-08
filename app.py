import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request
import unicodedata

st.set_page_config(page_title="Farma Cedulkovač PRO - International", layout="wide")

@st.cache_resource
def get_czech_font():
    font_path = "Roboto-Bold.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
            urllib.request.urlretrieve(url, font_path)
        except: return None
    return font_path

def clean_filename(text):
    nfkd_form = unicodedata.normalize('NFKD', text)
    return nfkd_form.encode('ASCII', 'ignore').decode('utf-8').replace(" ", "_").upper()

# --- HLAVNÍ ROZHRANÍ ---
st.title("🌿 PRO Cedulkovač - Mezinárodní Marketing")

# 1. ZADÁNÍ NÁZVU
nazev = st.text_input("1. Zadejte přesný název odrůdy (pro vyhledávání):", placeholder="např. Rajče San Marzano")

if nazev:
    st.markdown("---")
    col_research, col_import = st.columns([1, 1])

    with col_research:
        st.subheader("🔍 Mezinárodní rešerše a Foto")
        q = nazev.replace(" ", "+")
        
        def tr_link(query, lang_terms):
            full_q = f"{query}+{lang_terms}"
            return f"https://translate.google.com/translate?sl=auto&tl=cs&u=https://www.google.com/search?q={full_q}"

        st.info("Odkazy níže prohledají odborné weby v dané zemi a ROVNOU je přeloží do češtiny:")
        
        st.markdown(f"🇮🇹 [**Itálie** (Rajčata/Papriky - technická data)]({tr_link(q, 'varieta+coltivazione+peso+sesto')})")
        st.markdown(f"🇳🇱 [**Holandsko** (Osiva/Cibuloviny - profi katalogy)]({tr_link(q, 'ras+kenmerken+plantafstand+hoogte')})")
        st.markdown(f"🇭🇺 [**Maďarsko** (Pálivé papriky - tradice)]({tr_link(q, 'fajta+termesztes+tavolsag+suly')})")
        st.markdown(f"🇩🇪 [**Německo/Rakousko** (Bylinky/Trvalky)]({tr_link(q, 'sorte+anbau+abstand+gewicht')})")
        
        st.write("---")
        st.subheader("📸 Odkazy na fotografie")
        st.write("Klikněte na odkaz, vyberte fotku, uložte ji do PC a nahrajte níže:")
        st.markdown(f"👉 [**Hledat Profi Fotky** (Google Images)] (https://www.google.com/search?tbm=isch&q={q}+fruit+detail+macro+white+background)")
        
        uploaded_file = st.file_uploader("2. Nahrajte staženou fotku:", type=["jpg", "png", "jpeg"])

    with col_import:
        st.subheader("📝 Import dat z AI (Gemini/ChatGPT)")
        st.caption("Zkopírujte a vložte do své AI tento dotaz:")
        prompt_text = f"Jsi odborník. Najdi o odrůdě {nazev} tyto údaje a vypiš je přesně takto:\nŘ1: Stanoviště: ... | Zálivka: ...\nŘ2: Spon: ... | Výška: ...\nŘ3: Plod: ... | Hmotnost: ...\nŘ4: Použití: ... | Tip: ..."
        st.code(prompt_text, language="text")
        
        ai_data = st.text_area("3. Sem vložte odpověď od AI:", height=150, placeholder="Sem vložte výsledek z Gemini...")
        
        r1, r2, r3, r4 = "", "", "", ""
        if ai_data:
            lines = ai_data.split('\n')
            for line in lines:
                if "Ř1:" in line: r1 = line.split("Ř1:")[1].strip()
                elif "Ř2:" in line: r2 = line.split("Ř2:")[1].strip()
                elif "Ř3:" in line: r3 = line.split("Ř3:")[1].strip()
                elif "Ř4:" in line: r4 = line.split("Ř4:")[1].strip()

        st.write("---")
        st.subheader("⚙️ Finální úprava textů na cedulku")
        
        # NOVÉ: Propisování názvu z vyhledávání s možností úpravy
        edit_nazev = st.text_input("NÁZEV NA CEDULECE:", value=nazev)
        
        edit_r1 = st.text_input("Řádek 1:", value=r1 if r1 else "Stanoviště: | Zálivka: ")
        edit_r2 = st.text_input("Řádek 2:", value=r2 if r2 else "Spon: | Výška: ")
        edit_r3 = st.text_input("Řádek 3:", value=r3 if r3 else "Plod: | Hmotnost: ")
        edit_r4 = st.text_input("Řádek 4:", value=r4 if r4 else "Použití: | Tip: ")

    # GENERATOR
    if st.button("🖨️ GENEROVAT PDF K TISKU", type="primary", use_container_width=True):
        if not uploaded_file:
            st.error("Chybí fotka!")
        else:
            img_p = Image.open(uploaded_file).convert("RGB")
            A4_W, A4_H = 2480, 3508
            L_W, L_H = A4_W // 2, A4_H // 2
            canvas = Image.new('RGB', (A4_W, A4_H), 'white')
            font_p = get_czech_font()

            def draw_label(name, img, lines):
                lbl = Image.new('RGB', (L_W, L_H), 'white')
                d = ImageDraw.Draw(lbl)
                y = 60
                try:
                    logo = Image.open("logo txt farma.JPG").convert("RGBA")
                    lw = L_W - 350
                    logo = logo.resize((lw, int(lw * (logo.height / logo.width))), Image.Resampling.LANCZOS)
                    lbl.paste(logo, ((L_W - lw) // 2, y), logo)
                    y += logo.height + 30
                except: y += 100
                
                f_t = ImageFont.truetype(font_p, 115) if font_p else ImageFont.load_default()
                d.text((L_W//2, y + 40), name.upper(), fill="#004D40", anchor="mm", font=f_t)
                y += 150
                
                max_th = int(L_H * 0.42); max_tw = L_W - 200
                w, h = img.size
                ratio = min(max_tw/w, max_th/h)
                new_size = (int(w*ratio), int(h*ratio))
                resized_img = img.resize(new_size, Image.Resampling.LANCZOS)
                lbl.paste(resized_img, ((L_W - new_size[0]) // 2, y))
                y += new_size[1] + 60
                
                f_b = ImageFont.truetype(font_p, 45) if font_p else ImageFont.load_default()
                for line in lines:
                    d.text((120, y), f"• {line}", fill="#333333", font=f_b)
                    y += 75
                
                bx_w, bx_h = 420, 160; bx_x, bx_y = (L_W - bx_w)//2, L_H - 220
                d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="#004D40", width=12)
                d.text((bx_x + bx_w + 40, bx_y + 80), "Kč", fill="black", anchor="lm", font=ImageFont.truetype(font_p, 100))
                return lbl

            # Využití nového upraveného názvu
            label = draw_label(edit_nazev, img_p, [edit_r1, edit_r2, edit_r3, edit_r4])
            canvas.paste(label, (0, 0)); canvas.paste(label, (L_W, 0))
            canvas.paste(label, (0, L_H)); canvas.paste(label, (L_W, L_H))
            
            buf = io.BytesIO()
            canvas.save(buf, format="PDF")
            st.download_button(f"📥 Stáhnout PDF {edit_nazev}", buf.getvalue(), f"{clean_filename(edit_nazev)}.pdf")

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request
import unicodedata

st.set_page_config(page_title="Profi Cedulkovač - Mezinárodní Search", layout="wide")

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

# --- ROZHRANÍ ---
st.title("🌍 Mezinárodní Cedulkovač Farma")
st.write("Specializované vyhledávání v evropských šlechtitelských databázích s automatickým překladem.")

nazev = st.text_input("Zadejte název odrůdy (ideálně i latinsky, pokud víte):", placeholder="např. Rajče Bejbino F1 nebo Lavandula angustifolia")

if nazev:
    st.markdown("---")
    col_links, col_edit = st.columns([1, 1])
    
    with col_links:
        st.subheader("🔎 Odborné zdroje (přeloženo do CZ)")
        q = nazev.replace(" ", "+")
        
        # Funkce pro vytvoření odkazu přes Google Translate pro celou doménu/vyhledávání
        def get_translate_link(query, lang_suffix, site=""):
            base_search = f"https://www.google.com/search?q={query}+{lang_suffix}+{site}"
            return f"https://translate.google.com/translate?sl=auto&tl=cs&u={base_search}"

        st.info("Kliknutím na vlajku otevřete odborné vyhledávání v dané zemi ROVNOU PŘELOŽENÉ do češtiny:")
        
        st.markdown(f"🇮🇹 **Itálie** (Špička na rajčata/papriky): [Hledat italské šlechtitele]({get_translate_link(q, 'varieta+coltivazione+peso+distanza')})")
        st.markdown(f"🇳🇱 **Holandsko** (Osiva a technologie): [Hledat holandské katalogy]({get_translate_link(q, 'ras+kenmerken+plantafstand+hoogte')})")
        st.markdown(f"🇭🇺 **Maďarsko** (Papriky a polní plodiny): [Hledat maďarské weby]({get_translate_link(q, 'fajta+termesztes+tavolsag+suly')})")
        st.markdown(f"🇩🇪 **Německo/Rakousko** (Bylinky a trvalky): [Hledat německé odborníky]({get_translate_link(q, 'sorte+anbau+abstand+gewicht')})")
        st.markdown(f"🇵🇱 **Polsko** (Osvědčené odrůdy pro naše klima): [Hledat polské pěstitele]({get_translate_link(q, 'odmiana+uprawa+rozstawa+masa')})")
        
        st.write("---")
        st.subheader("🖼️ Fotografie")
        st.markdown(f"📸 [Najít detailní fotky plodů (Google Images)] (https://www.google.com/search?tbm=isch&q={q}+fruit+detail+macro)")
        
        uploaded_file = st.file_uploader("Nahrajte vybranou fotku:", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            st.session_state.img = Image.open(uploaded_file).convert("RGB")
            st.image(st.session_state.img, width=250)

    with col_edit:
        st.subheader("📝 Údaje na cedulku")
        st.caption("Přečtěte si info z odkazů vlevo a doplňte:")
        
        r1 = st.text_input("Řádek 1:", value="Stanoviště: | Zálivka: ")
        r2 = st.text_input("Řádek 2:", value="Spon: | Výška: ")
        r3 = st.text_input("Řádek 3:", value="Plod: | Hmotnost: ")
        r4 = st.text_input("Řádek 4:", value="Použití: | Tip: ")
        
        st.write("---")
        if st.button("🖨️ GENEROVAT PDF K TISKU", type="primary", use_container_width=True):
            if 'img' not in st.session_state:
                st.error("Chybí fotka!")
            else:
                # PDF GENERÁTOR (stejný jako dříve, ověřený)
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
                    
                    f_t = ImageFont.truetype(font_p, 115)
                    d.text((L_W//2, y + 40), name.upper(), fill="#004D40", anchor="mm", font=f_t)
                    y += 150
                    
                    th = int(L_H * 0.42); tw = int(th * (img.width / img.height))
                    if tw > L_W - 200: tw = L_W - 200; th = int(tw / (img.width / img.height))
                    lbl.paste(img.resize((tw, th), Image.Resampling.LANCZOS), ((L_W - tw) // 2, y))
                    y += th + 60
                    
                    f_b = ImageFont.truetype(font_p, 45)
                    for line in lines:
                        d.text((120, y), f"• {line}", fill="#333333", font=f_b)
                        y += 75
                    
                    # Box na cenu
                    bx_w, bx_h = 420, 160; bx_x, bx_y = (L_W - bx_w)//2, L_H - 220
                    d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="#004D40", width=12)
                    d.text((bx_x + bx_w + 40, bx_y + 80), "Kč", fill="black", anchor="lm", font=ImageFont.truetype(font_p, 100))
                    return lbl

                label = draw_label(nazev, st.session_state.img, [r1, r2, r3, r4])
                canvas.paste(label, (0, 0)); canvas.paste(label, (L_W, 0))
                canvas.paste(label, (0, L_H)); canvas.paste(label, (L_W, L_H))
                
                buf = io.BytesIO()
                canvas.save(buf, format="PDF")
                st.download_button(f"📥 Stáhnout PDF {nazev}", buf.getvalue(), f"{clean_filename(nazev)}.pdf")

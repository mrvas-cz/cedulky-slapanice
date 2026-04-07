import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request
import unicodedata
from duckduckgo_search import DDGS

st.set_page_config(page_title="PRO Cedulkovač Farma", layout="wide")

@st.cache_resource
def get_czech_font():
    font_path = "Roboto-Bold.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
        urllib.request.urlretrieve(url, font_path)
    return font_path

def clean_filename(text):
    nfkd_form = unicodedata.normalize('NFKD', text)
    return nfkd_form.encode('ASCII', 'ignore').decode('utf-8').replace(" ", "_").upper()

# --- BEZPLATNÁ AI (BEZ API KLÍČE) ---
def get_free_ai_info(query):
    try:
        with DDGS() as ddgs:
            prompt = f"""
            Jsi expert na zahradnictví. Vyhledej detailní informace o rostlině/odrůdě: {query}.
            Zaměř se striktně na tyto technické parametry:
            1. U ZELENINY (rajčata, papriky): gramáž plodu (g), typ vzrůstu (tyčkové/keřové), tvar, barva, chuť, ranost, pálivost u paprik.
            2. U BYLINEK: využití v kuchyni, co léčí, zda je to trvalka/letnička, nároky na pěstování.
            3. U OKRASNÝCH: výška, barva, doba kvetení.
            
            Výstup vytvoř takto:
            ČÁST A: 10 velmi krátkých bodů (max 6 slov) ideálních pro zkopírování na prodejní cedulku.
            ČÁST B: Krátký souvislý odstavec o této odrůdě.
            Piš pouze česky.
            """
            
            # Zavolání AI přímo přes DuckDuckGo
            response = ddgs.chat(prompt, model='gpt-4o-mini')
            
            # Ošetření výstupu
            if isinstance(response, str):
                return response
            else:
                return "".join(list(response))
                
    except Exception as e:
        return f"Došlo k chybě připojení (vyhledávač občas omezuje přístupy při velkém množství dotazů). \n\nZkuste prosím kliknout na tlačítko vyhledat znovu za 10 vteřin.\n\nTechnický detail: {e}"

# --- UI ---
st.title("🌿 Inteligentní Cedulkovač (Bez API klíčů)")

if 'full_info' not in st.session_state: st.session_state.full_info = ""
if 'pro_img' not in st.session_state: st.session_state.pro_img = None

nazev = st.text_input("Zadejte přesný název rostliny/odrůdy:", placeholder="např. Rajče Tornádo F1 nebo Levandule lékařská")

if st.button("🔍 Vyhledat vše o rostlině pomocí AI", type="primary"):
    if nazev:
        with st.spinner('Zjišťuji gramáže, vzrůst a účinky přes bezplatnou AI...'):
            st.session_state.full_info = get_free_ai_info(nazev)
    else:
        st.warning("Zadejte název.")

st.markdown("---")

if st.session_state.full_info:
    col_a, col_b = st.columns([1, 1])
    
    with col_a:
        st.subheader("📖 Co AI zjistila (Náhled dat)")
        st.text_area("Informace k nakopírování na cedulku:", value=st.session_state.full_info, height=350)
        
    with col_b:
        st.subheader("🖼️ Odkazy na fotografie")
        st.write("Klikněte, stáhněte si nejhezčí fotku k sobě do počítače a nahrajte ji níže:")
        
        search_query = nazev.replace(" ", "+")
        st.markdown(f"👉 [Najít fotku na **Google Obrázcích**](https://www.google.com/search?tbm=isch&q={search_query}+plod+detail)")
        st.markdown(f"👉 [Najít fotku na **Bingu**](https://www.bing.com/images/search?q={search_query}+rostlina)")
        
        st.markdown("---")
        uploaded_file = st.file_uploader("Nahrát staženou fotku sem:", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            st.session_state.pro_img = Image.open(uploaded_file).convert("RGB")
            st.image(st.session_state.pro_img, caption="Tato fotka bude na cedulce", width=200)

    st.markdown("---")
    st.subheader("📝 Finalizace cedulky")
    st.info("Z levého šedého okna si zkopírujte 4 nejlepší body (např. gramáž, vzrůst) do políček níže.")
    
    c1, c2 = st.columns(2)
    with c1:
        e1 = st.text_input("Bod 1:", value="")
        e2 = st.text_input("Bod 2:", value="")
    with c2:
        e3 = st.text_input("Bod 3:", value="")
        e4 = st.text_input("Bod 4:", value="")

    if st.button("🖨️ GENEROVAT PDF K TISKU", use_container_width=True):
        if not st.session_state.pro_img:
            st.error("Před generováním nahrajte prosím obrázek!")
        else:
            A4_W, A4_H = 2480, 3508
            L_W, L_H = A4_W // 2, A4_H // 2
            canvas = Image.new('RGB', (A4_W, A4_H), 'white')
            font_p = get_czech_font()

            def draw_label(name, img, pts):
                lbl = Image.new('RGB', (L_W, L_H), 'white')
                d = ImageDraw.Draw(lbl)
                y = 60
                
                try:
                    logo = Image.open("logo txt farma.JPG").convert("RGBA")
                    lw = L_W - 320
                    logo = logo.resize((lw, int(lw * (logo.height / logo.width))), Image.Resampling.LANCZOS)
                    lbl.paste(logo, ((L_W - lw) // 2, y), logo)
                    y += logo.height + 30
                except: y += 100
                
                f_t = ImageFont.truetype(font_p, 110)
                d.text((L_W//2, y + 40), name.upper(), fill="#004D40", anchor="mm", font=f_t)
                y += 140
                
                if img:
                    th = int(L_H * 0.41); tw = int(th * (img.width / img.height))
                    if tw > L_W - 180: tw = L_W - 180; th = int(tw / (img.width / img.height))
                    lbl.paste(img.resize((tw, th), Image.Resampling.LANCZOS), ((L_W - tw) // 2, y))
                    y += th + 55
                
                f_b = ImageFont.truetype(font_p, 48)
                for p in pts:
                    if p.strip():
                        d.text((120, y), f"• {p[:60]}", fill="#333333", font=f_b)
                        y += 75
                
                bx_w, bx_h = 420, 160; bx_x, bx_y = (L_W - bx_w)//2, L_H - 225
                d.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline="#004D40", width=14)
                d.text((bx_x + bx_w + 35, bx_y + 85), "Kč", fill="black", anchor="lm", font=ImageFont.truetype(font_p, 100))
                return lbl

            final_label = draw_label(nazev, st.session_state.pro_img, [e1, e2, e3, e4])
            canvas.paste(final_label, (0, 0)); canvas.paste(final_label, (L_W, 0))
            canvas.paste(final_label, (0, L_H)); canvas.paste(final_label, (L_W, L_H))
            
            st.image(canvas, use_column_width=True)
            buf = io.BytesIO()
            canvas.save(buf, format="PDF")
            st.download_button(f"📥 STÁHNOUT PDF: {nazev}", buf.getvalue(), f"{clean_filename(nazev)}.pdf")

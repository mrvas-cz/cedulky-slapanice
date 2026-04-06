import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import requests
import urllib.request
import wikipedia
import re

# Nastavení češtiny pro Wikipedii
wikipedia.set_lang("cs")

st.set_page_config(page_title="Cedulkovač Šlapanice", layout="centered")

st.title("🚜 Šlapanický Cedulkovač s umělou inteligencí")
st.write("Stačí zadat název. Aplikace sama najde fotku, vytvoří popisky a přidá logo naší farmy!")

# --- FUNKCE PRO ZÍSKÁNÍ FONTU S ČESKOU DIAKRITIKOU ---
@st.cache_resource
def get_czech_font():
    font_path = "Roboto-Bold.ttf"
    if not os.path.exists(font_path):
        # Automatické stažení profi fontu přímo od Googlu (zdarma a legální)
        url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
        urllib.request.urlretrieve(url, font_path)
    return font_path

# --- FUNKCE PRO STAŽENÍ DAT Z WEBU ---
def fetch_plant_data(nazev):
    bullets = []
    img_url = None
    try:
        # Hledání stránky na Wikipedii
        page = wikipedia.page(nazev, auto_suggest=True)
        summary = wikipedia.summary(nazev, sentences=3)
        
        # Rozsekání textu na jednoduché body (max 4 body, max 5 slov)
        sentences = re.split(r'[.!?]', summary)
        for s in sentences:
            s = s.strip()
            if s and len(s) > 3:
                words = s.split()
                # Vezmeme prvních max 5 slov a přidáme tečky, pokud je text delší
                if len(words) > 5:
                    bullet = " ".join(words[:5]) + "..."
                else:
                    bullet = " ".join(words)
                bullets.append(f"• {bullet}")
            if len(bullets) >= 4:
                break
                
        # Získání fotky (hledáme jpg nebo png)
        for url in page.images:
            if url.lower().endswith(('.jpg', '.jpeg', '.png')) and "icon" not in url.lower():
                img_url = url
                break
                
    except Exception:
        bullets = ["• Informace z webu", "• se nepodařilo", "• automaticky", "• dohledat."]
        img_url = None
        
    return bullets, img_url

# --- UŽIVATELSKÉ ROZHRANÍ (JEDNODUCHÉ PRO DĚTI) ---
nazev_produktu = st.text_input("Zadej název sazenice (např. Rajče jedlé, Máta peprná):", "")

if nazev_produktu:
    with st.spinner('🕵️ Hledám informace a fotky na internetu...'):
        bullets, img_url = fetch_plant_data(nazev_produktu)
        
        # Pokud se nenašla fotka, necháme uživatele nahrát vlastní (záložní plán)
        uploaded_img = None
        if not img_url:
            st.warning("Nepodařilo se mi najít fotku. Prosím, nahraj ji ručně.")
            uploaded_file = st.file_uploader("Nahrát fotku z počítače/mobilu:", type=["jpg", "png"])
            if uploaded_file:
                uploaded_img = Image.open(uploaded_file).convert("RGB")
        else:
            try:
                response = requests.get(img_url)
                uploaded_img = Image.open(io.BytesIO(response.content)).convert("RGB")
            except:
                st.warning("Fotka z webu nešla načíst.")
        
        if uploaded_img or img_url is None: # Pokračujeme i bez fotky
            
            # Definice rozměrů A4
            A4_WIDTH = 2480
            A4_HEIGHT = 3508
            LABEL_W = A4_WIDTH // 2
            LABEL_H = A4_HEIGHT // 2
            
            a4_canvas = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), 'white')
            
            def create_label():
                label = Image.new('RGB', (LABEL_W, LABEL_H), 'white')
                draw = ImageDraw.Draw(label)
                font_path = get_czech_font()
                
                # 1. VLOŽENÍ LOGA FARMY (úplně nahoru)
                try:
                    logo = Image.open("logo txt farma.JPG").convert("RGBA")
                    logo_w = LABEL_W - 200
                    logo_aspect = logo.width / logo.height
                    logo_h = int(logo_w / logo_aspect)
                    logo_resized = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
                    # Přilepení loga (vycentrované nahoře)
                    label.paste(logo_resized, ((LABEL_W - logo_w) // 2, 40), logo_resized)
                    offset_y = 40 + logo_h + 40
                except FileNotFoundError:
                    # Pokud se logo nenajde na GitHubu, vypíšeme text
                    font_logo = ImageFont.truetype(font_path, 80)
                    draw.text((LABEL_W // 2, 80), "RODINNÁ FARMA ŠLAPANICE", fill="darkred", anchor="mm", font=font_logo)
                    offset_y = 160

                # 2. ZVÝRAZNĚNÝ NÁZEV
                font_title = ImageFont.truetype(font_path, 110)
                draw.text((LABEL_W // 2, offset_y + 60), nazev_produktu.upper(), fill="black", anchor="mm", font=font_title)
                
                # 3. FOTKA ROSTLINY Z WEBU (uprostřed)
                offset_y += 150
                if uploaded_img:
                    img_aspect = uploaded_img.width / uploaded_img.height
                    target_h = int(LABEL_H * 0.35)
                    target_w = int(target_h * img_aspect)
                    if target_w > LABEL_W - 100:
                        target_w = LABEL_W - 100
                        target_h = int(target_w / img_aspect)
                        
                    img_resized = uploaded_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    label.paste(img_resized, ((LABEL_W - target_w) // 2, offset_y))
                    offset_y += target_h + 50
                
                # 4. KRÁTKÉ BODY Z WIKIPEDIE (pod fotkou)
                font_bullets = ImageFont.truetype(font_path, 60)
                for bullet in bullets:
                    draw.text((100, offset_y), bullet, fill="#333333", anchor="ls", font=font_bullets)
                    offset_y += 80
                
                # 5. RÁMEČEK NA CENU FIXOU (úplně dole)
                box_w, box_h = 450, 160
                box_x = (LABEL_W - box_w) // 2
                box_y = LABEL_H - 220
                draw.rectangle([box_x, box_y, box_x + box_w, box_y + box_h], outline="black", width=8)
                draw.text((box_x + box_w + 30, box_y + 80), "Kč", fill="black", anchor="lm", font=font_title)
                
                # Okraj pro stříhání
                draw.rectangle([0, 0, LABEL_W-2, LABEL_H-2], outline="#CCCCCC", width=3)
                
                return label

            # Generování 4 cedulek
            single_label = create_label()
            a4_canvas.paste(single_label, (0, 0))
            a4_canvas.paste(single_label, (LABEL_W, 0))
            a4_canvas.paste(single_label, (0, LABEL_H))
            a4_canvas.paste(single_label, (LABEL_W, LABEL_H))

            st.success("Hotovo! Cedulky jsou připravené.")
            st.image(a4_canvas, caption="Náhled vaší A4 stránky", use_column_width=True)

            buf = io.BytesIO()
            a4_canvas.save(buf, format="PDF")
            
            st.download_button(
                label="🖨️ STÁHNOUT PDF K TISKU",
                data=buf.getvalue(),
                file_name=f"cedulka_{nazev_produktu}.pdf",
                mime="application/pdf"
            )

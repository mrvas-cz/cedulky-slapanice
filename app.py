import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io

# Nastavení vzhledu stránky v prohlížeči
st.set_page_config(page_title="Šlapanický Cedulkovač", layout="centered")

st.title("🚜 Šlapanický Cedulkovač")
st.write("Jednoduchý nástroj pro rodinnou farmu. Vyfoťte, pojmenujte a vytiskněte.")

# Vstupy od uživatele (jednoduché ovládání)
nazev_produktu = st.text_input("Napište název (např. Rajčata, Papriky, Bylinky):", "")
uploaded_file = st.file_uploader("Nahrajte nebo pořiďte fotku:", type=["jpg", "jpeg", "png"])

if uploaded_file and nazev_produktu:
    # Definice rozměrů pro kvalitní tisk A4 (300 DPI)
    A4_WIDTH = 2480
    A4_HEIGHT = 3508
    LABEL_WIDTH = A4_WIDTH // 2
    LABEL_HEIGHT = A4_HEIGHT // 2

    # Vytvoření čistého bílého papíru A4
    a4_canvas = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), 'white')
    
    # Načtení nahrané fotky
    img = Image.open(uploaded_file).convert("RGB")
    
    def create_label():
        # Vytvoření jedné cedulky (1/4 z A4)
        label = Image.new('RGB', (LABEL_WIDTH, LABEL_HEIGHT), 'white')
        draw = ImageDraw.Draw(label)
        
        # 1. Zpracování fotky (automatické oříznutí a zmenšení)
        img_aspect = img.width / img.height
        target_h = int(LABEL_HEIGHT * 0.55)
        target_w = int(target_h * img_aspect)
        
        if target_w > LABEL_WIDTH - 150:
            target_w = LABEL_WIDTH - 150
            target_h = int(target_w / img_aspect)
            
        img_resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        # Vložení fotky na střed horní části
        label.paste(img_resized, ((LABEL_WIDTH - target_w) // 2, 60))
        
        # 2. Vložení názvu produktu
        try:
            # Pokus o načtení standardního písma
            font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 130)
        except:
            font_title = ImageFont.load_default()

        # Text názvu (vycentrovaný)
        draw.text((LABEL_WIDTH // 2, int(LABEL_HEIGHT * 0.72)), nazev_produktu.upper(), fill="black", anchor="mm", font=font_title)
        
        # 3. Rámeček na cenu (prázdný pro dopsání fixem)
        box_w, box_h = 450, 180
        box_x = (LABEL_WIDTH - box_w) // 2
        box_y = int(LABEL_HEIGHT * 0.83)
        draw.rectangle([box_x, box_y, box_x + box_w, box_y + box_h], outline="black", width=8)
        
        # Symbol měny vedle rámečku
        draw.text((box_x + box_w + 30, box_y + 90), "Kč", fill="black", anchor="lm", font=font_title)
        
        # 4. Označení původu (Farma Šlapanice)
        try:
            font_small = ImageFont.truetype("DejaVuSans.ttf", 45)
            draw.text((LABEL_WIDTH // 2, LABEL_HEIGHT - 60), "RODINNÁ FARMA ŠLAPANICE", fill="gray", anchor="mm", font=font_small)
        except:
            pass

        # Šedý okraj pro snadné stříhání nůžkami
        draw.rectangle([0, 0, LABEL_WIDTH-2, LABEL_HEIGHT-2], outline="#EEEEEE", width=3)
        
        return label

    # Vygenerování cedulky a její rozmístění 4x na list A4
    single_label = create_label()
    a4_canvas.paste(single_label, (0, 0))
    a4_canvas.paste(single_label, (LABEL_WIDTH, 0))
    a4_canvas.paste(single_label, (0, LABEL_HEIGHT))
    a4_canvas.paste(single_label, (LABEL_WIDTH, LABEL_HEIGHT))

    # Zobrazení náhledu přímo v aplikaci
    st.image(a4_canvas, caption="Takhle bude vypadat váš papír A4 (4 cedulky)", use_column_width=True)

    # Tlačítko pro stažení PDF
    pdf_buffer = io.BytesIO()
    a4_canvas.save(pdf_buffer, format="PDF")
    
    st.download_button(
        label="✅ STÁHNOUT PDF K TISKU",
        data=pdf_buffer.getvalue(),
        file_name=f"cedulky_{nazev_produktu}.pdf",
        mime="application/pdf"
    )

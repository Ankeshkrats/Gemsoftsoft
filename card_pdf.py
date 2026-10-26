import os
import pypdfium2 as pdfium
from PIL import Image as PILImage
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

BASE_DIR = r"C:\Users\LENOVO\Desktop\Gemsoftsoft"
CARD_WIDTH  = 85.6 * mm
CARD_HEIGHT = 54.0 * mm

# Premium color palette for highest print contrast & luxury certificate look
COLOR_PRIMARY   = colors.HexColor('#0c2340')  # Deep Royal Imperial Navy
COLOR_NAVY_LIGHT= colors.HexColor('#163b66')  # Sapphire Blue
COLOR_ACCENT    = colors.HexColor('#c49a45')  # Rich Warm Gold
COLOR_ACCENT_BG = colors.HexColor('#fcfaf5')  # Subtle gold tint
COLOR_RED       = colors.HexColor('#b91c1c')  # Deep Ruby Red
COLOR_TEXT_DARK = colors.HexColor('#0f172a')  # Slate 900 (ultra high contrast)
COLOR_TEXT_MID  = colors.HexColor('#334155')  # Slate 700
COLOR_BORDER    = colors.HexColor('#cbd5e1')  # Slate 300
COLOR_CARD_BORDER = colors.HexColor('#0c2340')
COLOR_ZEBRA     = colors.HexColor('#f8fafc')  # Alternating row background

def draw_card(c: canvas.Canvas, x: float, y: float, cert: dict, base_dir: str = '.', gemologist_name: str = 'Gemologist'):
    """
    Draw a single ID card at position (x, y) with dimensions 85.6mm x 54mm.
    (x, y) is the bottom-left corner of the card.
    High-contrast, bold typography, enlarged QR code, luxury security styling.
    """
    c.saveState()

    # 1. Outer Card Container
    c.setFillColor(colors.white)
    c.setStrokeColor(COLOR_CARD_BORDER)
    c.setLineWidth(0.8)
    c.roundRect(x, y, CARD_WIDTH, CARD_HEIGHT, 2.5 * mm, fill=1, stroke=1)

    # Inner decorative gold hairline security border
    c.setStrokeColor(COLOR_ACCENT)
    c.setLineWidth(0.35)
    c.roundRect(x + 0.8 * mm, y + 0.8 * mm, CARD_WIDTH - 1.6 * mm, CARD_HEIGHT - 1.6 * mm, 2.0 * mm, fill=0, stroke=1)

    # 2. Top Header (Logo + Institute Title)
    header_height = 9.2 * mm
    header_y = y + CARD_HEIGHT - header_height

    # Top header soft ivory/white background
    c.setFillColor(colors.HexColor('#fbfcfd'))
    c.rect(x + 0.8 * mm, header_y, CARD_WIDTH - 1.6 * mm, header_height - 0.8 * mm, fill=1, stroke=0)

    # Logo
    thumb_path = os.path.join(base_dir, 'static', 'logo_card_thumb.png')
    logo_path  = os.path.join(base_dir, 'static', 'logo.jpeg')
    active_logo = None
    if os.path.exists(thumb_path):
        active_logo = thumb_path
    elif os.path.exists(logo_path):
        try:
            pil_img = PILImage.open(logo_path)
            bbox = pil_img.getbbox()
            if bbox:
                cropped = pil_img.crop(bbox)
                w, h = cropped.size
                max_dim = max(w, h)
                square_img = PILImage.new('RGBA', (max_dim, max_dim), (255, 255, 255, 0))
                square_img.paste(cropped, ((max_dim - w) // 2, (max_dim - h) // 2))
                square_img.thumbnail((512, 512), PILImage.Resampling.LANCZOS)
                square_img.save(thumb_path, optimize=True)
                active_logo = thumb_path
            else:
                active_logo = logo_path
        except Exception:
            active_logo = logo_path

    logo_size = 8.2 * mm
    logo_x = x + 2.0 * mm
    logo_y = header_y + 0.5 * mm

    if active_logo and os.path.exists(active_logo):
        try:
            c.saveState()
            c.drawImage(active_logo, logo_x, logo_y,
                        width=logo_size, height=logo_size, preserveAspectRatio=True, mask='auto')
            # Gold circular ring
            c.setStrokeColor(COLOR_ACCENT)
            c.setLineWidth(0.5)
            c.circle(logo_x + logo_size / 2.0, logo_y + logo_size / 2.0, logo_size / 2.0 + 0.15 * mm, fill=0, stroke=1)
            c.restoreState()
        except Exception:
            pass

    # Header Text
    text_x = logo_x + logo_size + 1.8 * mm

    c.setFillColor(COLOR_PRIMARY)
    c.setFont("Helvetica-Bold", 8.8)
    c.drawString(text_x, header_y + 4.8 * mm, "INDIAN GEMOLOGICAL INSTITUTE")

    c.setFillColor(COLOR_ACCENT)
    c.setFont("Helvetica-Bold", 4.8)
    c.drawString(text_x, header_y + 2.0 * mm, "INTERNATIONAL GEM TESTING LABORATORY")

    # Right side security badges in header
    c.setFillColor(COLOR_PRIMARY)
    c.setFont("Helvetica-Bold", 4.2)
    c.drawRightString(x + CARD_WIDTH - 2.5 * mm, header_y + 2.0 * mm, "ISO 9001:2015")
    c.setFillColor(colors.HexColor('#15803d'))
    c.drawRightString(x + CARD_WIDTH - 2.5 * mm, header_y + 4.8 * mm, "✓ AUTHENTIC")

    # Header underline: Navy + Gold accent bar
    c.setStrokeColor(COLOR_PRIMARY)
    c.setLineWidth(0.8)
    c.line(x + 0.8 * mm, header_y, x + CARD_WIDTH - 0.8 * mm, header_y)
    c.setStrokeColor(COLOR_ACCENT)
    c.setLineWidth(0.4)
    c.line(x + 0.8 * mm, header_y - 0.3 * mm, x + CARD_WIDTH - 0.8 * mm, header_y - 0.3 * mm)

    # 3. Title Bar (Banner)
    title_height = 3.6 * mm
    title_y = header_y - 0.4 * mm - title_height
    c.setFillColor(COLOR_PRIMARY)
    c.rect(x + 0.8 * mm, title_y, CARD_WIDTH - 1.6 * mm, title_height, fill=1, stroke=0)

    # Gold corner accents on title bar
    c.setFillColor(COLOR_ACCENT)
    c.rect(x + 1.2 * mm, title_y + 0.6 * mm, 1.8 * mm, title_height - 1.2 * mm, fill=1, stroke=0)
    c.rect(x + CARD_WIDTH - 3.0 * mm, title_y + 0.6 * mm, 1.8 * mm, title_height - 1.2 * mm, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 5.8)
    c.drawCentredString(x + CARD_WIDTH / 2.0, title_y + 1.0 * mm, "GEMSTONE IDENTIFICATION REPORT")

    # 4. Body Area
    body_y = y + 0.8 * mm
    body_height = title_y - body_y

    # Right column boundary (expanded to 25.5mm)
    right_col_width = 25.5 * mm
    right_col_x = x + CARD_WIDTH - 0.8 * mm - right_col_width

    # Separator line
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.line(right_col_x, body_y, right_col_x, title_y)

    # 4A. Left: Watermark (0.07 opacity so text prints razor sharp)
    if active_logo and os.path.exists(active_logo):
        try:
            c.saveState()
            c.setFillAlpha(0.07)
            watermark_size = 28 * mm
            c.drawImage(active_logo,
                        x + 2.0 * mm + (right_col_x - x - 2.0 * mm - watermark_size) / 2.0,
                        body_y + (body_height - watermark_size) / 2.0,
                        width=watermark_size, height=watermark_size,
                        preserveAspectRatio=True, mask='auto')
            c.restoreState()
        except Exception:
            pass

    # 4B. Left: Field Rows (10 rows)
    gem_name   = (cert.get('gemstone_name') or 'Gemstone')[:24]
    rep_num    = (cert.get('report_number') or '')[:18]
    raw_wt     = str(cert.get('weight_carat') or '')
    if raw_wt and not any(unit in raw_wt.lower() for unit in ['ct', 'cts', 'carat']):
        weight_val = raw_wt + ' ct'
    else:
        weight_val = raw_wt or '—'

    shape_val  = (cert.get('shape_cut') or '—')[:22]
    color_val  = (cert.get('color') or '—')[:22]
    ri_val     = (cert.get('refractive_index') or '—')[:18]
    hard_val   = (cert.get('hardness') or '—')[:16]
    clar_val   = (cert.get('clarity') or 'Transparent')[:22]
    comm_val   = (cert.get('comments') or cert.get('crystal_system') or 'None')[:24]
    issued_val = (cert.get('customer_name') or 'N/A')[:22]

    fields = [
        ("Gemstone",    gem_name,   COLOR_RED,                  6.6),
        ("Report No.",  rep_num,    COLOR_PRIMARY,              6.2),
        ("Weight",      weight_val, COLOR_TEXT_DARK,            6.2),
        ("Shape / Cut", shape_val,  COLOR_TEXT_DARK,            6.0),
        ("Colour",      color_val,  COLOR_TEXT_DARK,            6.0),
        ("Refractive",  ri_val,     COLOR_TEXT_DARK,            6.0),
        ("Hardness",    hard_val,   COLOR_TEXT_DARK,            6.0),
        ("Clarity",     clar_val,   COLOR_TEXT_DARK,            6.0),
        ("Comments",    comm_val,   colors.HexColor('#92400e'), 5.8),
        ("Issued To",   issued_val, COLOR_TEXT_DARK,            5.8),
    ]

    field_start_x = x + 2.2 * mm
    colon_x       = field_start_x + 16.5 * mm
    val_x         = colon_x + 2.0 * mm
    row_height    = 3.7 * mm
    curr_y        = title_y - 3.2 * mm

    # Zebra striping for easy reading
    left_width = right_col_x - (x + 0.8 * mm)
    for i in range(len(fields)):
        row_top = title_y - (i * row_height)
        if i % 2 == 1:
            c.setFillColor(COLOR_ZEBRA)
            c.rect(x + 0.8 * mm, row_top - row_height, left_width, row_height, fill=1, stroke=0)

    # Field text
    for key, val, val_color, val_size in fields:
        c.setFillColor(COLOR_TEXT_DARK)
        c.setFont("Helvetica-Bold", 5.6)
        c.drawString(field_start_x, curr_y, key)

        c.setFillColor(COLOR_TEXT_MID)
        c.setFont("Helvetica-Bold", 5.6)
        c.drawString(colon_x, curr_y, ":")

        c.setFillColor(val_color)
        c.setFont("Helvetica-Bold", val_size)
        c.drawString(val_x, curr_y, str(val))

        curr_y -= row_height

    # 4C. Right Column (Large QR + Scan Pill + Gem Photo + Gemologist)
    right_mid_x = right_col_x + (right_col_width / 2.0)

    # 1) Large QR Code (16.5mm x 16.5mm)
    qr_size = 16.5 * mm
    qr_x = right_mid_x - qr_size / 2.0
    qr_y = title_y - qr_size - 1.0 * mm

    # Clean white background card with border
    c.setFillColor(colors.white)
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.4)
    c.roundRect(qr_x - 0.4 * mm, qr_y - 0.4 * mm, qr_size + 0.8 * mm, qr_size + 0.8 * mm, 1.0 * mm, fill=1, stroke=1)

    qr_file = cert.get('qr_code_path')
    qr_drawn = False
    if qr_file:
        qr_full = os.path.join(base_dir, 'static', 'uploads', 'qrcodes', qr_file)
        if os.path.exists(qr_full):
            try:
                c.drawImage(qr_full, qr_x, qr_y,
                            width=qr_size, height=qr_size, preserveAspectRatio=True)
                qr_drawn = True
            except Exception:
                pass
    if not qr_drawn:
        c.setStrokeColor(COLOR_BORDER)
        c.rect(qr_x, qr_y, qr_size, qr_size, fill=0, stroke=1)
        c.setFillColor(COLOR_TEXT_MID)
        c.setFont("Helvetica-Bold", 5.0)
        c.drawCentredString(right_mid_x, qr_y + qr_size / 2.0 - 1.5 * mm, "QR CODE")

    # 2) Sleek "SCAN TO VERIFY" badge pill
    pill_w = 19.0 * mm
    pill_h = 2.5 * mm
    pill_x = right_mid_x - pill_w / 2.0
    pill_y = qr_y - pill_h - 0.8 * mm

    c.setFillColor(COLOR_PRIMARY)
    c.setStrokeColor(COLOR_ACCENT)
    c.setLineWidth(0.3)
    c.roundRect(pill_x, pill_y, pill_w, pill_h, 0.8 * mm, fill=1, stroke=1)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 4.0)
    c.drawCentredString(right_mid_x, pill_y + 0.7 * mm, "SCAN TO VERIFY")

    # 3) Gem Photo (11.5mm x 11.5mm)
    gem_size = 11.5 * mm
    gem_box_x = right_mid_x - gem_size / 2.0
    gem_box_y = y + 6.5 * mm

    img_file = cert.get('image_path')
    img_drawn = False
    if img_file:
        img_full = os.path.join(base_dir, 'static', 'uploads', img_file)
        if os.path.exists(img_full):
            try:
                c.drawImage(img_full, gem_box_x, gem_box_y,
                            width=gem_size, height=gem_size, preserveAspectRatio=True)
                c.setStrokeColor(COLOR_BORDER)
                c.setLineWidth(0.4)
                c.roundRect(gem_box_x, gem_box_y, gem_size, gem_size, 0.8 * mm, fill=0, stroke=1)
                img_drawn = True
            except Exception:
                pass
    if not img_drawn:
        c.setStrokeColor(COLOR_BORDER)
        c.setFillColor(COLOR_ZEBRA)
        c.roundRect(gem_box_x, gem_box_y, gem_size, gem_size, 0.8 * mm, fill=1, stroke=1)
        c.setFillColor(COLOR_ACCENT)
        c.setFont("Helvetica-Bold", 9.0)
        c.drawCentredString(right_mid_x, gem_box_y + 4.5 * mm, "◆")
        c.setFillColor(COLOR_TEXT_MID)
        c.setFont("Helvetica-Bold", 3.8)
        c.drawCentredString(right_mid_x, gem_box_y + 1.6 * mm, "GEM PHOTO")

    # 4) Gemologist Signature & Seal
    c.setFillColor(COLOR_PRIMARY)
    c.setFont("Helvetica-BoldOblique", 4.8)
    c.drawCentredString(right_mid_x, y + 4.0 * mm, (gemologist_name or 'Gemologist')[:16])
    c.setFillColor(COLOR_TEXT_MID)
    c.setFont("Helvetica-Bold", 3.6)
    c.drawCentredString(right_mid_x, y + 2.0 * mm, "Certified Gemologist")

    c.restoreState()


def generate_single_card_pdf(cert: dict, output_stream_or_path, base_dir: str = '.', gemologist_name: str = 'Gemologist'):
    """
    Generate a standalone CR-80 card PDF (85.6mm x 54mm).
    Direct 1-page PDF download.
    """
    can = canvas.Canvas(output_stream_or_path, pagesize=(CARD_WIDTH, CARD_HEIGHT))
    can.setTitle(f"{cert.get('report_number', 'Card')} - ID Card")
    draw_card(can, 0, 0, cert, base_dir=base_dir, gemologist_name=gemologist_name)
    can.showPage()
    can.save()


def generate_merged_cards_pdf(certs: list, output_stream_or_path, base_dir: str = '.', gemologist_name: str = 'Gemologist'):
    """
    Generate an A4 page containing up to 10 cards in a 2-column x 5-row grid.
    Strictly 1 single A4 page with trim guide marks.
    """
    can = canvas.Canvas(output_stream_or_path, pagesize=A4)
    can.setTitle("Gemstone ID Cards - Merged Sheet (10 Cards)")

    page_width, page_height = A4  # 210mm x 297mm

    # Limit to max 10 cards for 1 page
    selected = certs[:10]

    # Grid layout: 2 columns, 5 rows
    col_gap = 6.0 * mm
    row_gap = 2.4 * mm

    total_grid_width = 2 * CARD_WIDTH + col_gap
    start_x = (page_width - total_grid_width) / 2.0  # Center horizontally

    # 5 rows layout: fit up to 10 cards comfortably on 1 single A4 page
    start_y = 234.0 * mm

    # Top header on print sheet
    can.saveState()
    can.setFillColor(COLOR_PRIMARY)
    can.setFont("Helvetica-Bold", 7.5)
    can.drawCentredString(page_width / 2.0, page_height - 5.5 * mm, "INDIAN GEMOLOGICAL INSTITUTE — ID CARD PRINT SHEET")
    can.setFillColor(COLOR_TEXT_MID)
    can.setFont("Helvetica", 5.2)
    can.drawCentredString(page_width / 2.0, page_height - 7.8 * mm, f"A4 Standard Sheet • {len(selected)} Card(s) on 1 Page • Cut Along Card Borders")
    can.restoreState()

    for idx, cert in enumerate(selected):
        row = idx // 2  # 0, 1, 2, 3, 4
        col = idx % 2   # 0, 1

        x = start_x + col * (CARD_WIDTH + col_gap)
        y = start_y - row * (CARD_HEIGHT + row_gap)

        draw_card(can, x, y, cert, base_dir=base_dir, gemologist_name=gemologist_name)

        # Subtle cutting guide marks in corners of card for print trimming
        can.saveState()
        can.setStrokeColor(COLOR_BORDER)
        can.setLineWidth(0.3)
        mark_len = 1.5 * mm
        # Top-left
        can.line(x - 0.5 * mm - mark_len, y + CARD_HEIGHT, x - 0.5 * mm, y + CARD_HEIGHT)
        can.line(x, y + CARD_HEIGHT + 0.5 * mm, x, y + CARD_HEIGHT + 0.5 * mm + mark_len)
        # Top-right
        can.line(x + CARD_WIDTH + 0.5 * mm, y + CARD_HEIGHT, x + CARD_WIDTH + 0.5 * mm + mark_len, y + CARD_HEIGHT)
        can.line(x + CARD_WIDTH, y + CARD_HEIGHT + 0.5 * mm, x + CARD_WIDTH, y + CARD_HEIGHT + 0.5 * mm + mark_len)
        # Bottom-left
        can.line(x - 0.5 * mm - mark_len, y, x - 0.5 * mm, y)
        can.line(x, y - 0.5 * mm - mark_len, x, y - 0.5 * mm)
        # Bottom-right
        can.line(x + CARD_WIDTH + 0.5 * mm, y, x + CARD_WIDTH + 0.5 * mm + mark_len, y)
        can.line(x + CARD_WIDTH, y - 0.5 * mm - mark_len, x + CARD_WIDTH, y - 0.5 * mm)
        can.restoreState()

    # Strictly 1 page
    can.showPage()
    can.save()

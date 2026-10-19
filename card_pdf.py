"""
Card PDF Generator for Indian Gemological Institute
Generates single CR-80 card PDFs (85.6mm x 54mm) and merged 6-card A4 PDFs (2x3 grid)
using ReportLab with exact dimensions, colors, logos, and QR codes.
"""

import os
from io import BytesIO
from PIL import Image as PILImage
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect

# Exact ATM / ISO CR-80 card dimensions
CARD_WIDTH  = 85.6 * mm
CARD_HEIGHT = 54.0 * mm

# Color palette
COLOR_PRIMARY = colors.HexColor('#1e3a5f')
COLOR_ACCENT  = colors.HexColor('#c9a84c')
COLOR_RED     = colors.HexColor('#c0392b')
COLOR_GRAY    = colors.HexColor('#555555')
COLOR_LIGHT   = colors.HexColor('#f8fafc')
COLOR_BORDER  = colors.HexColor('#cccccc')


def draw_card(c: canvas.Canvas, x: float, y: float, cert: dict, base_dir: str = '.', gemologist_name: str = 'Gemologist'):
    """
    Draw a single ID card at position (x, y) with dimensions 85.6mm x 54mm.
    (x, y) is the bottom-left corner of the card.
    """
    c.saveState()

    # 1. Card Outer Container & Clipping
    c.setStrokeColor(COLOR_BORDER)
    c.setFillColor(colors.white)
    c.setLineWidth(0.6)
    c.roundRect(x, y, CARD_WIDTH, CARD_HEIGHT, 2 * mm, fill=1, stroke=1)

    # 2. Top Header (Logo + Institute Title)
    header_height = 8.5 * mm
    header_y = y + CARD_HEIGHT - header_height

    # Optimized logo thumbnail for small fast PDF
    thumb_path = os.path.join(base_dir, 'static', 'logo_card_thumb.png')
    logo_path  = os.path.join(base_dir, 'static', 'logo.jpeg')
    active_logo = None
    if os.path.exists(thumb_path):
        active_logo = thumb_path
    elif os.path.exists(logo_path):
        try:
            pil_img = PILImage.open(logo_path)
            pil_img.thumbnail((250, 250), PILImage.Resampling.LANCZOS)
            pil_img.save(thumb_path, optimize=True)
            active_logo = thumb_path
        except Exception:
            active_logo = logo_path

    if active_logo and os.path.exists(active_logo):
        try:
            c.drawImage(active_logo, x + 1.8 * mm, header_y + 0.8 * mm,
                        width=7.0 * mm, height=7.0 * mm, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # Header text
    c.setFillColor(COLOR_PRIMARY)
    c.setFont("Helvetica-Bold", 6.8)
    c.drawString(x + 10.0 * mm, header_y + 4.8 * mm, "Indian Gemological Institute")

    c.setFillColor(COLOR_GRAY)
    c.setFont("Helvetica", 3.8)
    c.drawString(x + 10.0 * mm, header_y + 1.6 * mm, "indiangemological.com  •  Gemological Testing Lab")

    # Header underline
    c.setStrokeColor(COLOR_PRIMARY)
    c.setLineWidth(1.0)
    c.line(x, header_y, x + CARD_WIDTH, header_y)

    # 3. Blue Title Bar
    title_height = 3.8 * mm
    title_y = header_y - title_height
    c.setFillColor(COLOR_PRIMARY)
    c.rect(x, title_y, CARD_WIDTH, title_height, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 5.2)
    c.drawCentredString(x + CARD_WIDTH / 2.0, title_y + 1.1 * mm, "GEMSTONE IDENTIFICATION CARD")

    # 4. Body Area
    body_y = y
    body_height = title_y - y

    # Right column boundary
    right_col_width = 21.0 * mm
    right_col_x = x + CARD_WIDTH - right_col_width

    # Separator between left fields and right photos
    c.setStrokeColor(colors.HexColor('#e2e8f0'))
    c.setLineWidth(0.5)
    c.line(right_col_x, body_y, right_col_x, title_y)

    # 4A. Left: Watermark (semi-transparent logo behind fields)
    if active_logo and os.path.exists(active_logo):
        try:
            c.saveState()
            c.setFillAlpha(0.12)
            watermark_size = 30 * mm
            c.drawImage(active_logo,
                        x + (CARD_WIDTH - right_col_width - watermark_size) / 2.0,
                        body_y + (body_height - watermark_size) / 2.0,
                        width=watermark_size, height=watermark_size,
                        preserveAspectRatio=True, mask='auto')
            c.restoreState()
        except Exception:
            pass

    # 4B. Left: Field Rows (10 rows)
    # Fields formatting: weight has NO 'ct', crystal sys is replaced by 'Comment'
    gem_name   = (cert.get('gemstone_name') or 'Gemstone')[:24]
    rep_num    = (cert.get('report_number') or '')[:18]
    weight_val = str(cert.get('weight_carat') or '')  # NO 'ct'
    shape_val  = (cert.get('shape_cut') or '—')[:22]
    color_val  = (cert.get('color') or '—')[:22]
    ri_val     = (cert.get('refractive_index') or '—')[:18]
    hard_val   = (cert.get('hardness') or '—')[:16]
    clar_val   = (cert.get('clarity') or 'Transparent')[:22]
    comm_val   = (cert.get('comments') or cert.get('crystal_system') or '..')[:24]
    issued_val = (cert.get('customer_name') or 'N/A')[:22]

    fields = [
        ("Name",        gem_name,   COLOR_RED,     True),
        ("Cert No.",    rep_num,    COLOR_PRIMARY, False),
        ("Weight",      weight_val, colors.black,  False),
        ("Shape / Cut", shape_val,  colors.black,  False),
        ("Colour",      color_val,  colors.black,  False),
        ("Refractive",  ri_val,     colors.black,  False),
        ("Hardness",    hard_val,   colors.black,  False),
        ("Clarity",     clar_val,   colors.black,  False),
        ("Comment",     comm_val,   colors.black,  False),
        ("Issued To",   issued_val, colors.black,  False),
    ]

    field_start_x = x + 1.8 * mm
    colon_x       = field_start_x + 16.5 * mm
    val_x         = colon_x + 2.0 * mm
    row_height    = 3.8 * mm
    curr_y        = title_y - 3.4 * mm

    for key, val, val_color, is_bold in fields:
        # Key
        c.setFillColor(colors.HexColor('#333333'))
        c.setFont("Helvetica-Bold", 4.9)
        c.drawString(field_start_x, curr_y, key)

        # Colon
        c.drawString(colon_x, curr_y, ":")

        # Value
        c.setFillColor(val_color)
        c.setFont("Helvetica-Bold" if is_bold else "Helvetica", 4.9)
        c.drawString(val_x, curr_y, str(val))

        curr_y -= row_height

    # 4C. Right Column (QR code + Gem image + Gemologist signature)
    right_mid_x = right_col_x + (right_col_width / 2.0)

    # 1) QR code at top of right column
    qr_file = cert.get('qr_code_path')
    qr_drawn = False
    if qr_file:
        qr_full = os.path.join(base_dir, 'static', 'uploads', 'qrcodes', qr_file)
        if os.path.exists(qr_full):
            try:
                qr_size = 13.5 * mm
                c.drawImage(qr_full, right_mid_x - qr_size / 2.0, title_y - qr_size - 1.2 * mm,
                            width=qr_size, height=qr_size, preserveAspectRatio=True)
                qr_drawn = True
            except Exception:
                pass
    if not qr_drawn:
        # Draw placeholder
        c.setStrokeColor(COLOR_BORDER)
        c.rect(right_mid_x - 6 * mm, title_y - 14 * mm, 12 * mm, 12 * mm, fill=0, stroke=1)
        c.setFont("Helvetica", 4)
        c.drawCentredString(right_mid_x, title_y - 8 * mm, "QR CODE")

    # 2) Gem photo in middle of right column
    img_file = cert.get('image_path')
    img_drawn = False
    gem_box_y = y + 7.5 * mm
    gem_size  = 12.0 * mm
    if img_file:
        img_full = os.path.join(base_dir, 'static', 'uploads', img_file)
        if os.path.exists(img_full):
            try:
                c.drawImage(img_full, right_mid_x - gem_size / 2.0, gem_box_y,
                            width=gem_size, height=gem_size, preserveAspectRatio=True)
                c.setStrokeColor(COLOR_BORDER)
                c.setLineWidth(0.4)
                c.rect(right_mid_x - gem_size / 2.0, gem_box_y, gem_size, gem_size, fill=0, stroke=1)
                img_drawn = True
            except Exception:
                pass
    if not img_drawn:
        c.setStrokeColor(COLOR_BORDER)
        c.setFillColor(COLOR_LIGHT)
        c.rect(right_mid_x - gem_size / 2.0, gem_box_y, gem_size, gem_size, fill=1, stroke=1)
        c.setFillColor(colors.HexColor('#888888'))
        c.setFont("Helvetica", 4.5)
        c.drawCentredString(right_mid_x, gem_box_y + 5.0 * mm, "GEM IMAGE")

    # 3) Gemologist signature text at bottom
    c.setFillColor(COLOR_PRIMARY)
    c.setFont("Helvetica-BoldOblique", 4.4)
    c.drawCentredString(right_mid_x, y + 4.0 * mm, (gemologist_name or 'Gemologist')[:16])
    c.setFillColor(COLOR_GRAY)
    c.setFont("Helvetica", 3.5)
    c.drawCentredString(right_mid_x, y + 1.8 * mm, "Certified Gemologist")

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
    Generate an A4 page containing up to 6 cards in a 2-column x 3-row grid.
    Strictly 1 single A4 page.
    """
    can = canvas.Canvas(output_stream_or_path, pagesize=A4)
    can.setTitle("Gemstone ID Cards - Merged Sheet")

    page_width, page_height = A4  # 210mm x 297mm

    # Limit to max 6 cards for 1 page
    selected = certs[:6]

    # Grid layout: 2 columns, 3 rows
    col_gap = 7.0 * mm
    row_gap = 8.0 * mm

    total_grid_width = 2 * CARD_WIDTH + col_gap
    start_x = (page_width - total_grid_width) / 2.0  # Center horizontally

    total_grid_height = 3 * CARD_HEIGHT + 2 * row_gap
    start_y = (page_height + total_grid_height) / 2.0 - CARD_HEIGHT  # Top row y

    # Optional header title at top of sheet
    can.saveState()
    can.setFillColor(COLOR_PRIMARY)
    can.setFont("Helvetica-Bold", 10)
    can.drawCentredString(page_width / 2.0, page_height - 14 * mm, "INDIAN GEMOLOGICAL INSTITUTE — ID CARD PRINT SHEET")
    can.setFillColor(COLOR_GRAY)
    can.setFont("Helvetica", 7)
    can.drawCentredString(page_width / 2.0, page_height - 18 * mm, f"A4 Sheet • {len(selected)} Card(s) on 1 Page")
    can.restoreState()

    for idx, cert in enumerate(selected):
        row = idx // 2  # 0, 1, 2
        col = idx % 2   # 0, 1

        x = start_x + col * (CARD_WIDTH + col_gap)
        y = start_y - row * (CARD_HEIGHT + row_gap)

        draw_card(can, x, y, cert, base_dir=base_dir, gemologist_name=gemologist_name)

    # Strictly 1 page
    can.showPage()
    can.save()

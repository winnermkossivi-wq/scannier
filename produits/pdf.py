"""Generation de PDF d'etiquettes code-barres pour les produits (vue patron / superuser)."""
import io

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

# Mise en page d'une page A4 : grille de etiquettes.
PAGE_W, PAGE_H = A4
LABEL_W = 270
LABEL_H = 150
MARGIN_X = 20
MARGIN_TOP = 20
GAP_X = 20
GAP_Y = 14
COLS = 2


def _barcode_image(data: str):
    """Genere une image code-barres Code128 en ImageReader. Fallback QR si echec."""
    try:
        import barcode
        from barcode.writer import ImageWriter

        code = barcode.get_barcode_class("code128")(str(data), writer=ImageWriter())
        buf = io.BytesIO()
        code.write(buf, options={"module_height": 10, "font_size": 10, "text_distance": 2, "quiet_zone": 2})
        buf.seek(0)
        return ImageReader(buf)
    except Exception:
        # fallback QR
        img = qrcode.make(data, box_size=4, border=2)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return ImageReader(buf)


def _qr_image(data: str, box_pixels: int = 4, border: int = 2):
    # Alias compat: anciennement QR, maintenant barcode
    return _barcode_image(data)


def generer_pdf_etiquettes(produit, quantite: int) -> bytes:
    """Retourne un PDF contenant `quantite` etiquettes du produit donne."""
    quantite = max(1, min(int(quantite or 1), 200))

    # Code-barres prioritaire (fallback id_qr pour anciennes donnees)
    payload = getattr(produit, "barcode_value", None) or (produit.code_barre if hasattr(produit, "code_barre") and produit.code_barre else str(produit.id_qr))
    if not payload:
        payload = str(produit.id_qr)
    nom = (produit.nom or "").strip()
    prix = "{:,.2f} FCFA".format(float(produit.prix))
    ref = (produit.reference.nom if produit.reference else "")
    code = str(payload)[:12]

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    per_page = 10
    for i in range(quantite):
        if i != 0 and i % per_page == 0:
            c.showPage()
        idx = i % per_page
        col = idx % COLS
        row = idx // COLS
        x = MARGIN_X + col * (LABEL_W + GAP_X)
        y_top = PAGE_H - MARGIN_TOP - (row + 1) * LABEL_H - row * GAP_Y
        y = y_top

        # Cadre de l'etiquette
        c.setStrokeColorRGB(0.6, 0.6, 0.6)
        c.setLineWidth(0.5)
        c.rect(x, y, LABEL_W, LABEL_H, stroke=1, fill=0)

        # Code-barres (rectangle en haut, centre)
        bar_w = 200
        bar_h = 55
        bar = _barcode_image(payload)
        bar_x = x + (LABEL_W - bar_w) / 2
        bar_y = y + LABEL_H - bar_h - 16
        c.drawImage(bar, bar_x, bar_y, width=bar_w, height=bar_h, preserveAspectRatio=True, anchor="c")

        # Texte sous le code-barres
        text_y = y + LABEL_H - bar_h - 28
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 12)
        label = nom if len(nom) <= 30 else nom[:28] + "\u2026"
        c.drawCentredString(x + LABEL_W / 2, text_y, label)

        c.setFont("Helvetica", 11)
        c.drawCentredString(x + LABEL_W / 2, text_y - 16, prix)

        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.35, 0.35, 0.35)
        if ref:
            c.drawCentredString(x + LABEL_W / 2, y + 10, ref)
        c.drawCentredString(x + LABEL_W / 2, y + 2, "ID " + code)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()

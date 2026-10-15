"""Create our own synthetic image-only PDFs. No real organizations or personal data."""
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "documents"
FONT_PATHS = ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def image_page(title, lines, subtitle="SYNTHETIC REFERENCE DOCUMENT"):
    font_path = next((p for p in FONT_PATHS if Path(p).exists()), None)
    font = ImageFont.truetype(font_path, 24) if font_path else ImageFont.load_default(size=24)
    heading = ImageFont.truetype(font_path, 42) if font_path else ImageFont.load_default(size=42)
    small = ImageFont.truetype(font_path, 18) if font_path else ImageFont.load_default(size=18)
    image = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1240, 12), fill="#275d4d")
    draw.text((95, 95), subtitle, font=small, fill="#789277")
    draw.text((95, 170), title, font=heading, fill="#244838")
    draw.line((95, 265, 1140, 265), fill="#d4dfcd", width=2)
    for i, line in enumerate(lines):
        draw.text((95, 325 + i * 64), line, font=font, fill="#293d2a")
    draw.text((95, 1640), "Generated fixture. Not a real invoice or legal agreement.", font=small, fill="#82957c")
    return image


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    invoice = image_page("INVOICE", [
        "Invoice number: INV-2026-0042", "Supplier: Cedar Example Studio", "Customer: Meadow Demo Labs",
        "Issue date: 2026-10-01", "Due date: 2026-10-31", "Currency: USD", "",
        "Description: Document automation reference build", "Subtotal: 2400.00", "Tax: 0.00", "Total due: 2400.00",
    ])
    invoice.save(ROOT / "synthetic-invoice.pdf", "PDF", resolution=150)
    invoice.save(ROOT / "synthetic-invoice.png")
    contract = image_page("SERVICE AGREEMENT", [
        "Agreement number: AGR-2026-0007", "Provider: Cedar Example Studio", "Customer: Meadow Demo Labs",
        "Effective date: 2026-10-05", "Currency: USD", "Total contract value: 7500.00", "",
        "Scope: Build a searchable document archive.", "The provider delivers source-linked structured records.",
        "No confidential information is included in this sample.",
    ])
    terms = image_page("AGREEMENT / TERMS", [
        "Agreement number: AGR-2026-0007", "Payment terms: Net 30 days after acceptance.",
        "Retention period: 30 days after the project ends.", "All data must be synthetic or publicly licensed.",
        "Governing law: Example jurisdiction (synthetic).",
    ])
    contract.save(ROOT / "synthetic-contract.pdf", "PDF", save_all=True, append_images=[terms], resolution=150)
    # An intentionally incomplete input exercises the missing-field review queue.
    incomplete = image_page("INVOICE / DRAFT", ["Invoice number: INV-2026-0099", "Supplier: Cedar Example Studio",
                                                "Currency: USD", "Total due: 180.00", "Customer: [illegible]"])
    incomplete.save(ROOT / "needs-review.pdf", "PDF", resolution=150)
    # Verify raster-only PDFs: OCR cannot secretly rely on embedded digital text.
    for path in ROOT.glob("*.pdf"):
        with pdfium.PdfDocument(path) as doc:
            assert all(not page.get_textpage().get_text_range().strip() for page in doc)
    print("Generated 3 image-only PDFs and 1 PNG; all data synthetic.")


if __name__ == "__main__":
    main()

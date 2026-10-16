import io
import threading
import warnings
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
import pytesseract
from PIL import Image

from app.config import Settings

Image.MAX_IMAGE_PIXELS = 16_000_000
# PDFium is not thread-safe, even for separate documents. API upload threads share this process.
_PDF_LOCK = threading.RLock()


@dataclass
class OcrPage:
    number: int
    text: str
    words: list[dict]
    width: int
    height: int


def inspect_file(path: Path, settings: Settings) -> int:
    with path.open("rb") as source:
        header = source.read(8)
    if header.startswith(b"%PDF-"):
        with _PDF_LOCK, pdfium.PdfDocument(path) as pdf:
            count = len(pdf)
            if not 1 <= count <= settings.max_pages:
                raise ValueError(f"Document must contain 1–{settings.max_pages} pages")
            for page in pdf:
                width, height = page.get_size()
                page.close()
                if width <= 0 or height <= 0 or width * height * 4 > Image.MAX_IMAGE_PIXELS:
                    raise ValueError("Page dimensions exceed the rendering limit")
            return count
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as image:
            if image.format not in {"PNG", "JPEG", "TIFF"}:
                raise ValueError("Only PDF, PNG, JPEG and TIFF are supported")
            count = getattr(image, "n_frames", 1)
            if not 1 <= count <= settings.max_pages:
                raise ValueError("Too many image frames")
            for number in range(count):
                image.seek(number)
                if image.width * image.height > Image.MAX_IMAGE_PIXELS:
                    raise ValueError("Image dimensions exceed the rendering limit")
                image.load()
            return count


def render_page(path: Path, number: int) -> Image.Image:
    with path.open("rb") as source:
        header = source.read(5)
    if header == b"%PDF-":
        with _PDF_LOCK, pdfium.PdfDocument(path) as pdf:
            page = pdf[number - 1]
            bitmap = page.render(scale=2)
            image = bitmap.to_pil().convert("RGB").copy()
            bitmap.close()
            page.close()
            return image
    with Image.open(path) as source:
        source.seek(number - 1)
        return source.convert("RGB").copy()


class TesseractOcr:
    def __init__(self, settings: Settings):
        self.language = settings.ocr_language

    def read(self, image: Image.Image, number: int) -> OcrPage:
        data = pytesseract.image_to_data(
            image,
            lang=self.language,
            config="--psm 3",
            timeout=90,
            output_type=pytesseract.Output.DICT,
        )
        words, lines = [], {}
        for i, raw in enumerate(data["text"]):
            text = raw.strip()
            if not text:
                continue
            line_id = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            lines.setdefault(line_id, []).append(text)
            words.append(
                {
                    "text": text,
                    "confidence": max(0, float(data["conf"][i])) / 100,
                    "box": [
                        data["left"][i] / image.width,
                        data["top"][i] / image.height,
                        data["width"][i] / image.width,
                        data["height"][i] / image.height,
                    ],
                }
            )
        return OcrPage(
            number, "\n".join(" ".join(line) for line in lines.values()), words, image.width, image.height
        )


class TextractOcr:
    """Opt-in only: SDK default credential chain; never create credentials here."""

    def __init__(self, settings: Settings, client=None):
        if not settings.allow_paid_ocr:
            raise ValueError("Textract requires owner approval and ALLOW_PAID_OCR=true")
        if client is None:
            import boto3

            client = boto3.client("textract", region_name=settings.aws_region)
        self.client = client

    def read(self, image: Image.Image, number: int) -> OcrPage:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        response = self.client.detect_document_text(Document={"Bytes": buffer.getvalue()})
        words, lines = [], []
        for block in response.get("Blocks", []):
            if block["BlockType"] == "LINE":
                lines.append(block["Text"])
            if block["BlockType"] == "WORD":
                box = block["Geometry"]["BoundingBox"]
                words.append(
                    {
                        "text": block["Text"],
                        "confidence": block["Confidence"] / 100,
                        "box": [box["Left"], box["Top"], box["Width"], box["Height"]],
                    }
                )
        return OcrPage(number, "\n".join(lines), words, image.width, image.height)


def make_ocr(settings: Settings):
    if settings.ocr_provider == "tesseract":
        return TesseractOcr(settings)
    if settings.ocr_provider == "textract":
        return TextractOcr(settings)
    raise ValueError("Unknown OCR provider")

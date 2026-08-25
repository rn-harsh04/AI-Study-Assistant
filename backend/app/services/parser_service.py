from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import logging
from pathlib import Path

logger = logging.getLogger("studyassistant.parser")


@dataclass(slots=True)
class ParsedPage:
    page_number: int | None
    text: str


class DocumentParser:
    def __init__(self, api_key: str | None = None, vision_model: str = "gemini-3.6-flash") -> None:
        self._api_key = api_key
        self._vision_model = vision_model or "gemini-3.6-flash"

    def parse(self, file_path: Path) -> list[ParsedPage]:
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return self._parse_pdf(file_path)
        if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            return self._parse_image(file_path)
        return self._parse_text(file_path)

    def _parse_pdf(self, file_path: Path) -> list[ParsedPage]:
        from pypdf import PdfReader
        from PIL import Image

        reader = PdfReader(str(file_path))
        pages: list[ParsedPage] = []

        for index, page in enumerate(reader.pages, start=1):
            text = ""
            try:
                text = (page.extract_text() or "").strip()
            except Exception as exc:
                logger.warning(f"Error extracting text from page {index}: {exc}")
                text = ""

            if not text:
                try:
                    import pytesseract
                    if hasattr(page, "images") and page.images:
                        for img in page.images:
                            if hasattr(img, "data") and len(img.data) > 10000:
                                pil_img = Image.open(BytesIO(img.data))
                                ocr_text = pytesseract.image_to_string(pil_img).strip()
                                if ocr_text:
                                    text = f"{text}\n{ocr_text}".strip()
                except Exception:
                    pass

            if text:
                pages.append(ParsedPage(page_number=index, text=text))

        return pages

    def _parse_text(self, file_path: Path) -> list[ParsedPage]:
        content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
        return [ParsedPage(page_number=None, text=content)] if content else []

    def _parse_image(self, file_path: Path) -> list[ParsedPage]:
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(file_path)
            ocr_text = pytesseract.image_to_string(img).strip()
            if ocr_text:
                return [ParsedPage(page_number=1, text=ocr_text)]
        except Exception:
            pass

        if not self._api_key:
            return []

        try:
            import google.generativeai as genai
            from PIL import Image

            genai.configure(api_key=self._api_key)
            model = genai.GenerativeModel(self._vision_model)
            image = Image.open(file_path)
            response = model.generate_content(
                [
                    "Extract all readable text, notes, equations, and diagrams from this study image. "
                    "Provide a clean structured transcript of the content. If completely unreadable, return EMPTY.",
                    image,
                ]
            )
            content = (getattr(response, "text", "") or "").strip()
            if not content or content.upper() == "EMPTY":
                return []
            return [ParsedPage(page_number=1, text=content)]
        except Exception as exc:
            logger.error(f"Image parsing error: {exc}")
            return []
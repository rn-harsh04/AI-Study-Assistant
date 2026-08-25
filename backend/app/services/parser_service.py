from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import logging
from pathlib import Path
import hashlib

logger = logging.getLogger("studyassistant.parser")


@dataclass(slots=True)
class ParsedPage:
    page_number: int | None
    text: str


class DocumentParser:
    def __init__(self, api_key: str | None = None, vision_model: str = "gemini-2.5-flash") -> None:
        self._api_key = api_key
        self._vision_model = vision_model

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

        # Configure generative vision client lazily if API key is provided
        genai_model = None
        if self._api_key:
            try:
                import google.generativeai as genai_pkg

                genai_pkg.configure(api_key=self._api_key)
                genai_model = genai_pkg.GenerativeModel(self._vision_model)
            except Exception as exc:
                logger.warning(f"Could not initialize Gemini vision model: {exc}")
                genai_model = None

        total_pages = len(reader.pages)
        vision_calls_count = 0
        MAX_VISION_CALLS = 5  # Cap vision calls per document to avoid 429 rate limits and long delays

        for index, page in enumerate(reader.pages, start=1):
            # 1) Extract digital text
            text = ""
            try:
                text = (page.extract_text() or "").strip()
            except Exception as exc:
                logger.warning(f"Error extracting text from page {index}: {exc}")
                text = ""

            # If page text is empty, check if OCR is available for scanned pages
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

            # 2) Extract prominent images / diagrams for description (if vision calls remaining)
            if vision_calls_count < MAX_VISION_CALLS and genai_model:
                try:
                    page_images = list(page.images) if hasattr(page, "images") else []
                    for img in page_images:
                        if vision_calls_count >= MAX_VISION_CALLS:
                            break
                        
                        img_data = getattr(img, "data", None)
                        if not img_data or len(img_data) < 5000:
                            # Skip tiny icons / decorative elements (<5KB)
                            continue

                        try:
                            pil_img = Image.open(BytesIO(img_data))
                            # Skip if image dimensions are too small to be a meaningful diagram
                            if pil_img.width < 150 or pil_img.height < 150:
                                continue

                            prompt = (
                                "Describe this diagram, chart, or image briefly (1-3 sentences). "
                                "List any key labels or data points. Reply with plain text only."
                            )
                            response = genai_model.generate_content([prompt, pil_img])
                            description = getattr(response, "text", "") or ""
                            if description.strip():
                                img_hash = hashlib.sha1(img_data).hexdigest()[:8]
                                pages.append(
                                    ParsedPage(
                                        page_number=index,
                                        text=f"[Diagram #{img_hash} on page {index}]: {description.strip()}",
                                    )
                                )
                                vision_calls_count += 1
                        except Exception as img_exc:
                            logger.debug(f"Image vision processing skipped: {img_exc}")
                except Exception:
                    pass

        return pages

    def _parse_text(self, file_path: Path) -> list[ParsedPage]:
        content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
        return [ParsedPage(page_number=None, text=content)] if content else []

    def _parse_image(self, file_path: Path) -> list[ParsedPage]:
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
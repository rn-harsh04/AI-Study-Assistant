from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
        # Enhanced PDF parsing: extract page text and any embedded images.
        # For images, attempt to get a short, searchable description using the
        # configured vision model (Gemini). Failures are non-fatal (we keep text).
        from pypdf import PdfReader
        from io import BytesIO
        from PIL import Image
        import hashlib

        reader = PdfReader(str(file_path))
        pages: list[ParsedPage] = []

        # configure generative vision client lazily
        genai = None
        model = None
        if self._api_key:
            try:
                import google.generativeai as genai_pkg

                genai_pkg.configure(api_key=self._api_key)
                genai = genai_pkg
                model = genai_pkg.GenerativeModel(self._vision_model)
            except Exception:
                genai = None
                model = None

        for index, page in enumerate(reader.pages, start=1):
            # 1) extract textual content if present
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if text and text.strip():
                pages.append(ParsedPage(page_number=index, text=text.strip()))

            # 2) extract images from the page. pypdf stores images in /Resources/XObject
            try:
                xobjects = page.get('/Resources', {}).get('/XObject', {})
            except Exception:
                xobjects = None

            # pypdf offers page.images() helper in newer versions; fall back safely
            images = []
            try:
                images = list(page.images) if hasattr(page, "images") else []
            except Exception:
                images = []

            # If images list empty, try the XObject approach
            if not images and xobjects:
                try:
                    for name, obj in (xobjects.items() if hasattr(xobjects, 'items') else []):
                        try:
                            data = obj.get_data()
                            images.append({"data": data})
                        except Exception:
                            continue
                except Exception:
                    images = images

            # process each image: generate a short description via vision LLM
            for img_idx, img in enumerate(images, start=1):
                img_bytes = None
                try:
                    # pypdf image entry may be an object with .data or dict with 'data'
                    if isinstance(img, dict) and img.get("data"):
                        img_bytes = img.get("data")
                    elif hasattr(img, "data"):
                        img_bytes = img.data
                    elif hasattr(img, "get_data"):
                        img_bytes = img.get_data()
                except Exception:
                    img_bytes = None

                if not img_bytes:
                    continue

                # create a stable short id for the image
                img_hash = hashlib.sha1(img_bytes).hexdigest()[:12]
                description = None

                # First try the vision LLM (if available)
                if genai and model:
                    try:
                        pil_img = Image.open(BytesIO(img_bytes))
                        prompt = (
                            "Describe the image briefly (1-3 sentences), mention any labels, diagram elements, "
                            "and extract any readable text. Reply with plain text only."
                        )
                        response = model.generate_content([prompt, pil_img])
                        # model.generate_content may set .text or .candidates
                        description = (getattr(response, "text", None) or "")
                        if not description:
                            # older responses may include candidates
                            candidates = getattr(response, "candidates", None)
                            if candidates:
                                description = str(candidates[0].get("content", ""))
                        description = (description or "").strip()
                    except Exception:
                        description = None

                if not description:
                    # as a graceful fallback, attempt to run OCR via pytesseract if available
                    try:
                        import pytesseract
                        pil_img = Image.open(BytesIO(img_bytes))
                        ocr = pytesseract.image_to_string(pil_img).strip()
                        if ocr:
                            description = f"Image with readable text: {ocr}"
                    except Exception:
                        description = None

                if description:
                    pages.append(
                        ParsedPage(
                            page_number=index,
                            text=f"[Image-description #{img_hash}] {description}",
                        )
                    )

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
                    "Extract all readable text from this image. Return only the extracted text. "
                    "If there is no readable text, return EMPTY.",
                    image,
                ]
            )
            content = (getattr(response, "text", "") or "").strip()
            if not content or content.upper() == "EMPTY":
                return []
            return [ParsedPage(page_number=None, text=content)]
        except Exception:
            return []

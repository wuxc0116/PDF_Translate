import io
import os
import tempfile
from typing import List

from flask import Flask, request, abort
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from deep_translator import GoogleTranslator

# Optional: if tesseract is not in PATH, set it here
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = Flask(__name__)

def extract_text_with_ocr(pdf_path: str, dpi: int = 300, ocr_lang: str = "eng") -> str:
    """
    Extract text from a PDF. For each page:
      - Try native text extraction (PyMuPDF).
      - If too little text, rasterize and OCR with Tesseract.
    Returns a single UTF-8 string with page separators.
    """
    doc = fitz.open(pdf_path)
    parts: List[str] = []

    for i, page in enumerate(doc):
        # 1) Native text extraction
        text = page.get_text("text") or ""
        # Heuristic: if less than ~40 non-whitespace chars, treat as scanned
        meaningful_len = len("".join(text.split()))
        if meaningful_len < 40:
            # 2) Rasterize + OCR
            # Use a matrix to achieve target DPI (72 base -> scale = dpi/72)
            scale = dpi / 72.0
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, alpha=False)  # no alpha channel

            # Convert Pixmap -> PIL.Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            # OCR
            ocr_text = pytesseract.image_to_string(img, lang=ocr_lang) or ""
            text = ocr_text

        # Add page header + text
        parts.append(f"\n\n===== Page {i+1} =====\n{text.strip()}")

    return "".join(parts).strip()

def chunk_text(s: str, max_len: int = 4500) -> List[str]:
    """
    Breaks text into chunks within translator-friendly limits,
    preferably on paragraph boundaries.
    """
    if not s:
        return []

    paragraphs = [p.strip() for p in s.split("\n\n") if p.strip()]
    chunks: List[str] = []
    buf: List[str] = []
    cur = 0

    for p in paragraphs:
        # If a single paragraph is huge, hard-split it
        if len(p) > max_len:
            if buf:
                chunks.append("\n\n".join(buf))
                buf, cur = [], 0
            # hard split
            start = 0
            while start < len(p):
                end = min(start + max_len, len(p))
                chunks.append(p[start:end])
                start = end
            continue

        if cur + len(p) + (2 if buf else 0) <= max_len:
            buf.append(p)
            cur += len(p) + (2 if buf else 0)
        else:
            chunks.append("\n\n".join(buf))
            buf, cur = [p], len(p)

    if buf:
        chunks.append("\n\n".join(buf))

    return chunks

def translate_text(text: str, target: str = "zh-CN") -> str:
    """
    Translate long text using deep-translator (GoogleTranslator) in chunks.
    """
    if not text:
        return ""

    translator = GoogleTranslator(source="auto", target=target)
    translated_parts: List[str] = []
    for chunk in chunk_text(text, max_len=4500):
        translated_parts.append(translator.translate(chunk))

    return "\n\n".join(translated_parts)

@app.route("/translate", methods=["POST"])
def translate_pdf_endpoint():
    """
    POST /translate
    Form-data:
      - file: the PDF to translate
      - target (optional): translation target (default zh-CN)
      - ocr_lang (optional): OCR language hint for Tesseract, default 'eng'
      - dpi (optional): rasterization DPI for OCR pages, default 300
    Returns: text/plain; UTF-8 translated text
    """
    if "file" not in request.files:
        abort(400, "No file part in request (expected 'file').")
    f = request.files["file"]
    if f.filename == "":
        abort(400, "No file selected.")
    if not f.filename.lower().endswith(".pdf"):
        abort(400, "Please upload a .pdf file.")

    target = request.form.get("target", "zh-CN")
    ocr_lang = request.form.get("ocr_lang", "eng")
    try:
        dpi = int(request.form.get("dpi", "300"))
    except ValueError:
        abort(400, "Invalid dpi (must be an integer).")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            f.save(tmp.name)
            tmp_path = tmp.name

        # 1) Extract (mixed-mode) text
        english_text = extract_text_with_ocr(tmp_path, dpi=dpi, ocr_lang=ocr_lang)

        if not english_text.strip():
            abort(422, "Could not extract any text from the PDF (even with OCR).")

        # 2) Translate
        translated = translate_text(english_text, target=target)

        return translated, 200, {"Content-Type": "text/plain; charset=utf-8"}

    except Exception as e:
        abort(500, f"Translation failed: {e}")

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    # For local dev; use a WSGI server (gunicorn/uwsgi) in production.
    app.run(host="0.0.0.0", port=5000, debug=True)

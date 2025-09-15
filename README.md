text_trans.py:

Can only translate pure text in pdf. i.e. no image, no formula

pip install flask deep-translator pymupdf pytesseract pillow

curl -X POST http://localhost:5000/translate \
  -F "file=@/path/to/your.pdf" \
  -H "Accept: text/plain"


-----------------------------------------------------------


OCR_Trans.py:

Can translate pdf that contains images

pip install flask deep-translator pymupdf pytesseract pillow

System Tesseract (required for OCR)
macOS (brew)

brew install tesseract

Ubuntu / Debian

sudo apt-get update && sudo apt-get install -y tesseract-ocr

Windows (choco; or download the Tesseract installer and add it to PATH)

choco install tesseract


# How to use:

Default: English -> Simplified Chinese, OCR with 'eng'
curl -X POST http://localhost:5000/translate \
  -F "file=@/path/to/your.pdf" \

  -H "Accept: text/plain"


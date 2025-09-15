from flask import Flask, request, abort
from deep_translator import GoogleTranslator
import tempfile
import os

app = Flask(__name__)

# Translate to Simplified Chinese; auto-detect source language (English in your case)
translator = GoogleTranslator(source="auto", target="zh-CN")

@app.route("/translate", methods=["POST"])
def translate_pdf():
    """
    Accepts a multipart/form-data upload with field name 'file' (a PDF).
    Returns the translated text as plain UTF-8.
    """
    if "file" not in request.files:
        abort(400, "No file part in request (expected field name 'file').")

    file = request.files["file"]
    if file.filename == "":
        abort(400, "No file selected.")

    # Ensure it's a PDF by extension (quick check; production could do MIME sniffing)
    if not file.filename.lower().endswith(".pdf"):
        abort(400, "Please upload a .pdf file.")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        # deep-translator will extract text from the PDF and translate it
        translated_text = translator.translate_file(tmp_path)

        # Return as plain text
        return translated_text, 200, {
            "Content-Type": "text/plain; charset=utf-8"
        }

    except Exception as e:
        # Bubble up the error message for easier debugging
        abort(500, f"Translation failed: {e}")

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    # For local testing only; use a proper WSGI server (e.g., gunicorn) in production
    app.run(host="0.0.0.0", port=5000, debug=True)

import functions_framework
import fitz  # PyMuPDF
import io
import re
import json

def rejoin_hyphenated_words(text: str) -> str:
    """
    Rejoins words that were hyphenated across lines in the PDF.
    """
    text = re.sub(r'-\\\s*\\n', '', text)
    return text

def clean_text(text: str) -> str:
    """
    Cleans the extracted text by removing in-line citations and other artifacts.
    """
    # Remove in-line citations like (Author, Year) or [1]
    text = re.sub(r'\\s*\\([^)]*\\s*,\\s*\\d{4}\\)', '', text)
    text = re.sub(r'\\s*\[\\d+\]', '', text)
    return text

@functions_framework.http
def pdf_processor(request):
    """
    Accepts a PDF file, cleans it, and chunks it into semantic "beats".
    """
    if request.method != 'POST':
        return 'Only POST requests are accepted', 405

    try:
        if 'file' not in request.files:
            return 'No file part in the request', 400

        file = request.files['file']

        if file.filename == '':
            return 'No file selected for uploading', 400

        file_bytes = file.read()
        doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
        
        full_text = ""
        for page in doc:
            page_height = page.rect.height
            header_margin = page_height * 0.10
            footer_margin = page_height * 0.90
            blocks = page.get_text("blocks")
            for block in blocks:
                if block[1] > header_margin and block[3] < footer_margin:
                    full_text += block[4]

        full_text = rejoin_hyphenated_words(full_text)

        reference_keywords = ["REFERENCES", "BIBLIOGRAPHY", "SEE ALSO"]
        for keyword in reference_keywords:
            if keyword in full_text:
                full_text = full_text.split(keyword)[0]
                break
        
        cleaned_text = clean_text(full_text)

        paragraphs = cleaned_text.split('\n')
        
        beats = []
        current_beat = []
        for para in paragraphs:
            processed_para = para.strip()
            if not processed_para:
                if current_beat:
                    beats.append(current_beat)
                    current_beat = []
            elif len(processed_para) > 20 and not processed_para.isdigit():
                current_beat.append(processed_para)
        
        if current_beat:
            beats.append(current_beat)

        return json.dumps({"beats": beats}), 200, {'Content-Type': 'application/json'}

    except Exception as e:
        return f"An error occurred: {e}", 500
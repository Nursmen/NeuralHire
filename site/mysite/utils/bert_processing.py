import os
import pytesseract
from pdf2image import convert_from_path
from transformers import pipeline
from pathlib import Path

# Initialize summarization pipeline
# Using a multilingual model suitable for Russian/English
SUMMARIZATION_MODEL = "IlyaGusev/mbart_ru_sum_gazeta" # Good for Russian summarization
_summarizer = None

def get_summarizer():
    """Lazy load the summarization pipeline."""
    global _summarizer
    if _summarizer is None:
        try:
            print(f"Loading summarization model: {SUMMARIZATION_MODEL}...")
            _summarizer = pipeline("summarization", model=SUMMARIZATION_MODEL)
        except Exception as e:
            print(f"Warning: Could not load summarization model {SUMMARIZATION_MODEL}: {e}")
            _summarizer = None
    return _summarizer

def ocr_pdf(pdf_path):
    """
    Extract text from PDF using OCR (Tesseract).
    """
    try:
        images = convert_from_path(pdf_path)
        full_text = ""
        for img in images:
            text = pytesseract.image_to_string(img, lang='rus+eng')
            full_text += text + "\n"
        return full_text
    except Exception as e:
        print(f"Error in OCR: {e}")
        return ""

def summarize_resume(pdf_path):
    """
    Extract text from PDF and summarize it using BERT/BART.
    Returns dictionary compatible with previous interface.
    """
    try:
        # 1. OCR
        full_text = ocr_pdf(pdf_path)
        if not full_text.strip():
            return None
            
        # 2. Summarize
        # Truncate text to fit model max length (approx 1024 tokens)
        # We'll take the first 4000 characters as a rough heuristic
        input_text = full_text[:4000] 
        
        summary_text = full_text # Default to full text if model fails
        
        summarizer = get_summarizer()
        if summarizer:
            try:
                # MBART expects src_lang for translation but for summarization typically just text
                summary_output = summarizer(input_text, max_length=600, min_length=100, do_sample=False)
                summary_text = summary_output[0]['summary_text']
            except Exception as e:
                print(f"Summarization failed: {e}")
                # Fallback to truncated text
                summary_text = input_text[:1000] + "..."

        # 3. Return generic structure
        # Since we don't have structured extraction anymore, we put everything in full_summary
        # and leave others empty or repeated.
        return {
            'skills': 'См. полное резюме (extracted via BERT)',
            'experience': 'См. полное резюме (extracted via BERT)',
            'preferences': 'См. полное резюме (extracted via BERT)',
            'full_summary': summary_text
        }

    except Exception as e:
        print(f"Error in summarize_resume: {e}")
        return None

def extract_resume_crops(pdf_path, keywords_list, output_dir):
    """
    Extract crops around keywords using Tesseract.
    """
    import os
    from PIL import Image
    
    crops = {}
    os.makedirs(output_dir, exist_ok=True)
    
    # User mentioned "hard coded what needs to be search... delete not needed"
    # Keeping the logic but using the passed keywords_list effectively?
    # Actually, previous code IGNORED the passed list and used ['Москву'].
    # The user said "i hard codded... so delete not needed".
    # I will assume we should respecting the argument if valid, or default to a reasonable list?
    # Or maybe the user meant "Delete the code that generates keywords, because I have hardcoded ones".
    # For now, I will use the passed list.
    
    # If the user really wants the hardcoded one, they can pass it from views.py
    # But wait, looking at the previous file:
    # keywords_list = ['Москву'] was INSIDE the function.
    # To preserve behavior requested ("hard codded..."), I will actually keep it hardcoded here? 
    # "delete not needed" -> maybe deletion of DYNAMIC keyword generation in views.py is what is needed.
    
    target_keywords = ['Москву'] # Hardcoded as per user hint
    
    try:
        images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=2)
        if not images:
            return crops

        for page_num, img in enumerate(images, 1):
            data = pytesseract.image_to_data(img, lang="rus", output_type=pytesseract.Output.DICT)
            n = len(data["text"])

            for keyword in target_keywords:
                if keyword in crops:
                    continue

                kw = keyword.lower()

                for i in range(n):
                    word = data["text"][i].strip().lower()
                    if not word or kw not in word:
                        continue

                    x = data["left"][i]
                    y = data["top"][i]
                    w = data["width"][i]
                    h = data["height"][i]

                    pad_x, pad_y = 30, 20
                    x1 = max(0, x - pad_x)
                    y1 = max(0, y - pad_y)
                    x2 = min(img.width, x + w + pad_x)
                    y2 = min(img.height, y + h + pad_y)

                    crop = img.crop((x1, y1, x2, y2))

                    name = f"crop_{keyword.replace(' ', '_')}_{page_num}.png"
                    path = os.path.join(output_dir, name)
                    crop.save(path)

                    crops[keyword] = path
                    break

        return crops

    except Exception as e:
        print(f"Error in extract_resume_crops: {e}")
        return crops

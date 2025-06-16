import pytesseract
from PIL import Image
from pdfminer.high_level import extract_text as extract_pdf_text
import io
import os

def extract_text_from_image(image_path):
    """Extracts text from a JPG/PNG image using Tesseract OCR."""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang='eng') # Specify language
        return text
    except Exception as e:
        logging.error(f"Error extracting text from image {image_path}: {e}")
        return ""

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF. Tries text extraction first, then OCR if needed."""
    try:
        # Try to extract searchable text first
        with open(pdf_path, 'rb') as fp:
            text = extract_pdf_text(fp)
        if text.strip(): # If text is found, it's a searchable PDF
            return text
        else: # PDF is likely scanned, perform OCR
            logging.info(f"No searchable text in {pdf_path}, attempting OCR...")
            return extract_text_from_scanned_pdf(pdf_path)
    except Exception as e:
        logging.error(f"Error extracting text from PDF {pdf_path}: {e}. Falling back to OCR if not already tried.")
        return extract_text_from_scanned_pdf(pdf_path) # Fallback if direct extraction fails


def extract_text_from_scanned_pdf(pdf_path):
    """Extracts text from a scanned PDF using OCR."""
    try:
        # Convert PDF to images, then OCR each image
        # This requires poppler-utils on the system for pdf2image to work,
        # but we are using PIL/pytesseract directly on images converted by other means,
        # or implicitly handled by pytesseract if it has pdf-to-image capabilities.
        # For simplicity in this example, we'll assume pytesseract can handle PDF input directly
        # or that the user preprocesses to images if direct OCR fails for multi-page PDFs.
        # A more robust solution might use `pdf2image` then loop through pages.
        # For this outline, we'll try pytesseract's direct PDF handling.
        text = pytesseract.image_to_string(Image.open(pdf_path), lang='eng')
        return text
    except Exception as e:
        logging.error(f"Error extracting text from scanned PDF {pdf_path} with OCR: {e}")
        return ""

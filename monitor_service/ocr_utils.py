import logging
import os
from PIL import Image
from pdfminer.high_level import extract_text as extract_pdf_text
import io

# Import Google Cloud Vision API client
from google.cloud import vision_v1p3beta1 as vision # Using v1p3beta1 for robust features, or use vision_v1
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import GoogleAPICallError

logger = logging.getLogger(__name__)

# Initialize Vision AI client with API key (assuming GEMINI_API_KEY works for Vision)
# It's better practice to use GOOGLE_APPLICATION_CREDENTIALS for service accounts
# but for simplicity with existing API key, we'll try this.
VISION_API_KEY = os.getenv("GEMINI_API_KEY") # Use your existing API key
client_options = ClientOptions(api_key=VISION_API_KEY)
vision_client = vision.ImageAnnotatorClient(client_options=client_options)


def detect_text_from_image_gcp(image_content):
    """Detects text in an image using Google Cloud Vision AI."""
    image = vision.Image(content=image_content)
    
    try:
        # Use document_text_detection for more comprehensive OCR, especially for documents
        response = vision_client.document_text_detection(image=image)
        # Or use text_detection for simpler, less dense text:
        # response = vision_client.text_detection(image=image)
        
        return response.full_text_annotation.text if response.full_text_annotation else ""
    except GoogleAPICallError as e:
        logger.error(f"Google Cloud Vision API error: {e}")
        return ""
    except Exception as e:
        logger.error(f"Error calling Google Cloud Vision API: {e}")
        return ""


def extract_text_from_image(image_path):
    """Extracts text from a JPG/PNG image using Google Cloud Vision AI."""
    try:
        with open(image_path, 'rb') as image_file:
            content = image_file.read()
        
        text = detect_text_from_image_gcp(content)
        return text
    except Exception as e:
        logger.error(f"Error processing image {image_path} for Vision AI: {e}")
        return ""


def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF.
    Attempts direct text extraction (for searchable PDFs) first.
    If no text is found, it falls back to OCR via Vision AI.
    For multi-page PDFs, Vision AI can process them directly but requires GCS.
    For local files, a simple fallback is to convert to images and then OCR.
    """
    try:
        # Try to extract searchable text first using pdfminer.six
        with open(pdf_path, 'rb') as fp:
            text = extract_pdf_text(fp)
        if text.strip(): # If text is found, it's a searchable PDF
            logger.info(f"Successfully extracted searchable text from PDF: {pdf_path}")
            return text
        else: # PDF is likely scanned or image-based, attempt OCR
            logger.info(f"No searchable text in {pdf_path}, attempting OCR via Vision AI...")
            # For simplicity, if pdfminer.six fails, we'll try to treat the PDF
            # as a single image for Vision AI. For multi-page PDFs,
            # you'd need to iterate pages (e.g., using pdf2image) or use Vision AI's
            # batch document text detection from GCS.
            with open(pdf_path, 'rb') as pdf_file:
                content = pdf_file.read()
            # Note: Directly sending PDF content might work for single-page image PDFs,
            # but for multi-page PDFs with Cloud Vision, it's better to use GCS.
            # As a simpler fallback for now, let's treat it as an image.
            # For better multi-page PDF OCR, you'd use Vision AI's async document detection on GCS.
            return detect_text_from_image_gcp(content)
            
    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_path}: {e}. Falling back to Vision AI OCR.")
        try:
            with open(pdf_path, 'rb') as pdf_file:
                content = pdf_file.read()
            return detect_text_from_image_gcp(content)
        except Exception as e_fallback:
            logger.error(f"Error in Vision AI fallback for PDF {pdf_path}: {e_fallback}")
            return ""

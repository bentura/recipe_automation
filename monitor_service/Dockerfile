FROM python:3.10-slim-buster

# Install Tesseract OCR engine
#RUN apt-get update && apt-get install -y \
#    tesseract-ocr \
#    libtesseract-dev \
#    tesseract-ocr-eng \
#    poppler-utils \
#    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "monitor.py"]

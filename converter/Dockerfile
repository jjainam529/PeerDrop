FROM python:3.12-slim
# Carlito/Caladea/Liberation are metric-compatible with Calibri/Cambria/Arial/Times,
# which is what keeps Word layouts from shifting in the PDF.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer libreoffice-impress libreoffice-calc fonts-liberation fonts-crosextra-carlito fonts-crosextra-caladea fonts-dejavu \
    tesseract-ocr ocrmypdf ghostscript \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" python-multipart pdf2docx
WORKDIR /app
COPY app.py .
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]

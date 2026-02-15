FROM python:3.10-slim

# Install LibreOffice (Mesin Konversi Word) & dependensi PDF ke Word
RUN apt-get update && apt-get install -y \
    libreoffice \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean

WORKDIR /app
COPY . .

# Pastikan requirements.txt Anda berisi: Flask, pdf2docx, Pillow, pypdf, gunicorn
RUN pip install --no-cache-dir -r requirements.txt

# Menjalankan server
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "api.app:app"]
import os
import subprocess
from flask import Flask, render_template, request, send_file, after_this_request, make_response
from werkzeug.utils import secure_filename

# Library untuk pemrosesan dokumen
from pdf2docx import Converter
from PIL import Image
from pypdf import PdfReader, PdfWriter

# Inisialisasi Flask
app = Flask(__name__, template_folder='../templates', static_folder='../static')

# --- KONFIGURASI SERVER ---
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024 

# Gunakan /tmp untuk menulis file sementara (Standar Docker & Cloud)
UPLOAD_FOLDER = '/tmp'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def hapus_file(filepath):
    """Fungsi pembantu untuk menghapus file dari server setelah dikirim."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Gagal menghapus {filepath}: {e}")

# --- ROUTES SEO & VERIFIKASI ---

@app.route('/ads.txt')
def ads_txt():
    return "google.com, pub-0000000000000000, DIRECT, f08c47fec0942fa0", 200, {'Content-Type': 'text/plain'}

@app.route('/google5b4bfe5fde837eb8.html')
def google_verification():
    return "google-site-verification: google5b4bfe5fde837eb8.html"

@app.route('/robots.txt')
def robots():
    return "User-agent: *\nDisallow: /uploads/\nAllow: /", 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://proconverterid.site/</loc></url>
      <url><loc>https://proconverterid.site/about</loc></url>
      <url><loc>https://proconverterid.site/privacy</loc></url>
      <url><loc>https://proconverterid.site/terms</loc></url>
    </urlset>"""
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response

# --- ROUTES HALAMAN UTAMA ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/about')
def about():
    return render_template('about.html')

# --- FITUR KONVERSI ---

# 1. WORD KE PDF (MENGGUNAKAN LIBREOFFICE DI SERVER)
@app.route('/word-to-pdf', methods=['POST'])
def word_to_pdf():
    file = request.files['file']
    if not file: return "No file", 400
    
    filename = secure_filename(file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(input_path)
    
    # Memanggil LibreOffice Headless untuk konversi Word ke PDF
    try:
        subprocess.run([
            'libreoffice', '--headless', '--convert-to', 'pdf', 
            '--outdir', UPLOAD_FOLDER, input_path
        ], check=True)
        
        output_path = os.path.splitext(input_path)[0] + ".pdf"
    except Exception as e:
        return f"Error konversi: {str(e)}", 500

    @after_this_request
    def cleanup(response):
        hapus_file(input_path)
        hapus_file(output_path)
        return response
    return send_file(output_path, as_attachment=True)

# 2. PDF KE WORD
@app.route('/pdf-to-word', methods=['POST'])
def pdf_to_word():
    file = request.files['file']
    if not file: return "No file", 400
    
    filename = secure_filename(file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    output_path = os.path.splitext(input_path)[0] + ".docx"
    
    file.save(input_path)
    try:
        cv = Converter(input_path)
        cv.convert(output_path)
        cv.close()
    except Exception as e:
        return f"Error konversi: {str(e)}", 500

    @after_this_request
    def cleanup(response):
        hapus_file(input_path)
        hapus_file(output_path)
        return response
    return send_file(output_path, as_attachment=True)

# 3. GAMBAR KE PDF
@app.route('/img-to-pdf', methods=['POST'])
def img_to_pdf():
    file = request.files['image']
    filename = secure_filename(file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    output_path = os.path.splitext(input_path)[0] + ".pdf"
    
    file.save(input_path)
    img = Image.open(input_path).convert('RGB')
    img.save(output_path)

    @after_this_request
    def cleanup(response):
        hapus_file(input_path)
        hapus_file(output_path)
        return response
    return send_file(output_path, as_attachment=True)

# 4. KOMPRES PDF
@app.route('/compress-pdf', methods=['POST'])
def compress_pdf():
    file = request.files['file']
    filename = secure_filename(file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    output_path = os.path.join(UPLOAD_FOLDER, "comp_" + filename)
    
    file.save(input_path)
    reader = PdfReader(input_path)
    writer = PdfWriter()
    for page in reader.pages:
        page.compress_content_streams()
        writer.add_page(page)
    
    with open(output_path, "wb") as f:
        writer.write(f)

    @after_this_request
    def cleanup(response):
        hapus_file(input_path)
        hapus_file(output_path)
        return response
    return send_file(output_path, as_attachment=True)

# 5. GABUNGKAN BEBERAPA PDF (MERGE)
@app.route('/merge-pdf', methods=['POST'])
def merge_pdf():
    files = request.files.getlist('files')
    merger = PdfWriter()
    output_path = os.path.join(UPLOAD_FOLDER, "merged_document.pdf")
    
    saved_paths = []
    for file in files:
        filename = secure_filename(file.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)
        saved_paths.append(path)
        merger.append(path)
    
    merger.write(output_path)
    merger.close()

    @after_this_request
    def cleanup(response):
        for p in saved_paths: hapus_file(p)
        hapus_file(output_path)
        return response
    return send_file(output_path, as_attachment=True)

# 6. BANYAK GAMBAR KE SATU PDF
@app.route('/multi-img-to-pdf', methods=['POST'])
def multi_img_to_pdf():
    files = request.files.getlist('images')
    image_list = []
    temp_paths = []
    
    for file in files:
        filename = secure_filename(file.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)
        temp_paths.append(path)
        img = Image.open(path).convert('RGB')
        image_list.append(img)
    
    output_path = os.path.join(UPLOAD_FOLDER, "combined_images.pdf")
    if image_list:
        image_list[0].save(output_path, save_all=True, append_images=image_list[1:])

    @after_this_request
    def cleanup(response):
        for p in temp_paths: hapus_file(p)
        hapus_file(output_path)
        return response
    return send_file(output_path, as_attachment=True)

# --- MENJALANKAN APLIKASI ---
if __name__ == '__main__':
    app.run(debug=True)
from pathlib import Path
import re
import time

from flask import Flask, flash, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = "local-archive-demo"
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

DOCUMENTS = [
    {"name": "Pedoman Administrasi 2026.pdf", "category": "Administrasi", "size": "1.2 MB"},
    {"name": "Laporan Keuangan Q3.xlsx", "category": "Keuangan", "size": "842 KB"},
    {"name": "Notulen Rapat Divisi.docx", "category": "Rapat", "size": "356 KB"},
    {"name": "Foto Kegiatan Kantor.jpg", "category": "Dokumentasi", "size": "2.0 MB"},
    {"name": "SOP Pengadaan Barang.pdf", "category": "Operasional", "size": "780 KB"},
]


@app.route("/")
def index():
    query = request.args.get("q", "").strip()
    documents = DOCUMENTS[:]
    search_error = None

    if query:
        try:
            pattern = re.compile(query, re.IGNORECASE)
            documents = [document for document in documents if pattern.search(document["name"])]
        except re.error as error:
            search_error = f"Regex tidak valid: {error}"
            documents = []

    uploaded = sorted((path.name for path in UPLOAD_DIR.iterdir() if path.is_file()), key=str.lower)
    return render_template(
        "index.html",
        documents=documents,
        uploaded=uploaded,
        query=query,
        search_error=search_error,
    )


@app.post("/upload")
def upload():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Pilih file terlebih dahulu.", "error")
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    if not filename:
        flash("Nama file tidak valid.", "error")
        return redirect(url_for("index"))

    file.save(UPLOAD_DIR / filename)
    flash(f"{filename} berhasil diunggah melalui browser.", "success")
    return redirect(url_for("index"))


@app.get("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.get("/export")
def export_report():
    # Workload is deliberately capped so this local teaching demo cannot exhaust the host.
    requested = request.args.get("items", default=100, type=int)
    items = max(1, min(requested, 5000))
    started = time.perf_counter()
    checksum = sum((index * 17) % 97 for index in range(items))
    elapsed_ms = (time.perf_counter() - started) * 1000
    return render_template("report.html", items=items, checksum=checksum, elapsed_ms=elapsed_ms)


@app.errorhandler(413)
def request_too_large(_error):
    flash("Ukuran file melebihi batas browser 2 MB.", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)

# ArsipKu - Portal Arsip Internal

Demo Flask sederhana untuk latihan keamanan aplikasi secara lokal. Fitur yang tersedia:

- pencarian dokumen dengan pola regex;
- upload browser dengan batas 2 MB;
- folder `uploads/` untuk mensimulasikan arsip yang terhubung ke FTP;
- export report dengan workload terukur.

## Menjalankan

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Buka `http://127.0.0.1:5000`.

> Demo ini tidak memasang server FTP dan tidak menjalankan workload tak terbatas. Jika ingin menguji keamanan, jalankan hanya di mesin/VM lokal yang terisolasi dan gunakan fitur simulasi dengan beban kecil.

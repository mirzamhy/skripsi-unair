# UNAIR Skripsi Downloader

Alat untuk mengunduh skripsi dari repository Universitas Airlangga ([ir.unair.ac.id](https://ir.unair.ac.id)) yang hanya bisa dibaca lewat tampilan flipbook, lalu menyimpannya jadi satu file PDF.

## Cara kerja

Viewer Digital Collection UNAIR memakai flipbook (FlipBuilder/FlipHTML5). Setiap halaman skripsi sebenarnya disimpan sebagai gambar JPG terpisah dengan pola URL:

```
https://ir.unair.ac.id/uploaded_files/temporary/DigitalCollection/<HASH>/files/mobile/<N>.jpg
```

`<HASH>` adalah kode koleksi yang ada di link skripsi, `<N>` nomor halaman mulai dari 1.

Alurnya:

1. Ambil `<HASH>` dari link `index.html` yang ditempel pengguna.
2. Baca judul skripsi dari `index.html` (`og:title`, `<title>`, atau meta `Description`) untuk dijadikan nama file.
3. Unduh `1.jpg`, `2.jpg`, dan seterusnya sampai halaman tidak ditemukan beberapa kali berturut-turut.
4. Gabungkan semua JPG jadi satu PDF memakai Pillow.

Ada jeda 0,15 detik antar halaman supaya tidak membebani server. Verifikasi SSL dimatikan karena sertifikat server UNAIR sering bermasalah.

## Struktur file

| File | Isi |
|------|-----|
| `scraper_core.py` | Logika inti: ambil HASH, judul, jumlah halaman, unduh halaman, gabung PDF. Dipakai oleh GUI. |
| `gui_scrapper.py` | GUI desktop pakai tkinter: input link, nama file, folder tujuan, progress, dan log. |
| `UNAIR Skripsi Downloader.spec` | Konfigurasi PyInstaller untuk membuat `.exe`. |
| `CARA_PAKAI.txt` | Panduan singkat untuk pengguna `.exe`. |

## Instalasi

Butuh Python 3.10 ke atas.

```bash
pip install -r requirements.txt
```

## Cara pakai

```bash
python gui_scrapper.py
```

1. Buka skripsi di browser sampai muncul tampilan flipbook, lalu salin link dari address bar. Contoh:
   `https://ir.unair.ac.id/uploaded_files/temporary/DigitalCollection/XXXXXX==/index.html`
2. Tempel link ke kolom "Link skripsi".
3. Klik "Deteksi judul" agar nama file terisi otomatis dari judul skripsi.
4. Pilih folder tujuan, lalu klik "Download PDF".

## Build jadi .exe

```bash
pip install pyinstaller
pyinstaller "UNAIR Skripsi Downloader.spec"
```

Hasilnya ada di folder `dist/`.

## Catatan

- Link skripsi bersifat sementara (folder `temporary`). Kalau hasilnya 0 halaman, buka ulang skripsi di browser dan salin link terbaru.
- Gunakan untuk keperluan belajar dan referensi pribadi. Hormati hak cipta penulis skripsi.

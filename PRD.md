Tentu, ini adalah rancangan komprehensif untuk proyek **Universal Video Downloader** Anda. Karena ini untuk penggunaan *local development*, kita akan fokus pada fungsionalitas inti tanpa terlalu memikirkan kompleksitas deployment produksi (seperti load balancing atau CDN).

> **⚠️ Disclaimer Penting:** Mengunduh konten dari YouTube, Instagram, Facebook, dan TikTok mungkin melanggar Ketentuan Layanan (Terms of Service) platform tersebut. Pastikan aplikasi ini digunakan untuk tujuan pembelajaran atau pengarsipan konten pribadi (Fair Use).

-----

### I. Product Requirements Document (PRD)

#### 1\. Ringkasan Proyek

Sebuah aplikasi web berbasis Django yang memungkinkan pengguna menempelkan (paste) URL dari berbagai platform media sosial, memproses video tersebut, dan memberikan opsi untuk mengunduhnya ke komputer lokal. PostgreSQL digunakan untuk menyimpan riwayat pengunduhan.

#### 2\. Fitur Utama (Functional Requirements)

  * **Input URL Universal:** Satu kolom input yang cerdas untuk mendeteksi link dari YouTube, FB, TikTok, atau IG.
  * **Ekstraksi Metadata:** Sebelum download, sistem menampilkan:
      * Thumbnail video.
      * Judul video.
      * Durasi.
      * Pilihan resolusi (jika tersedia).
  * **Download Handler:** Mengunduh video ke server lokal (folder `media/`) lalu menyajikannya ke browser user, atau memberikan *direct stream*.
  * **Riwayat Download:** Menyimpan log aktivitas (URL asli, Judul, Tanggal Download) ke dalam PostgreSQL.
  * **Format Handling:** Mendukung format MP4.

#### 3\. Alur Pengguna (User Flow)

1.  User membuka halaman beranda.
2.  User menempelkan link (misal: link TikTok) ke kolom input.
3.  User menekan tombol "Proses".
4.  Aplikasi menampilkan preview video dan tombol "Download Video".
5.  User menekan tombol download.
6.  File tersimpan di komputer user dan data tercatat di database.

#### 4\. Spesifikasi Teknis

  * **Backend:** Python 3.10+, Django 5.x
  * **Database:** PostgreSQL (menyimpan tabel `DownloadHistory`)
  * **Engine Downloader:** `yt-dlp` (Library paling powerful saat ini, fork dari youtube-dl).
  * **Frontend:** HTML5 Standard + CSS Framework (rekomendasi: Bootstrap atau Tailwind via CDN untuk dev lokal).

-----

### II. Rekomendasi Library & Tools

Untuk kebutuhan ini, Anda tidak perlu membuat scraper dari nol. Gunakan library yang sudah teruji.

| Kategori | Nama Library/Tool | Fungsi |
| :--- | :--- | :--- |
| **Core Downloader** | **`yt-dlp`** | **Wajib.** Ini adalah library paling powerful. Mendukung YouTube, TikTok, FB, dan IG secara native. Jauh lebih baik daripada `pytube`. |
| **Database Driver** | `psycopg2-binary` | Driver agar Django bisa berkomunikasi dengan PostgreSQL. |
| **Environment** | `python-dotenv` | Untuk menyimpan kredensial database dan SECRET\_KEY dengan aman di file `.env`. |
| **UI Styling** | `django-crispy-forms` | (Opsional) Agar form Django terlihat bagus secara otomatis dengan Bootstrap/Tailwind. |
| **Utility** | `ffmpeg` | **Software (Bukan Python lib)**. Harus diinstall di OS Anda (Mac/Windows/Linux). `yt-dlp` butuh ini untuk menggabungkan video & audio (merging). |

**Perintah Install:**

```bash
pip install django psycopg2-binary yt-dlp python-dotenv
```

-----

### III. Struktur Project (Django Best Practices)

Berikut adalah struktur folder yang direkomendasikan agar kode rapi dan mudah dikembangkan (scalable).

```text
video_downloader_project/
│
├── manage.py
├── .env                  <-- Simpan setting DB di sini
├── requirements.txt
│
├── core_project/         <-- Folder setting Django utama
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── downloader/           <-- App utama kita
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py         <-- Model 'DownloadHistory'
│   ├── urls.py           <-- Routing URL khusus downloader
│   ├── views.py          <-- Logic HTTP request/response
│   │
│   ├── services.py       <-- PENTING: Taruh logic yt-dlp di sini (jangan numpuk di views)
│   │
│   ├── templates/
│   │   └── downloader/
│   │       ├── base.html
│   │       ├── home.html
│   │       └── result.html
│   │
│   └── migrations/
│
└── media/                <-- Tempat video sementara disimpan sebelum dikirim ke user
    └── downloads/
```

-----

### IV. Rancangan Database (Models)

Di `downloader/models.py`, kita buat sederhana saja untuk mencatat riwayat.

```python
from django.db import models

class DownloadHistory(models.Model):
    PLATFORM_CHOICES = [
        ('YT', 'YouTube'),
        ('FB', 'Facebook'),
        ('IG', 'Instagram'),
        ('TT', 'TikTok'),
        ('OT', 'Other'),
    ]

    original_url = models.URLField(max_length=500)
    title = models.CharField(max_length=255, blank=True, null=True)
    platform = models.CharField(max_length=2, choices=PLATFORM_CHOICES, default='OT')
    file_size = models.CharField(max_length=50, blank=True, null=True) # misal: "15.4 MB"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or self.original_url
```

-----

### V. Strategi Logika Downloader (`services.py`)

Jangan taruh logika berat di `views.py`. Gunakan `services.py` agar kode bersih. Berikut contoh *pseudocode*-nya menggunakan `yt-dlp`:

```python
# downloader/services.py
import yt_dlp

def get_video_info(url):
    ydl_opts = {
        'format': 'best', # Ambil kualitas terbaik
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False) # False = cuma ambil data, jangan download dulu
            return {
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'platform': info.get('extractor_key'),
                'direct_url': info.get('url') # Link langsung ke file video (jika didukung)
            }
        except Exception as e:
            return {'error': str(e)}

def download_video_file(url):
    # Logic untuk benar-benar mendownload file ke folder /media/
    pass
```

### VI. Tantangan Teknis (Untuk Diperhatikan)

1.  **Cookies & Login:** Instagram dan Facebook seringkali memblokir akses jika tidak ada session login. `yt-dlp` memiliki fitur `--cookies-from-browser`, namun untuk aplikasi web, Anda mungkin perlu mengekspor cookies (`cookies.txt`) dan menyimpannya di server agar `yt-dlp` bisa menggunakannya.
2.  **TikTok Watermark:** Secara default, `yt-dlp` seringkali mengambil versi dengan watermark. Mengambil versi *non-watermark* mungkin memerlukan konfigurasi API khusus atau library tambahan.
3.  **Waktu Proses:** Mendownload video panjang akan memakan waktu. Di local development, browser mungkin akan *timeout*.
      * *Solusi Simple:* Batasi durasi video (misal max 10 menit).
      * *Solusi Advanced:* Gunakan Celery (Asynchronous Task) - *tapi ini mungkin terlalu rumit untuk tahap awal.*

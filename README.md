# NVR CCTV Manager

Aplikasi desktop berbasis Python dan OpenCV untuk mengelola, memantau, dan merekam stream video kamera CCTV melalui protokol RTSP (Real-Time Streaming Protocol).

Aplikasi ini dirancang untuk operasional stabil multi-kamera, dengan pemrosesan rekaman di latar belakang (background thread) agar antarmuka tidak membeku (freeze), pemisahan berkas video mandiri per kamera, dan pembersihan otomatis berkas rekaman lama.

---

## Fitur Utama

- **Perekaman RTSP Multi-Kamera**: Mendukung pemantauan dan perekaman beberapa kamera CCTV secara simultan melalui transport TCP yang stabil.
- **Isolasi Berkas Rekaman**: Setiap kamera menyimpan video ke berkas terpisah dengan penamaan berbasis IP dan timestamp (`rec_{ip}_{timestamp}.mp4`), mencegah konflik penimpaan data antar kamera.
- **Perekaman Asinkron & Antarmuka Responsif**: Koneksi dan pembacaan stream dijalankan pada thread terpisah. Jendela aplikasi tetap responsif meskipun kamera sedang offline atau mengalami gangguan jaringan.
- **Pembagian Berkas Berkala (Split Recording)**: Membagi rekaman video ke berkas baru secara periodik (misal setiap 5 menit) tanpa kehilangan frame dan tanpa kebocoran memori.
- **Pembersihan Rekaman Otomatis**: Menghapus folder rekaman lama secara berkala berdasarkan rentang hari (retensi) yang ditentukan pengguna.
- **Finalisasi Berkas Aman (Graceful Shutdown)**: Saat aplikasi ditutup, seluruh encoder video ditutup secara berurutan untuk memastikan berkas MP4 tidak korup.
- **Antarmuka Desktop Industrial Clean**: Desain bertema kontras tinggi yang memenuhi standar aksesibilitas WCAG AA, dilengkapi tabel status CCTV, tombol uji koneksi cepat, dan konsol catatan aktivitas real-time.
- **Tersedia Versi Executable (.exe)**: Dapat langsung dijalankan di Windows tanpa perlu menginstal Python atau pustaka tambahan.

---

## Persyaratan Sistem

### Menjalankan Berkas Executable (.exe)
- **Sistem Operasi**: Windows 10 atau Windows 11 (64-bit)
- Tidak memerlukan instalasi Python tambahan.

### Menjalankan dari Kode Sumber (Python)
- **Python**: Versi 3.8 hingga 3.12 (64-bit)
- **Pustaka Python**:
  - `opencv-python` (versi 4.x atau 5.x)
  - `numpy`
  - `tkinter` (bawaan instalasi standar Python)

Instalasi pustaka yang diperlukan:
```bash
pip install opencv-python numpy
```

---

## Panduan Penggunaan

### 1. Menjalankan Versi Executable
Buka folder `dist/` dan jalankan:
```text
dist/NVR-CCTV-Manager.exe
```

### 2. Menjalankan dari Kode Sumber
Buka terminal di direktori proyek dan jalankan:
```bash
python nvr_improved.py
```

### 3. Menambahkan Kamera CCTV
1. Klik tombol **+ Tambah CCTV**.
2. Masukkan parameter kamera:
   - **Alamat IP**: Alamat IPv4 kamera (contoh: `192.168.1.100`).
   - **Username**: Nama pengguna untuk otentikasi RTSP (contoh: `admin`).
   - **Password**: Kata sandi kamera.
3. Tekan **Enter** atau klik **Simpan CCTV**.

### 4. Menguji Koneksi Kamera
1. Pilih baris kamera pada tabel.
2. Klik tombol **Uji Koneksi Kamera**.
3. Aplikasi akan mencoba membuka stream RTSP di latar belakang dan melaporkan hasilnya melalui dialog dan konsol log.

### 5. Mengatur Parameter Perekaman
- **Durasi Total (detik)**: Batas waktu total perekaman. Isi `0` jika ingin merekam terus-menerus hingga dihentikan secara manual.
- **Durasi File / Split (detik)**: Panjang durasi tiap berkas rekaman sebelum dibagi ke berkas baru (default: `300` detik = 5 menit).
- **Masa Simpan (hari)**: Jumlah hari penyimpanan rekaman. Berkas yang lebih tua dari batas ini akan dihapus saat pembersihan dijalankan (default: `7` hari).
- Klik **Simpan Parameter** untuk menyimpan perubahan ke berkas konfigurasi `nvr_config.json`.

### 6. Memulai dan Menghentikan Rekaman
- Klik tombol hijau **Mulai Perekaman** untuk memulai perekaman seluruh CCTV yang terdaftar.
- Klik tombol merah **Hentikan Perekaman** untuk mengakhiri perekaman dan memfinalisasi semua berkas video.

---

## Format Penyimpanan Berkas

Rekaman disimpan secara otomatis pada folder `storage/` yang dikelompokkan berdasarkan tanggal:

```text
storage/
└── 2026-10-27/
    ├── rec_192_168_1_100_20261027_080000.mp4
    ├── rec_192_168_1_100_20261027_080500.mp4
    └── rec_192_168_1_101_20261027_080000.mp4
```

Setiap nama berkas menyertakan IP kamera dan tanggal-waktu mulai rekaman, sehingga data dari kamera yang berbeda tidak akan saling menimpa.

---

## Cara Membuat Berkas Executable Sendiri

Untuk mengompilasi ulang kode sumber menjadi berkas `.exe` mandiri menggunakan PyInstaller:

1. Pasang PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Jalankan perintah kompilasi:
   ```bash
   python -m PyInstaller --noconfirm --clean --onefile --windowed --name "NVR-CCTV-Manager" nvr_improved.py
   ```
3. Berkas executable yang dihasilkan akan tersedia di folder `dist/NVR-CCTV-Manager.exe`.

---

## Struktur Berkas Proyek

```text
Nvr-CCTV-Manager-/
├── nvr_improved.py        # Program utama dengan perbaikan thread safety dan arsitektur asinkron
├── nvr.py                 # Versi skrip awal (referensi historis)
├── nvr_config.json        # Berkas konfigurasi CCTV dan parameter perekaman
├── dist/
│   └── NVR-CCTV-Manager.exe # Berkas aplikasi mandiri siap pakai untuk Windows
├── storage/               # Direktori penyimpanan rekaman video (dikelompokkan per tanggal)
├── README.md              # Dokumentasi teknis proyek
└── user_guide.md          # Panduan lengkap operasional dan pemecahan masalah
```

---

## Pemecahan Masalah (Troubleshooting)

- **Kamera Berstatus "Koneksi Gagal" atau "Sinyal Hilang"**:
  - Pastikan komputer dan kamera berada di subnet jaringan yang sama.
  - Periksa apakah port `554` pada kamera terbuka dan tidak diblokir oleh firewall router.
  - Pastikan username dan password RTSP sudah sesuai dengan konfigurasi kamera.
- **Port RTSP Berbeda**:
  - Secara default, aplikasi menggunakan port standar `554` dengan channel path `/Streaming/Channels/101` (kompatibel dengan Hikvision, Dahua, ONVIF, dan merek sejenis).
- **Video Rusak Saat Komputer Mati Mendadak**:
  - Format container yang digunakan adalah MP4 dengan encoder `mp4v`. Gunakan pemutar media seperti VLC Media Player untuk kompatibilitas codec optimal.

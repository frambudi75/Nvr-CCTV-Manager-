# Catatan Perubahan (Changelog)

Semua perubahan penting pada proyek NVR CCTV Manager dicatat dalam berkas ini. Format penulisan mengacu pada standar [Keep a Changelog](https://keepachangelog.com/).

---

## [3.1.0] - 2026-10-27

Pembaruan besar arsitektur backend, peningkatan stabilitas multi-kamera, pembuatan versi executable mandiri, dan perombakan antarmuka pengguna berbasis standar industrial modern.

### Diperbaiki (Fixed)
- **Konflik Nama Berkas Multi-Kamera**: Memperbaiki masalah kritis di mana beberapa kamera yang merekam bersamaan menulis ke berkas yang sama dan menyebabkan korupsi data. Nama berkas kini dipisahkan secara independen berdasarkan IP kamera (`rec_{ip}_{timestamp}.mp4`).
- **Antarmuka Membeku (UI Freeze)**: Memperbaiki pemblokiran thread utama Tkinter saat mencoba menghubungkan ke kamera RTSP yang sedang offline. Semua proses jaringan kini dijalankan asinkron pada background thread.
- **Crash `NoneType` saat Split Recording**: Memperbaiki pengecualian `AttributeError: 'NoneType' object has no attribute 'write'` ketika koneksi stream sempat terputus saat rotasi berkas video berlangsung.
- **Frame Hilang pada Rotasi Berkas**: Memperbaiki logika pembagian rekaman agar frame yang sedang dibaca langsung ditulis ke berkas baru tanpa terbuang.
- **Batas Durasi Total Diabaikan**: Memperbaiki loop monitoring worker agar mematuhi parameter durasi total yang diatur pengguna.
- **Akumulasi Latensi Buffer**: Menghilangkan jeda tidur statis (hardcoded sleep) yang menyebabkan pembacaan frame tertinggal dari waktu nyata kamera.
- **Korupsi Header Video MP4**: Menambahkan penanganan protokol penutupan jendela (`WM_DELETE_WINDOW`) agar seluruh VideoWriter merilis berkas secara bersih sebelum aplikasi keluar.
- **Pembersihan Berkas Lama Tidak Akurat**: Mengubah metode deteksi folder lama dari `os.path.getmtime` menjadi parsing tanggal kalender pasti (`YYYY-MM-DD`) untuk menghindari ketidakkonsistenan metadata NTFS di Windows.

### Ditambahkan (Added)
- **Aplikasi Mandiri Executable (.exe)**: Menambahkan berkas siap pakai `dist/NVR-CCTV-Manager.exe` untuk sistem operasi Windows tanpa perlu menginstal Python dan pustaka OpenCV.
- **Desain Antarmuka Industrial Clean**: Membangun ulang GUI dengan tema kontras tinggi yang memenuhi standar aksesibilitas WCAG AA (Deep Charcoal `#13161c` dan Slate).
- **Tabel Monitoring Status CCTV**: Menampilkan daftar kamera secara terstruktur lengkap dengan status operasional real-time per kamera (Siap, Menghubungkan, Merekam, Sinyal Hilang).
- **Fitur Uji Koneksi Cepat**: Menambahkan tombol pengujian koneksi langsung untuk memverifikasi alamat IP, port 554, dan kredensial RTSP sebelum perekaman dimulai.
- **Konsol Catatan Aktivitas Real-Time**: Panel log langsung di bagian bawah aplikasi untuk memantau status RTSP, rotasi berkas, dan peringatan jaringan per detik.
- **Aksesibilitas Navigasi Keyboard**: Mendukung navigasi Tab yang logis, tombol `Enter` untuk konfirmasi formulir, dan tombol `Escape` untuk menutup jendela dialog.
- **Berkas Konfigurasi Git (.gitignore)**: Menambahkan aturan pengabaian untuk cache Python (`__pycache__`), folder penyimpanan (`storage/`), dan artefak kompilasi (`build/`, `dist/`, `*.spec`).

### Diubah (Changed)
- Menulis ulang seluruh dokumentasi [README.md](README.md) dan [user_guide.md](user_guide.md) dengan bahasa yang terstruktur, faktual, bebas dari klaim berlebihan, dan sesuai dengan alur kerja aplikasi terkini.
- Memperbarui berkas [nvr_config.json](nvr_config.json) untuk mendukung parameter default baru yang lebih stabil.

---

## [3.0.0] - 2025-08-05

### Diperbaiki (Fixed)
- Pembaruan penanganan koneksi RTSP dasar pada `nvr_improved.py`.
- Penyesuaian dokumentasi awal pada panduan pengguna.

---

## [2.0.0] - 2025-08-05

### Ditambahkan (Added)
- Integrasi skrip perbaikan awal `nvr_improved.py`.
- Pengenalan mekanisme retry koneksi sederhana.

---

## [1.0.0] - 2024-01-15

### Ditambahkan (Added)
- Rilis awal skrip NVR CCTV Manager (`nvr.py`).
- Dukungan dasar koneksi RTSP menggunakan OpenCV.
- Pengaturan durasi rekaman dan rotasi file sederhana.
- Antarmuka pengguna dasar berbasis Tkinter.

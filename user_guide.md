# Panduan Pengguna - NVR CCTV Manager

Dokumen ini berisi panduan lengkap untuk instalasi, konfigurasi, operasional, dan pemecahan masalah aplikasi NVR CCTV Manager.

---

## Daftar Isi
1. [Pengenalan Sistem](#pengenalan-sistem)
2. [Persyaratan Perangkat & Jaringan](#persyaratan-perangkat--jaringan)
3. [Cara Menjalankan Aplikasi](#cara-menjalankan-aplikasi)
4. [Tata Cara Penggunaan Antarmuka](#tata-cara-penggunaan-antarmuka)
5. [Manajemen Rekaman & Penyimpanan](#manajemen-rekaman--penyimpanan)
6. [Kompilasi Berkas Executable](#kompilasi-berkas-executable)
7. [Panduan Pemecahan Masalah](#panduan-pemecahan-masalah)
8. [Pertanyaan yang Sering Diajukan (FAQ)](#pertanyaan-yang-sering-diajukan-faq)

---

## Pengenalan Sistem

NVR CCTV Manager adalah perangkat lunak perekam video jaringan (Network Video Recorder) berbasis komputer desktop. Aplikasi ini menghubungkan komputer Anda ke kamera CCTV IP melalui protokol RTSP (Real-Time Streaming Protocol) dan menyimpan rekaman ke dalam format video MP4 terkompresi.

Fitur keamanan dan stabilitas utama:
- Setiap kamera merekam ke dalam berkas independen dengan identitas IP pada nama berkas.
- Proses inisialisasi jaringan dan perekaman berjalan di latar belakang (asinkron), menjaga antarmuka tetap lancar tanpa gangguan "Not Responding".
- Perekaman jangka panjang dibagi secara otomatis ke dalam interval berkas (split recording) untuk memudahkan pencarian arsip dan mencegah ukuran berkas terlalu besar.
- Fitur pembersihan otomatis menghapus berkas rekaman lama berdasarkan tanggal kalender.

---

## Persyaratan Perangkat & Jaringan

### Kebutuhan Perangkat Keras
- **Prosesor**: Intel Core i3 / AMD Ryzen 3 atau setara (disarankan quad-core untuk lebih dari 4 kamera).
- **RAM**: Minimal 4 GB (disarankan 8 GB jika merekam banyak kamera beresolusi tinggi).
- **Ruang Penyimpanan**: Hard disk atau SSD dengan kapasitas memadai untuk menyimpan berkas video.

### Kebutuhan Jaringan
- Komputer dan kamera CCTV harus berada dalam satu jaringan lokal (LAN) atau terhubung melalui routing/VPN yang dapat saling menjangkau.
- Port RTSP standar `554` harus terbuka dan dapat diakses dari komputer perekam.
- Kamera CCTV mendukung streaming RTSP H.264/MPEG-4 (seperti Hikvision, Dahua, EZVIZ, Tapo, Reolink, IMOU, dan kamera bersertifikasi ONVIF).

---

## Cara Menjalankan Aplikasi

### Metode 1: Menggunakan Berkas Executable (.exe)
Jika Anda menggunakan Windows dan tidak memiliki Python terpasang:
1. Masuk ke folder `dist/`.
2. Klik ganda berkas `NVR-CCTV-Manager.exe`.
3. Aplikasi akan langsung terbuka tanpa perlu konfigurasi pustaka tambahan.

### Metode 2: Menggunakan Python dari Kode Sumber
Jika Anda ingin menjalankan aplikasi dari kode sumber:
1. Pastikan Python 3.8 atau yang lebih baru telah terpasang di komputer.
2. Buka terminal atau Command Prompt pada folder proyek.
3. Pasang pustaka OpenCV dan NumPy:
   ```bash
   pip install opencv-python numpy
   ```
4. Jalankan aplikasi:
   ```bash
   python nvr_improved.py
   ```

---

## Tata Cara Penggunaan Antarmuka

Antarmuka NVR CCTV Manager terdiri dari empat bagian fungsional:

### 1. Panel Daftar Kamera CCTV
Menampilkan daftar seluruh kamera CCTV yang tersimpan dalam sistem beserta status operasionalnya.

- **Menambahkan CCTV Baru**:
  1. Klik tombol **+ Tambah CCTV** di atas tabel.
  2. Masukkan alamat IP kamera (contoh: `192.168.1.100`).
  3. Masukkan username dan password RTSP kamera.
  4. Klik **Simpan CCTV** atau tekan tombol **Enter**.
- **Menghapus CCTV**:
  1. Pilih salah satu baris kamera pada tabel.
  2. Klik tombol **Hapus Terpilih**.
  3. Konfirmasi dialog penghapusan.
- **Menguji Koneksi Kamera**:
  1. Pilih baris kamera pada tabel.
  2. Klik tombol **Uji Koneksi Kamera**.
  3. Sistem akan menguji apakah stream RTSP kamera dapat diakses secara langsung tanpa memulai rekaman.

### 2. Panel Pengaturan Perekaman
Digunakan untuk mengatur parameter teknis penyimpanan video:
- **Durasi Total (detik)**: Mengatur lama perekaman berjalan. Jika diisi `0`, perekaman akan berlangsung terus-menerus hingga Anda menekan tombol hentikan secara manual.
- **Durasi File / Split (detik)**: Mengatur durasi pemecahan berkas rekaman. Nilai default adalah `300` detik (5 menit per berkas video).
- **Masa Simpan (hari)**: Mengatur batas retensi penyimpanan. Berkas video yang berumur lebih tua dari jumlah hari ini akan dihapus saat pembersihan dijalankan.
- Klik tombol **Simpan Parameter** untuk menyimpan pengaturan ke berkas `nvr_config.json`.

### 3. Panel Kontrol Operasi
- **Mulai Perekaman**: Menghubungkan seluruh kamera yang terdaftar dan mulai menulis data video ke disk. Tombol ini otomatis dinonaktifkan saat perekaman aktif.
- **Hentikan Perekaman**: Mengirim sinyal penghentian ke seluruh proses perekaman, menutup berkas MP4 dengan aman, dan merilis sumber daya stream.
- **Bersihkan Rekaman Lama**: Menghapus direktori rekaman yang tanggalnya telah melampaui masa simpan.

### 4. Panel Catatan Aktivitas Sistem
Menampilkan riwayat kejadian secara kronologis (timestamp, status koneksi, pembuatan berkas baru, peringatan jaringan, dan pesan error).

---

## Manajemen Rekaman & Penyimpanan

### Lokasi dan Struktur Direktori
Semua berkas rekaman disimpan di dalam folder `storage/` pada direktori kerja aplikasi. Struktur folder menggunakan format tanggal kalender:

```text
storage/
├── 2026-10-26/
│   ├── rec_192_168_1_50_20261026_090000.mp4
│   └── rec_192_168_1_50_20261026_090500.mp4
└── 2026-10-27/
    ├── rec_192_168_1_50_20261027_080000.mp4
    └── rec_192_168_1_51_20261027_080000.mp4
```

### Format Penamaan Berkas
Setiap berkas diberi nama dengan pola:
```text
rec_{IP_KAMERA}_{TAHUNBULANTANGGAL}_{JAMMENITDETIK}.mp4
```
Contoh: `rec_192_168_1_100_20261027_143000.mp4`. Penamaan ini menjamin tidak ada dua kamera yang menulis ke berkas yang sama meskipun waktu perekaman bertepatan.

---

## Kompilasi Berkas Executable

Jika Anda memodifikasi kode program dan ingin membuat berkas `.exe` baru:

1. Pasang PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Jalankan perintah kompilasi:
   ```bash
   python -m PyInstaller --noconfirm --clean --onefile --windowed --name "NVR-CCTV-Manager" nvr_improved.py
   ```
3. Berkas executable siap didistribusikan akan berada pada folder `dist/NVR-CCTV-Manager.exe`.

---

## Panduan Pemecahan Masalah

### 1. Status Kamera Menampilkan "Koneksi Gagal"
- Periksa kesesuaian segmen IP antara komputer dan kamera. Misalnya, jika IP komputer adalah `10.11.12.124`, komputer tidak dapat mengakses kamera di IP `10.10.0.5` secara langsung tanpa adanya gateway atau rute antar-subnet.
- Uji koneksi fisik menggunakan perintah ping di terminal:
  ```bash
  ping <IP_CCTV>
  ```
- Periksa apakah username atau password RTSP memiliki karakter khusus yang memerlukan verifikasi ulang.

### 2. Berkas Rekaman Tidak Dapat Diputar di Pemutar Bawaan Windows
- Aplikasi menggunakan codec standar `mp4v`. Beberapa versi pemutar media bawaan Windows memerlukan paket codec tambahan.
- Disarankan menggunakan pemutar media VLC Media Player atau MPC-HC untuk hasil pemutaran yang optimal.

### 3. Log Menampilkan "Sinyal Hilang" saat Perekaman
- Kondisi ini menandakan transmisi paket video dari kamera ke komputer terputus sementara.
- Sistem secara otomatis akan mencoba membaca kembali stream setiap detik hingga transmisi pulih tanpa menghentikan aplikasi.

### 4. Perekaman Berhenti Sendiri
- Periksa nilai **Durasi Total** pada pengaturan. Jika nilai durasi diisi selain `0` (misalnya 3600), perekaman akan berhenti otomatis setelah durasi tersebut tercapai. Ubah ke `0` untuk perekaman tanpa batas.

---

## Pertanyaan yang Sering Diajukan (FAQ)

**Q: Apakah aplikasi ini membutuhkan koneksi internet untuk merekam?**  
A: Tidak. Aplikasi bekerja sepenuhnya pada jaringan lokal (LAN). Selama komputer dan kamera terhubung pada switch atau router lokal, perekaman tetap berjalan normal tanpa internet.

**Q: Berapa jumlah maksimal kamera yang dapat ditambahkan?**  
A: Tidak ada batasan bawaan pada perangkat lunak. Jumlah kamera yang dapat direkam secara stabil bergantung pada kapasitas CPU, kecepatan kartu jaringan (NIC), dan kecepatan baca-tulis media penyimpanan komputer Anda.

**Q: Apa yang terjadi jika komputer mati mendadak saat merekam?**  
A: Berkas video yang sedang aktif ditulis mungkin terputus pada detik terakhir, namun berkas-berkas interval sebelumnya yang telah di-split tetap utuh dan tersimpan secara aman di direktori `storage/`.

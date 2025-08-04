# NVR CCTV Manager - Versi Bahasa Indonesia

## 📋 **Ringkasan Proyek**
NVR CCTV Manager adalah sistem perekaman video jaringan berbasis Python untuk kamera CCTV. Sistem ini mendukung pemantauan langsung dan perekaman dari kamera CCTV melalui protokol RTSP dengan penanganan koneksi otomatis dan manajemen file yang cerdas.

## 🆕 **Update Terbaru - nvr_improved.py**
**Versi terbaru dengan perbaikan bug kritis dan peningkatan performa!**

### ✅ **Perbaikan Utama dari Versi Lama:**
- **Koneksi RTSP yang Stabil** - Dengan retry otomatis hingga 3 kali
- **Memory Management** - Tidak ada lagi memory leak
- **Thread Safety** - Operasi multi-thread yang aman
- **File Video yang Sehat** - Tidak ada lagi file rusak
- **Error Handling** - Penanganan error yang komprehensif

## 🚀 **Fitur Lengkap**

### **Fitur Baru di nvr_improved.py:**
- ✅ **Koneksi Otomatis** dengan retry logic
- ✅ **Pembersihan File Lama** otomatis berdasarkan hari
- ✅ **Validasi Input** untuk IP address dan pengaturan
- ✅ **Monitoring Status** real-time
- ✅ **Logging dengan Rotasi** otomatis
- ✅ **Split File Otomatis** untuk mencegah file terlalu besar
- ✅ **Resource Management** yang baik

### **Fitur Asli yang Dipertahankan:**
- 📹 **Live streaming** dari CCTV
- 🎥 **Perekaman video** otomatis
- 🖥️ **GUI berbasis Tkinter** yang user-friendly
- ⚙️ **Manajemen CCTV** (tambah, lihat, hapus)
- 🗂️ **Penyimpanan terorganisir** per tanggal
- 🧹 **Pembersihan otomatis** file lama

## 📦 **Persyaratan Sistem**

### **Software Requirements:**
- Python 3.7 atau lebih baru
- OpenCV (`opencv-python` dan `opencv-python-headless`)
- Tkinter (sudah termasuk di Python)
- FFmpeg untuk decoding H.264

### **Instalasi Dependencies:**
```bash
# Install semua dependencies
pip install opencv-python opencv-python-headless
```

## 🛠️ **Cara Instalasi dan Penggunaan**

### **Langkah 1: Jalankan Program**
```bash
# Gunakan versi yang sudah diperbaiki
python nvr_improved.py
```

### **2. Menambahkan CCTV Baru**
1. Klik tombol **"➕ Tambah CCTV"**
2. Masukkan **IP Address** CCTV (contoh: 192.168.1.100)
3. Masukkan **Username** untuk login CCTV
4. Masukkan **Password** untuk login CCTV
5. Klik OK untuk menyimpan

### **3. Pengaturan Rekaman**
- **Durasi Total Perekaman**: Total waktu perekaman dalam detik (default: 3600 = 1 jam)
- **Durasi File Rekaman**: Durasi per file video sebelum di-split (default: 300 = 5 menit)
- **Simpan Selama**: Berapa hari file akan disimpan (default: 7 hari)

### **4. Kontrol Rekaman**
- **▶️ Mulai Rekaman**: Mulai merekam semua CCTV yang terdaftar
- **⏹️ Hentikan**: Berhenti merekam semua CCTV
- **🧹 Bersihkan Lama**: Hapus file rekaman lama secara manual

## 📁 **Struktur File**

```
NVR-CCTV-Manager/
├── nvr_improved.py      # Program utama (versi yang diperbaiki)
├── nvr.py               # Program lama (untuk referensi)
├── nvr_config.json      # File konfigurasi (auto-generated)
├── nvr_log.txt          # Log aktivitas (auto-generated)
├── storage/             # Folder penyimpanan video
│   ├── 2024-01-15/
│   │   ├── recording_143000.mp4
│   │   └── recording_143500.mp4
│   └── 2024-01-16/
└── README.md            # File ini
```

## 🎯 **Panduan Penggunaan (Bahasa Indonesia)**

### **1. Menambahkan CCTV Baru**
1. Jalankan program: `python nvr_improved.py`
2. Klik tombol **"➕ Tambah CCTV"**
3. Masukkan IP Address CCTV (contoh: 192.168.1.100)
4. Masukkan Username dan Password
5. Klik OK untuk menyimpan

### **2. Melihat Daftar CCTV**
- Klik **"📋 Lihat Daftar"** untuk melihat semua CCTV yang terdaftar
- Informasi yang ditampilkan: nomor urut, IP address, dan username

### **3. Menghapus CCTV**
- Klik **"🗑️ Hapus CCTV"** dan pilih dari daftar
- Konfirmasi penghapusan untuk menghapus CCTV

### **4. Pengaturan Rekaman**
- **Durasi Total**: Total waktu perekaman dalam detik
- **Durasi File**: Durasi per file video sebelum di-split
- **Simpan Selama**: Berapa hari file akan disimpan

## 🔧 **Troubleshooting**

### **Masalah Umum dan Solusi:**
- **Koneksi CCTV Gagal**: Pastikan IP address benar dan kamera terjangkau
- **File Video Rusak**: Codec otomatis menggunakan mp4v/avc1 yang stabil
- **Memory Leak**: Sudah diperbaiki dengan resource management otomatis

## 📞 **Dukungan**
Untuk pertanyaan atau laporan bug, silakan buat issue di repository ini.

## 📄 **Lisensi**
Proyek ini open-source dan tersedia untuk digunakan secara gratis.

"""
NVR CCTV Manager - Improved & Hardened Version
Arsitektur thread-safe, non-blocking UI, penamaan file per-kamera independen,
rotasi log otomatis, dan antarmuka industrial clean berstandar WCAG AA.
"""

import cv2
import datetime
import os
import time
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from threading import Thread, Event, Lock
import urllib.parse
import logging
from logging.handlers import RotatingFileHandler
import json
import re
from typing import List, Dict, Optional, Tuple
import numpy as np


# ============================================================================
# LOGGING SYSTEM
# ============================================================================
class NVRLogger:
    """Sistem logging thread-safe dengan rotasi file otomatis."""
    def __init__(self, log_file: str = 'nvr_log.txt', max_size: int = 5 * 1024 * 1024):
        self.logger = logging.getLogger('NVR')
        self.logger.setLevel(logging.INFO)
        
        # Hindari duplikasi handler jika diinisialisasi ulang
        if not self.logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            
            # File handler dengan rotasi (maks 5MB, simpan 3 backup)
            file_handler = RotatingFileHandler(log_file, maxBytes=max_size, backupCount=3, encoding='utf-8')
            file_handler.setFormatter(formatter)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def get_logger(self) -> logging.Logger:
        return self.logger


logger = NVRLogger().get_logger()


# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================
class NVRConfig:
    """Manajemen konfigurasi thread-safe untuk pengaturan dan daftar CCTV."""
    def __init__(self, config_file: str = 'nvr_config.json'):
        self.config_file = config_file
        self.lock = Lock()
        self._config = self._load_config()

    def _default_config(self) -> Dict:
        return {
            'cctv_list': [],
            'settings': {
                'duration': 3600,         # 0 = tanpa batas / manual stop
                'split_duration': 300,    # 5 menit per file
                'days_to_keep': 7,        # hapus file lebih tua dari 7 hari
                'max_retries': 3,
                'retry_delay': 3,
                'fps_target': 20
            }
        }

    def _load_config(self) -> Dict:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    defaults = self._default_config()
                    # Pastikan struktur kunci lengkap
                    if 'cctv_list' not in data:
                        data['cctv_list'] = defaults['cctv_list']
                    if 'settings' not in data:
                        data['settings'] = defaults['settings']
                    else:
                        for key, val in defaults['settings'].items():
                            data['settings'].setdefault(key, val)
                    return data
            except Exception as e:
                logger.error(f"Gagal membaca konfigurasi: {e}")
                return self._default_config()
        return self._default_config()

    def save(self, cctv_list: List[Dict], settings: Dict):
        with self.lock:
            self._config = {
                'cctv_list': cctv_list,
                'settings': settings
            }
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self._config, f, indent=4)
                logger.info("Konfigurasi berhasil disimpan ke file")
            except Exception as e:
                logger.error(f"Gagal menyimpan konfigurasi: {e}")

    def get(self) -> Tuple[List[Dict], Dict]:
        with self.lock:
            return list(self._config.get('cctv_list', [])), dict(self._config.get('settings', {}))


# ============================================================================
# RTSP CONNECTION HANDLER
# ============================================================================
class RTSPConnection:
    """Pengelola koneksi RTSP mandiri dengan opsi socket TCP dan deteksi stream."""
    def __init__(self, url: str, ip: str, max_retries: int = 3, retry_delay: int = 3):
        self.url = url
        self.ip = ip
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.cap: Optional[cv2.VideoCapture] = None
        self.width = 1280
        self.height = 720
        self.fps = 20.0

    def connect(self, stop_event: Optional[Event] = None) -> bool:
        """Membuka koneksi RTSP dengan percobaan ulang (retry)."""
        # Konfigurasi capture options sebelum memanggil VideoCapture
        os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = (
            'rtsp_transport;tcp|buffer_size;1024000|stimeout;5000000'
        )

        for attempt in range(1, self.max_retries + 1):
            if stop_event and stop_event.is_set():
                return False

            try:
                logger.info(f"[{self.ip}] Percobaan koneksi RTSP {attempt}/{self.max_retries}...")
                self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
                
                if self.cap.isOpened():
                    # Set buffer size ke 1 frame untuk mencegah lag latency
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                    # Ambil informasi resolusi dan frame rate
                    w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    raw_fps = self.cap.get(cv2.CAP_PROP_FPS)

                    # Uji baca satu frame pertama untuk memastikan transmisi berjalan
                    ret, sample_frame = self.cap.read()
                    if ret and sample_frame is not None:
                        actual_h, actual_w = sample_frame.shape[:2]
                        self.width = actual_w if actual_w > 0 else (w if w > 0 else 1280)
                        self.height = actual_h if actual_h > 0 else (h if h > 0 else 720)
                        
                        # RTSP sering mengembalikan FPS 0 atau tidak valid; berikan fallback aman
                        if raw_fps and 1.0 <= raw_fps <= 120.0:
                            self.fps = float(raw_fps)
                        else:
                            self.fps = 20.0

                        logger.info(
                            f"[{self.ip}] Terhubung: {self.width}x{self.height} @ {self.fps:.1f} FPS"
                        )
                        return True
                    else:
                        logger.warning(f"[{self.ip}] Stream terbuka tetapi frame pertama gagal dibaca.")

                if self.cap:
                    self.cap.release()
                    self.cap = None

            except Exception as e:
                logger.error(f"[{self.ip}] Error saat membuka koneksi attempt {attempt}: {e}")
                if self.cap:
                    self.cap.release()
                    self.cap = None

            if attempt < self.max_retries:
                # Tidur dalam interval kecil agar responsif jika stop_event diaktifkan
                slept = 0
                while slept < self.retry_delay:
                    if stop_event and stop_event.is_set():
                        return False
                    time.sleep(0.5)
                    slept += 0.5

        return False

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Membaca satu frame secara aman."""
        if not self.cap or not self.cap.isOpened():
            return False, None
        try:
            ret, frame = self.cap.read()
            if ret and frame is not None and frame.size > 0:
                return True, frame
            return False, None
        except Exception as e:
            logger.error(f"[{self.ip}] Pengecualian saat membaca frame: {e}")
            return False, None

    def release(self):
        """Melepaskan sumber daya stream."""
        if self.cap:
            try:
                self.cap.release()
            except Exception as e:
                logger.error(f"[{self.ip}] Error saat melepaskan capture: {e}")
            self.cap = None


# ============================================================================
# VIDEO RECORDER (PER-CAMERA ISOLATION)
# ============================================================================
class VideoRecorder:
    """Perekam video independen per kamera dengan penamaan unik dan rotasi file aman."""
    def __init__(self, cctv: Dict, output_dir: str, settings: Dict):
        self.cctv = cctv
        self.ip = cctv['ip']
        self.username = cctv['username']
        self.password = cctv['password']
        self.output_dir = output_dir
        self.settings = settings
        
        self.split_duration = max(30, int(settings.get('split_duration', 300)))
        self.connection: Optional[RTSPConnection] = None
        self.writer: Optional[cv2.VideoWriter] = None
        
        self.is_recording = False
        self.split_start_time = 0.0
        self.current_file: Optional[str] = None
        self.frames_written = 0
        self.status_text = "Siap"

    def _create_rtsp_url(self) -> str:
        safe_user = urllib.parse.quote(self.username)
        safe_pass = urllib.parse.quote(self.password)
        return f"rtsp://{safe_user}:{safe_pass}@{self.ip}:554/Streaming/Channels/101"

    def _get_output_filename(self) -> str:
        # Gunakan IP yang disanitasi agar file tiap kamera terisolasi 100%
        safe_ip = self.ip.replace('.', '_').replace(':', '_')
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.output_dir, f"rec_{safe_ip}_{timestamp}.mp4")

    def _create_writer(self, width: int, height: int, fps: float) -> Optional[cv2.VideoWriter]:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        safe_fps = fps if (fps and 1.0 <= fps <= 120.0) else 20.0
        try:
            writer = cv2.VideoWriter(self.current_file, fourcc, safe_fps, (width, height))
            if not writer.isOpened():
                # Fallback jika mp4v ditolak
                fallback_fourcc = cv2.VideoWriter_fourcc(*'XVID')
                writer = cv2.VideoWriter(self.current_file, fallback_fourcc, safe_fps, (width, height))
            return writer
        except Exception as e:
            logger.error(f"[{self.ip}] Gagal menginisialisasi VideoWriter: {e}")
            return None

    def start(self, stop_event: Event) -> bool:
        """Memulai sesi perekaman untuk kamera ini."""
        self.status_text = "Menghubungkan"
        url = self._create_rtsp_url()
        self.connection = RTSPConnection(
            url=url,
            ip=self.ip,
            max_retries=int(self.settings.get('max_retries', 3)),
            retry_delay=int(self.settings.get('retry_delay', 3))
        )

        if not self.connection.connect(stop_event=stop_event):
            self.status_text = "Koneksi Gagal"
            logger.error(f"[{self.ip}] Tidak dapat terhubung ke stream RTSP.")
            return False

        os.makedirs(self.output_dir, exist_ok=True)
        self.current_file = self._get_output_filename()
        self.writer = self._create_writer(
            self.connection.width,
            self.connection.height,
            self.connection.fps
        )

        if not self.writer or not self.writer.isOpened():
            self.status_text = "Writer Error"
            logger.error(f"[{self.ip}] Gagal membuka file rekaman: {self.current_file}")
            self.stop()
            return False

        self.is_recording = True
        self.split_start_time = time.time()
        self.frames_written = 0
        self.status_text = "Merekam"
        logger.info(f"[{self.ip}] Perekaman dimulai: {self.current_file}")
        return True

    def record_step(self, stop_event: Event) -> bool:
        """Menjalankan satu langkah pembacaan dan penulisan frame."""
        if not self.is_recording or not self.connection:
            return False

        ret, frame = self.connection.read_frame()
        if not ret or frame is None:
            return False

        now = time.time()
        # Periksa apakah sudah waktunya membagi (split) file rekaman
        if (now - self.split_start_time) >= self.split_duration:
            self._split_file(frame)

        if self.writer and self.writer.isOpened():
            try:
                self.writer.write(frame)
                self.frames_written += 1
            except Exception as e:
                logger.error(f"[{self.ip}] Kesalahan saat menulis frame: {e}")
                return False

        return True

    def _split_file(self, current_frame: np.ndarray):
        """Membagi file rekaman dengan aman tanpa kehilangan frame."""
        logger.info(f"[{self.ip}] Membagi file rekaman (durasi interval tercapai)...")
        if self.writer:
            try:
                self.writer.release()
            except Exception as e:
                logger.error(f"[{self.ip}] Gagal menutup writer lama: {e}")
            self.writer = None

        self.current_file = self._get_output_filename()
        h, w = current_frame.shape[:2]
        fps = self.connection.fps if self.connection else 20.0
        self.writer = self._create_writer(w, h, fps)
        self.split_start_time = time.time()

        if self.writer and self.writer.isOpened():
            # Tulis frame sekarang ke file baru langsung
            self.writer.write(current_frame)
            self.frames_written += 1
            logger.info(f"[{self.ip}] File baru dimulai: {self.current_file}")
        else:
            logger.error(f"[{self.ip}] Gagal membuat file baru saat split.")

    def stop(self):
        """Menghentikan perekaman dan merilis berkas video dengan sempurna."""
        self.is_recording = False
        self.status_text = "Berhenti"

        if self.writer:
            try:
                self.writer.release()
                logger.info(f"[{self.ip}] Writer ditutup. Total frame: {self.frames_written}")
            except Exception as e:
                logger.error(f"[{self.ip}] Error saat menutup VideoWriter: {e}")
            self.writer = None

        if self.connection:
            self.connection.release()
            self.connection = None


# ============================================================================
# NVR MANAGER (COORDINATOR)
# ============================================================================
class NVRManager:
    """Koordinator perekaman multi-kamera dengan worker terisolasi dan pemantau status."""
    def __init__(self):
        self.config = NVRConfig()
        self.recorders: Dict[str, VideoRecorder] = {}
        self.worker_threads: Dict[str, Thread] = {}
        self.coordinator_thread: Optional[Thread] = None
        self.stop_event = Event()
        self.lock = Lock()
        
        self.is_running = False
        self.global_status = "Siap"
        self.start_timestamp = 0.0
        self.total_duration_limit = 0

    def start_recording(
        self,
        cctv_list: List[Dict],
        settings: Dict,
        on_status_change=None,
        on_finished=None
    ):
        """Memulai perekaman secara asinkron di thread terpisah agar UI tidak pernah freeze."""
        with self.lock:
            if self.is_running:
                return

            self.stop_event.clear()
            self.is_running = True
            self.recorders.clear()
            self.worker_threads.clear()
            self.start_timestamp = time.time()
            self.total_duration_limit = int(settings.get('duration', 0))

        # Folder penyimpanan berbasis tanggal hari ini
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        output_dir = os.path.join("storage", today_str)

        def _coordinator():
            logger.info("Memulai koordinator perekaman NVR...")
            if on_status_change:
                on_status_change("Menghubungkan ke CCTV...")

            # Buat recorder untuk tiap kamera
            for cctv in cctv_list:
                rec = VideoRecorder(cctv, output_dir, settings)
                with self.lock:
                    self.recorders[cctv['ip']] = rec

            # Luncurkan worker per kamera secara paralel
            success_count = 0
            for ip, rec in list(self.recorders.items()):
                if self.stop_event.is_set():
                    break

                def _cam_worker(recorder: VideoRecorder):
                    started = recorder.start(stop_event=self.stop_event)
                    if not started:
                        logger.warning(f"[{recorder.ip}] Gagal mengawali sesi rekaman.")
                        return

                    consecutive_errors = 0
                    while not self.stop_event.is_set():
                        ok = recorder.record_step(self.stop_event)
                        if not ok:
                            consecutive_errors += 1
                            if consecutive_errors > 10:
                                recorder.status_text = "Sinyal Hilang"
                                # Istirahat sejenak sebelum mencoba membaca kembali
                                time.sleep(1.0)
                            else:
                                time.sleep(0.1)
                        else:
                            consecutive_errors = 0

                    recorder.stop()

                t = Thread(target=_cam_worker, args=(rec,), daemon=True)
                t.start()
                with self.lock:
                    self.worker_threads[ip] = t

            # Beri jeda 2 detik untuk memeriksa berapa kamera yang berhasil terhubung
            time.sleep(2.0)
            with self.lock:
                active_count = sum(1 for r in self.recorders.values() if r.is_recording)

            if active_count > 0:
                self.global_status = f"Merekam ({active_count}/{len(cctv_list)} kamera aktif)"
            else:
                self.global_status = "Gagal menghubungkan ke kamera"

            if on_status_change:
                on_status_change(self.global_status)

            # Monitor loop untuk durasi total dan pembersihan
            while not self.stop_event.is_set():
                # Cek batas durasi total (jika diatur > 0)
                if self.total_duration_limit > 0:
                    elapsed = time.time() - self.start_timestamp
                    if elapsed >= self.total_duration_limit:
                        logger.info("Batas durasi total rekaman tercapai. Menghentikan...")
                        break

                time.sleep(1.0)

            # Selesai: hentikan semua recorder
            self._internal_stop()
            if on_finished:
                on_finished()

        self.coordinator_thread = Thread(target=_coordinator, daemon=True)
        self.coordinator_thread.start()

    def _internal_stop(self):
        """Menghentikan semua thread recorder dengan aman."""
        self.stop_event.set()
        with self.lock:
            for rec in self.recorders.values():
                rec.stop()
            self.recorders.clear()
            self.worker_threads.clear()
            self.is_running = False
            self.global_status = "Berhenti"
        logger.info("Semua proses perekaman NVR telah dihentikan secara aman.")

    def stop_recording(self):
        """Permintaan penghentian dari antarmuka pengguna."""
        self.stop_event.set()

    def cleanup_old_videos(self, days_to_keep: int) -> int:
        """Membersihkan folder rekaman yang lebih tua dari batas hari yang ditentukan."""
        storage_path = "storage"
        if not os.path.exists(storage_path):
            return 0

        cutoff_date = datetime.date.today() - datetime.timedelta(days=days_to_keep)
        deleted_count = 0

        try:
            for item in os.listdir(storage_path):
                folder_path = os.path.join(storage_path, item)
                if os.path.isdir(folder_path):
                    try:
                        # Format folder pasti: YYYY-MM-DD
                        folder_date = datetime.datetime.strptime(item, "%Y-%m-%d").date()
                        if folder_date < cutoff_date:
                            shutil.rmtree(folder_path)
                            deleted_count += 1
                            logger.info(f"Menghapus folder rekaman lama: {folder_path}")
                    except ValueError:
                        # Abaikan folder yang namanya bukan format tanggal YYYY-MM-DD
                        continue
        except Exception as e:
            logger.error(f"Error saat membersihkan rekaman lama: {e}")

        return deleted_count


# ============================================================================
# INDUSTRIAL CLEAN UI (TKINTER)
#
# Antarmuka desktop CCTV NVR berstandar industrial-clean dan aksesibilitas WCAG.
# ============================================================================
class NVRGUI:
    """Antarmuka pengguna desktop CCTV NVR berstandar industrial-clean."""
    
    # Palet Warna Utilitarian (Memenuhi standar kontras WCAG AA)
    COLOR_BG = "#13161c"           # Background utama (Deep charcoal slate)
    COLOR_SURFACE = "#1c212b"      # Kartu / Surface panel
    COLOR_SURFACE_ALT = "#242a36"  # Background header / list
    COLOR_BORDER = "#333c4d"       # Batas / Divider halus
    COLOR_TEXT = "#f1f5f9"         # Teks utama (Kontras tinggi > 13:1)
    COLOR_MUTED = "#94a3b8"        # Teks sekunder / label (> 5:1)
    
    # Aksi Terarah (Satu aksen fungsi utama per aksi)
    COLOR_ACCENT = "#2563eb"       # Biru fungsional (Tambah / Simpan)
    COLOR_START = "#15803d"        # Hijau fungsional (Mulai Perekaman)
    COLOR_STOP = "#b91c1c"         # Merah fungsional (Hentikan)
    COLOR_WARNING = "#d97706"      # Kuning status

    def __init__(self):
        self.manager = NVRManager()
        self.root: Optional[tk.Tk] = None
        self.cctv_tree: Optional[ttk.Treeview] = None
        self.status_badge: Optional[tk.Label] = None
        self.log_text: Optional[tk.Text] = None
        self.btn_start: Optional[tk.Button] = None
        self.btn_stop: Optional[tk.Button] = None

        self.entry_duration: Optional[tk.Entry] = None
        self.entry_split: Optional[tk.Entry] = None
        self.entry_retention: Optional[tk.Entry] = None

    def create_gui(self):
        self.root = tk.Tk()
        self.root.title("NVR CCTV Manager")
        self.root.geometry("820x680")
        self.root.minsize(760, 600)
        self.root.configure(bg=self.COLOR_BG)

        # Penanganan penutupan jendela bersih agar berkas tidak rusak
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_window)

        # Inisialisasi style ttk untuk Treeview dan scrollbar
        self._setup_styles()

        # Layout Utama: Header -> CCTV List -> Settings -> Controls -> Logs
        main_container = tk.Frame(self.root, bg=self.COLOR_BG, padx=16, pady=16)
        main_container.pack(fill=tk.BOTH, expand=True)

        self._build_header(main_container)
        self._build_cctv_section(main_container)
        self._build_settings_and_controls(main_container)
        self._build_log_console(main_container)

        # Muat data awal ke tabel
        self._refresh_cctv_table()

        # Polling periodik untuk memperbarui status kamera di UI
        self.root.after(1000, self._periodic_ui_update)

        return self.root

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Style Treeview
        style.configure(
            "CCTV.Treeview",
            background=self.COLOR_SURFACE,
            foreground=self.COLOR_TEXT,
            fieldbackground=self.COLOR_SURFACE,
            rowheight=28,
            font=('Segoe UI', 9),
            borderwidth=0
        )
        style.configure(
            "CCTV.Treeview.Heading",
            background=self.COLOR_SURFACE_ALT,
            foreground=self.COLOR_TEXT,
            font=('Segoe UI', 9, 'bold'),
            borderwidth=1,
            relief='flat'
        )
        style.map(
            "CCTV.Treeview",
            background=[('selected', self.COLOR_ACCENT)],
            foreground=[('selected', '#ffffff')]
        )

    def _build_header(self, parent: tk.Frame):
        header_frame = tk.Frame(parent, bg=self.COLOR_BG)
        header_frame.pack(fill=tk.X, pady=(0, 14))

        title_box = tk.Frame(header_frame, bg=self.COLOR_BG)
        title_box.pack(side=tk.LEFT)

        title_lbl = tk.Label(
            title_box,
            text="NVR CCTV Manager",
            font=('Segoe UI', 15, 'bold'),
            fg=self.COLOR_TEXT,
            bg=self.COLOR_BG
        )
        title_lbl.pack(anchor='w')

        sub_lbl = tk.Label(
            title_box,
            text="Sistem Perekaman RTSP Mandiri dan Pengarsipan Terjadwal",
            font=('Segoe UI', 9),
            fg=self.COLOR_MUTED,
            bg=self.COLOR_BG
        )
        sub_lbl.pack(anchor='w')

        # Status badge di sisi kanan
        self.status_badge = tk.Label(
            header_frame,
            text="Status: Siap",
            font=('Segoe UI', 9, 'bold'),
            fg=self.COLOR_TEXT,
            bg=self.COLOR_SURFACE_ALT,
            padx=12,
            pady=6,
            highlightbackground=self.COLOR_BORDER,
            highlightthickness=1
        )
        self.status_badge.pack(side=tk.RIGHT, pady=4)

    def _build_cctv_section(self, parent: tk.Frame):
        sec_frame = tk.LabelFrame(
            parent,
            text=" Daftar Kamera CCTV ",
            font=('Segoe UI', 10, 'bold'),
            fg=self.COLOR_TEXT,
            bg=self.COLOR_SURFACE,
            bd=1,
            relief='solid',
            padx=12,
            pady=10
        )
        sec_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        # Action bar di atas tabel
        btn_bar = tk.Frame(sec_frame, bg=self.COLOR_SURFACE)
        btn_bar.pack(fill=tk.X, pady=(0, 8))

        btn_add = tk.Button(
            btn_bar,
            text="+ Tambah CCTV",
            font=('Segoe UI', 9, 'bold'),
            bg=self.COLOR_ACCENT,
            fg='#ffffff',
            activebackground='#1d4ed8',
            activeforeground='#ffffff',
            relief='flat',
            padx=10,
            pady=4,
            cursor='hand2',
            command=self.open_add_cctv_dialog
        )
        btn_add.pack(side=tk.LEFT, padx=(0, 6))

        btn_remove = tk.Button(
            btn_bar,
            text="Hapus Terpilih",
            font=('Segoe UI', 9),
            bg=self.COLOR_SURFACE_ALT,
            fg=self.COLOR_TEXT,
            activebackground=self.COLOR_BORDER,
            relief='flat',
            padx=10,
            pady=4,
            cursor='hand2',
            command=self.remove_selected_cctv
        )
        btn_remove.pack(side=tk.LEFT, padx=(0, 6))

        btn_test = tk.Button(
            btn_bar,
            text="Uji Koneksi Kamera",
            font=('Segoe UI', 9),
            bg=self.COLOR_SURFACE_ALT,
            fg=self.COLOR_TEXT,
            activebackground=self.COLOR_BORDER,
            relief='flat',
            padx=10,
            pady=4,
            cursor='hand2',
            command=self.test_selected_connection
        )
        btn_test.pack(side=tk.LEFT)

        # Tabel Kamera (Treeview)
        tree_container = tk.Frame(sec_frame, bg=self.COLOR_SURFACE)
        tree_container.pack(fill=tk.BOTH, expand=True)

        cols = ("no", "ip", "username", "status")
        self.cctv_tree = ttk.Treeview(
            tree_container,
            columns=cols,
            show='headings',
            style="CCTV.Treeview",
            selectmode='browse'
        )

        self.cctv_tree.heading("no", text="No")
        self.cctv_tree.heading("ip", text="IP Address CCTV")
        self.cctv_tree.heading("username", text="Username")
        self.cctv_tree.heading("status", text="Status Operasional")

        self.cctv_tree.column("no", width=45, anchor='center', stretch=False)
        self.cctv_tree.column("ip", width=220, anchor='w')
        self.cctv_tree.column("username", width=160, anchor='w')
        self.cctv_tree.column("status", width=200, anchor='w')

        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.cctv_tree.yview)
        self.cctv_tree.configure(yscrollcommand=scrollbar.set)

        self.cctv_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_settings_and_controls(self, parent: tk.Frame):
        mid_frame = tk.Frame(parent, bg=self.COLOR_BG)
        mid_frame.pack(fill=tk.X, pady=(0, 12))

        # Panel Pengaturan
        set_frame = tk.LabelFrame(
            mid_frame,
            text=" Pengaturan Perekaman ",
            font=('Segoe UI', 9, 'bold'),
            fg=self.COLOR_TEXT,
            bg=self.COLOR_SURFACE,
            bd=1,
            relief='solid',
            padx=12,
            pady=8
        )
        set_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        _, settings = self.manager.config.get()

        # Grid form pengaturan
        tk.Label(set_frame, text="Durasi Total (detik, 0=tanpa henti):", font=('Segoe UI', 8), fg=self.COLOR_MUTED, bg=self.COLOR_SURFACE).grid(row=0, column=0, sticky='w', pady=2)
        self.entry_duration = tk.Entry(set_frame, bg=self.COLOR_SURFACE_ALT, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, relief='flat', width=12)
        self.entry_duration.insert(0, str(settings.get('duration', 3600)))
        self.entry_duration.grid(row=0, column=1, sticky='w', padx=(6, 16), pady=2)

        tk.Label(set_frame, text="Durasi File / Split (detik):", font=('Segoe UI', 8), fg=self.COLOR_MUTED, bg=self.COLOR_SURFACE).grid(row=1, column=0, sticky='w', pady=2)
        self.entry_split = tk.Entry(set_frame, bg=self.COLOR_SURFACE_ALT, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, relief='flat', width=12)
        self.entry_split.insert(0, str(settings.get('split_duration', 300)))
        self.entry_split.grid(row=1, column=1, sticky='w', padx=(6, 16), pady=2)

        tk.Label(set_frame, text="Masa Simpan (hari):", font=('Segoe UI', 8), fg=self.COLOR_MUTED, bg=self.COLOR_SURFACE).grid(row=2, column=0, sticky='w', pady=2)
        self.entry_retention = tk.Entry(set_frame, bg=self.COLOR_SURFACE_ALT, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, relief='flat', width=12)
        self.entry_retention.insert(0, str(settings.get('days_to_keep', 7)))
        self.entry_retention.grid(row=2, column=1, sticky='w', padx=(6, 16), pady=2)

        btn_save_settings = tk.Button(
            set_frame,
            text="Simpan Parameter",
            font=('Segoe UI', 8),
            bg=self.COLOR_SURFACE_ALT,
            fg=self.COLOR_TEXT,
            relief='flat',
            padx=8,
            pady=3,
            cursor='hand2',
            command=self.save_settings_from_gui
        )
        btn_save_settings.grid(row=3, column=0, columnspan=2, sticky='w', pady=(6, 2))

        # Panel Kontrol Eksekusi
        ctrl_frame = tk.LabelFrame(
            mid_frame,
            text=" Kontrol Operasi ",
            font=('Segoe UI', 9, 'bold'),
            fg=self.COLOR_TEXT,
            bg=self.COLOR_SURFACE,
            bd=1,
            relief='solid',
            padx=12,
            pady=8
        )
        ctrl_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(8, 0))

        self.btn_start = tk.Button(
            ctrl_frame,
            text="Mulai Perekaman",
            font=('Segoe UI', 10, 'bold'),
            bg=self.COLOR_START,
            fg='#ffffff',
            activebackground='#166534',
            activeforeground='#ffffff',
            relief='flat',
            width=18,
            pady=6,
            cursor='hand2',
            command=self.start_recording_action
        )
        self.btn_start.pack(pady=(2, 6))

        self.btn_stop = tk.Button(
            ctrl_frame,
            text="Hentikan Perekaman",
            font=('Segoe UI', 10, 'bold'),
            bg=self.COLOR_STOP,
            fg='#ffffff',
            activebackground='#991b1b',
            activeforeground='#ffffff',
            relief='flat',
            width=18,
            pady=6,
            cursor='hand2',
            state=tk.DISABLED,
            command=self.stop_recording_action
        )
        self.btn_stop.pack(pady=(0, 6))

        btn_cleanup = tk.Button(
            ctrl_frame,
            text="Bersihkan Rekaman Lama",
            font=('Segoe UI', 8),
            bg=self.COLOR_SURFACE_ALT,
            fg=self.COLOR_TEXT,
            relief='flat',
            width=22,
            pady=3,
            cursor='hand2',
            command=self.run_manual_cleanup
        )
        btn_cleanup.pack()

    def _build_log_console(self, parent: tk.Frame):
        log_frame = tk.LabelFrame(
            parent,
            text=" Catatan Aktivitas Sistem ",
            font=('Segoe UI', 9, 'bold'),
            fg=self.COLOR_TEXT,
            bg=self.COLOR_SURFACE,
            bd=1,
            relief='solid',
            padx=10,
            pady=8
        )
        log_frame.pack(fill=tk.BOTH, expand=False)

        self.log_text = tk.Text(
            log_frame,
            height=5,
            bg=self.COLOR_BG,
            fg=self.COLOR_MUTED,
            font=('Consolas', 8),
            relief='flat',
            wrap='word'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.append_log("Aplikasi NVR CCTV Manager siap digunakan.")

    def append_log(self, message: str):
        """Menambahkan pesan ke log console GUI secara thread-safe."""
        if not self.root:
            return
        
        def _insert():
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)

        if threading.current_thread() is threading.main_thread():
            _insert()
        else:
            self.root.after(0, _insert)

    def _refresh_cctv_table(self):
        """Memperbarui isi tabel kamera dari konfigurasi."""
        if not self.cctv_tree:
            return
        for row in self.cctv_tree.get_children():
            self.cctv_tree.delete(row)

        cctv_list, _ = self.manager.config.get()
        if not cctv_list:
            self.cctv_tree.insert("", tk.END, values=("-", "Belum ada CCTV", "-", "Silakan klik + Tambah CCTV"))
            return

        for idx, cctv in enumerate(cctv_list, 1):
            ip = cctv.get('ip', '')
            status = "Siap"
            if self.manager.is_running:
                rec = self.manager.recorders.get(ip)
                if rec:
                    status = rec.status_text
            self.cctv_tree.insert("", tk.END, iid=ip, values=(idx, ip, cctv.get('username', ''), status))

    def _periodic_ui_update(self):
        """Memperbarui status kamera secara berkala tanpa intervensi pengguna."""
        if self.manager.is_running:
            self.status_badge.config(
                text=f"Status: {self.manager.global_status}",
                fg="#4ade80"
            )
            # Perbarui status di setiap baris tabel
            for ip, rec in self.manager.recorders.items():
                if self.cctv_tree.exists(ip):
                    current_vals = list(self.cctv_tree.item(ip, 'values'))
                    if len(current_vals) >= 4:
                        current_vals[3] = rec.status_text
                        self.cctv_tree.item(ip, values=current_vals)
        else:
            self.status_badge.config(
                text=f"Status: {self.manager.global_status}",
                fg=self.COLOR_TEXT
            )

        if self.root:
            self.root.after(1000, self._periodic_ui_update)

    # ------------------------------------------------------------------------
    # DIALOGS & ACTIONS
    # ------------------------------------------------------------------------
    def open_add_cctv_dialog(self):
        """Membuka dialog tambah CCTV dengan penanganan keyboard Escape & Enter."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Tambah Kamera CCTV")
        dialog.geometry("380x240")
        dialog.resizable(False, False)
        dialog.configure(bg=self.COLOR_SURFACE)
        dialog.transient(self.root)
        dialog.grab_set()

        # Keyboard accessibility
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        frame = tk.Frame(dialog, bg=self.COLOR_SURFACE, padx=20, pady=16)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Alamat IP CCTV:", font=('Segoe UI', 9), fg=self.COLOR_TEXT, bg=self.COLOR_SURFACE).pack(anchor='w', pady=(0, 2))
        entry_ip = tk.Entry(frame, bg=self.COLOR_SURFACE_ALT, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, relief='flat', font=('Segoe UI', 9))
        entry_ip.pack(fill=tk.X, pady=(0, 8))
        entry_ip.focus_set()

        tk.Label(frame, text="Username RTSP:", font=('Segoe UI', 9), fg=self.COLOR_TEXT, bg=self.COLOR_SURFACE).pack(anchor='w', pady=(0, 2))
        entry_user = tk.Entry(frame, bg=self.COLOR_SURFACE_ALT, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, relief='flat', font=('Segoe UI', 9))
        entry_user.pack(fill=tk.X, pady=(0, 8))

        tk.Label(frame, text="Password RTSP:", font=('Segoe UI', 9), fg=self.COLOR_TEXT, bg=self.COLOR_SURFACE).pack(anchor='w', pady=(0, 2))
        entry_pass = tk.Entry(frame, bg=self.COLOR_SURFACE_ALT, fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, relief='flat', font=('Segoe UI', 9), show='*')
        entry_pass.pack(fill=tk.X, pady=(0, 14))

        def _submit():
            ip = entry_ip.get().strip()
            username = entry_user.get().strip()
            password = entry_pass.get()

            if not ip or not username or not password:
                messagebox.showwarning("Data Tidak Lengkap", "Harap isi Alamat IP, Username, dan Password CCTV.", parent=dialog)
                return

            # Validasi format IP dasar
            if not re.match(r'^\d{1,3}(?:\.\d{1,3}){3}$', ip):
                messagebox.showerror("Format IP Tidak Valid", "Alamat IP harus berupa format desimal IPv4 (contoh: 192.168.1.100).", parent=dialog)
                return

            cctv_list, settings = self.manager.config.get()
            # Cek duplikasi IP
            if any(item.get('ip') == ip for item in cctv_list):
                messagebox.showerror("IP Sudah Terdaftar", f"CCTV dengan IP {ip} sudah ada dalam daftar.", parent=dialog)
                return

            cctv_list.append({
                "ip": ip,
                "username": username,
                "password": password
            })
            self.manager.config.save(cctv_list, settings)
            self._refresh_cctv_table()
            self.append_log(f"Kamera CCTV {ip} berhasil ditambahkan.")
            dialog.destroy()

        dialog.bind("<Return>", lambda e: _submit())

        btn_box = tk.Frame(frame, bg=self.COLOR_SURFACE)
        btn_box.pack(fill=tk.X)

        tk.Button(
            btn_box,
            text="Batal",
            font=('Segoe UI', 9),
            bg=self.COLOR_SURFACE_ALT,
            fg=self.COLOR_TEXT,
            relief='flat',
            padx=12,
            pady=4,
            command=dialog.destroy
        ).pack(side=tk.RIGHT, padx=(6, 0))

        tk.Button(
            btn_box,
            text="Simpan CCTV",
            font=('Segoe UI', 9, 'bold'),
            bg=self.COLOR_ACCENT,
            fg='#ffffff',
            relief='flat',
            padx=12,
            pady=4,
            command=_submit
        ).pack(side=tk.RIGHT)

    def remove_selected_cctv(self):
        """Menghapus CCTV yang dipilih pada tabel dengan konfirmasi."""
        selected = self.cctv_tree.selection()
        if not selected:
            messagebox.showinfo("Pilih CCTV", "Pilih salah satu kamera pada tabel yang ingin dihapus.")
            return

        target_ip = selected[0]
        cctv_list, settings = self.manager.config.get()
        matched = next((c for c in cctv_list if c.get('ip') == target_ip), None)
        if not matched:
            return

        if messagebox.askyesno("Konfirmasi Hapus", f"Apakah Anda yakin ingin menghapus CCTV {target_ip}?"):
            cctv_list = [c for c in cctv_list if c.get('ip') != target_ip]
            self.manager.config.save(cctv_list, settings)
            self._refresh_cctv_table()
            self.append_log(f"Kamera CCTV {target_ip} telah dihapus dari daftar.")

    def test_selected_connection(self):
        """Menguji koneksi ke CCTV terpilih tanpa membekukan antarmuka."""
        selected = self.cctv_tree.selection()
        if not selected:
            messagebox.showinfo("Pilih CCTV", "Pilih kamera dari tabel untuk diuji koneksinya.")
            return

        target_ip = selected[0]
        cctv_list, _ = self.manager.config.get()
        cctv = next((c for c in cctv_list if c.get('ip') == target_ip), None)
        if not cctv:
            return

        self.append_log(f"Memulai pengujian koneksi ke {target_ip}...")
        
        def _async_test():
            safe_u = urllib.parse.quote(cctv['username'])
            safe_p = urllib.parse.quote(cctv['password'])
            url = f"rtsp://{safe_u}:{safe_p}@{target_ip}:554/Streaming/Channels/101"
            conn = RTSPConnection(url, target_ip, max_retries=1, retry_delay=1)
            success = conn.connect()
            conn.release()

            def _show_result():
                if success:
                    self.append_log(f"Uji koneksi ke {target_ip} berhasil.")
                    messagebox.showinfo("Uji Berhasil", f"Koneksi RTSP ke CCTV {target_ip} terhubung normal.")
                else:
                    self.append_log(f"Uji koneksi ke {target_ip} gagal.")
                    messagebox.showerror("Uji Gagal", f"Tidak dapat terhubung ke CCTV {target_ip}. Periksa IP, jaringan, dan kredensial login.")

            self.root.after(0, _show_result)

        Thread(target=_async_test, daemon=True).start()

    def save_settings_from_gui(self):
        """Menyimpan pengaturan form ke konfigurasi JSON dengan validasi angka."""
        try:
            dur = max(0, int(self.entry_duration.get()))
            split = max(30, int(self.entry_split.get()))
            ret = max(1, int(self.entry_retention.get()))
        except ValueError:
            messagebox.showerror("Input Tidak Valid", "Nilai durasi dan retensi harus berupa angka bulat positif.")
            return

        cctv_list, settings = self.manager.config.get()
        settings['duration'] = dur
        settings['split_duration'] = split
        settings['days_to_keep'] = ret

        self.manager.config.save(cctv_list, settings)
        self.append_log("Pengaturan parameter perekaman berhasil disimpan.")
        messagebox.showinfo("Tersimpan", "Parameter perekaman berhasil diperbarui.")

    def start_recording_action(self):
        """Memulai proses perekaman untuk semua CCTV yang terdaftar."""
        cctv_list, settings = self.manager.config.get()
        if not cctv_list:
            messagebox.showwarning("CCTV Kosong", "Belum ada kamera CCTV yang terdaftar. Tambahkan CCTV terlebih dahulu.")
            return

        # Simpan nilai pengaturan terkini dari form
        try:
            settings['duration'] = max(0, int(self.entry_duration.get()))
            settings['split_duration'] = max(30, int(self.entry_split.get()))
            settings['days_to_keep'] = max(1, int(self.entry_retention.get()))
            self.manager.config.save(cctv_list, settings)
        except ValueError:
            pass

        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.append_log("Memulai proses perekaman seluruh kamera CCTV...")

        def _on_status_change(status: str):
            self.append_log(f"Status NVR: {status}")

        def _on_finish():
            def _reset_buttons():
                self.btn_start.config(state=tk.NORMAL)
                self.btn_stop.config(state=tk.DISABLED)
                self.append_log("Sesi perekaman telah berakhir.")
            self.root.after(0, _reset_buttons)

        self.manager.start_recording(
            cctv_list=cctv_list,
            settings=settings,
            on_status_change=_on_status_change,
            on_finished=_on_finish
        )

    def stop_recording_action(self):
        """Menghentikan seluruh perekaman secara teratur."""
        self.btn_stop.config(state=tk.DISABLED)
        self.append_log("Mengirim instruksi penghentian ke semua perekam...")
        
        def _async_stop():
            self.manager.stop_recording()
            def _done():
                self.btn_start.config(state=tk.NORMAL)
                self.append_log("Perekaman seluruh kamera berhasil dihentikan.")
            self.root.after(0, _done)

        Thread(target=_async_stop, daemon=True).start()

    def run_manual_cleanup(self):
        """Menjalankan pembersihan rekaman lama berdasarkan masa simpan."""
        try:
            days = max(1, int(self.entry_retention.get()))
        except ValueError:
            days = 7

        if messagebox.askyesno("Konfirmasi Pembersihan", f"Apakah Anda ingin menghapus seluruh rekaman yang berusia lebih dari {days} hari?"):
            deleted = self.manager.cleanup_old_videos(days)
            self.append_log(f"Pembersihan selesai: {deleted} folder tanggal lama dihapus.")
            messagebox.showinfo("Pembersihan Selesai", f"Pembersihan berhasil. {deleted} folder lama telah dihapus.")

    def on_close_window(self):
        """Memastikan semua file rekaman difinalisasi dengan aman sebelum jendela ditutup."""
        if self.manager.is_running:
            if not messagebox.askyesno("Perekaman Masih Aktif", "Perekaman sedang berlangsung. Apakah Anda ingin menghentikan perekaman dan keluar dari aplikasi?"):
                return
            self.append_log("Menghentikan perekaman sebelum menutup aplikasi...")
            self.manager.stop_recording()
            time.sleep(0.5)

        self.root.destroy()

    def run(self):
        root = self.create_gui()
        root.mainloop()


if __name__ == "__main__":
    app = NVRGUI()
    app.run()

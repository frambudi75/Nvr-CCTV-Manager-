import cv2
import datetime
import os
import time
import shutil
import tkinter as tk
from tkinter import simpledialog, messagebox
from threading import Thread, Event, Lock
import urllib.parse
import logging
import json
import queue
import gc
from typing import List, Dict, Optional, Tuple
import numpy as np

# Setup logging with rotation
class NVRLogger:
    def __init__(self, log_file='nvr_log.txt', max_size=10*1024*1024):
        self.logger = logging.getLogger('NVR')
        self.logger.setLevel(logging.INFO)
        
        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(log_file, maxBytes=max_size, backupCount=5)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, msg):
        self.logger.info(msg)
    
    def error(self, msg):
        self.logger.error(msg)
    
    def warning(self, msg):
        self.logger.warning(msg)

# Global logger instance
logger = NVRLogger().logger

class NVRConfig:
    """Thread-safe configuration management"""
    def __init__(self, config_file='nvr_config.json'):
        self.config_file = config_file
        self.lock = Lock()
        self._config = self._load_config()
    
    def _load_config(self) -> Dict:
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return self._default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self._default_config()
    
    def _default_config(self) -> Dict:
        return {
            'cctv_list': [],
            'settings': {
                'duration': 3600,
                'split_duration': 300,
                'days_to_keep': 7,
                'max_retries': 3,
                'retry_delay': 5,
                'buffer_size': 1024,
                'fps_target': 15,
                'resolution': '720p'
            }
        }
    
    def save(self, cctv_list: List[Dict], settings: Dict):
        with self.lock:
            self._config = {
                'cctv_list': cctv_list,
                'settings': settings
            }
            try:
                with open(self.config_file, 'w') as f:
                    json.dump(self._config, f, indent=4)
                logger.info("Configuration saved successfully")
            except Exception as e:
                logger.error(f"Error saving config: {e}")
    
    def get(self) -> Tuple[List[Dict], Dict]:
        with self.lock:
            return self._config.get('cctv_list', []), self._config.get('settings', {})

class RTSPConnection:
    """Improved RTSP connection with retry logic and error handling"""
    def __init__(self, url: str, max_retries: int = 3, retry_delay: int = 5):
        self.url = url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.cap = None
        self.frame_queue = queue.Queue(maxsize=30)
        self.is_running = False
        self.thread = None
    
    def connect(self) -> bool:
        """Establish RTSP connection with retry logic"""
        for attempt in range(self.max_retries):
            try:
                # Set environment variables for better stability
                os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = (
                    'rtsp_transport;tcp|buffer_size;8192|stimeout;5000000'
                )
                
                self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
                
                if self.cap.isOpened():
                    # Set buffer size to reduce latency
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    
                    # Get actual stream properties
                    width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = self.cap.get(cv2.CAP_PROP_FPS)
                    
                    if width > 0 and height > 0 and fps > 0:
                        logger.info(f"Connected to {self.url} - {width}x{height}@{fps}fps")
                        return True
                    else:
                        logger.warning(f"Invalid stream properties from {self.url}")
                
                self.cap.release()
                
            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed for {self.url}: {e}")
                if self.cap:
                    self.cap.release()
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        
        return False
    
    def read_frame(self) -> Optional[np.ndarray]:
        """Read frame with error handling"""
        if not self.cap or not self.cap.isOpened():
            return None
        
        try:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                return frame
        except Exception as e:
            logger.error(f"Error reading frame: {e}")
        
        return None
    
    def release(self):
        """Release resources properly"""
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        cv2.destroyAllWindows()

class VideoRecorder:
    """Improved video recorder with better resource management"""
    def __init__(self, rtsp_url: str, output_dir: str, config: Dict):
        self.rtsp_url = rtsp_url
        self.output_dir = output_dir
        self.config = config
        self.connection = None
        self.writer = None
        self.is_recording = False
        self.start_time = None
        self.current_file = None
        
    def _get_output_filename(self) -> str:
        """Generate unique filename with timestamp"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.output_dir, f"recording_{timestamp}.mp4")
    
    def _create_writer(self, frame: np.ndarray) -> cv2.VideoWriter:
        """Create video writer with proper settings"""
        height, width = frame.shape[:2]
        
        # Adjust codec based on platform
        if os.name == 'nt':  # Windows
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        else:  # Linux/Mac
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
        
        fps = min(self.config.get('fps_target', 15), 30)
        return cv2.VideoWriter(
            self.current_file, fourcc, fps, (width, height)
        )
    
    def start_recording(self) -> bool:
        """Start recording with proper initialization"""
        try:
            self.connection = RTSPConnection(
                self.rtsp_url,
                self.config.get('max_retries', 3),
                self.config.get('retry_delay', 5)
            )
            
            if not self.connection.connect():
                logger.error(f"Failed to connect to {self.rtsp_url}")
                return False
            
            # Read first frame to get dimensions
            frame = self.connection.read_frame()
            if frame is None:
                logger.error("Failed to read first frame")
                return False
            
            # Create output directory
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Initialize writer
            self.current_file = self._get_output_filename()
            self.writer = self._create_writer(frame)
            self.is_recording = True
            self.start_time = time.time()
            
            logger.info(f"Started recording to {self.current_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            self.stop_recording()
            return False
    
    def record_frame(self) -> bool:
        """Record a single frame"""
        if not self.is_recording:
            return False
        
        try:
            frame = self.connection.read_frame()
            if frame is None:
                return False
            
            self.writer.write(frame)
            
            # Check if we need to split the file
            if time.time() - self.start_time >= self.config.get('split_duration', 300):
                self._split_recording()
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording frame: {e}")
            return False
    
    def _split_recording(self):
        """Split recording into new file"""
        try:
            if self.writer:
                self.writer.release()
            
            self.current_file = self._get_output_filename()
            frame = self.connection.read_frame()
            if frame is not None:
                self.writer = self._create_writer(frame)
                self.start_time = time.time()
                logger.info(f"Split recording to {self.current_file}")
                
        except Exception as e:
            logger.error(f"Error splitting recording: {e}")
    
    def stop_recording(self):
        """Stop recording and cleanup"""
        self.is_recording = False
        
        if self.writer:
            self.writer.release()
            self.writer = None
        
        if self.connection:
            self.connection.release()
            self.connection = None
        
        # Force garbage collection
        gc.collect()
        logger.info("Recording stopped and resources cleaned up")

class NVRManager:
    """Main NVR manager with improved thread safety"""
    def __init__(self):
        self.config = NVRConfig()
        self.recorders = {}
        self.threads = []
        self.stop_event = Event()
        self.lock = Lock()
    
    def _create_rtsp_url(self, cctv: Dict) -> str:
        """Create RTSP URL with proper encoding"""
        username = urllib.parse.quote(cctv['username'])
        password = urllib.parse.quote(cctv['password'])
        ip = cctv['ip']
        return f"rtsp://{username}:{password}@{ip}:554/Streaming/Channels/101"
    
    def start_recording(self, cctv_list: List[Dict], settings: Dict) -> bool:
        """Start recording for all CCTV"""
        try:
            with self.lock:
                if self.stop_event.is_set():
                    self.stop_event.clear()
                
                self.recorders.clear()
                self.threads.clear()
                
                # Create output directory
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                output_dir = os.path.join("storage", today)
                
                for cctv in cctv_list:
                    rtsp_url = self._create_rtsp_url(cctv)
                    recorder = VideoRecorder(rtsp_url, output_dir, settings)
                    
                    if recorder.start_recording():
                        self.recorders[cctv['ip']] = recorder
                        
                        # Start recording thread
                        thread = Thread(
                            target=self._recording_worker,
                            args=(recorder,),
                            daemon=True
                        )
                        thread.start()
                        self.threads.append(thread)
                
                return len(self.recorders) > 0
                
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            return False
    
    def _recording_worker(self, recorder: VideoRecorder):
        """Worker thread for recording"""
        while not self.stop_event.is_set():
            try:
                if not recorder.record_frame():
                    # If frame read fails, wait and retry
                    time.sleep(1)
                    continue
                    
                # Small sleep to prevent CPU overload
                time.sleep(0.033)  # ~30fps
                
            except Exception as e:
                logger.error(f"Recording worker error: {e}")
                break
    
    def stop_recording(self):
        """Stop all recording"""
        with self.lock:
            self.stop_event.set()
            
            for recorder in self.recorders.values():
                recorder.stop_recording()
            
            # Wait for threads to finish
            for thread in self.threads:
                thread.join(timeout=5)
            
            self.recorders.clear()
            self.threads.clear()
            logger.info("All recording stopped")
    
    def cleanup_old_videos(self, days_to_keep: int):
        """Clean up old video files"""
        try:
            storage_path = "storage"
            if not os.path.exists(storage_path):
                return
            
            now = time.time()
            cutoff = now - (days_to_keep * 86400)
            
            for folder in os.listdir(storage_path):
                folder_path = os.path.join(storage_path, folder)
                if os.path.isdir(folder_path) and os.path.getmtime(folder_path) < cutoff:
                    shutil.rmtree(folder_path)
                    logger.info(f"Deleted old folder: {folder_path}")
                    
        except Exception as e:
            logger.error(f"Error cleaning old videos: {e}")

# GUI Improvements
class NVRGUI:
    """Improved GUI with better error handling"""
    def __init__(self):
        self.manager = NVRManager()
        self.root = None
        
    def create_gui(self):
        """Create the main GUI"""
        self.root = tk.Tk()
        self.root.title("NVR CCTV Manager - Improved")
        self.root.geometry("500x700")
        self.root.configure(bg='#f5f5f5')
        
        # Load configuration
        cctv_list, settings = self.manager.config.get()
        
        # Main frame
        main_frame = tk.Frame(self.root, bg='#f5f5f5')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Styles
        style = {
            'bg': '#2196F3',
            'fg': 'white',
            'font': ('Arial', 10, 'bold'),
            'width': 25,
            'height': 2
        }
        
        # CCTV Management Frame
        cctv_frame = tk.LabelFrame(main_frame, text="Manajemen CCTV", 
                                 font=('Arial', 12, 'bold'), bg='#f5f5f5')
        cctv_frame.pack(fill=tk.X, pady=10)
        
        # Add CCTV button
        add_btn = tk.Button(cctv_frame, text="➕ Tambah CCTV", 
                          command=self.add_cctv, **style)
        add_btn.pack(pady=5)
        
        # Show list button
        list_btn = tk.Button(cctv_frame, text="📋 Lihat Daftar", 
                           command=self.show_cctv_list, **style)
        list_btn.pack(pady=5)
        
        # Remove CCTV button
        remove_btn = tk.Button(cctv_frame, text="🗑️ Hapus CCTV", 
                             command=self.remove_cctv, **style)
        remove_btn.pack(pady=5)
        
        # Settings Frame
        settings_frame = tk.LabelFrame(main_frame, text="Pengaturan", 
                                   font=('Arial', 12, 'bold'), bg='#f5f5f5')
        settings_frame.pack(fill=tk.X, pady=10)
        
        # Settings entries
        self.create_settings_entries(settings_frame, settings)
        
        # Control Frame
        control_frame = tk.LabelFrame(main_frame, text="Kontrol", 
                                    font=('Arial', 12, 'bold'), bg='#f5f5f5')
        control_frame.pack(fill=tk.X, pady=10)
        
        # Status label
        self.status_label = tk.Label(control_frame, text="Status: Siap", 
                                   bg='#f5f5f5', font=('Arial', 10))
        self.status_label.pack(pady=5)
        
        # Start/Stop buttons
        start_btn = tk.Button(control_frame, text="▶️ Mulai Rekaman", 
                            command=self.start_recording, bg='#4CAF50', fg='white',
                            font=('Arial', 10, 'bold'), width=20, height=2)
        start_btn.pack(pady=5)
        
        stop_btn = tk.Button(control_frame, text="⏹️ Hentikan", 
                           command=self.stop_recording, bg='#f44336', fg='white',
                           font=('Arial', 10, 'bold'), width=20, height=2)
        stop_btn.pack(pady=5)
        
        # Cleanup button
        cleanup_btn = tk.Button(control_frame, text="🧹 Bersihkan Lama", 
                              command=self.cleanup_old, bg='#FF9800', fg='white',
                              font=('Arial', 10, 'bold'), width=20, height=2)
        cleanup_btn.pack(pady=5)
        
        return self.root
    
    def create_settings_entries(self, parent, settings):
        """Create settings entry fields"""
        entries = {}
        
        settings_map = {
            'duration': ('Durasi Total (detik)', 3600),
            'split_duration': ('Durasi File (detik)', 300),
            'days_to_keep': ('Simpan Selama (hari)', 7),
            'max_retries': ('Max Retry', 3),
            'retry_delay': ('Retry Delay (detik)', 5)
        }
        
        for key, (label, default) in settings_map.items():
            frame = tk.Frame(parent, bg='#f5f5f5')
            frame.pack(fill=tk.X, pady=2)
            
            tk.Label(frame, text=f"{label}:", bg='#f5f5f5', width=20, anchor='w').pack(side=tk.LEFT)
            entry = tk.Entry(frame, width=10)
            entry.insert(0, str(settings.get(key, default)))
            entry.pack(side=tk.LEFT, padx=5)
            entries[key] = entry
        
        self.settings_entries = entries
    
    def get_settings(self) -> Dict:
        """Get current settings from GUI"""
        settings = {}
        for key, entry in self.settings_entries.items():
            try:
                settings[key] = int(entry.get())
            except ValueError:
                settings[key] = 300  # Default fallback
        return settings
    
    def add_cctv(self):
        """Add new CCTV with validation"""
        ip = simpledialog.askstring("Tambah CCTV", "IP Address:")
        if not ip:
            return
        
        username = simpledialog.askstring("Tambah CCTV", "Username:")
        if not username:
            return
        
        password = simpledialog.askstring("Tambah CCTV", "Password:", show='*')
        if not password:
            return
        
        # Validate IP format
        import re
        if not re.match(r'^\d{1,3}(?:\.\d{1,3}){3}$', ip):
            messagebox.showerror("Error", "Format IP tidak valid!")
            return
        
        cctv_list, settings = self.manager.config.get()
        cctv_list.append({
            "ip": ip,
            "username": username,
            "password": password
        })
        
        self.manager.config.save(cctv_list, settings)
        messagebox.showinfo("Sukses", f"CCTV {ip} ditambahkan!")
    
    def show_cctv_list(self):
        """Show CCTV list in dialog"""
        cctv_list, _ = self.manager.config.get()
        if not cctv_list:
            messagebox.showinfo("Daftar CCTV", "Belum ada CCTV yang ditambahkan")
            return
        
        info = "Daftar CCTV:\n\n"
        for i, cctv in enumerate(cctv_list, 1):
            info += f"{i}. {cctv['ip']} ({cctv['username']})\n"
        
        messagebox.showinfo("Daftar CCTV", info)
    
    def remove_cctv(self):
        """Remove CCTV with confirmation"""
        cctv_list, settings = self.manager.config.get()
        if not cctv_list:
            messagebox.showwarning("Peringatan", "Tidak ada CCTV untuk dihapus")
            return
        
        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Hapus CCTV")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Pilih CCTV yang akan dihapus:").pack(pady=10)
        
        listbox = tk.Listbox(dialog, height=5)
        listbox.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        for cctv in cctv_list:
            listbox.insert(tk.END, f"{cctv['ip']} ({cctv['username']})")
        
        def delete_selected():
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                removed = cctv_list.pop(index)
                self.manager.config.save(cctv_list, settings)
                messagebox.showinfo("Sukses", f"CCTV {removed['ip']} dihapus!")
                dialog.destroy()
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Hapus", command=delete_selected, bg='#f44336', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Batal", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def start_recording(self):
        """Start recording with validation"""
        cctv_list, settings = self.manager.config.get()
        
        if not cctv_list:
            messagebox.showwarning("Peringatan", "Tambahkan CCTV terlebih dahulu!")
            return
        
        current_settings = self.get_settings()
        self.manager.config.save(cctv_list, current_settings)
        
        if self.manager.start_recording(cctv_list, current_settings):
            self.status_label.config(text="Status: Sedang Merekam", fg='green')
            messagebox.showinfo("Info", "Perekaman dimulai!")
        else:
            messagebox.showerror("Error", "Gagal memulai perekaman")
    
    def stop_recording(self):
        """Stop recording"""
        self.manager.stop_recording()
        self.status_label.config(text="Status: Berhenti", fg='red')
        messagebox.showinfo("Info", "Perekaman dihentikan")
    
    def cleanup_old(self):
        """Clean up old videos"""
        _, settings = self.manager.config.get()
        days = settings.get('days_to_keep', 7)
        
        if messagebox.askyesno("Konfirmasi", f"Hapus rekaman lama dari {days} hari yang lalu?"):
            self.manager.cleanup_old_videos(days)
            messagebox.showinfo("Sukses", "Pembersihan selesai!")
    
    def run(self):
        """Run the GUI application"""
        root = self.create_gui()
        root.mainloop()

if __name__ == "__main__":
    app = NVRGUI()
    app.run()

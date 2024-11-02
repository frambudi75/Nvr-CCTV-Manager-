import cv2
import datetime
import os
import time
import shutil
import tkinter as tk
from tkinter import simpledialog, messagebox
from threading import Thread, Event
import urllib.parse
import logging
import json

# Setup logging
logging.basicConfig(
    filename='nvr_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Fungsi-fungsi untuk manajemen file dan direktori
def create_directory_for_today():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    directory = f"storage/{today}"
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory

def get_video_filename(directory):
    current_time = datetime.datetime.now().strftime("%H-%M-%S")
    return os.path.join(directory, f"video_{current_time}.mp4")

def clean_old_videos(storage_path, days_to_keep):
    try:
        now = time.time()
        cutoff = now - (days_to_keep * 86400)
        for folder in os.listdir(storage_path):
            folder_path = os.path.join(storage_path, folder)
            if os.path.isdir(folder_path) and os.path.getmtime(folder_path) < cutoff:
                shutil.rmtree(folder_path)
                logger.info(f"Deleted old folder: {folder_path}")
    except Exception as e:
        logger.error(f"Error cleaning old videos: {str(e)}")

# Fungsi-fungsi untuk pengaturan
def save_settings(cctv_list, settings):
    try:
        config = {
            'cctv_list': cctv_list,
            'settings': settings
        }
        with open('nvr_config.json', 'w') as f:
            json.dump(config, f, indent=4)
        logger.info("Settings saved successfully")
    except Exception as e:
        logger.error(f"Error saving settings: {str(e)}")
        messagebox.showerror("Error", "Gagal menyimpan pengaturan")

def load_settings():
    try:
        with open('nvr_config.json', 'r') as f:
            config = json.load(f)
            return config.get('cctv_list', []), config.get('settings', {})
    except FileNotFoundError:
        return [], {
            'duration': 3600,
            'split_duration': 300,
            'days_to_keep': 7
        }
    except Exception as e:
        logger.error(f"Error loading settings: {str(e)}")
        return [], {
            'duration': 3600,
            'split_duration': 300,
            'days_to_keep': 7
        }

# Fungsi-fungsi untuk manajemen CCTV
def add_device(cctv_list):
    ip = simpledialog.askstring("Input", "Masukkan IP CCTV:")
    username = simpledialog.askstring("Input", "Masukkan Username:")
    password = simpledialog.askstring("Input", "Masukkan Password:")

    if ip and username and password:
        cctv_list.append({"ip": ip, "username": username, "password": password})
        messagebox.showinfo("Info", f"CCTV {ip} berhasil ditambahkan.")
        return True
    return False

def show_cctv_list(cctv_list):
    if not cctv_list:
        messagebox.showinfo("Daftar CCTV", "Belum ada CCTV yang ditambahkan")
        return
    
    cctv_info = "Daftar CCTV:\n\n"
    for i, cctv in enumerate(cctv_list, 1):
        cctv_info += f"{i}. IP: {cctv['ip']}\n   Username: {cctv['username']}\n\n"
    
    messagebox.showinfo("Daftar CCTV", cctv_info)

def remove_cctv(cctv_list):
    if not cctv_list:
        messagebox.showwarning("Peringatan", "Tidak ada CCTV untuk dihapus")
        return

    ip_list = [f"{i+1}. {cctv['ip']}" for i, cctv in enumerate(cctv_list)]
    message = "Masukkan nomor CCTV yang akan dihapus:\n\n"
    for ip in ip_list:
        message += ip + "\n"
    
    ip_to_remove = simpledialog.askstring("Hapus CCTV", message)

    try:
        if ip_to_remove:
            index = int(ip_to_remove) - 1
            if 0 <= index < len(cctv_list):
                removed_ip = cctv_list.pop(index)['ip']
                messagebox.showinfo("Info", f"CCTV {removed_ip} berhasil dihapus")
                return True
    except ValueError:
        messagebox.showerror("Error", "Masukkan nomor yang valid")
    return False

# Fungsi untuk merekam video
def record_video(rtsp_url, record_duration, days_to_keep, stop_event, split_duration=300):
    try:
        # Gunakan FFMPEG options untuk meningkatkan stabilitas
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))
        
        # Set buffer yang lebih besar
        os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp|buffer_size;2048'
        
        if not cap.isOpened():
            logger.error("Tidak dapat membuka stream RTSP")
            return

        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))

        while not stop_event.is_set():
            directory = create_directory_for_today()
            start_time = time.time()

            while time.time() - start_time < record_duration and not stop_event.is_set():
                video_file = get_video_filename(directory)
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(video_file, fourcc, fps, (frame_width, frame_height))

                split_start_time = time.time()
                while time.time() - split_start_time < split_duration and not stop_event.is_set():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    out.write(frame)
                    resized_frame = cv2.resize(frame, (680, 460))
                    cv2.imshow('CCTV Monitor', resized_frame)

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        stop_event.set()
                        break

                out.release()

            clean_old_videos('storage/', days_to_keep)

    except Exception as e:
        logger.error(f"Recording error: {str(e)}")
    finally:
        cap.release()
        cv2.destroyAllWindows()

def start_recording(cctv_list, duration, days_to_keep, stop_event, split_duration):
    threads = []
    for cctv in cctv_list:
        rtsp_url = f"rtsp://{cctv['username']}:{urllib.parse.quote(cctv['password'])}@{cctv['ip']}:554/Streaming/Channels/101"
        thread = Thread(target=record_video, 
                       args=(rtsp_url, duration, days_to_keep, stop_event, split_duration))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

# Fungsi utama untuk GUI
def main_gui():
    root = tk.Tk()
    root.title("NVR CCTV Manager")
    root.geometry("400x600")

    cctv_list, settings = load_settings()
    stop_event = Event()

    main_frame = tk.Frame(root, bg='#f0f0f0')
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    button_style = {'bg': '#4CAF50', 'fg': 'white', 'pady': 5, 'padx': 10, 'width': 20}
    entry_style = {'width': 20}

    cctv_frame = tk.LabelFrame(main_frame, text="Manajemen CCTV", bg='#f0f0f0')
    cctv_frame.pack(fill=tk.X, pady=10)

    def add_device_and_save():
        if add_device(cctv_list):
            save_settings(cctv_list, settings)

    def remove_device_and_save():
        if remove_cctv(cctv_list):
            save_settings(cctv_list, settings)

    add_device_button = tk.Button(cctv_frame, text="Tambahkan CCTV", 
                                command=add_device_and_save, **button_style)
    add_device_button.pack(pady=5)

    show_list_button = tk.Button(cctv_frame, text="Lihat Daftar CCTV", 
                               command=lambda: show_cctv_list(cctv_list), **button_style)
    show_list_button.pack(pady=5)

    remove_cctv_button = tk.Button(cctv_frame, text="Hapus CCTV", 
                                 command=remove_device_and_save, **button_style)
    remove_cctv_button.pack(pady=5)

    settings_frame = tk.LabelFrame(main_frame, text="Pengaturan Rekaman", bg='#f0f0f0')
    settings_frame.pack(fill=tk.X, pady=10)

    tk.Label(settings_frame, text="Durasi Perekaman (detik):", bg='#f0f0f0').pack()
    duration_entry = tk.Entry(settings_frame, **entry_style)
    duration_entry.insert(0, str(settings.get('duration', 3600)))
    duration_entry.pack(pady=5)

    tk.Label(settings_frame, text="Durasi File Rekaman (detik):", bg='#f0f0f0').pack()
    split_duration_entry = tk.Entry(settings_frame, **entry_style)
    split_duration_entry.insert(0, str(settings.get('split_duration', 300)))
    split_duration_entry.pack(pady=5)

    tk.Label(settings_frame, text="Siklus Hapus Rekaman (hari):", bg='#f0f0f0').pack()
    days_to_keep_entry = tk.Entry(settings_frame, **entry_style)
    days_to_keep_entry.insert(0, str(settings.get('days_to_keep', 7)))
    days_to_keep_entry.pack(pady=5)

    def save_current_settings():
        current_settings = {
            'duration': int(duration_entry.get()),
            'split_duration': int(split_duration_entry.get()),
            'days_to_keep': int(days_to_keep_entry.get())
        }
        save_settings(cctv_list, current_settings)

    save_settings_button = tk.Button(settings_frame, text="Simpan Pengaturan", 
                                   command=save_current_settings, **button_style)
    save_settings_button.pack(pady=5)

    control_frame = tk.LabelFrame(main_frame, text="Kontrol Rekaman", bg='#f0f0f0')
    control_frame.pack(fill=tk.X, pady=10)

    def start_recording_action():
        if not cctv_list:
            messagebox.showwarning("Peringatan", "Tambahkan CCTV terlebih dahulu!")
            return

        save_current_settings()
        
        duration = int(duration_entry.get())
        days_to_keep = int(days_to_keep_entry.get())
        split_duration = int(split_duration_entry.get())
        stop_event.clear()
        recording_thread = Thread(target=start_recording, 
                               args=(cctv_list, duration, days_to_keep, stop_event, split_duration))
        recording_thread.start()
        messagebox.showinfo("Info", "Perekaman dimulai")

    def stop_recording_action():
        stop_event.set()
        messagebox.showinfo("Info", "Perekaman dihentikan.")

    start_recording_button = tk.Button(control_frame, text="Mulai Perekaman", 
                                    command=start_recording_action, **button_style)
    start_recording_button.pack(pady=5)

    stop_recording_button = tk.Button(control_frame, text="Hentikan Perekaman", 
                                   command=stop_recording_action, **button_style)
    stop_recording_button.pack(pady=5)

    root.mainloop()
if __name__ == "__main__":
    main_gui()
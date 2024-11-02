![image](https://github.com/user-attachments/assets/daab5176-7eea-4bac-b9f6-f90371484c52)


# NVR CCTV with Python

## Overview
This project is a Python-based Network Video Recorder (NVR) system for CCTV. It supports live monitoring and recording from CCTV cameras over RTSP protocol, handling disconnections and reconnection automatically. The recorded video is stored as an AVI file with H.264 encoding. The project includes a simple Tkinter-based GUI to add, view, and manage CCTV devices.

## Features
- **Live CCTV stream monitoring**
- **Automatic reconnection** if the connection to the CCTV camera is lost
- **Recording video** to an AVI file using H.264 encoding
- **Multiple camera management** via a user-friendly GUI
- **Error handling** and reconnection mechanism in case of network issues
- **Customizable recording duration** with automatic deletion cycles

## Requirements
- Python 3.7 or above
- OpenCV (`opencv-python` and `opencv-python-headless`)
- Tkinter (comes pre-installed with Python)
- ffmpeg for handling H.264 decoding

You can install the required Python packages using the following command:

```bash
pip install opencv-python opencv-python-headless






# User Guide - NVR CCTV

## Table of Contents
1. [Introduction](#introduction)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [Running the Application](#running-the-application)
5. [Using the Application](#using-the-application)
6. [Recording and Storage](#recording-and-storage)
7. [Handling Connection Issues](#handling-connection-issues)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)
10. [Contact and Support](#contact-and-support)

---

## Introduction

The **NVR CCTV** system allows users to monitor and record CCTV camera streams via RTSP. With a graphical user interface (GUI), the system provides an easy way to add multiple devices, view live streams, and manage recorded video files.

---

## System Requirements

Before using the system, ensure you meet the following requirements:

- **Operating System**: Windows, Linux, or MacOS
- **Python**: Version 3.7 or higher
- **FFmpeg**: For video processing and encoding
- **CCTV Camera**: With RTSP streaming capabilities

### Required Python Libraries:
- `opencv-python`
- `opencv-python-headless`
- `ffmpeg-python`

### Compatible CCTV Brands & Models
Any IP camera or DVR/NVR that exposes an **RTSP stream** is supported.  
Popular tested brands include (but are not limited to):
- **Hikvision** (all models with RTSP enabled)
- **Dahua** / **Imou** / **Lorex**
- **Reolink**, **Tapo**, **EZVIZ**, **Amcrest**, **Axis**, **Ubiquiti UniFi Protect**
- **ONVIF-compliant** cameras from any manufacturer

As long as your camera provides a valid RTSP URL, it will work with this application.

---

## Installation

### Step 1: Install Python

Ensure that you have **Python 3.7+** installed on your system. You can download it from the [official Python website](https://www.python.org/downloads/).

### Step 2: Install Dependencies

Open a terminal or command prompt and install the necessary Python libraries:
```bash
pip install opencv-python opencv-python-headless
```

### Step 3: Install FFmpeg

For **Windows**:
1. Download **FFmpeg** from the [official website](https://ffmpeg.org/download.html).
2. Extract the files and add the `bin` folder to your system's PATH.

For **Linux** (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install ffmpeg
```

For **MacOS**:
```bash
brew install ffmpeg
```

### Step 4: Clone the Project

Clone the repository to your local system:
```bash
git clone https://github.com/yourusername/NVR-CCTV.git
cd NVR-CCTV
```

---

## Running the Application

### Step 1: Start the Application

Run the application using the following command:
```bash
python nvr_improved.py
```

### Step 2: Application Interface

When the application starts, a graphical user interface (GUI) will appear, allowing you to manage your CCTV devices.

---

## Using the Application

### Adding a CCTV Camera

1. In the application window, click **Add Device**.
2. Enter the following details:
   - **RTSP URL**: The RTSP stream URL for your CCTV camera.
   - **Username** and **Password** (if required for access).
3. Click **Add**. The live feed from the camera should appear.

### Viewing CCTV Devices

You can view the list of added devices by clicking **View Devices**. This shows all the connected CCTV cameras.

### Recording Video

To start recording:
1. Select the camera you want to record from.
2. Click **Start Recording**. The video will be saved in the `recorded_videos/` folder in AVI format.
   
To stop recording:
1. Click **Stop Recording**.

### Removing a Device

1. To remove a camera, select it from the device list.
2. Click **Remove Device**. The device will be removed from the monitoring list.

---

## Recording and Storage

- Recorded videos are stored in the `recorded_videos/` directory in the application's folder.
- You can configure the **recording duration** and set up an **automatic deletion cycle** for managing storage space.
  
### Managing Storage

To prevent storage from filling up, you can set up automatic file deletion based on a certain timeframe (e.g., delete files older than 7 days).

---

## Handling Connection Issues

The system is designed to handle common issues such as disconnections or decoding errors:

1. **Automatic Reconnection**: If the connection to a CCTV camera is lost, the system will automatically try to reconnect.
2. **Error Notification**: If a connection or stream error occurs, you will see a notification in the console (e.g., `[rtsp @ ...] error while decoding`).

### Manual Reconnection

If a camera doesn't reconnect automatically, you can try to manually reconnect by removing and re-adding the device.

---

## Troubleshooting

Here are some common issues you may encounter and how to resolve them:

### 1. FFmpeg Not Found
If you receive an error indicating that FFmpeg is not installed, ensure that it is correctly added to your system's PATH. Refer to the [Installation](#installation) section for details.

### 2. Decoding Errors
You may see errors like `[h264 @ ...] error while decoding`. This usually happens if the network connection is unstable. The application will attempt to reconnect automatically.

### 3. No Video or Black Screen
If the live feed does not show the video:
- Ensure the RTSP URL is correct.
- Check network connectivity between the application and the CCTV camera.
- Verify that the camera is online and streaming correctly.

### 4. Video File Not Saved
If recording does not generate a video file:
- Ensure that you have write permissions to the `recorded_videos/` directory.
- Check the application's console output for any errors related to file saving.

---

## FAQ

**Q1: What is the recommended RTSP URL format?**

A1: RTSP URLs vary by camera model, but a common format is:
```
rtsp://<username>:<password>@<camera-ip>:<port>/<stream>
```
For example:
```
rtsp://admin:password@192.168.1.100:554/stream
```

**Q2: How do I add multiple cameras?**

A2: You can add multiple cameras by clicking the **Add Device** button multiple times and entering each camera's details.

**Q3: Where are my recorded videos stored?**

A3: Videos are stored in the `recorded_videos/` folder within the application directory.

---

## Contact and Support

If you encounter any issues or need help with the application, please reach out to the project maintainers:

- **Email**: frambudihabib@gmail.com
- **GitHub Issues**: [GitHub Issues](https://github.com/frambudi75/Nvr-CCTV-Manager/issues)

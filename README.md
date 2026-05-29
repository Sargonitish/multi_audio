# 🎧 Live Bluetooth Audio Sync Pro

A modern Python desktop application that streams live system audio to multiple Bluetooth headphones and audio devices simultaneously.

Built with:

* Python
* CustomTkinter
* SoundDevice
* NumPy
* Matplotlib

---

# ✨ Features

✅ Stream live system audio
✅ Multiple Bluetooth headphone support
✅ Modern dark UI
✅ Real-time audio visualizer
✅ Individual volume control
✅ Auto device refresh
✅ Low-latency optimized playback
✅ Professional desktop interface

---

# 📸 Preview

<img width="900" alt="preview" src="https://via.placeholder.com/900x500.png?text=Live+Bluetooth+Audio+Sync+Pro">

---

# 🚀 Installation

## 1️⃣ Clone Repository

```bash
git clone https://github.com/your-username/live-bluetooth-audio-sync-pro.git
cd live-bluetooth-audio-sync-pro
```

---

## 2️⃣ Install Requirements

```bash
pip install -r requirements.txt
```

---

# 📦 requirements.txt

```txt
customtkinter
sounddevice
numpy
matplotlib
```

---

# ▶ Run Application

```bash
python app.py
```

---

# 🛠 Windows Setup (IMPORTANT)

To capture system audio correctly, use one of these:

## Option 1 — VB-CABLE (Recommended)

Install:

* VB-CABLE Virtual Audio Device

After installation:

1. Set Windows output to:

   * `CABLE Input`
2. In the app select:

   * `CABLE Output`
3. Select Bluetooth devices
4. Start streaming

---

## Option 2 — Stereo Mix

1. Open:

   * Control Panel → Sound
2. Recording Tab
3. Enable:

   * Stereo Mix
4. Select it inside the app

---

# 🎧 How It Works

The app:

1. Captures live system audio
2. Buffers audio using NumPy
3. Streams audio to multiple devices simultaneously
4. Uses threading for independent Bluetooth outputs
5. Visualizes audio in real time

---

# ⚡ Performance Notes

Bluetooth streaming has hardware limitations.

For best performance:

* Use Bluetooth 5.0+
* Use same headphone models
* Close heavy apps during streaming
* Disable Windows Audio Enhancements
* Use maximum 2–3 devices for stable playback

---

# 🖥 Technologies Used

* Python
* CustomTkinter
* SoundDevice
* NumPy
* Matplotlib
* Threading

---

# 📂 Project Structure

```text
live-bluetooth-audio-sync-pro/
│
├── app.py
├── requirements.txt
├── profiles.json
├── README.md
│
├── dist/
├── build/
└── installer/
```

---

# 🔥 Future Improvements

* WiFi audio streaming
* Mobile companion app
* AI noise suppression
* WASAPI low-latency engine
* System tray support
* Audio recording
* Per-device delay compensation
* OBS integration
* Auto reconnect devices

---

# 📦 Build EXE

Install PyInstaller:

```bash
pip install pyinstaller
```

Build executable:

```bash
pyinstaller --onefile --windowed --collect-all customtkinter --hidden-import sounddevice --hidden-import matplotlib app.py
```

Generated EXE:

```text
dist/app.exe
```

---

# 🛠 Build Installer

Recommended:

* Inno Setup

Official Website:
https://jrsoftware.org/isinfo.php

---

# 🤝 Contributing

Pull requests are welcome.

For major changes:

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Open a pull request

---

# 📜 License

MIT License

---

# ⭐ Support

If you like this project:
⭐ Star the repository on GitHub

---

# 👨‍💻 Author

Developed with Python and Bluetooth audio streaming technologies.

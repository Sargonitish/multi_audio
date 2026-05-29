# 🎧 Live Bluetooth Audio Sync

A Python application that captures live system audio and streams it simultaneously to multiple Bluetooth headphones or audio devices in real time.

Built using:

* `tkinter` for the graphical interface
* `sounddevice` for real-time audio streaming
* `threading` for multi-device synchronization

---

## 🚀 Features

* 🎵 Capture live system audio using:

  * Virtual Audio Cable
  * Stereo Mix
* 🔊 Stream audio to multiple Bluetooth headphones simultaneously
* 🖥 Simple GUI built with Tkinter
* ⚡ Real-time low-latency audio forwarding
* 🎧 Multi-output support using threads

---

## 📸 Preview

<img width="500" alt="app-preview" src="https://via.placeholder.com/500x300.png?text=Live+Bluetooth+Audio+Sync">

---

## 🛠 Requirements

Install Python packages:

```bash
pip install sounddevice
```

Tkinter usually comes pre-installed with Python.

---

## 🔧 Windows Setup (Important)

To capture system audio, you need one of the following:

### Option 1 — Virtual Audio Cable (Recommended)

Install:

* VB-CABLE Virtual Audio Device

After installation:

1. Set your system output to `CABLE Input`
2. In the app select:

   * `CABLE Output` / `Line 1`
3. Select your Bluetooth headphones as outputs

---

### Option 2 — Stereo Mix

1. Open:

   * Control Panel → Sound → Recording
2. Enable:

   * `Stereo Mix`
3. Select it in the app as the input source

---

## ▶ Running the App

```bash
python app.py
```

---

## 📋 How It Works

1. The app captures live audio from:

   * Virtual Cable OR Stereo Mix
2. Creates a dedicated audio stream for every selected output device
3. Uses threading to broadcast audio simultaneously

---

## 🧠 Technologies Used

* Python
* Tkinter
* SoundDevice
* Threading

---

## ⚠ Known Limitations

* Bluetooth devices may have slight latency differences
* Works best on Windows
* Audio quality depends on device drivers
* Some devices may not support simultaneous playback

---

## 📁 Project Structure

```text
live-bluetooth-audio-sync/
│
├── app.py
├── README.md
└── requirements.txt
```

---

## 📦 requirements.txt

```txt
sounddevice
```

---

## 💡 Future Improvements

* Device latency compensation
* Volume controls per device
* Auto reconnect
* Better audio buffering
* Dark mode UI

---

## 🤝 Contributing

Pull requests are welcome.

For major changes:

1. Fork the repository
2. Create a new branch
3. Commit your changes
4. Open a pull request

---

## 📜 License

MIT License

---

## ⭐ Support

If you like this project, give it a star on GitHub ⭐

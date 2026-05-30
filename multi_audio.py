import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog
import sounddevice as sd
import numpy as np
import threading
import json
import os
import time
import wave
import serial
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Default settings
SETTINGS_FILE = "config.json"
DEFAULT_CONFIG = {
    "theme": "dark",
    "latency": "Balanced",
    "active_profile": "Default",
    "profiles": {
        "Default": {"input": "", "outputs": {}}
    }
}

class TactileHardwareBridge:
    """Handles serial communication to external tactile/Braille hardware."""
    def __init__(self, port="COM3", baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.connect()

    def connect(self):
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Hardware Bridge connected on {self.port}")
        except Exception as e:
            print(f"Hardware Bridge offline. Ensure the device is connected to {self.port}. Error: {e}")

    def send_state(self, status, active_device_count, max_vu):
        """
        Transmits a formatted string for a microcontroller (e.g., Arduino/ESP32) to parse.
        Format: STAT:[IDLE/PLAY]|DEVS:[NUM]|VU:[0-100]\n
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            return

        try:
            vu_percentage = int(max_vu * 100)
            payload = f"STAT:{status}|DEVS:{active_device_count}|VU:{vu_percentage}\n"
            self.serial_conn.write(payload.encode('utf-8'))
        except Exception:
            pass
            
    def close(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()

class RingBuffer:
    """A thread-safe Numpy-based ring buffer for audio streaming."""
    def __init__(self, capacity, channels=2):
        self.capacity = capacity
        self.buffer = np.zeros((capacity, channels), dtype=np.float32)
        self.write_ptr = 0
        self.read_ptr = 0
        self.size = 0
        self.lock = threading.Lock()

    def push(self, data):
        with self.lock:
            frames = data.shape[0]
            if frames > self.capacity:
                data = data[-self.capacity:]
                frames = self.capacity
            
            # If buffer is full, advance read pointer (drop oldest)
            if self.size + frames > self.capacity:
                overflow = (self.size + frames) - self.capacity
                self.read_ptr = (self.read_ptr + overflow) % self.capacity
                self.size -= overflow

            end = min(self.write_ptr + frames, self.capacity)
            first_part = end - self.write_ptr
            self.buffer[self.write_ptr:end] = data[:first_part]

            if first_part < frames:
                self.buffer[0:frames - first_part] = data[first_part:]
                self.write_ptr = frames - first_part
            else:
                self.write_ptr = end % self.capacity
            
            self.size += frames

    def pop(self, frames):
        with self.lock:
            if self.size < frames:
                return np.zeros((frames, self.buffer.shape[1]), dtype=np.float32)
            
            out = np.zeros((frames, self.buffer.shape[1]), dtype=np.float32)
            end = min(self.read_ptr + frames, self.capacity)
            first_part = end - self.read_ptr
            
            out[:first_part] = self.buffer[self.read_ptr:end]
            if first_part < frames:
                out[first_part:] = self.buffer[0:frames - first_part]
                self.read_ptr = frames - first_part
            else:
                self.read_ptr = end % self.capacity
            
            self.size -= frames
            return out

class AudioDevice:
    def __init__(self, index, device_info, buffer_capacity):
        self.index = index
        self.name = device_info["name"]
        
        # Auto-detect Bluetooth in name
        bt_keywords = ["bluetooth", "a2dp", "hands-free", "bth"]
        self.is_bluetooth = any(kw in self.name.lower() for kw in bt_keywords)
        if self.is_bluetooth:
            self.name = f"[BT] {self.name}"

        self.volume = 1.0
        self.enabled = False
        self.delay_ms = 0.0
        self.vu_level = 0.0
        self.buffer = RingBuffer(buffer_capacity)

class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, config, on_save):
        super().__init__(parent)
        self.title("⚙ Settings")
        self.geometry("400x300")
        self.config = config
        self.on_save = on_save

        ctk.CTkLabel(self, text="Appearance", font=("Arial", 16, "bold")).pack(pady=(20, 5))
        self.theme_var = ctk.StringVar(value=self.config.get("theme", "dark"))
        ctk.CTkOptionMenu(self, values=["dark", "light", "system"], variable=self.theme_var).pack()

        ctk.CTkLabel(self, text="Latency Preset", font=("Arial", 16, "bold")).pack(pady=(20, 5))
        self.latency_var = ctk.StringVar(value=self.config.get("latency", "Balanced"))
        ctk.CTkOptionMenu(self, values=["Low (Fast)", "Balanced", "Stable (Safe)"], variable=self.latency_var).pack()

        ctk.CTkButton(self, text="Save & Apply", command=self.save_settings).pack(pady=30)

    def save_settings(self):
        self.config["theme"] = self.theme_var.get()
        self.config["latency"] = self.latency_var.get()
        self.on_save(self.config)
        self.destroy()

class LiveAudioSyncPro:
    def __init__(self, root):
        self.root = root
        self.root.title("🎧 Live Audio Sync Pro - Assistive Edition")
        self.root.geometry("1300x800")
        
        # Initialize hardware bridge (Change COM3 to your specific port if needed)
        self.hardware = TactileHardwareBridge(port="COM3") 

        self.sample_rate = 44100
        self.load_config()
        self.apply_latency_preset()

        # Recording state
        self.is_recording = False
        self.recorded_frames = []

        self.stop_event = threading.Event()
        self.audio_lock = threading.Lock()

        self.current_audio = np.zeros((self.block_size, 2), dtype=np.float32)
        self.latest_audio = np.zeros(1024, dtype=np.float32)

        self.input_stream = None
        self.stream_threads = []
        
        self.device_ui_frames = {}
        self.device_vars = {}
        self.device_vu = {}

        self.reload_devices()
        self.build_ui()
        self.apply_accessibility_bindings()
        self.refresh_devices()
        self.load_active_profile()
        self.start_ui_updater()

    def load_config(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    self.config = json.load(f)
            except:
                self.config = DEFAULT_CONFIG.copy()
        else:
            self.config = DEFAULT_CONFIG.copy()
            
        ctk.set_appearance_mode(self.config.get("theme", "dark"))
        ctk.set_default_color_theme("blue")

    def save_config(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def apply_latency_preset(self):
        preset = self.config.get("latency", "Balanced")
        if preset == "Low (Fast)":
            self.block_size = 1024
            self.buffer_size = self.sample_rate * 2
        elif preset == "Stable (Safe)":
            self.block_size = 8192
            self.buffer_size = self.sample_rate * 10
        else:
            self.block_size = 4096
            self.buffer_size = self.sample_rate * 5

    def reload_devices(self):
        self.devices = sd.query_devices()
        self.input_devices = [{"index": i, **d} for i, d in enumerate(self.devices) if d["max_input_channels"] > 0]
        self.output_devices = [AudioDevice(i, d, self.buffer_size) for i, d in enumerate(self.devices) if d["max_output_channels"] > 0]

    def build_ui(self):
        # Sidebar
        self.sidebar = ctk.CTkFrame(self.root, width=320)
        self.sidebar.pack(side="left", fill="y")

        self.main = ctk.CTkFrame(self.root)
        self.main.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(self.sidebar, text="🎧 Audio Sync Pro", font=("Arial", 24, "bold")).pack(pady=20)

        # Profile Selector
        profile_frame = ctk.CTkFrame(self.sidebar)
        profile_frame.pack(fill="x", padx=15, pady=5)
        self.profile_var = ctk.StringVar(value=self.config["active_profile"])
        self.profile_menu = ctk.CTkOptionMenu(profile_frame, values=list(self.config["profiles"].keys()), variable=self.profile_var, command=self.change_profile)
        self.profile_menu.pack(side="left", fill="x", expand=True, padx=(5,0), pady=5)
        ctk.CTkButton(profile_frame, text="Save", width=50, command=self.save_current_profile).pack(side="right", padx=5, pady=5)

        # Input Selection
        ctk.CTkLabel(self.sidebar, text="Audio Source", font=("Arial", 16, "bold")).pack(anchor="w", padx=20, pady=(15, 0))
        self.input_var = ctk.StringVar()
        names = [d["name"] for d in self.input_devices]
        self.input_menu = ctk.CTkOptionMenu(self.sidebar, values=names if names else ["No Input Devices"], variable=self.input_var)
        self.input_menu.pack(padx=20, pady=5)
        if names: self.input_var.set(names[0])

        # Controls
        self.start_btn = ctk.CTkButton(self.sidebar, text="▶ Start Streaming", command=self.start_streaming)
        self.start_btn.pack(fill="x", padx=20, pady=10)

        self.stop_btn = ctk.CTkButton(self.sidebar, text="■ Stop", state="disabled", command=self.stop_streaming)
        self.stop_btn.pack(fill="x", padx=20)
        
        self.record_btn = ctk.CTkButton(self.sidebar, text="⏺ Start Recording", fg_color="darkred", hover_color="red", command=self.toggle_recording)
        self.record_btn.pack(fill="x", padx=20, pady=10)

        self.status_label = ctk.CTkLabel(self.sidebar, text="Status: Idle")
        self.status_label.pack(pady=10)

        ctk.CTkButton(self.sidebar, text="⚙ Settings", command=self.open_settings).pack(side="bottom", pady=20, padx=20, fill="x")

        # Main Content
        top_bar = ctk.CTkFrame(self.main, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(top_bar, text="Output Devices", font=("Arial", 18, "bold")).pack(side="left", padx=5)
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.filter_devices)
        ctk.CTkEntry(top_bar, placeholder_text="Search devices...", textvariable=self.search_var, width=250).pack(side="right", padx=5)

        self.device_frame = ctk.CTkScrollableFrame(self.main)
        self.device_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Visualizer
        vis_frame = ctk.CTkFrame(self.main)
        vis_frame.pack(fill="x", padx=10, pady=10)
        self.figure = Figure(figsize=(8, 1.5), dpi=100)
        self.figure.patch.set_facecolor('#2b2b2b' if self.config.get("theme") == "dark" else '#f0f0f0')
        self.ax = self.figure.add_subplot(111)
        self.ax.set_ylim(-1, 1)
        self.ax.set_xlim(0, 1024)
        self.ax.axis('off')
        self.line, = self.ax.plot(np.zeros(1024), color='#1f538d')
        self.canvas = FigureCanvasTkAgg(self.figure, master=vis_frame)
        self.canvas.get_tk_widget().pack(fill="x")

    def apply_accessibility_bindings(self):
        """Ensures the application is fully navigable via keyboard for screen readers."""
        self.root.bind("<Tab>", self.focus_next_window)
        self.root.bind("<Shift-Tab>", self.focus_prev_window)
        
        # Bind enter/space to activate focused buttons
        self.root.bind("<Return>", lambda event: event.widget.invoke() if hasattr(event.widget, 'invoke') else None)
        self.root.bind("<space>", lambda event: event.widget.invoke() if hasattr(event.widget, 'invoke') else None)

    def focus_next_window(self, event):
        event.widget.tk_focusNext().focus()
        return "break"

    def focus_prev_window(self, event):
        event.widget.tk_focusPrev().focus()
        return "break"

    def filter_devices(self, *args):
        query = self.search_var.get().lower()
        for name, frame in self.device_ui_frames.items():
            if query in name.lower():
                frame.pack(fill="x", padx=5, pady=5)
            else:
                frame.pack_forget()

    def refresh_devices(self):
        for child in self.device_frame.winfo_children():
            child.destroy()
        
        self.device_ui_frames.clear()
        self.device_vars.clear()
        self.device_vu.clear()

        for device in self.output_devices:
            frame = ctk.CTkFrame(self.device_frame)
            frame.pack(fill="x", padx=5, pady=5)
            self.device_ui_frames[device.name] = frame

            # Top row: Checkbox + VU Meter
            top_row = ctk.CTkFrame(frame, fg_color="transparent")
            top_row.pack(fill="x", padx=10, pady=(5, 0))
            
            var = tk.BooleanVar(value=device.enabled)
            self.device_vars[device.name] = var
            cb = ctk.CTkCheckBox(top_row, text=device.name, variable=var, font=("Arial", 14, "bold"), command=lambda d=device, v=var: self.toggle_device(d, v))
            cb.pack(side="left")

            vu = ctk.CTkProgressBar(top_row, width=100, height=10)
            vu.set(0)
            vu.pack(side="right", pady=5)
            self.device_vu[device.name] = vu

            # Sliders row: Volume + Delay
            sliders_row = ctk.CTkFrame(frame, fg_color="transparent")
            sliders_row.pack(fill="x", padx=10, pady=5)

            ctk.CTkLabel(sliders_row, text="Vol:").pack(side="left")
            vol_slider = ctk.CTkSlider(sliders_row, from_=0, to=100, width=150, command=lambda v, d=device: setattr(d, 'volume', float(v)/100.0))
            vol_slider.set(device.volume * 100)
            vol_slider.pack(side="left", padx=10)

            ctk.CTkLabel(sliders_row, text="Delay (ms):").pack(side="left", padx=(10, 0))
            delay_slider = ctk.CTkSlider(sliders_row, from_=0, to=1000, width=150, command=lambda v, d=device: setattr(d, 'delay_ms', float(v)))
            delay_slider.set(device.delay_ms)
            delay_slider.pack(side="left", padx=10)

    def toggle_device(self, device, var):
        device.enabled = var.get()

    def open_settings(self):
        SettingsDialog(self.root, self.config, self.apply_settings)

    def apply_settings(self, new_config):
        self.config = new_config
        self.save_config()
        ctk.set_appearance_mode(self.config["theme"])
        self.apply_latency_preset()
        self.figure.patch.set_facecolor('#2b2b2b' if self.config["theme"] == "dark" else '#f0f0f0')

    def change_profile(self, profile_name):
        self.config["active_profile"] = profile_name
        self.load_active_profile()

    def save_current_profile(self):
        prof_name = simpledialog.askstring("Save Profile", "Enter profile name:", initialvalue=self.config["active_profile"])
        if prof_name:
            data = {
                "input": self.input_var.get(),
                "outputs": {
                    d.name: {"enabled": d.enabled, "volume": d.volume, "delay_ms": d.delay_ms}
                    for d in self.output_devices
                }
            }
            self.config["profiles"][prof_name] = data
            self.config["active_profile"] = prof_name
            self.save_config()
            self.profile_menu.configure(values=list(self.config["profiles"].keys()))
            self.profile_var.set(prof_name)

    def load_active_profile(self):
        prof_name = self.config["active_profile"]
        data = self.config["profiles"].get(prof_name, {})
        
        if "input" in data and data["input"] in [d["name"] for d in self.input_devices]:
            self.input_var.set(data["input"])
            
        outputs = data.get("outputs", {})
        for device in self.output_devices:
            if device.name in outputs:
                device.enabled = outputs[device.name]["enabled"]
                device.volume = outputs[device.name]["volume"]
                device.delay_ms = outputs[device.name].get("delay_ms", 0.0)
            else:
                device.enabled = False
        
        self.refresh_devices()

    def audio_callback(self, indata, frames, time_info, status):
        if indata.shape[1] == 1:
            indata = np.repeat(indata, 2, axis=1)

        audio = indata.copy()

        if self.is_recording:
            self.recorded_frames.append(audio.copy())

        with self.audio_lock:
            self.current_audio = audio
            self.latest_audio = audio[:, 0].copy()

        for device in self.output_devices:
            if device.enabled:
                device.buffer.push(audio.copy())

    def output_worker(self, device):
        def callback(outdata, frames, time_info, status):
            delay_frames = int((device.delay_ms / 1000.0) * self.sample_rate)
            audio = device.buffer.pop(frames)
            
            if device.buffer.size < delay_frames:
                outdata[:] = np.zeros((frames, 2), dtype=np.float32)
            else:
                outdata[:] = audio * device.volume

            # Calculate RMS for VU meter
            rms = np.sqrt(np.mean(outdata**2))
            device.vu_level = min(1.0, rms * 5)

        with sd.OutputStream(
            device=device.index, samplerate=self.sample_rate, channels=2,
            blocksize=self.block_size, dtype="float32", callback=callback
        ):
            while not self.stop_event.is_set():
                time.sleep(0.05)

    def start_streaming(self):
        enabled = [d for d in self.output_devices if d.enabled]
        if not enabled:
            messagebox.showwarning("Warning", "Select at least one output device")
            return

        match = next((d for d in self.input_devices if d["name"] == self.input_var.get()), None)
        if not match: return

        self.stop_event.clear()
        
        for d in enabled:
            d.buffer = RingBuffer(self.buffer_size)

        self.input_stream = sd.InputStream(
            device=match["index"], channels=min(2, match["max_input_channels"]),
            samplerate=self.sample_rate, blocksize=self.block_size, dtype="float32",
            callback=self.audio_callback
        )
        self.input_stream.start()

        self.stream_threads = []
        for device in enabled:
            t = threading.Thread(target=self.output_worker, args=(device,), daemon=True)
            t.start()
            self.stream_threads.append(t)

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_label.configure(text="Status: Streaming")

    def stop_streaming(self):
        self.stop_event.set()
        if self.input_stream:
            self.input_stream.stop()
            self.input_stream.close()
            
        if self.is_recording:
            self.toggle_recording()

        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="Status: Idle")

    def toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.recorded_frames = []
            self.record_btn.configure(text="⏹ Stop Recording", fg_color="red")
        else:
            self.is_recording = False
            self.record_btn.configure(text="⏺ Start Recording", fg_color="darkred")
            self.save_wav()

    def save_wav(self):
        if not self.recorded_frames:
            return
            
        filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        audio_data = np.concatenate(self.recorded_frames, axis=0)
        audio_int16 = np.int16(np.clip(audio_data, -1.0, 1.0) * 32767)
        
        try:
            with wave.open(filename, "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_int16.tobytes())
            messagebox.showinfo("Saved", f"Recording saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save recording:\n{e}")

    def start_ui_updater(self):
        self.update_ui_loop()

    def update_ui_loop(self):
        try:
            self.line.set_ydata(self.latest_audio)
            self.canvas.draw_idle()
        except: pass

        highest_vu = 0.0
        active_count = 0

        if not self.stop_event.is_set():
            for device in self.output_devices:
                if device.enabled:
                    active_count += 1
                    if device.name in self.device_vu:
                        current = self.device_vu[device.name].get()
                        new_val = max(device.vu_level, current - 0.05)
                        self.device_vu[device.name].set(new_val)
                        
                        if new_val > highest_vu:
                            highest_vu = new_val
                            
                        device.vu_level = 0.0

        # Transmit data to external Braille/Haptic hardware
        status = "PLAY" if not self.stop_event.is_set() and active_count > 0 else "IDLE"
        self.hardware.send_state(status, active_count, highest_vu)

        self.root.after(50, self.update_ui_loop)

    def on_close(self):
        self.stop_streaming()
        self.hardware.close()
        self.root.destroy()

if __name__ == "__main__":
    root = ctk.CTk()
    app = LiveAudioSyncPro(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

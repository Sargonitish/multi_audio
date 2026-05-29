import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import sounddevice as sd
import numpy as np
import threading
import json
import os
import time
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# ---------------- SETTINGS ----------------

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

SETTINGS_FILE = "profiles.json"

# ---------------- AUDIO DEVICE ----------------


class AudioDevice:

    def __init__(self, device_info):

        self.name = device_info['name']
        self.index = device_info['index']
        self.volume = 1.0
        self.enabled = False


# ---------------- MAIN APP ----------------


class LiveAudioSyncPro:

    def __init__(self, root):

        self.root = root

        self.root.title("🎧 Live Bluetooth Audio Sync Pro")

        self.root.geometry("1200x750")

        self.sample_rate = 44100

        # BIGGER BUFFER = MORE STABLE BLUETOOTH
        self.block_size = 4096

        self.stop_event = threading.Event()

        self.stream_threads = []

        self.current_audio = np.zeros(
            (self.block_size, 2),
            dtype=np.float32
        )

        self.latest_audio = np.zeros(1024)

        self.devices = sd.query_devices()

        self.input_devices = [
            d for d in self.devices
            if d['max_input_channels'] > 0
        ]

        self.output_devices = [
            AudioDevice(d)
            for d in self.devices
            if d['max_output_channels'] > 0
        ]

        self.build_ui()

        self.refresh_devices()

        self.start_visualizer()

    # ---------------- UI ----------------

    def build_ui(self):

        # SIDEBAR
        self.sidebar = ctk.CTkFrame(
            self.root,
            width=300
        )

        self.sidebar.pack(
            side="left",
            fill="y"
        )

        # MAIN
        self.main = ctk.CTkFrame(self.root)

        self.main.pack(
            side="right",
            fill="both",
            expand=True
        )

        # TITLE
        title = ctk.CTkLabel(
            self.sidebar,
            text="🎧 Audio Sync Pro",
            font=("Arial", 28, "bold")
        )

        title.pack(pady=25)

        # INPUT
        input_label = ctk.CTkLabel(
            self.sidebar,
            text="Audio Source",
            font=("Arial", 18, "bold")
        )

        input_label.pack(
            anchor="w",
            padx=20,
            pady=(20, 5)
        )

        input_names = [
            d['name']
            for d in self.input_devices
        ]

        self.input_var = ctk.StringVar()

        self.input_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=input_names,
            variable=self.input_var,
            width=240
        )

        self.input_menu.pack(padx=20)

        if input_names:
            self.input_var.set(input_names[0])

        # AUTO DETECT VIRTUAL CABLE
        for d in input_names:

            low = d.lower()

            if (
                "virtual" in low or
                "stereo mix" in low or
                "line" in low
            ):

                self.input_var.set(d)
                break

        # START BUTTON
        self.start_btn = ctk.CTkButton(
            self.sidebar,
            text="▶ Start Streaming",
            height=50,
            font=("Arial", 16, "bold"),
            command=self.start_streaming
        )

        self.start_btn.pack(
            fill="x",
            padx=20,
            pady=(35, 10)
        )

        # STOP BUTTON
        self.stop_btn = ctk.CTkButton(
            self.sidebar,
            text="■ Stop",
            height=50,
            fg_color="#cc3333",
            hover_color="#aa2222",
            font=("Arial", 16, "bold"),
            state="disabled",
            command=self.stop_streaming
        )

        self.stop_btn.pack(
            fill="x",
            padx=20
        )

        # REFRESH
        self.refresh_btn = ctk.CTkButton(
            self.sidebar,
            text="🔄 Refresh Devices",
            height=40,
            command=self.refresh_devices
        )

        self.refresh_btn.pack(
            fill="x",
            padx=20,
            pady=(20, 10)
        )

        # STATUS
        self.status_label = ctk.CTkLabel(
            self.sidebar,
            text="Status: Idle",
            font=("Arial", 16)
        )

        self.status_label.pack(pady=30)

        # DEVICE FRAME
        self.device_frame = ctk.CTkScrollableFrame(
            self.main,
            label_text="🎧 Output Devices"
        )

        self.device_frame.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=12
        )

        self.device_widgets = []

        # VISUALIZER FRAME
        vis_frame = ctk.CTkFrame(self.main)

        vis_frame.pack(
            fill="x",
            padx=12,
            pady=(0, 12)
        )

        vis_label = ctk.CTkLabel(
            vis_frame,
            text="📊 Live Audio Visualizer",
            font=("Arial", 20, "bold")
        )

        vis_label.pack(pady=10)

        self.figure = Figure(
            figsize=(8, 2),
            dpi=100
        )

        self.ax = self.figure.add_subplot(111)

        self.ax.set_ylim(-1, 1)

        self.ax.set_xlim(0, 1024)

        self.ax.set_facecolor("black")

        self.line, = self.ax.plot(
            np.zeros(1024)
        )

        self.canvas = FigureCanvasTkAgg(
            self.figure,
            master=vis_frame
        )

        self.canvas.get_tk_widget().pack(
            fill="x",
            padx=10,
            pady=10
        )

    # ---------------- DEVICE HANDLING ----------------

    def refresh_devices(self):

        for widget in self.device_widgets:
            widget.destroy()

        self.device_widgets.clear()

        self.devices = sd.query_devices()

        self.output_devices = [
            AudioDevice(d)
            for d in self.devices
            if d['max_output_channels'] > 0
        ]

        for device in self.output_devices:

            card = ctk.CTkFrame(self.device_frame)

            card.pack(
                fill="x",
                padx=5,
                pady=8
            )

            var = tk.BooleanVar()

            checkbox = ctk.CTkCheckBox(
                card,
                text=device.name,
                variable=var,
                command=lambda d=device, v=var:
                self.toggle_device(d, v)
            )

            checkbox.pack(
                anchor="w",
                padx=15,
                pady=(10, 5)
            )

            slider = ctk.CTkSlider(
                card,
                from_=0,
                to=100,
                command=lambda value, d=device:
                self.change_volume(d, value)
            )

            slider.set(100)

            slider.pack(
                fill="x",
                padx=15,
                pady=(0, 10)
            )

            self.device_widgets.append(card)

    def toggle_device(self, device, var):

        device.enabled = var.get()

    def change_volume(self, device, value):

        device.volume = value / 100.0

    # ---------------- AUDIO ----------------

    def audio_callback(
        self,
        indata,
        frames,
        time_info,
        status
    ):

        if status:
            print(status)

        try:

            self.current_audio = indata.copy()

            self.latest_audio = indata[:, 0]

        except Exception as e:
            print(e)

    def output_worker(self, device):

        try:

            silence = np.zeros(
                (self.block_size, 2),
                dtype=np.float32
            )

            def callback(
                outdata,
                frames,
                time_info,
                status
            ):

                try:

                    audio = self.current_audio.copy()

                    if len(audio) < frames:

                        outdata[:] = silence

                        return

                    outdata[:] = (
                        audio * device.volume
                    )

                except Exception as e:

                    print(e)

                    outdata[:] = silence

            with sd.OutputStream(

                device=device.index,

                samplerate=self.sample_rate,

                blocksize=self.block_size,

                channels=2,

                dtype='float32',

                latency='high',

                callback=callback

            ):

                while not self.stop_event.is_set():

                    time.sleep(0.1)

        except Exception as e:

            print(
                f"Error with {device.name}: {e}"
            )

    def start_streaming(self):

        enabled_devices = [

            d for d in self.output_devices

            if d.enabled

        ]

        if not enabled_devices:

            messagebox.showwarning(
                "Warning",
                "Select at least one output device"
            )

            return

        input_name = self.input_var.get()

        input_index = None

        for d in self.input_devices:

            if d['name'] == input_name:

                input_index = d['index']

                break

        if input_index is None:

            messagebox.showerror(
                "Error",
                "Invalid input device"
            )

            return

        self.stop_event.clear()

        try:

            self.input_stream = sd.InputStream(

                device=input_index,

                channels=2,

                samplerate=self.sample_rate,

                blocksize=self.block_size,

                dtype='float32',

                latency='high',

                callback=self.audio_callback

            )

            self.input_stream.start()

            self.stream_threads = []

            for device in enabled_devices:

                t = threading.Thread(
                    target=self.output_worker,
                    args=(device,),
                    daemon=True
                )

                t.start()

                self.stream_threads.append(t)

            self.start_btn.configure(
                state="disabled"
            )

            self.stop_btn.configure(
                state="normal"
            )

            self.status_label.configure(
                text="Status: Streaming"
            )

        except Exception as e:

            messagebox.showerror(
                "Audio Error",
                str(e)
            )

    def stop_streaming(self):

        self.stop_event.set()

        try:

            self.input_stream.stop()

            self.input_stream.close()

        except:
            pass

        self.start_btn.configure(
            state="normal"
        )

        self.stop_btn.configure(
            state="disabled"
        )

        self.status_label.configure(
            text="Status: Idle"
        )

    # ---------------- VISUALIZER ----------------

    def start_visualizer(self):

        self.update_visualizer()

    def update_visualizer(self):

        try:

            self.line.set_ydata(
                self.latest_audio
            )

            self.canvas.draw_idle()

        except:
            pass

        # LOWER FPS = BETTER AUDIO
        self.root.after(
            120,
            self.update_visualizer
        )


# ---------------- RUN ----------------

if __name__ == "__main__":

    root = ctk.CTk()

    app = LiveAudioSyncPro(root)

    root.mainloop()

import tkinter as tk
from tkinter import messagebox
import sounddevice as sd
import threading

class LiveSystemAudioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Live Bluetooth Audio Sync")
        self.root.geometry("480x480")
        self.root.config(padx=20, pady=20)

        self.stream_threads = []
        self.stop_event = threading.Event()

        # Query all audio devices on your laptop
        self.devices = sd.query_devices()
        self.in_devices = [d for d in self.devices if d['max_input_channels'] > 0]
        self.out_devices = [d for d in self.devices if d['max_output_channels'] > 0]

        # --- 1. Input Selection (Capture) ---
        tk.Label(root, text="1. Select Audio Source (Input)", font=("Arial", 11, "bold")).pack(anchor="w")
        tk.Label(root, text="Select 'Line 1 (Virtual Audio Cable)' or 'Stereo Mix'", font=("Arial", 9, "italic")).pack(anchor="w", pady=(0, 5))
        
        self.in_var = tk.StringVar(root)
        self.in_dropdown = tk.OptionMenu(root, self.in_var, *[d['name'] for d in self.in_devices])
        self.in_dropdown.pack(fill=tk.X, pady=5)
        
        # Attempt to automatically select the Virtual Cable if it exists
        for d in self.in_devices:
            if "Virtual" in d['name'] or "Line 1" in d['name'] or "Stereo Mix" in d['name']:
                self.in_var.set(d['name'])
                break

        # --- 2. Output Selection (Playback) ---
        tk.Label(root, text="2. Select Output Headphones", font=("Arial", 11, "bold")).pack(anchor="w", pady=(15, 0))
        tk.Label(root, text="Hold CTRL to select multiple headphones", font=("Arial", 9)).pack(anchor="w", pady=(0, 5))

        self.listbox = tk.Listbox(root, selectmode=tk.MULTIPLE, height=8)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        for device in self.out_devices:
            self.listbox.insert(tk.END, device['name'])

        # --- 3. Controls ---
        self.btn_frame = tk.Frame(root)
        self.btn_frame.pack(fill=tk.X, pady=15)

        self.start_btn = tk.Button(self.btn_frame, text="▶ Start Live Sync", font=("Arial", 11, "bold"), bg="#4CAF50", fg="white", command=self.start_sync)
        self.start_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.stop_btn = tk.Button(self.btn_frame, text="■ Stop", font=("Arial", 11, "bold"), bg="#f44336", fg="white", state=tk.DISABLED, command=self.stop_sync)
        self.stop_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)

    def audio_worker(self, in_idx, out_idx):
        """Creates a dedicated real-time stream from the virtual cable to a specific headset."""
        try:
            def callback(indata, outdata, frames, time, status):
                outdata[:] = indata # Instantly copy input audio to output buffer

            with sd.Stream(device=(in_idx, out_idx), 
                           samplerate=44100, 
                           blocksize=1024,
                           dtype='float32',
                           channels=2, 
                           callback=callback):
                self.stop_event.wait() # Keep the stream open until Stop is clicked
        except Exception as e:
            print(f"Error streaming to device {out_idx}: {e}")

    def start_sync(self):
        in_name = self.in_var.get()
        selected = self.listbox.curselection()

        if not in_name or not selected:
            messagebox.showwarning("Warning", "Select one input and at least one output headphone!")
            return

        in_idx = next(d['index'] for d in self.in_devices if d['name'] == in_name)
        out_indices = [self.out_devices[i]['index'] for i in selected]

        self.stop_event.clear()
        self.stream_threads = []

        # Spin up a simultaneous audio channel for every headphone selected
        for out_idx in out_indices:
            t = threading.Thread(target=self.audio_worker, args=(in_idx, out_idx), daemon=True)
            t.start()
            self.stream_threads.append(t)

        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

    def stop_sync(self):
        self.stop_event.set()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = LiveSystemAudioApp(root)
    root.mainloop()
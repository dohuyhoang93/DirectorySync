import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import subprocess
import time
import json
import threading
from pathlib import Path
import sys

class SyncApp:
    def __init__(self, root):
        self.root = root
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.title("Directory Sync Tool")
        self.root.configure(bg='#2C2F33')  # Dark background
        self.config_file = "config.json"
        self.running = False
        self.pairs = []
        # Set icon with exception handling and load from PyInstaller bundle
        try:
            if getattr(sys, '_MEIPASS', False):
                # Run from PyInstaller bundle, get temporary path
                icon_path = os.path.join(sys._MEIPASS, "DirectorySync.ico")
            else:
                # Run from regular script, using relative path
                icon_path = "DirectorySync.ico"
            self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error setting icon: {e}. Using default icon.")
        self.create_gui()
        self.load_config()

    def create_gui(self):
        # Configure style for dark theme and modern buttons
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#2C2F33')
        style.configure('TLabel', background='#2C2F33', foreground='#FFFFFF', font=('Segoe UI', 10))
        style.configure('TEntry', fieldbackground='#3B3F46', foreground='#FFFFFF', font=('Segoe UI', 10))
        style.configure('TButton', background='#00B7EB', foreground='#FFFFFF', font=('Segoe UI', 10, 'bold'), 
                        padding=4, borderwidth=2, relief='flat')
        style.map('TButton', 
                  background=[('active', '#4DD0E1')], 
                  foreground=[('active', '#FFFFFF')])  # Gradient effect on hover

        # Custom style for rounded buttons
        style.configure('Rounded.TButton', background='#00B7EB', foreground='#FFFFFF', 
                        font=('Segoe UI', 10, 'bold'), padding=4, borderwidth=2, relief='flat')
        style.map('Rounded.TButton', 
                  background=[('active', '#009ACD')],  # Darker blue on hover
                  foreground=[('active', '#FFFFFF')])

        # Configure style for Checkbutton
        style.configure('TCheckbutton', background='#2C2F33', foreground='#FFFFFF', font=('Segoe UI', 9))

        # Main Frame
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)
        for i in range(3):
            self.main_frame.grid_columnconfigure(i, weight=1)

        # Pairs Frame
        self.pairs_frame = ttk.Frame(self.main_frame)
        self.pairs_frame.grid_rowconfigure(0, weight=1)
        self.pairs_frame.grid_columnconfigure(0, weight=1)
        self.pairs_frame.grid(row=0, column=0, columnspan=3, sticky="nsew", pady=15)
        
        # Interval Input
        # interval_frame = ttk.Frame(self.main_frame)
        # interval_frame.grid(row=1, column=0, columnspan=3, pady=15, sticky=(tk.W))
        #ttk.Label(interval_frame, text="Interval (seconds):").grid(row=0, column=0, padx=10)
        # self.interval_entry = ttk.Entry(interval_frame, width=10)
        # self.interval_entry.grid(row=0, column=1, padx=5)
        # self.interval_entry.insert(0, "60")

        # Buttons
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=1, column=0, columnspan=3, pady=10)
        ttk.Label(button_frame, text="Interval (seconds):").grid(row=0, column=0, padx=10)
        self.interval_entry = ttk.Entry(button_frame, width=10)
        self.interval_entry.grid(row=0, column=1, padx=10)
        self.interval_entry.insert(0, "60")
        ttk.Button(button_frame, text="Add pair", command=self.add_pair, style='Rounded.TButton', width=12).grid(row=0, column=2, padx=10)
        ttk.Button(button_frame, text="Save config", command=self.save_config, style='Rounded.TButton', width=12).grid(row=0, column=3, padx=10)
        ttk.Button(button_frame, text="Start", command=self.start_sync, style='Rounded.TButton', width=12).grid(row=0, column=4, padx=10)
        ttk.Button(button_frame, text="Stop", command=self.stop_sync, style='Rounded.TButton', width=12).grid(row=0, column=5, padx=10)

        # Log Area with Scrollbar
        log_frame = ttk.Frame(self.main_frame)
        log_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=15)
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log = tk.Text(log_frame, height=20, width=140, bg='#3B3F46', fg='#FFFFFF', font=('Segoe UI', 9), 
                           borderwidth=2, relief='groove')
        self.log.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log['yscrollcommand'] = scrollbar.set
        self.log.configure(state='disabled')

    def log_message(self, message):
        self.log.configure(state='normal')
        self.log.insert(tk.END, f"{time.strftime('%Y-%m-%d %H:%M:%S')}: {message}\n")
        self.log.see(tk.END)
        self.log.configure(state='disabled')

    def add_pair(self, source="", dest="", is_rclone=False):
        index = len(self.pairs) + 1
        frame = ttk.Frame(self.pairs_frame)
        frame.pack(fill="x", pady=5)
        # frame.grid(row=index-1, column=0, sticky=(tk.W, tk.E), pady=10)
        # for i in range(7):
        #     frame.grid_columnconfigure(i, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(4, weight=1)
        self.pairs_frame.grid_columnconfigure(0, weight=1)

        # Source
        ttk.Label(frame, text=f"Source {index}:").grid(row=0, column=0, sticky=tk.W, padx=10)
        source_entry = ttk.Entry(frame, width=30)
        source_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10)
        source_entry.insert(0, source)
        ttk.Button(frame, text="Browse", command=lambda: self.browse_dir(source_entry), style='Rounded.TButton', width=8).grid(row=0, column=2, padx=10)

        # Destination
        ttk.Label(frame, text=f"Destination {index}:").grid(row=0, column=3, sticky=tk.W, padx=10)
        dest_entry = ttk.Entry(frame, width=30)
        dest_entry.grid(row=0, column=4, sticky=(tk.W, tk.E), padx=10)
        dest_entry.insert(0, dest)
        ttk.Button(frame, text="Browse", command=lambda: self.browse_dir(dest_entry), style='Rounded.TButton', width=8).grid(row=0, column=5, padx=10)

        # Rclone Checkbox
        is_rclone_var = tk.BooleanVar(value=is_rclone)
        ttk.Checkbutton(frame, text="Using Rclone", variable=is_rclone_var, style='TCheckbutton').grid(row=0, column=6, padx=10)

        # Remove Button
        ttk.Button(frame, text="Remove", command=lambda: self.remove_pair(frame, (source_entry, dest_entry, is_rclone_var)), style='Rounded.TButton', width=8).grid(row=0, column=7, padx=10)

        self.pairs.append((frame, source_entry, dest_entry, is_rclone_var))

    def browse_dir(self, entry):
        path = filedialog.askdirectory()
        if path:
            # Normalize path to use double backslashes
            path = str(Path(path)).replace('/', '\\')
            entry.delete(0, tk.END)
            entry.insert(0, path)

    def remove_pair(self, frame, pair):
        frame.destroy()
        self.pairs.remove((frame, *pair))

    def load_config(self):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.interval_entry.delete(0, tk.END)
                self.interval_entry.insert(0, config.get("interval", "60"))
                self.log_message(f"Loaded configuration with interval: {config.get('interval', '60')} seconds")
                for pair in config.get("pairs", []):
                    self.add_pair(pair["source"], pair["destination"], pair.get("is_rclone", False))
        except FileNotFoundError:
            self.add_pair()
            self.log_message("No configuration file found, added a default pair with default interval: 60 seconds")
        except json.JSONDecodeError as e:
            self.add_pair()
            self.log_message(f"JSON format error in config.json: {str(e)}. Added a default pair with default interval: 60 seconds")
        except Exception as e:
            self.add_pair()
            self.log_message(f"Error reading configuration: {str(e)}. Added a default pair with default interval: 60 seconds")

    def save_config(self):
        config = {
            "interval": self.interval_entry.get(),
            "pairs": [{"source": source.get(), "destination": dest.get(), "is_rclone": var.get()} for _, source, dest, var in self.pairs]
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            self.log_message("Configuration has been saved to config.json")
        except Exception as e:
            self.log_message(f"Error saving configuration: {str(e)}")

    def run_command(self, cmd, desc):
        self.log_message(f"Running {desc}...")
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        last_line = None
        while True:
            stdout_line = process.stdout.readline()
            if stdout_line == '' and process.poll() is not None:
                break
            if stdout_line:
                # Repeat filter for rclone (progress usually overwrites the same line)
                if 'rclone' in desc and stdout_line.strip() == last_line:
                    continue
                # Only write important lines for robocopy (summary or newline)
                if 'robocopy' in desc and not stdout_line.strip().startswith(('New Dir', '    ', '*EXTRA')):
                    self.log_message(stdout_line.strip())
                else:
                    self.log_message(stdout_line.strip())
                last_line = stdout_line.strip()
        stderr = process.stderr.read()
        if process.returncode != 0:
            self.log_message(f"Error in {desc} (Error code: {process.returncode}): {stderr or 'No error message'}")

    def is_rust_project(self, path):
        return any(os.path.exists(os.path.join(root, "Cargo.toml")) for root, _, _ in os.walk(path))

    def run_cargo_clean(self, path):
        for root, _, files in os.walk(path):
            if "Cargo.toml" in files:
                self.run_command(f'cd /d "{root}" && cargo clean', f"Cargo clean in {root}")

    def sync_loop(self):
        while self.running:
            self.log_message("Start sync cycle...")
            for i, (frame, source_entry, dest_entry, is_rclone_var) in enumerate(self.pairs):
                source = source_entry.get()
                dest = dest_entry.get()
                # if not os.path.exists(source):
                #     self.log_message(f"Error: Source directory {i+1} '{source}' does not exist")
                #     continue
                if not is_rclone_var.get():  # Only for robocopy
                    try:
                        os.makedirs(dest, exist_ok=True)
                        if not os.access(dest, os.W_OK):
                            self.log_message(f"Error: No write permissions for destination {i+1} '{dest}'")
                            continue
                    except Exception as e:
                        self.log_message(f"Error creating destination {i+1} '{dest}': {str(e)}")
                        continue
                if self.is_rust_project(source):
                    self.run_cargo_clean(source)
                if is_rclone_var.get():
                    self.run_command(
                        f'rclone copy "{source}" "{dest}" --checkers=32 --transfers=16 --multi-thread-streams=8 --update --copy-links --progress --log-file="log.txt" --log-level=INFO',
                        f"Synchronize source {i+1} to {dest} (rclone)"
                    )
                else:
                    self.run_command(
                        f'robocopy "{source}" "{dest}" /MT:32 /MIR /Z /COPY:DAT /R:3 /W:10',
                        f"Synchronize source {i+1} to {dest} (robocopy)"
                    )
            self.log_message("Sync cycle completed. Waiting for next cycle...")
            time.sleep(int(self.interval_entry.get() or 60))

    def start_sync(self):
        if not self.running:
            self.running = True
            self.log_message("Start synchronous loop...")
            threading.Thread(target=self.sync_loop, daemon=True).start()
        else:
            self.log_message("Sync is running.")

    def stop_sync(self):
        self.running = False
        self.log_message("Sync stopped.")

if __name__ == "__main__":
    root = tk.Tk()
    app = SyncApp(root)
    root.mainloop()
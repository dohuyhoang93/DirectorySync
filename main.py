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
        self.root.title("Directory Sync Tool")
        self.root.configure(bg='#2C2F33')  # Dark background
        self.config_file = "config.json"
        self.running = False
        self.pairs = []
        # Đặt icon với xử lý ngoại lệ và tải từ bundle của PyInstaller
        try:
            if getattr(sys, '_MEIPASS', False):
                # Chạy từ PyInstaller bundle, lấy đường dẫn tạm
                icon_path = os.path.join(sys._MEIPASS, "DirectorySync.ico")
            else:
                # Chạy từ script thông thường, dùng đường dẫn tương đối
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

        # Pairs Frame
        self.pairs_frame = ttk.Frame(self.main_frame)
        self.pairs_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15)

        # Interval Input
        ttk.Label(self.main_frame, text="Khoảng thời gian lặp (giây):").grid(row=1, column=0, sticky=tk.W, pady=10, padx=5)
        self.interval_entry = ttk.Entry(self.main_frame, width=10)
        self.interval_entry.grid(row=1, column=1, sticky=tk.W, pady=10, padx=5)
        self.interval_entry.insert(0, "60")

        # Buttons
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=15)
        ttk.Button(button_frame, text="Thêm cặp", command=self.add_pair, style='Rounded.TButton', width=12).grid(row=0, column=0, padx=10)
        ttk.Button(button_frame, text="Lưu cấu hình", command=self.save_config, style='Rounded.TButton', width=12).grid(row=0, column=1, padx=10)
        ttk.Button(button_frame, text="Bắt đầu đồng bộ", command=self.start_sync, style='Rounded.TButton', width=15).grid(row=0, column=2, padx=10)
        ttk.Button(button_frame, text="Dừng đồng bộ", command=self.stop_sync, style='Rounded.TButton', width=15).grid(row=0, column=3, padx=10)

        # Log Area with Scrollbar
        log_frame = ttk.Frame(self.main_frame)
        log_frame.grid(row=3, column=0, columnspan=3, pady=15, sticky=(tk.W, tk.E))
        self.log = tk.Text(log_frame, height=30, width=140, bg='#3B3F46', fg='#FFFFFF', font=('Segoe UI', 9), 
                           borderwidth=2, relief='groove')
        self.log.grid(row=0, column=0, sticky=(tk.W, tk.E))
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
        frame.grid(row=index-1, column=0, sticky=(tk.W, tk.E), pady=10)

        # Source
        ttk.Label(frame, text=f"Nguồn {index}:").grid(row=0, column=0, sticky=tk.W, padx=10)
        source_entry = ttk.Entry(frame, width=30)
        source_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10)
        source_entry.insert(0, source)
        ttk.Button(frame, text="Duyệt", command=lambda: self.browse_dir(source_entry), style='Rounded.TButton', width=6).grid(row=0, column=2, padx=10)

        # Destination
        ttk.Label(frame, text=f"Đích {index}:").grid(row=0, column=3, sticky=tk.W, padx=10)
        dest_entry = ttk.Entry(frame, width=30)
        dest_entry.grid(row=0, column=4, sticky=(tk.W, tk.E), padx=10)
        dest_entry.insert(0, dest)
        ttk.Button(frame, text="Duyệt", command=lambda: self.browse_dir(dest_entry), style='Rounded.TButton', width=6).grid(row=0, column=5, padx=10)

        # Rclone Checkbox
        is_rclone_var = tk.BooleanVar(value=is_rclone)
        ttk.Checkbutton(frame, text="Sử dụng Rclone", variable=is_rclone_var, style='TCheckbutton').grid(row=0, column=6, padx=10)

        # Remove Button
        ttk.Button(frame, text="Xóa", command=lambda: self.remove_pair(frame, (source_entry, dest_entry, is_rclone_var)), style='Rounded.TButton', width=6).grid(row=0, column=7, padx=10)

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
                self.log_message(f"Đã tải cấu hình với interval: {config.get('interval', '60')} giây")
                for pair in config.get("pairs", []):
                    self.add_pair(pair["source"], pair["destination"], pair.get("is_rclone", False))
        except FileNotFoundError:
            self.add_pair()
            self.log_message("Không tìm thấy file cấu hình, đã thêm một cặp mặc định với interval mặc định: 60 giây")
        except json.JSONDecodeError as e:
            self.add_pair()
            self.log_message(f"Lỗi định dạng JSON trong config.json: {str(e)}. Đã thêm một cặp mặc định với interval mặc định: 60 giây")
        except Exception as e:
            self.add_pair()
            self.log_message(f"Lỗi khi đọc cấu hình: {str(e)}. Đã thêm một cặp mặc định với interval mặc định: 60 giây")

    def save_config(self):
        config = {
            "interval": self.interval_entry.get(),
            "pairs": [{"source": source.get(), "destination": dest.get(), "is_rclone": var.get()} for _, source, dest, var in self.pairs]
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            self.log_message("Cấu hình đã được lưu vào config.json")
        except Exception as e:
            self.log_message(f"Lỗi khi lưu cấu hình: {str(e)}")

    def run_command(self, cmd, desc):
        self.log_message(f"Đang chạy {desc}...")
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        last_line = None
        while True:
            stdout_line = process.stdout.readline()
            if stdout_line == '' and process.poll() is not None:
                break
            if stdout_line:
                # Lọc lặp lại cho rclone (progress thường overwrite cùng dòng)
                if 'rclone' in desc and stdout_line.strip() == last_line:
                    continue
                # Chỉ ghi dòng quan trọng cho robocopy (tổng kết hoặc dòng mới)
                if 'robocopy' in desc and not stdout_line.strip().startswith(('New Dir', '    ', '*EXTRA')):
                    self.log_message(stdout_line.strip())
                else:
                    self.log_message(stdout_line.strip())
                last_line = stdout_line.strip()
        stderr = process.stderr.read()
        if process.returncode != 0:
            self.log_message(f"Lỗi trong {desc} (Mã lỗi: {process.returncode}): {stderr or 'Không có thông báo lỗi'}")

    def is_rust_project(self, path):
        return any(os.path.exists(os.path.join(root, "Cargo.toml")) for root, _, _ in os.walk(path))

    def run_cargo_clean(self, path):
        for root, _, files in os.walk(path):
            if "Cargo.toml" in files:
                self.run_command(f'cd /d "{root}" && cargo clean', f"Cargo clean trong {root}")

    def sync_loop(self):
        while self.running:
            self.log_message("Bắt đầu chu kỳ đồng bộ...")
            for i, (frame, source_entry, dest_entry, is_rclone_var) in enumerate(self.pairs):
                source = source_entry.get()
                dest = dest_entry.get()
                if not os.path.exists(source):
                    self.log_message(f"Lỗi: Thư mục nguồn {i+1} '{source}' không tồn tại")
                    continue
                if not is_rclone_var.get():  # Only for robocopy
                    try:
                        os.makedirs(dest, exist_ok=True)
                        if not os.access(dest, os.W_OK):
                            self.log_message(f"Lỗi: Không có quyền ghi cho đích {i+1} '{dest}'")
                            continue
                    except Exception as e:
                        self.log_message(f"Lỗi khi tạo đích {i+1} '{dest}': {str(e)}")
                        continue
                if self.is_rust_project(source):
                    self.run_cargo_clean(source)
                if is_rclone_var.get():
                    self.run_command(
                        f'rclone copy "{source}" "{dest}" --checkers=32 --transfers=16 --multi-thread-streams=8 --update --copy-links --progress --log-file="log.txt" --log-level=INFO',
                        f"Đồng bộ Nguồn {i+1} tới {dest} (rclone)"
                    )
                else:
                    self.run_command(
                        f'robocopy "{source}" "{dest}" /MT:32 /MIR /Z /COPY:DAT /R:3 /W:10',
                        f"Đồng bộ Nguồn {i+1} tới {dest} (robocopy)"
                    )
            self.log_message("Chu kỳ đồng bộ hoàn thành. Chờ chu kỳ tiếp theo...")
            time.sleep(int(self.interval_entry.get() or 60))

    def start_sync(self):
        if not self.running:
            self.running = True
            self.log_message("Bắt đầu vòng lặp đồng bộ...")
            threading.Thread(target=self.sync_loop, daemon=True).start()
        else:
            self.log_message("Đồng bộ đang chạy.")

    def stop_sync(self):
        self.running = False
        self.log_message("Đã dừng đồng bộ.")

if __name__ == "__main__":
    root = tk.Tk()
    app = SyncApp(root)
    root.mainloop()
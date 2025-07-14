import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import ttkbootstrap as ttk_bs
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import Meter
import json
import os
import queue
import time
from sync_manager import SyncManager
from pathlib import Path
import shutil

class SyncApp:
    def __init__(self, root):
        self.root = root
        self.config_file = "config.json"
        self.pairs = []
        self.message_queue = queue.Queue()
        self.sync_manager = None
        
        # Initialize ttkbootstrap style
        self.style = ttk_bs.Style()
        self.available_themes = self.style.theme_names()
        self.current_theme = "darkly"  # Default theme
        
        self.create_gui()
        self.load_config()
        
        # Start polling for messages
        self.poll_messages()
    
    def create_gui(self):
        # Apply initial theme
        self.style.theme_use(self.current_theme)
        
        # Main container
        main_frame = ttk_bs.Frame(self.root, padding=10)
        main_frame.pack(fill=BOTH, expand=True)
        
        # Top control panel
        self.create_control_panel(main_frame)
        
        # Pairs management section
        self.create_pairs_section(main_frame)
        
        # Progress and logging section
        self.create_progress_section(main_frame)
    
    def create_control_panel(self, parent):
        control_frame = ttk_bs.LabelFrame(parent, text="Control Panel", padding=10)
        control_frame.pack(fill=X, pady=(0, 10))
        
        # Theme selector
        theme_frame = ttk_bs.Frame(control_frame)
        theme_frame.pack(fill=X, pady=(0, 10))
        
        ttk_bs.Label(theme_frame, text="Theme:").pack(side=LEFT, padx=(0, 5))
        self.theme_var = tk.StringVar(value=self.current_theme)
        theme_combo = ttk_bs.Combobox(theme_frame, textvariable=self.theme_var, 
                                     values=list(self.available_themes), state="readonly", width=15)
        theme_combo.pack(side=LEFT, padx=(0, 20))
        theme_combo.bind("<<ComboboxSelected>>", self.change_theme)
        
        # Interval setting
        ttk_bs.Label(theme_frame, text="Interval (seconds):").pack(side=LEFT, padx=(0, 5))
        self.interval_var = tk.StringVar(value="60")
        interval_entry = ttk_bs.Entry(theme_frame, textvariable=self.interval_var, width=10)
        interval_entry.pack(side=LEFT, padx=(0, 20))
        
        # Control buttons
        button_frame = ttk_bs.Frame(control_frame)
        button_frame.pack(fill=X, pady=(10, 0))
        
        ttk_bs.Button(button_frame, text="Add Pair", command=self.add_pair, 
                     bootstyle=SUCCESS).pack(side=LEFT, padx=(0, 10))
        ttk_bs.Button(button_frame, text="Save Config", command=self.save_config, 
                     bootstyle=INFO).pack(side=LEFT, padx=(0, 10))
        ttk_bs.Button(button_frame, text="Start Sync", command=self.start_sync, 
                     bootstyle=PRIMARY).pack(side=LEFT, padx=(0, 10))
        ttk_bs.Button(button_frame, text="Stop Sync", command=self.stop_sync, 
                     bootstyle=DANGER).pack(side=LEFT, padx=(0, 10))
    
    def create_pairs_section(self, parent):
        pairs_frame = ttk_bs.LabelFrame(parent, text="Sync Pairs", padding=10)
        pairs_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        
        # Scrollable frame for pairs
        canvas = tk.Canvas(pairs_frame, highlightthickness=0)
        scrollbar = ttk_bs.Scrollbar(pairs_frame, orient=VERTICAL, command=canvas.yview)
        self.pairs_container = ttk_bs.Frame(canvas)
        
        self.pairs_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.pairs_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # Bind mousewheel to canvas
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
    
    def create_progress_section(self, parent):
        progress_frame = ttk_bs.LabelFrame(parent, text="Progress & Logs", padding=10)
        progress_frame.pack(fill=BOTH, expand=True)
        
        # Progress meter (shared for all pairs)
        meter_frame = ttk_bs.Frame(progress_frame)
        meter_frame.pack(side=LEFT, padx=(0, 20))
        
        self.progress_meter = Meter(
            master=meter_frame,
            metersize=200,
            padding=5,
            amountused=0,
            metertype="semi",
            subtext="Ready",
            interactive=False,
            bootstyle=INFO
        )
        self.progress_meter.pack()
        
        # Log area
        log_frame = ttk_bs.Frame(progress_frame)
        log_frame.pack(side=RIGHT, fill=BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            width=80,
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.log_text.pack(fill=BOTH, expand=True)
    
    def change_theme(self, event=None):
        """Change the application theme dynamically"""
        new_theme = self.theme_var.get()
        if new_theme != self.current_theme:
            self.current_theme = new_theme
            self.style.theme_use(new_theme)
            self.log_message(f"Theme changed to: {new_theme}")
    
    def add_pair(self, source="", dest="", tool="robocopy", mode="MIR", enabled=True):
        """Add a new sync pair"""
        pair_frame = ttk_bs.LabelFrame(self.pairs_container, text=f"Pair #{len(self.pairs) + 1}", padding=10)
        pair_frame.pack(fill=X, pady=(0, 10))
        
        # Enabled toggle
        enabled_var = tk.BooleanVar(value=enabled)
        enabled_check = ttk_bs.Checkbutton(pair_frame, text="Enabled", variable=enabled_var)
        enabled_check.grid(row=0, column=0, sticky=W, padx=(0, 10))
        
        # Source path
        ttk_bs.Label(pair_frame, text="Source:").grid(row=0, column=1, sticky=W, padx=(0, 5))
        source_var = tk.StringVar(value=source)
        source_entry = ttk_bs.Entry(pair_frame, textvariable=source_var, width=30)
        source_entry.grid(row=0, column=2, sticky=EW, padx=(0, 5))
        
        ttk_bs.Button(pair_frame, text="Browse", 
                     command=lambda: self.browse_directory(source_var),
                     bootstyle=OUTLINE).grid(row=0, column=3, padx=(0, 10))
        
        # Destination path
        ttk_bs.Label(pair_frame, text="Destination:").grid(row=1, column=1, sticky=W, padx=(0, 5), pady=(5, 0))
        dest_var = tk.StringVar(value=dest)
        dest_entry = ttk_bs.Entry(pair_frame, textvariable=dest_var, width=30)
        dest_entry.grid(row=1, column=2, sticky=EW, padx=(0, 5), pady=(5, 0))
        
        ttk_bs.Button(pair_frame, text="Browse", 
                     command=lambda: self.browse_directory(dest_var),
                     bootstyle=OUTLINE).grid(row=1, column=3, padx=(0, 10), pady=(5, 0))
        
        # Tool selection
        ttk_bs.Label(pair_frame, text="Tool:").grid(row=2, column=1, sticky=W, padx=(0, 5), pady=(5, 0))
        tool_var = tk.StringVar(value=tool)
        tool_combo = ttk_bs.Combobox(pair_frame, textvariable=tool_var, 
                                    values=["robocopy", "rclone"], state="readonly", width=15)
        tool_combo.grid(row=2, column=2, sticky=W, padx=(0, 5), pady=(5, 0))
        
        # Mode selection
        ttk_bs.Label(pair_frame, text="Mode:").grid(row=3, column=1, sticky=W, padx=(0, 5), pady=(5, 0))
        mode_var = tk.StringVar(value=mode)
        mode_combo = ttk_bs.Combobox(pair_frame, textvariable=mode_var, 
                                    values=["MIR", "E-Copy", "sync", "copy"], state="readonly", width=15)
        mode_combo.grid(row=3, column=2, sticky=W, padx=(0, 5), pady=(5, 0))
        
        # Remove button
        ttk_bs.Button(pair_frame, text="Remove", 
                     command=lambda: self.remove_pair(pair_frame),
                     bootstyle=DANGER).grid(row=3, column=3, padx=(0, 10), pady=(5, 0))
        
        # Configure grid weights
        pair_frame.grid_columnconfigure(2, weight=1)
        
        # Store pair data
        pair_data = {
            'frame': pair_frame,
            'enabled_var': enabled_var,
            'source_var': source_var,
            'dest_var': dest_var,
            'tool_var': tool_var,
            'mode_var': mode_var
        }
        
        self.pairs.append(pair_data)
        self.log_message(f"Added sync pair #{len(self.pairs)}")
    
    def remove_pair(self, frame):
        """Remove a sync pair"""
        for i, pair in enumerate(self.pairs):
            if pair['frame'] == frame:
                frame.destroy()
                self.pairs.pop(i)
                self.log_message(f"Removed sync pair")
                break
        
        # Renumber remaining pairs
        for i, pair in enumerate(self.pairs):
            pair['frame'].configure(text=f"Pair #{i + 1}")
    
    def browse_directory(self, var):
        """Browse for directory"""
        directory = filedialog.askdirectory()
        if directory:
            var.set(str(Path(directory)))
    
    def validate_interval(self):
        """Validate interval input"""
        try:
            interval = int(self.interval_var.get())
            if interval <= 0:
                raise ValueError("Interval must be positive")
            return interval
        except ValueError:
            self.log_message("Invalid interval, using default: 60 seconds")
            self.interval_var.set("60")
            return 60
    
    def validate_pairs(self):
        """Validate and return enabled pairs"""
        valid_pairs = []
        
        for pair in self.pairs:
            if not pair['enabled_var'].get():
                continue
            
            source = pair['source_var'].get().strip()
            dest = pair['dest_var'].get().strip()
            tool = pair['tool_var'].get()
            mode = pair['mode_var'].get()
            
            if not source or not dest:
                self.log_message("Error: Source and destination cannot be empty")
                continue
            
            # Validate robocopy paths
            if tool == "robocopy":
                if not os.path.exists(source):
                    self.log_message(f"Error: Source directory '{source}' does not exist")
                    continue
                if not os.path.isdir(source):
                    self.log_message(f"Error: Source '{source}' is not a directory")
                    continue
            
            # Validate rclone availability
            if tool == "rclone":
                if not shutil.which("rclone"):
                    self.log_message("Error: rclone not found in system PATH")
                    continue
            
            valid_pairs.append({
                'source': source,
                'destination': dest,
                'tool': tool,
                'mode': mode
            })
        
        return valid_pairs
    
    def start_sync(self):
        """Start synchronization"""
        if self.sync_manager and self.sync_manager.is_running():
            self.log_message("Sync is already running")
            return
        
        # Validate inputs
        interval = self.validate_interval()
        valid_pairs = self.validate_pairs()
        
        if not valid_pairs:
            self.log_message("No valid pairs to sync")
            return
        
        # Reset progress meter
        self.progress_meter.configure(amountused=0, subtext="Starting...")
        
        # Start sync manager
        self.sync_manager = SyncManager(valid_pairs, interval, self.message_queue)
        self.sync_manager.start()
        
        self.log_message(f"Started sync with {len(valid_pairs)} pairs, interval: {interval}s")
    
    def stop_sync(self):
        """Stop synchronization"""
        if self.sync_manager:
            self.sync_manager.stop()
            self.log_message("Sync stopped")
            self.progress_meter.configure(amountused=0, subtext="Stopped")
    
    def save_config(self):
        """Save configuration to file"""
        config = {
            "interval": self.interval_var.get(),
            "theme": self.current_theme,
            "pairs": []
        }
        
        for pair in self.pairs:
            config["pairs"].append({
                "source": pair['source_var'].get(),
                "destination": pair['dest_var'].get(),
                "tool": pair['tool_var'].get(),
                "mode": pair['mode_var'].get(),
                "enabled": pair['enabled_var'].get()
            })
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            self.log_message("Configuration saved successfully")
        except Exception as e:
            self.log_message(f"Error saving configuration: {e}")
    
    def load_config(self):
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Load interval
            self.interval_var.set(config.get("interval", "60"))
            
            # Load theme
            theme = config.get("theme", "darkly")
            if theme in self.available_themes:
                self.current_theme = theme
                self.theme_var.set(theme)
                self.style.theme_use(theme)
            
            # Load pairs
            for pair_config in config.get("pairs", []):
                self.add_pair(
                    source=pair_config.get("source", ""),
                    dest=pair_config.get("destination", ""),
                    tool=pair_config.get("tool", "robocopy"),
                    mode=pair_config.get("mode", "MIR"),
                    enabled=pair_config.get("enabled", True)
                )
            
            self.log_message("Configuration loaded successfully")
            
        except FileNotFoundError:
            self.log_message("No configuration file found, using defaults")
            self.add_pair()  # Add default empty pair
        except json.JSONDecodeError as e:
            self.log_message(f"Invalid JSON in config file: {e}")
            self.add_pair()  # Add default empty pair
        except Exception as e:
            self.log_message(f"Error loading configuration: {e}")
            self.add_pair()  # Add default empty pair
    
    def log_message(self, message):
        """Add message to log"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
    
    def poll_messages(self):
        """Poll for messages from sync manager"""
        try:
            while True:
                message_type, *args = self.message_queue.get_nowait()
                
                if message_type == "log":
                    self.log_message(args[0])
                elif message_type == "meter":
                    index, percent = args
                    self.progress_meter.configure(amountused=percent, subtext=f"Pair {index + 1}")
                elif message_type == "complete":
                    self.progress_meter.configure(amountused=100, subtext="Complete")
                elif message_type == "error":
                    self.progress_meter.configure(amountused=0, subtext="Error")
                
        except queue.Empty:
            pass
        
        # Schedule next poll
        self.root.after(100, self.poll_messages)
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import ttkbootstrap as ttk_bs
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
import json
import os
import queue
import time
from sync_manager import SyncManager
from pathlib import Path
import shutil
import copy

class SyncApp:
    def __init__(self, root):
        self.root = root
        self.config_file = "config.json"
        self.pairs = []
        self.message_queue = queue.Queue()
        self.sync_manager = SyncManager(self.message_queue)
        self.selected_pair_index = None
        
        self.detail_widgets = {}
        self.detail_vars = {}
        self._is_updating_vars = False

        self.style = ttk_bs.Style()
        self.available_themes = self.style.theme_names()
        self.current_theme = "darkly"

        self.create_gui()
        self.load_config()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.poll_messages()

    def create_gui(self):
        self.style.theme_use(self.current_theme)
        main_frame = ttk_bs.Frame(self.root, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        self.create_control_panel(main_frame)

        paned_window = ttk.PanedWindow(main_frame, orient=HORIZONTAL)
        paned_window.pack(fill=BOTH, expand=True, pady=(10, 0))

        master_frame = ttk_bs.LabelFrame(paned_window, text="Sync Pairs", padding=10)
        paned_window.add(master_frame, weight=2)

        self.pair_listbox = tk.Listbox(master_frame, height=15, selectmode=tk.BROWSE, exportselection=False)
        self.pair_listbox.pack(fill=BOTH, expand=True)
        self.pair_listbox.bind("<<ListboxSelect>>", self.on_pair_select)
        self.pair_listbox.bind("<Button-3>", self.show_context_menu)

        detail_container = ttk_bs.LabelFrame(paned_window, text="Pair Configuration", padding=10)
        paned_window.add(detail_container, weight=3)
        
        self.create_detail_widgets(detail_container)
        self.create_log_section(main_frame)
        self.create_context_menu()
        
        self.set_detail_widgets_state(tk.DISABLED)

    def _auto_commit_details(self, event=None):
        """Callback to commit changes from detail widgets automatically."""
        if self._is_updating_vars:
            return
        self.commit_ui_to_data()

    def create_detail_widgets(self, parent):
        frame = ttk_bs.Frame(parent)
        frame.pack(fill=BOTH, expand=True)
        
        settings_frame = ttk_bs.Frame(frame)
        settings_frame.pack(fill=X, expand=True)
        self.create_basic_settings_widgets(settings_frame)

        self.create_exclusions_widgets(frame)

        self.advanced_options_container = ttk_bs.Frame(frame)
        self.advanced_options_container.pack(fill=BOTH, expand=True, pady=(10, 0))
        self.create_advanced_options_widgets(self.advanced_options_container)
        
        self.detail_vars['tool'].trace_add("write", self.on_tool_change)


    def create_basic_settings_widgets(self, parent):
        self.detail_vars.update({
            'enabled': tk.BooleanVar(), 'source': tk.StringVar(), 'destination': tk.StringVar(),
            'tool': tk.StringVar(), 'mode': tk.StringVar()
        })
        self.detail_widgets['enabled_check'] = ttk_bs.Checkbutton(parent, text="Enabled", variable=self.detail_vars['enabled'], command=self._auto_commit_details)
        self.detail_widgets['enabled_check'].grid(row=0, column=0, columnspan=3, sticky=W, pady=(0, 10))
        ttk_bs.Label(parent, text="Source:").grid(row=1, column=0, sticky=W, padx=(0, 5))
        self.detail_widgets['source_entry'] = ttk_bs.Entry(parent, textvariable=self.detail_vars['source'], width=40)
        self.detail_widgets['source_entry'].grid(row=1, column=1, sticky=EW)
        self.detail_widgets['source_entry'].bind("<FocusOut>", self._auto_commit_details)
        self.detail_widgets['source_browse'] = ttk_bs.Button(parent, text="Browse", command=lambda: self.browse_directory(self.detail_vars['source']), bootstyle=OUTLINE)
        self.detail_widgets['source_browse'].grid(row=1, column=2, padx=(5, 0))
        ttk_bs.Label(parent, text="Destination:").grid(row=2, column=0, sticky=W, padx=(0, 5), pady=(5, 0))
        self.detail_widgets['dest_entry'] = ttk_bs.Entry(parent, textvariable=self.detail_vars['destination'], width=40)
        self.detail_widgets['dest_entry'].grid(row=2, column=1, sticky=EW, pady=(5, 0))
        self.detail_widgets['dest_entry'].bind("<FocusOut>", self._auto_commit_details)
        self.detail_widgets['dest_browse'] = ttk_bs.Button(parent, text="Browse", command=lambda: self.browse_directory(self.detail_vars['destination']), bootstyle=OUTLINE)
        self.detail_widgets['dest_browse'].grid(row=2, column=2, padx=(5, 0), pady=(5, 0))
        ttk_bs.Label(parent, text="Tool:").grid(row=3, column=0, sticky=W, padx=(0, 5), pady=(5, 0))
        self.detail_widgets['tool_combo'] = ttk_bs.Combobox(parent, textvariable=self.detail_vars['tool'], values=["robocopy", "rclone"], state="readonly", width=15)
        self.detail_widgets['tool_combo'].grid(row=3, column=1, sticky=W, pady=(5, 0))
        ttk_bs.Label(parent, text="Mode:").grid(row=4, column=0, sticky=W, padx=(0, 5), pady=(5, 0))
        self.detail_widgets['mode_combo'] = ttk_bs.Combobox(parent, textvariable=self.detail_vars['mode'], state="readonly", width=15)
        self.detail_widgets['mode_combo'].grid(row=4, column=1, sticky=W, pady=(5, 0))
        self.detail_widgets['mode_combo'].bind("<<ComboboxSelected>>", self._auto_commit_details)
        parent.grid_columnconfigure(1, weight=1)

    def create_exclusions_widgets(self, parent):
        exclusions_header = ttk_bs.Frame(parent)
        exclusions_header.pack(fill=X, pady=(10, 0))
        ttk_bs.Label(exclusions_header, text="Exclusions").pack(side=LEFT)
        help_label = ttk_bs.Label(exclusions_header, text=" ( ?)", bootstyle="info")
        help_label.pack(side=LEFT, padx=(5,0))
        ToolTip(help_label, text=r"""Exclusion Rules:
- One pattern per line.
- Directories: End with a slash (e.g., build/, node_modules\).
- Wildcard Files: Use * (e.g., *.log, *.tmp).
- Rules are adapted for robocopy and rclone.""", bootstyle="info")
        
        exclusions_frame = ttk_bs.Frame(parent)
        exclusions_frame.pack(fill=BOTH, expand=True)
        self.detail_widgets['exclusions_text'] = scrolledtext.ScrolledText(exclusions_frame, height=4, wrap=tk.WORD, font=("Consolas", 9))
        self.detail_widgets['exclusions_text'].pack(fill=BOTH, expand=True)
        self.detail_widgets['exclusions_text'].bind("<FocusOut>", self._auto_commit_details)
        self.placeholder = "# Examples:\ntarget/\n*.log\n.cache/"
        self.detail_widgets['exclusions_text'].tag_config("placeholder", foreground="grey")
        self.set_exclusions_placeholder()

    def create_advanced_options_widgets(self, parent):
        self.robocopy_options_frame = ttk_bs.LabelFrame(parent, text="Advanced Robocopy Options", padding=10)
        self.detail_vars.update({'threads': tk.IntVar(), 'retries': tk.IntVar(), 'wait': tk.IntVar()})
        robocopy_values = {'threads': [1, 2, 4, 8, 12, 16, 24, 32, 64, 128], 'retries': [0, 1, 2, 3, 5, 10], 'wait': [1, 3, 5, 10, 15, 30, 60]}
        ttk_bs.Label(self.robocopy_options_frame, text="Threads:").grid(row=0, column=0, sticky=W, padx=5)
        self.detail_widgets['threads_combo'] = ttk_bs.Combobox(self.robocopy_options_frame, textvariable=self.detail_vars['threads'], width=5, state="readonly", values=robocopy_values['threads'])
        self.detail_widgets['threads_combo'].grid(row=0, column=1, sticky=W)
        self.detail_widgets['threads_combo'].bind("<<ComboboxSelected>>", self._auto_commit_details)
        ToolTip(self.robocopy_options_frame.grid_slaves(row=0, column=0)[0], "Number of threads to use (/MT)", bootstyle="info")
        ttk_bs.Label(self.robocopy_options_frame, text="Retries:").grid(row=0, column=2, sticky=W, padx=5)
        self.detail_widgets['retries_combo'] = ttk_bs.Combobox(self.robocopy_options_frame, textvariable=self.detail_vars['retries'], width=5, state="readonly", values=robocopy_values['retries'])
        self.detail_widgets['retries_combo'].grid(row=0, column=3, sticky=W)
        self.detail_widgets['retries_combo'].bind("<<ComboboxSelected>>", self._auto_commit_details)
        ToolTip(self.robocopy_options_frame.grid_slaves(row=0, column=2)[0], "Retries on failed copies (/R)", bootstyle="info")
        ttk_bs.Label(self.robocopy_options_frame, text="Wait (s):").grid(row=0, column=4, sticky=W, padx=5)
        self.detail_widgets['wait_combo'] = ttk_bs.Combobox(self.robocopy_options_frame, textvariable=self.detail_vars['wait'], width=5, state="readonly", values=robocopy_values['wait'])
        self.detail_widgets['wait_combo'].grid(row=0, column=5, sticky=W)
        self.detail_widgets['wait_combo'].bind("<<ComboboxSelected>>", self._auto_commit_details)
        ToolTip(self.robocopy_options_frame.grid_slaves(row=0, column=4)[0], "Wait time between retries in seconds (/W)", bootstyle="info")

        self.rclone_options_frame = ttk_bs.LabelFrame(parent, text="Advanced Rclone Options", padding=10)
        self.detail_vars.update({'checkers': tk.IntVar(), 'transfers': tk.IntVar(), 'multi_thread_streams': tk.IntVar()})
        rclone_values = {'checkers': [4, 8, 16, 32, 64], 'transfers': [2, 4, 8, 16, 32], 'multi_thread_streams': [0, 1, 2, 4, 8, 16]}
        ttk_bs.Label(self.rclone_options_frame, text="Checkers:").grid(row=0, column=0, sticky=W, padx=5)
        self.detail_widgets['checkers_combo'] = ttk_bs.Combobox(self.rclone_options_frame, textvariable=self.detail_vars['checkers'], width=5, state="readonly", values=rclone_values['checkers'])
        self.detail_widgets['checkers_combo'].grid(row=0, column=1, sticky=W)
        self.detail_widgets['checkers_combo'].bind("<<ComboboxSelected>>", self._auto_commit_details)
        ToolTip(self.rclone_options_frame.grid_slaves(row=0, column=0)[0], "Number of parallel checkers", bootstyle="info")
        ttk_bs.Label(self.rclone_options_frame, text="Transfers:").grid(row=0, column=2, sticky=W, padx=5)
        self.detail_widgets['transfers_combo'] = ttk_bs.Combobox(self.rclone_options_frame, textvariable=self.detail_vars['transfers'], width=5, state="readonly", values=rclone_values['transfers'])
        self.detail_widgets['transfers_combo'].grid(row=0, column=3, sticky=W)
        self.detail_widgets['transfers_combo'].bind("<<ComboboxSelected>>", self._auto_commit_details)
        ToolTip(self.rclone_options_frame.grid_slaves(row=0, column=2)[0], "Number of parallel transfers", bootstyle="info")
        ttk_bs.Label(self.rclone_options_frame, text="Streams:").grid(row=0, column=4, sticky=W, padx=5)
        self.detail_widgets['multi_thread_streams_combo'] = ttk_bs.Combobox(self.rclone_options_frame, textvariable=self.detail_vars['multi_thread_streams'], width=5, state="readonly", values=rclone_values['multi_thread_streams'])
        self.detail_widgets['multi_thread_streams_combo'].grid(row=0, column=5, sticky=W)
        self.detail_widgets['multi_thread_streams_combo'].bind("<<ComboboxSelected>>", self._auto_commit_details)
        ToolTip(self.rclone_options_frame.grid_slaves(row=0, column=4)[0], "Multi-thread streams per transfer (0 to disable)", bootstyle="info")

    def on_tool_change(self, *args):
        if self._is_updating_vars: return
        self.update_mode_options()
        self.toggle_advanced_options()
        self.commit_ui_to_data()

    def commit_ui_to_data(self):
        if self.selected_pair_index is None or self.selected_pair_index >= len(self.pairs):
            return

        try:
            pair = self.pairs[self.selected_pair_index]
            
            # Update basic info from vars
            for key, var in self.detail_vars.items():
                is_opt = key in ['threads', 'retries', 'wait', 'checkers', 'transfers', 'multi_thread_streams']
                try:
                    value = var.get()
                    if is_opt:
                        if 'tool_options' not in pair: pair['tool_options'] = {}
                        pair['tool_options'][key] = value
                    else:
                        pair[key] = value
                except (KeyError, tk.TclError): pass # Ignore errors for irrelevant vars

            # Update exclusions from text widget
            exclusions_text = self.detail_widgets['exclusions_text'].get("1.0", tk.END).strip()
            if exclusions_text == self.placeholder:
                pair['exclusions'] = []
            else:
                pair['exclusions'] = [line.strip() for line in exclusions_text.split('\n') if line.strip()]
            
            # After committing, update the listbox entry to reflect any name change
            self.update_listbox_entry(self.selected_pair_index, select_it=False)
        except Exception as e: self.log_message(f"Error committing changes: {e}", "ERROR")

    def toggle_advanced_options(self):
        tool = self.detail_vars['tool'].get()
        if tool == 'robocopy':
            self.rclone_options_frame.pack_forget()
            self.robocopy_options_frame.pack(fill=X, expand=True)
        elif tool == 'rclone':
            self.robocopy_options_frame.pack_forget()
            self.rclone_options_frame.pack(fill=X, expand=True)
        else:
            self.robocopy_options_frame.pack_forget()
            self.rclone_options_frame.pack_forget()

    def display_pair_details(self):
        if self.selected_pair_index is None: return
        self._is_updating_vars = True
        try:
            pair = self.pairs[self.selected_pair_index]
            opts = pair.get('tool_options', {})

            self.detail_vars['enabled'].set(pair.get("enabled", True))
            self.detail_vars['source'].set(pair.get("source", ""))
            self.detail_vars['destination'].set(pair.get("destination", ""))
            self.detail_vars['tool'].set(pair.get("tool", "robocopy"))
            
            self.update_mode_options()
            self.detail_vars['mode'].set(pair.get("mode", "MIR"))
            
            defaults = {'threads': 16, 'retries': 3, 'wait': 5, 'checkers': 16, 'transfers': 8, 'multi_thread_streams': 4}
            for key, default_val in defaults.items():
                self.detail_vars[key].set(opts.get(key, default_val))

            exclusions = pair.get("exclusions", [])
            exclusions_text = self.detail_widgets['exclusions_text']
            exclusions_text.delete("1.0", tk.END)
            if exclusions:
                exclusions_text.insert("1.0", "\n".join(exclusions))
            else:
                self.set_exclusions_placeholder(force=True)
        finally:
            self._is_updating_vars = False
        
        self.set_detail_widgets_state(tk.NORMAL)
        self.toggle_advanced_options()

    def add_pair(self):
        self.commit_ui_to_data()
        new_pair = {"source": "New Pair", "destination": "", "tool": "robocopy", "mode": "MIR", "enabled": True, "status": "Idle", "exclusions": [], "tool_options": {}}
        self.pairs.append(new_pair)
        new_index = len(self.pairs) - 1
        self.update_listbox_entry(new_index, select_it=True)
        self.on_pair_select(None)
        self.save_config_to_file()
        self.log_message("Added a new sync pair.", "INFO")

    def remove_selected_pair(self):
        if self.selected_pair_index is None:
            messagebox.showwarning("Warning", "No pair selected to remove.")
            return
        
        current_index = self.selected_pair_index
        self.pairs.pop(current_index)
        self.pair_listbox.delete(current_index)
        
        self.selected_pair_index = None
        self.set_detail_widgets_state(tk.DISABLED)
        self._is_updating_vars = True
        try:
            for var in self.detail_vars.values():
                if isinstance(var, tk.BooleanVar): var.set(False)
                else: var.set("")
            self.set_exclusions_placeholder(force=True)
        finally:
            self._is_updating_vars = False
            
        self.save_config_to_file()
        self.log_message("Removed a sync pair.", "INFO")

    def set_exclusions_placeholder(self, force=False):
        text_widget = self.detail_widgets['exclusions_text']
        if force or text_widget.get("1.0", "end-1c") == "":
            text_widget.delete("1.0", tk.END)
            text_widget.insert("1.0", self.placeholder, "placeholder")
            
    def on_exclusions_focus_in(self, event=None):
        text_widget = self.detail_widgets['exclusions_text']
        if text_widget.get("1.0", "end-1c") == self.placeholder:
            text_widget.delete("1.0", tk.END)
            text_widget.tag_remove("placeholder", "1.0", tk.END)
            
    def on_exclusions_focus_out(self, event=None):
        self.set_exclusions_placeholder()

    def create_log_section(self, parent):
        log_frame = ttk_bs.LabelFrame(parent, text="Logs", padding=10)
        log_frame.pack(fill=BOTH, expand=True, pady=(10, 0))
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD, font=("Consolas", 9), state=tk.DISABLED)
        self.log_text.pack(fill=BOTH, expand=True)
        self.log_text.tag_config("INFO", foreground=self.style.colors.fg)
        self.log_text.tag_config("SUCCESS", foreground=self.style.colors.success)
        self.log_text.tag_config("ERROR", foreground=self.style.colors.danger)
        self.log_text.tag_config("WARNING", foreground=self.style.colors.warning)
        
    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Sync This Pair Now", command=self.sync_selected_pair)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Open Source Folder", command=lambda: self.open_selected_folder('source'))
        self.context_menu.add_command(label="Open Destination Folder", command=lambda: self.open_selected_folder('destination'))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Duplicate Pair", command=self.duplicate_selected_pair)
        
    def show_context_menu(self, event):
        selection = self.pair_listbox.nearest(event.y)
        if selection != -1:
            self.commit_ui_to_data()
            self.pair_listbox.selection_clear(0, tk.END)
            self.pair_listbox.selection_set(selection)
            self.on_pair_select(None)
            self.context_menu.post(event.x_root, event.y_root)
            
    def sync_selected_pair(self):
        if self.selected_pair_index is None: return
        self.commit_ui_to_data()
        self.save_config_to_file()
        pair = self.pairs[self.selected_pair_index]
        self.log_message(f"Manual sync triggered for '{os.path.basename(pair.get('source'))}'.", "INFO")
        self.sync_manager.run_single_pair(pair)
        
    def open_selected_folder(self, path_type):
        if self.selected_pair_index is None: return
        self.commit_ui_to_data()
        pair = self.pairs[self.selected_pair_index]
        path_to_open = pair.get(path_type)
        if not path_to_open:
            self.log_message(f"Cannot open folder: {path_type} path is empty.", "WARNING")
            return
        try: os.startfile(os.path.normpath(path_to_open))
        except Exception as e: self.log_message(f"Failed to open '{path_to_open}': {e}", "ERROR")
        
    def duplicate_selected_pair(self):
        if self.selected_pair_index is None: return
        self.commit_ui_to_data()
        original_pair = self.pairs[self.selected_pair_index]
        new_pair = copy.deepcopy(original_pair)
        source_path = new_pair.get("source", "")
        if source_path: new_pair["source"] = f"{source_path} (Copy)"
        self.pairs.insert(self.selected_pair_index + 1, new_pair)
        self.update_listbox_entry(self.selected_pair_index + 1, select_it=True)
        self.save_config_to_file()
        self.log_message(f"Duplicated pair: {os.path.basename(original_pair.get('source'))}", "INFO")
        
    def log_message(self, message, level="INFO"):
        self.log_text.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] ", "INFO")
        self.log_text.insert(tk.END, f"{message}\n", level)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def poll_messages(self):
        try:
            while True:
                message_type, *args = self.message_queue.get_nowait()
                if message_type == "log": self.log_message(args[0], args[1])
                elif message_type == "status":
                    status_text, original_pair_data = args
                    for i, p in enumerate(self.pairs):
                        if p['source'] == original_pair_data['source'] and p['destination'] == original_pair_data['destination']:
                            p["status"] = status_text
                            self.update_listbox_entry(i, select_it=False)
                            break
                elif message_type == "error": messagebox.showerror("Sync Error", args[0])
        except queue.Empty: pass
        self.root.after(100, self.poll_messages)
        
    def start_sync(self):
        self.commit_ui_to_data()
        self.save_config_to_file()
        if self.sync_manager.is_running():
            self.log_message("Sync cycle is already running.", "WARNING")
            return
        interval = self.validate_interval()
        valid_pairs = self.validate_pairs()
        if valid_pairs is None: return
        if not valid_pairs:
            self.log_message("No enabled pairs to sync.", "WARNING")
            return
        self.sync_manager.start_cycle(list(valid_pairs), interval)
        
    def stop_sync(self):
        if self.sync_manager.is_running(): self.sync_manager.stop_cycle()
        else: self.log_message("Sync cycle is not running.", "INFO")
        
    def on_closing(self):
        self.commit_ui_to_data()
        self.save_config_to_file()
        if self.sync_manager: self.sync_manager.stop_cycle()
        self.root.destroy()
        
    def create_control_panel(self, parent):
        control_frame = ttk_bs.LabelFrame(parent, text="Control Panel", padding=10)
        control_frame.pack(fill=X)
        settings_frame = ttk_bs.Frame(control_frame)
        settings_frame.pack(fill=X, expand=True, pady=(0, 10))
        ttk_bs.Label(settings_frame, text="Theme:").pack(side=LEFT, padx=(0, 5))
        self.theme_var = tk.StringVar(value=self.current_theme)
        theme_combo = ttk_bs.Combobox(settings_frame, textvariable=self.theme_var, values=list(self.available_themes), state="readonly", width=15)
        theme_combo.pack(side=LEFT, padx=(0, 20))
        theme_combo.bind("<<ComboboxSelected>>", self.change_theme)
        ttk_bs.Label(settings_frame, text="Interval (s):").pack(side=LEFT, padx=(0, 5))
        self.interval_var = tk.StringVar(value="60")
        interval_entry = ttk_bs.Entry(settings_frame, textvariable=self.interval_var, width=10)
        interval_entry.pack(side=LEFT, padx=(0, 20))
        button_frame = ttk_bs.Frame(control_frame)
        button_frame.pack(fill=X, expand=True)
        ttk_bs.Button(button_frame, text="Add Pair", command=self.add_pair, bootstyle=SUCCESS).pack(side=LEFT, padx=(0, 10))
        ttk_bs.Button(button_frame, text="Remove Selected", command=self.remove_selected_pair, bootstyle=DANGER).pack(side=LEFT, padx=(0, 10))
        ttk_bs.Button(button_frame, text="Start Sync", command=self.start_sync, bootstyle=PRIMARY).pack(side=LEFT, padx=(0, 10))
        ttk_bs.Button(button_frame, text="Stop Sync", command=self.stop_sync, bootstyle=WARNING).pack(side=LEFT, padx=(0, 10))
        
    def set_detail_widgets_state(self, state):
        for widget_key, widget in self.detail_widgets.items():
            if widget_key != 'frame':
                try: widget.config(state=state)
                except tk.TclError: pass
        self.detail_widgets['exclusions_text'].config(state=state)
        
    def update_mode_options(self, *args):
        tool = self.detail_vars['tool'].get()
        current_mode = self.detail_vars['mode'].get()
        if tool == "robocopy":
            self.detail_widgets['mode_combo']['values'] = ["MIR", "E-Copy"]
            if current_mode not in ["MIR", "E-Copy"]: self.detail_vars['mode'].set("MIR")
        elif tool == "rclone":
            self.detail_widgets['mode_combo']['values'] = ["sync", "copy"]
            if current_mode not in ["sync", "copy"]: self.detail_vars['mode'].set("sync")
            
    def on_pair_select(self, event):
        selected_indices = self.pair_listbox.curselection()
        if not selected_indices:
            self.commit_ui_to_data()
            self.selected_pair_index = None
            self.set_detail_widgets_state(tk.DISABLED)
            return
            
        new_index = selected_indices[0]
        if self.selected_pair_index == new_index:
            return

        self.commit_ui_to_data()
        self.selected_pair_index = new_index
        self.display_pair_details()
        
    def update_listbox_entry(self, index, select_it=False):
        if index is None or index >= len(self.pairs): return
        pair = self.pairs[index]
        source_path = pair.get("source", "New Pair")
        name = os.path.basename(source_path) if source_path else "New Pair"
        status = pair.get("status", "Idle")
        display_text = f"{name}  -  [{status}]"
        
        is_selected = self.pair_listbox.curselection() and self.pair_listbox.curselection()[0] == index

        self._is_updating_vars = True
        self.pair_listbox.delete(index)
        self.pair_listbox.insert(index, display_text)
        if select_it:
            self.pair_listbox.selection_clear(0, tk.END)
            self.pair_listbox.selection_set(index)
        elif is_selected:
             self.pair_listbox.selection_set(index)
        self._is_updating_vars = False
        
    def load_config(self):
        try:
            if not os.path.exists(self.config_file):
                self.log_message("No config file found. Add a pair to start.", "INFO")
                return
            with open(self.config_file, 'r', encoding='utf-8') as f: config = json.load(f)
            
            self.interval_var.set(config.get("interval", "60"))
            
            theme = config.get("theme", "darkly")
            if theme in self.available_themes:
                self.current_theme = theme
                self.theme_var.set(theme)
                self.style.theme_use(theme)
            self.pairs = config.get("pairs", [])
            self.pair_listbox.delete(0, tk.END)
            for i in range(len(self.pairs)):
                self.update_listbox_entry(i, select_it=False)
            
            if self.pairs:
                self.pair_listbox.selection_set(0)
                self.on_pair_select(None)

            self.log_message("Configuration loaded successfully.", "SUCCESS")
        except (json.JSONDecodeError, Exception) as e:
            self.log_message(f"Failed to load config: {e}. A new config will be created.", "ERROR")
            self.pairs = []
            
    def browse_directory(self, var):
        directory = filedialog.askdirectory()
        if directory:
            var.set(str(Path(directory)))
        
    def validate_interval(self):
        try:
            interval = int(self.interval_var.get())
            if interval > 0: return interval
        except ValueError: pass
        self.interval_var.set("60")
        messagebox.showwarning("Invalid Interval", "Interval must be a positive number. Defaulting to 60 seconds.")
        return 60
        
    def validate_pairs(self):
        valid_pairs = []
        for i, pair in enumerate(self.pairs):
            if not pair.get("enabled", False): continue
            source, dest, tool = pair.get("source"), pair.get("destination"), pair.get("tool")
            if not source or not dest:
                messagebox.showerror("Validation Error", f"Pair '{self.pair_listbox.get(i)}' has an empty source or destination.")
                return None
            if tool == "robocopy" and not os.path.isdir(source):
                messagebox.showerror("Validation Error", f"Source directory for pair '{self.pair_listbox.get(i)}' does not exist: {source}")
                return None
            if tool == "rclone" and not shutil.which("rclone"):
                messagebox.showerror("Validation Error", "rclone executable not found in system PATH.")
                return None
            valid_pairs.append(pair)
        return valid_pairs
        
    def save_config_to_file(self):
        config = {"interval": self.interval_var.get(), "theme": self.current_theme, "pairs": self.pairs}
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f: json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e: self.log_message(f"Error saving configuration: {e}", "ERROR")
        
    def change_theme(self, event=None):
        self.commit_ui_to_data()
        new_theme = self.theme_var.get()
        if new_theme != self.current_theme:
            self.current_theme = new_theme
            self.style.theme_use(new_theme)
            self.log_text.tag_config("INFO", foreground=self.style.colors.fg)
            self.log_text.tag_config("SUCCESS", foreground=self.style.colors.success)
            self.log_text.tag_config("ERROR", foreground=self.style.colors.danger)
            self.log_text.tag_config("WARNING", foreground=self.style.colors.warning)
            self.save_config_to_file()
            self.log_message(f"Theme changed to: {new_theme}", "INFO")
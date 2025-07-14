import tkinter as tk
from gui import SyncApp
import sys
import os

def main():
    # Set up for PyInstaller compatibility
    if getattr(sys, 'frozen', False):
        # Running from PyInstaller bundle
        app_path = sys._MEIPASS
    else:
        # Running from source
        app_path = os.path.dirname(os.path.abspath(__file__))
    
    # Initialize main window
    root = tk.Tk()
    root.title("Directory Sync Tool")
    root.geometry("1200x800")
    root.minsize(1000, 600)
    
    # Set icon if available
    try:
        icon_path = os.path.join(app_path, "DirectorySync.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception as e:
        print(f"Could not load icon: {e}")
    
    # Initialize application
    app = SyncApp(root)
    
    # Start the GUI
    root.mainloop()

if __name__ == "__main__":
    main()
# Directory Sync Tool

**Directory Sync Tool** is a graphical interface (GUI) that simplifies the use of Windows' built-in **Robust File Copy (Robocopy)** utility for efficient folder synchronization on Windows systems.  
It also offers optional integration with **Rclone**, making it easier to synchronize with cloud storage services by leveraging Rclone’s powerful capabilities.

## Features

- **Multiple Folder Pairs**: Add, remove, and configure multiple source-destination folder pairs.
- **Rclone Support**: Seamlessly integrate with [Rclone](https://rclone.org/) for cloud synchronization.
- **Robocopy-Based Sync**: Leverages Robocopy for high-speed, reliable local sync on Windows.
- **Multi-threaded Performance**: Both Robocopy and Rclone are configured by default to use multi-threading, accelerating synchronization for both local and cloud transfers.
- **Rust Project Detection**: Automatically executes `cargo clean` if the source directory is detected as a Rust project.
- **Repeat Interval Configuration**: Set the synchronization interval (in seconds) for periodic syncs.
- **Save & Load Configurations**: Save folder pair settings and sync intervals to a `config.json` file.
- **Dark Mode UI**: Modern, user-friendly interface with dark theme, folder selection dialog, and detailed logging panel.

---

## Requirements

- Python 3.x (if running via `main.py`)
- [Rclone](https://rclone.org/) (required for cloud sync)
- *(Optional)* Cargo (required for Rust project cleanup)

---

## How to Use

1. **Install necessary tools** (Rclone, Cargo if needed).
2. **Run the application**:
   - Launch `DirectorySync.exe`, or run the script directly:
     ```bash
     python main.py
     ```


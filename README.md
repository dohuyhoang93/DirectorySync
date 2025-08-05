# Directory Sync Tool

A modern, user-friendly GUI for synchronizing directories using robocopy, rclone, or rsync.

<p align="center">
  <img src="./docs/assets/img/DRST_screenshot.png" alt="screenshot" width="700">
</p>

## Features

- **Modern UI**: Built with `ttkbootstrap` for a contemporary look and feel with theme support.
- **Multiple Sync Engines**:
    - **Robocopy**: For high-performance local and network sync on Windows.
    - **Rclone**: For syncing with over 40 cloud storage providers.
    - **Rsync**: For reliable and standard syncing on Linux and macOS.
- **Thread-Safe**: Sync operations run in the background without freezing the UI.
- **Configuration Management**: Save and load multiple sync configurations to a `config.json` file.
- **Flexible Modes**: Supports common modes for each tool (e.g., MIR, sync, copy).
- **Advanced Options**: Configure threads, retries, transfers, and other tool-specific settings.
- **Detailed Logging**: A dedicated log area shows real-time status and errors.

---

## Installation and Usage

This guide provides instructions for setting up a development environment and for building a distributable application.

### 1. Prerequisites

Before you begin, ensure you have the following installed on your system.

- **Python 3.7+** and **pip**.

- **External Sync Tools**: The application relies on external command-line tools. The `setup.py` script will check for them when building.
    - **On Windows**:
        - `robocopy`: Included with Windows by default.
        - `rclone`: **Required.** Download from [rclone.org](https://rclone.org/downloads/) and add its location to your system's PATH.
    - **On Linux / macOS**:
        - `rsync`: Usually pre-installed. If not, install it via your system's package manager (e.g., `sudo apt install rsync`).
        - `rclone`: **Required.** Install using the official script: `sudo -v ; curl https://rclone.org/install.sh | sudo bash`.

### 2. Setting up the Development Environment

To set up the project for development, clone the repository and use `pip` to install the project in "editable" mode. This will install all required Python libraries and allow you to test your code changes immediately.

```bash
# Clone the repository
git clone <repository_url>
cd DirectorySync

# Install dependencies and the project in editable mode
pip install -e .
```

### 3. Running the Application from Source

After setting up the environment, you can run the application directly with:

```bash
python main.py
```

### 4. Building a Standalone Executable

This project uses `setup.py` and `PyInstaller` to create a standalone executable file that can be run without needing to install Python or any libraries.

**First, ensure `pyinstaller` is installed:**
```bash
pip install pyinstaller
```

**Then, use the custom `build_binary` command:**

- **To build a one-directory bundle (Recommended for testing):**
  This creates a folder in the `dist/` directory containing the executable and all its dependencies.
  ```bash
  python setup.py build_binary
  ```

- **To build a single-file executable (Best for distribution):**
  This creates a single `.exe` or binary file in the `dist/` directory. It may start up slightly slower than the one-directory version.
  ```bash
  python setup.py build_binary --onefile
  ```

The final application will be located in the `dist/` folder.

---

## How It Works

- **GUI (`gui.py`):** Manages the entire user interface, including widgets, event handling, and configuration.
- **Sync Manager (`sync_manager.py`):** Handles the logic for building and running the `robocopy`, `rclone`, or `rsync` commands in background threads.
- **Configuration (`config.json`):** Stores all sync pairs and application settings. This file is loaded on startup and saved on exit.

## License

This project is open source. See the `LICENSE` file for details.
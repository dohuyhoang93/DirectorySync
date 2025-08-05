# Gemini Project Context: Directory Sync Tool

## Project Overview

This project is a graphical user interface (GUI) application for synchronizing directories. It is built with Python using the `tkinter` and `ttkbootstrap` libraries for the UI. The application provides a user-friendly way to manage and run synchronization tasks using either `robocopy` (for local and network file transfers on Windows) or `rclone` (for cloud storage synchronization).

The core functionality is split into three main files:
-   `main.py`: The entry point of the application, responsible for initializing the main window and the application class.
-   `gui.py`: Manages the entire graphical user interface, including the main window, widgets, event handling, and configuration management. It uses `ttkbootstrap` for a modern look and feel.
-   `sync_manager.py`: Handles the background synchronization processes. It runs `robocopy` or `rclone` commands in separate threads to avoid freezing the UI, and communicates back to the GUI using a queue.

The application supports saving and loading synchronization configurations from a `config.json` file, allowing users to persist their settings and sync pairs.

## Building and Running

### Prerequisites

-   Python 3.7+
-   `robocopy` (included with Windows)
-   `rclone` (must be downloaded from [rclone.org](https://rclone.org) and added to the system's PATH)

### Installation

1.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

To run the application from the source code, execute the following command in the project's root directory:

```bash
python main.py
```

### Building a Standalone Executable

A standalone executable can be created using `pyinstaller`. This bundles the application and its dependencies into a single `.exe` file.

1.  Install `pyinstaller`:
    ```bash
    pip install pyinstaller
    ```
2.  Run the build command:
    ```bash
    pyinstaller --onefile --windowed --icon=DirectorySync.ico main.py
    ```
    The executable will be located in the `dist` directory.

## Development Conventions

-   **UI Framework**: The application uses `tkinter` for the basic GUI structure and `ttkbootstrap` for modern widgets and themes.
-   **Concurrency**: Synchronization tasks are performed in background threads (`threading` module) to keep the UI responsive. Communication between the background threads and the GUI is handled safely using a `queue.Queue`.
-   **Configuration**: Application settings and sync pairs are stored in a `config.json` file in the root directory. This file is loaded on startup and saved when changes are made or when the application is closed.
-   **Code Structure**:
    -   `main.py`: Application entry point.
    -   `gui.py`: All UI-related code.
    -   `sync_manager.py`: Logic for running external synchronization tools (`robocopy`, `rclone`).
-   **Error Handling**: The application includes error handling for file operations, configuration loading, and process execution. Errors and status messages are displayed in a dedicated log area in the UI.
-   **Cross-Platform considerations**: While `robocopy` is Windows-specific, the use of `rclone` allows for cross-platform synchronization capabilities, although the GUI itself is built with `tkinter`. The code in `sync_manager.py` checks the platform to correctly terminate processes.

# setup.py
import sys
import os
import shutil
import subprocess
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py

# --- Metadata ---
NAME = 'DirectorySyncTool'
VERSION = '1.0.0'
DESCRIPTION = 'A GUI tool for synchronizing directories using robocopy, rclone, or rsync.'
AUTHOR = 'Gemini'
ENTRY_POINT = 'main.py'
ICON_FILE = 'DirectorySync.ico'
REQUIREMENTS_FILE = 'requirements.txt'

# --- Helper Functions ---

def read_requirements():
    """Reads the requirements.txt file and returns a list of dependencies."""
    with open(REQUIREMENTS_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

def check_external_dependencies():
    """
    Checks for required command-line tools (rclone, rsync).
    If a tool is missing, it prints installation instructions and exits.
    """
    print("--- Checking for external dependencies ---")
    is_windows = sys.platform == "win32"
    
    # 1. Check for rclone (required on all OS)
    if not shutil.which("rclone"):
        print("\n[ERROR] rclone is not installed or not in the system's PATH.")
        if is_windows:
            print("Please download it from https://rclone.org/downloads/ and add it to your PATH.")
        else:
            print("Please install it using the official script:")
            print("  sudo -v ; curl https://rclone.org/install.sh | sudo bash")
        sys.exit(1)
    else:
        print("[OK] rclone found.")

    # 2. Check for rsync (required on Linux/macOS)
    if not is_windows:
        if not shutil.which("rsync"):
            print("\n[ERROR] rsync is not installed or not in the system's PATH.")
            if sys.platform == "darwin": # macOS
                 print("Please install it using Homebrew: brew install rsync")
            else: # Linux
                 print("Please install it using your system's package manager, for example:")
                 print("  sudo apt-get update && sudo apt-get install rsync  (for Debian/Ubuntu)")
                 print("  sudo dnf install rsync                          (for Fedora/CentOS)")
            sys.exit(1)
        else:
            print("[OK] rsync found.")
    
    print("--- All external dependencies are met. ---\\n")


class BuildBinaryCommand(build_py):
    """Custom command to build the application into a binary using PyInstaller."""
    
    description = 'Build the application into a binary (requires PyInstaller)'
    user_options = build_py.user_options + [
        ('onefile', None, 'Build as a single executable file.'),
        ('onedir', None, 'Build as a folder containing all dependencies (default).')
    ]

    def initialize_options(self):
        super().initialize_options()
        self.onefile = None
        self.onedir = None

    def finalize_options(self):
        super().finalize_options()
        # Default to onedir if no option is specified
        if self.onefile is None and self.onedir is None:
            self.onedir = True

    def run(self):
        # 1. First, check for external command-line tools
        check_external_dependencies()

        # 2. Ensure pyinstaller is installed
        try:
            import PyInstaller
        except ImportError:
            print("\n[ERROR] PyInstaller is not installed. Please install it first:")
            print(f"  {sys.executable} -m pip install pyinstaller")
            sys.exit(1)

        # 3. Build the PyInstaller command
        separator = ';' if sys.platform.startswith('win') else ':'
        command = [
            'pyinstaller',
            '--noconfirm', # Overwrite output directory without asking
            '--windowed',  # No console window for the GUI
            f'--icon={ICON_FILE}',
            f'--add-data={ICON_FILE}{separator}.',
            f'--name={NAME}',
            f'--distpath={os.path.abspath("dist")}',
            ENTRY_POINT
        ]

        if self.onefile:
            print("\n--- Building a single-file executable ---")
            command.append('--onefile')
        else:
            print("\n--- Building a one-directory bundle ---")
            # No extra flag needed for one-dir, it's the default

        # 4. Run the command
        print(f"Running command: {' '.join(command)}")
        try:
            subprocess.run(command, check=True)
            print("\n--- Build successful! ---")
            print(f"The output is in the '{os.path.abspath('dist')}' directory.")
        except subprocess.CalledProcessError as e:
            print(f"\n[ERROR] PyInstaller failed with exit code {e.returncode}.")
            sys.exit(1)
        except FileNotFoundError:
            print("\n[ERROR] 'pyinstaller' command not found. Is it installed and in your PATH?")
            sys.exit(1)


# --- Setup Configuration ---
setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    author=AUTHOR,
    packages=find_packages(),
    install_requires=read_requirements(),
    entry_points={
        'console_scripts': [
            'directorysync=main:main',
        ],
    },
    cmdclass={
        'build_binary': BuildBinaryCommand,
    },
)

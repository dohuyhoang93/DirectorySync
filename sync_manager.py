from operator import index
import threading
import time
import subprocess
import os
import queue
import signal
import sys

class SyncManager:
    def __init__(self, pairs, interval, message_queue):
        self.pairs = pairs
        self.interval = interval
        self.message_queue = message_queue
        self.running = False
        self.thread = None
        self.current_process = None
        
    def start(self):
        """Start the sync manager in a background thread"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._sync_loop, daemon=True)
            self.thread.start()
    
    def stop(self):
        """Stop the sync manager"""
        self.running = False
        
        # Terminate current process if running
        if self.current_process:
            try:
                if sys.platform == "win32":
                    # Windows
                    self.current_process.terminate()
                else:
                    # Unix-like systems
                    os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
                
                # Wait for process to terminate
                self.current_process.wait(timeout=5)
                
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate gracefully
                if sys.platform == "win32":
                    self.current_process.kill()
                else:
                    os.killpg(os.getpgid(self.current_process.pid), signal.SIGKILL)
                    
            except Exception as e:
                self._log(f"Error terminating process: {e}")
            
            finally:
                self.current_process = None
        
        self._log("Sync manager stopped")
    
    def is_running(self):
        """Check if sync manager is running"""
        return self.running
    
    def _sync_loop(self):
        """Main sync loop running in background thread"""
        while self.running:
            try:
                self._log("Starting sync cycle...")
                
                for index, pair in enumerate(self.pairs):
                    if not self.running:
                        break
                    
                    self._log(f"Syncing pair {index + 1}: {pair['source']} -> {pair['destination']}")
                    
                    # Reset meter for this pair
                    self.message_queue.put(("meter", index, 0))

                    # Simulate progress from 0% to 80%
                    for percent in range(1, 81):
                            self.message_queue.put(("meter", index, percent))
                            time.sleep(0.1)  # total ~1s animation
                    self._log(f"Pair {index + 1} completed successfully")

                    # Execute sync command
                    success = self._execute_sync(pair, index)
                    
                    if success:
                        # self.message_queue.put(("meter", index, 100))
                        # self._log(f"Pair {index + 1} completed successfully")
                        # Simulate progress from 81% to 100%
                        for percent in range(81, 101):
                            if not self.running:
                                break
                            self.message_queue.put(("meter", index, percent))
                            time.sleep(0.1)  # total ~1s animation
                        self._log(f"Pair {index + 1} completed successfully")
                    else:
                        self.message_queue.put(("error", index))
                        self._log(f"Pair {index + 1} failed")
                
                if self.running:
                    self.message_queue.put(("complete",))
                    self._log(f"Sync cycle completed. Next cycle in {self.interval} seconds...")
                    
                    # Wait for next cycle or until stopped
                    for _ in range(self.interval):
                        if not self.running:
                            break
                        time.sleep(1)
                
            except Exception as e:
                self._log(f"Error in sync loop: {e}")
                time.sleep(5)  # Wait before retrying
    
    def _execute_sync(self, pair, index):
        """Execute sync command for a pair"""
        try:
            # Generate command based on tool and mode
            command = self._generate_command(pair)
            
            if not command:
                self._log(f"Failed to generate command for pair {index + 1}")
                return False
            
            self._log(f"Executing: {command}")
            
            # Check for Rust project and run cargo clean if needed
            if pair['tool'] == 'robocopy' and self._is_rust_project(pair['source']):
                self._run_cargo_clean(pair['source'])
            
            # Execute the command
            self.current_process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            # Wait for completion
            stdout, stderr = self.current_process.communicate()
            returncode = self.current_process.returncode
            
            # Process results
            if returncode == 0:
                self._log(f"Command completed successfully")
                if stdout.strip():
                    self._log(f"Output: {stdout.strip()}")
                return True
            else:
                self._log(f"Command failed with code {returncode}")
                if stderr.strip():
                    self._log(f"Error: {stderr.strip()}")
                return False
                
        except Exception as e:
            self._log(f"Exception during sync execution: {e}")
            return False
        finally:
            self.current_process = None
    
    def _generate_command(self, pair):
        """Generate sync command based on tool and mode"""
        source = pair['source']
        destination = pair['destination']
        tool = pair['tool']
        mode = pair['mode']
        
        if tool == 'robocopy':
            return self._generate_robocopy_command(source, destination, mode)
        elif tool == 'rclone':
            return self._generate_rclone_command(source, destination, mode)
        else:
            self._log(f"Unknown tool: {tool}")
            return None
    
    def _generate_robocopy_command(self, source, destination, mode):
        """Generate robocopy command"""
        base_cmd = f'robocopy "{source}" "{destination}"'
        
        if mode == "MIR":
            # Mirror mode - exact copy with deletions
            cmd = f'{base_cmd} /MIR /MT:16 /Z /COPY:DAT /R:3 /W:10 /NP'
        elif mode == "E-Copy":
            # Copy subdirectories including empty ones
            cmd = f'{base_cmd} /E /MT:16 /Z /COPY:DAT /R:3 /W:10 /NP'
        else:
            # Default robocopy
            cmd = f'{base_cmd} /MT:16 /Z /COPY:DAT /R:3 /W:10 /NP'
        
        return cmd
    
    def _generate_rclone_command(self, source, destination, mode):
        """Generate rclone command"""
        base_cmd = f'rclone'
        
        if mode == "sync":
            # Sync mode - make destination match source
            cmd = f'{base_cmd} sync "{source}" "{destination}"'
        elif mode == "copy":
            # Copy mode - copy new/changed files
            cmd = f'{base_cmd} copy "{source}" "{destination}"'
        else:
            # Default to sync
            cmd = f'{base_cmd} sync "{source}" "{destination}"'
        
        # Add common rclone options
        cmd += ' --checkers=16 --transfers=8 --update --copy-links --progress --stats=10s'
        
        return cmd
    
    def _is_rust_project(self, path):
        """Check if path contains Rust projects"""
        try:
            for root, dirs, files in os.walk(path):
                if "Cargo.toml" in files:
                    return True
            return False
        except Exception:
            return False
    
    def _run_cargo_clean(self, path):
        """Run cargo clean in all Rust projects within path"""
        try:
            for root, dirs, files in os.walk(path):
                if "Cargo.toml" in files:
                    self._log(f"Running cargo clean in: {root}")
                    process = subprocess.Popen(
                        f'cd /d "{root}" && cargo clean',
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    stdout, stderr = process.communicate()
                    
                    if process.returncode == 0:
                        self._log(f"Cargo clean completed in {root}")
                    else:
                        self._log(f"Cargo clean failed in {root}: {stderr}")
        except Exception as e:
            self._log(f"Error running cargo clean: {e}")
    
    def _log(self, message):
        """Send log message to GUI"""
        try:
            self.message_queue.put(("log", message))
        except Exception:
            # If queue is full or unavailable, continue silently
            pass
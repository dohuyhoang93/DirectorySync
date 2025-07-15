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
                    # Terminate the process group on Windows
                    subprocess.run(f"taskkill /F /T /PID {self.current_process.pid}", shell=True)
                else:
                    # Terminate the process group on Unix-like systems
                    os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
            except Exception as e:
                self._log(f"Error terminating process: {e}")
            finally:
                self.current_process = None
        
        self._log("Sync manager stopped")
    
    def is_running(self):
        """Check if sync manager is running"""
        return self.running
    
    def _simulate_progress(self, index, stop_event):
        """Simulate progress for a pair"""
        percent = 0
        while not stop_event.is_set() and percent < 90:
            percent += 1
            self.message_queue.put(("meter", index, percent))
            time.sleep(0.2)
        
        # Wait for completion signal
        while not stop_event.is_set():
            time.sleep(0.1)
        
        # Phase 2: Animate to 100%
        if percent < 90:
            step = 10
            interval = 0.1
        else:
            step = 10
            interval = 0.2
        
        while percent < 100:
            percent = min(100, percent + step)
            self.message_queue.put(("meter", index, percent))
            time.sleep(interval)
        
        self.message_queue.put(("meter", index, 100))
    
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
                    
                    # Create stop event for simulation
                    stop_event = threading.Event()
                    
                    # Start simulation thread
                    sim_thread = threading.Thread(target=self._simulate_progress, args=(index, stop_event))
                    sim_thread.start()
                    
                    # Execute sync command
                    success = self._execute_sync(pair, index)
                    
                    # Signal completion to simulation thread
                    stop_event.set()
                    
                    # Wait for simulation thread to finish
                    sim_thread.join()
                    
                    if success:
                        self._log(f"Pair {index + 1} completed successfully")
                    else:
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
            
            # Execute the command with start_new_session=True
            if pair['tool'] == 'rclone':
                # rclone logs are handled via --log-file
                self.current_process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    start_new_session=True
                )
                self.current_process.wait()
                returncode = self.current_process.returncode
                
                if returncode != 0:
                    with open('rclone_log.txt', 'r', encoding='utf-8') as f:
                        log_content = f.read()
                    self._log(f"Error: rclone failed with return code {returncode}\n{log_content}")
                    return False
                else:
                    self._log("rclone completed successfully")
                    return True
            else:  # robocopy
                self.current_process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    start_new_session=True
                )
                stdout, stderr = self.current_process.communicate()
                returncode = self.current_process.returncode
                
                if returncode == 0:
                    self._log("robocopy completed successfully")
                    if stdout.strip():
                        self._log(f"Output: {stdout.strip()}")
                    return True
                else:
                    self._log(f"robocopy failed with code {returncode}")
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
            cmd = f'{base_cmd} /MIR /MT:16 /Z /COPY:DAT /R:3 /W:10 /NP'
        elif mode == "E-Copy":
            cmd = f'{base_cmd} /E /MT:16 /Z /COPY:DAT /R:3 /W:10 /NP'
        else:
            cmd = f'{base_cmd} /MT:16 /Z /COPY:DAT /R:3 /W:10 /NP'
        return cmd
    
    def _generate_rclone_command(self, source, destination, mode):
        """Generate rclone command with specified parameters"""
        base_cmd = 'rclone'
        if mode == "sync":
            cmd = f'{base_cmd} sync "{source}" "{destination}"'
        elif mode == "copy":
            cmd = f'{base_cmd} copy "{source}" "{destination}"'
        else:
            cmd = f'{base_cmd} sync "{source}" "{destination}"'
        cmd += ' --checkers=32 --transfers=16 --multi-thread-streams=8 --update --copy-links --log-file=rclone_log.txt --log-level=INFO'
        return cmd
    
    def _is_rust_project(self, path):
        """Check if path contains Rust projects"""
        try:
            for root, _, files in os.walk(path):
                if "Cargo.toml" in files:
                    return True
            return False
        except Exception:
            return False
    
    def _run_cargo_clean(self, path):
        """Run cargo clean in all Rust projects within path"""
        try:
            for root, _, files in os.walk(path):
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
            pass
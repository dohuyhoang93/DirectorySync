import threading
import time
import subprocess
import os
import queue
import signal
import sys
import tempfile

class SyncManager:
    def __init__(self, message_queue):
        self.message_queue = message_queue
        self.running = False
        self.main_thread = None
        self.current_process = None
        self.pairs_to_sync = []
        self.interval = 60
        
    def start_cycle(self, pairs, interval):
        if not self.running:
            self.running = True
            self.pairs_to_sync = pairs
            self.interval = interval
            self.main_thread = threading.Thread(target=self._sync_loop, daemon=True)
            self.main_thread.start()
            self._log("Sync cycle started.", "SUCCESS")

    def stop_cycle(self):
        if self.running:
            self.running = False
            if self.current_process:
                self._terminate_process()
            self._log("Sync cycle stopped.", "WARNING")
    
    def run_single_pair(self, pair_data):
        self._log(f"Starting immediate sync for: {os.path.basename(pair_data.get('source'))}", "INFO")
        single_run_thread = threading.Thread(target=self._execute_and_report_status, args=(pair_data,), daemon=True)
        single_run_thread.start()

    def _terminate_process(self):
        if not self.current_process: return
        try:
            if sys.platform == "win32":
                subprocess.run(f"taskkill /F /T /PID {self.current_process.pid}", shell=True, capture_output=True)
            else:
                os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
        except Exception as e:
            self._log(f"Error terminating process: {e}", "ERROR")
        finally:
            self.current_process = None

    def is_running(self):
        return self.running
    
    def _sync_loop(self):
        while self.running:
            try:
                self._log("Starting sync cycle...", "INFO")
                for pair in self.pairs_to_sync:
                    if not self.running: break
                    self._execute_and_report_status(pair)
                if self.running:
                    self._log(f"Cycle finished. Next run in {self.interval}s.", "INFO")
                    for _ in range(self.interval):
                        if not self.running: break
                        time.sleep(1)
            except Exception as e:
                self._log(f"Critical error in sync loop: {e}", "ERROR")
                self.message_queue.put(("error", f"A critical error occurred: {e}"))
                time.sleep(10)

    def _execute_and_report_status(self, pair):
        source_name = os.path.basename(pair.get("source", "Unknown"))
        self._log(f"Processing pair '{source_name}': {pair['source']} -> {pair['destination']}", "INFO")
        self.message_queue.put(("status", "Syncing...", pair))
        success, error_message = self._execute_sync(pair)
        if success:
            self.message_queue.put(("status", "Completed", pair))
            self._log(f"Pair '{source_name}' completed successfully.", "SUCCESS")
        else:
            self.message_queue.put(("status", "Failed", pair))
            self._log(f"Pair '{source_name}' failed. {error_message}", "ERROR")
            if error_message:
                self.message_queue.put(("error", error_message))

    def _execute_sync(self, pair):
        try:
            command = self._generate_command(pair)
            if not command:
                return False, "Failed to generate command."
            self._log(f"Executing: {command}", "INFO")
            self.current_process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='replace',
                shell=True, start_new_session=True
            )
            stdout, stderr = self.current_process.communicate()
            returncode = self.current_process.returncode
            if pair['tool'] == 'robocopy':
                if returncode < 8:
                    if stdout and stdout.strip(): self._log(f"Robocopy output:\n{stdout.strip()}", "INFO")
                    return True, None
                else:
                    return False, f"Robocopy failed (code {returncode}): {stderr.strip()}"
            elif pair['tool'] == 'rclone':
                if returncode == 0:
                    return True, None
                else:
                    log_content = self._read_and_delete_temp_log(command)
                    return False, f"Rclone failed (code {returncode}):\n{log_content}\n{stderr.strip()}"
        except Exception as e:
            return False, f"Exception during execution: {e}"
        finally:
            self.current_process = None
        return False, "Unknown error."

    def _read_and_delete_temp_log(self, command_str):
        try:
            log_path_arg = [arg for arg in command_str.split() if arg.startswith('--log-file=')]
            if log_path_arg:
                log_path = log_path_arg[0].split('=', 1)[1].strip('"')
                if os.path.exists(log_path):
                    with open(log_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    os.remove(log_path)
                    return content
        except Exception as e:
            return f"(Could not read/delete log file: {e})"
        return "(Log file not found or specified)"

    def _generate_command(self, pair):
        source, dest, tool, mode = pair['source'], pair['destination'], pair['tool'], pair['mode']
        exclusions = pair.get('exclusions', [])
        options = pair.get('tool_options', {})

        if tool == 'robocopy':
            threads = options.get('threads', 16)
            retries = options.get('retries', 3)
            wait = options.get('wait', 5)
            
            base_cmd = f'robocopy "{source}" "{dest}"'
            mode_opt = {"MIR": "/MIR", "E-Copy": "/E"}.get(mode, "")
            common_opts = f"/MT:{threads} /R:{retries} /W:{wait} /Z /COPY:DAT /NP /NJH /NJS"
            
            exclude_dirs = []
            exclude_files = []
            for p in exclusions:
                pattern = p.strip()
                if not pattern:
                    continue
                
                # Convention: If it ends with a slash, it's a directory for /XD.
                if pattern.endswith('/') or pattern.endswith('\\'):
                    # Robocopy wants dir names without the trailing slash.
                    cleaned_p = pattern.rstrip('/\\')
                    exclude_dirs.append('"' + cleaned_p + '"')
                else:
                    # Otherwise, it's a file/path pattern for /XF.
                    exclude_files.append('"' + pattern + '"')

            exclude_opts = []
            if exclude_dirs:
                # Group all directory exclusions under a single /XD flag.
                exclude_opts.append('/XD ' + ' '.join(exclude_dirs))
            if exclude_files:
                # Group all file exclusions under a single /XF flag.
                exclude_opts.append('/XF ' + ' '.join(exclude_files))
            
            return f'{base_cmd} {mode_opt} {common_opts} {" ".join(exclude_opts)}'
        
        elif tool == 'rclone':
            checkers = options.get('checkers', 16)
            transfers = options.get('transfers', 8)
            multi_thread = options.get('multi_thread_streams', 4)

            action = 'sync' if mode == 'sync' else 'copy'
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log', encoding='utf-8') as log_file:
                log_path = log_file.name
            
            common_opts = f'--checkers={checkers} --transfers={transfers} --multi-thread-streams={multi_thread} --update --copy-links --log-level=INFO --log-file="{log_path}"'
            
            exclude_opts = []
            for pattern in exclusions:
                pattern = pattern.strip()
                if not pattern: continue
                if pattern.endswith('/') or pattern.endswith('\\'):
                    pattern = pattern.rstrip('/\\') + "/**"
                exclude_opts.append(f'--exclude "{pattern}"')

            return f'rclone {action} "{source}" "{dest}" {common_opts} {" ".join(exclude_opts)}'
        
        return None

    def _log(self, message, level):
        try:
            self.message_queue.put(("log", message, level))
        except Exception:
            pass

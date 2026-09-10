import logging
import psutil
import subprocess
import time
import win32con
import win32com.client
import win32gui
import win32process
from pathlib import Path

class ProcessManager:
    def __init__(self, process_path: Path):
        if not process_path.exists():
            raise FileNotFoundError(f"Target executable not found: {process_path}")
        self.process_path = process_path.resolve()
        self.target: str = process_path.name.lower()
        self.process: subprocess.Popen | None = None


    def _find_matches(self) -> list[psutil.Process]:
        """Private helper: always gets a fresh snapshot of matching processes."""
        matches = []
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info["name"]
                if name and name.lower() == self.target:
                    matches.append(proc)
            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue
        return matches


    def is_running(self) -> bool:
        """Returns True if at least one instance is currently alive."""
        if self.process:
            return self.process.poll() is None
        return len(self._find_matches()) > 0


    def terminate(self, timeout: float = 3.0) -> bool:
        """Gracefully terminates, then force-kills any lingering instances."""
        if self.process:
            self.process.terminate()
            self.process = None
            return True

        procs = self._find_matches()
        if not procs:
            logging.warning(f"{self.target} not found.")
            return False

        for p in procs:
            try:
                p.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                logging.warning(f"Failed to terminate {self.target} gracefully, trying to kill it..")

        _, alive = psutil.wait_procs(procs, timeout=timeout)
        for p in alive:
            p.kill()

        logging.info(f"{self.target} terminated successfully.")
        self.process = None
        return True


    def launch(self) -> None:
        self.process = subprocess.Popen(self.process_path, cwd=self.process_path.parent)


    def focus(self, timeout: float = 5.0) -> bool:
        """
        Brings the launched process window to the foreground.
        Polls until the window handle (HWND) is ready or timeout expires.
        """
        if not self.process:
            logging.error(f"{self.target} not found!")
            raise RuntimeError(f"Cannot focus {self.process}!")

        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Get all alive PIDs matching the target name
            active_pids = [p.pid for p in self._find_matches()]
            logging.debug(f"Found active PIDs: {active_pids}")
            
            for pid in active_pids:
                hwnd = self._get_hwnd_for_pid(pid)
                if hwnd:
                    if win32gui.IsIconic(hwnd):
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    else:
                        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

                    try: 
                        win32gui.SetForegroundWindow(hwnd)
                    except Exception:
                        shell = win32com.client.Dispatch("WScript.shell")
                        shell.SendKeys("%")
                        win32gui.SetForegroundWindow(hwnd)

                logging.info(F"Window (HWND: {hwnd}) focused successfully.")
                return True

            time.sleep(0.1)

        logging.error(f"Failed to focus {self.target}")
        return False


    @staticmethod
    def _get_hwnd_for_pid(pid: int) -> int | None:
        """Finds the primary visible top level window belonging to a PID."""
        matched_hwnds = []

        def enum_windows_callback(hwnd: int, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                    if window_pid == pid:
                        matched_hwnds.append(hwnd)
            return True

        win32gui.EnumWindows(enum_windows_callback, None)

        # Return the first match or inspect the list to pick the primary window
        return matched_hwnds[0] if matched_hwnds else None

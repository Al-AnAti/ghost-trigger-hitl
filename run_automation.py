import logging
import time
import sys
import pyautogui as pyg
from pathlib import Path

from process_manager import ProcessManager

artifacts_path = Path(__file__).resolve().parent / "artifacts"
exe_path = Path(r"C:\Windows\System32\notepad.exe")

DEFAULT_LOGGING_FORMAT = "%(asctime)s %(levelname)-s %(message)s"
DEFAULT_DATE_FORMAT = "%m-%d %H:%M"

def setup_logging() -> None:
    log_file = "harness.log"
    
    logging.basicConfig(
        filename=str(log_file),
        filemode='w',
        format=DEFAULT_LOGGING_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT,
        level=logging.DEBUG,
        force=True
    )
    console = logging.StreamHandler()
    formatter = logging.Formatter(DEFAULT_LOGGING_FORMAT)
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


def run(pm: ProcessManager):
    if pm.is_running():
        pm.terminate()

    pm.launch()
    if not pm.focus():
        raise RuntimeError("Failed to focus the target application. Aborting input.")

    logging.info("Writing to the file...")
    pyg.write(f"HITL Automation Run Verified - [{time.strftime('%d-%m-%Y, %H:%M:%S')}]", interval=0.03)

    if not artifacts_path.exists():
        artifacts_path.mkdir(exist_ok=True)

    logging.info("Capturing screen state to artifacts/verification.png")
    pyg.screenshot(str(artifacts_path / "verification.png"))


if __name__ == "__main__":
    try:
        setup_logging()
        pm = ProcessManager(exe_path)
        run(pm)
        sys.exit(0)
    except Exception as e:
        logging.critical(f"Unhandled pipeline failure: {e}", exc_info=True)
        sys.exit(1)
    finally:
        pm.terminate()

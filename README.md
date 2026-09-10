# Ghost Desktop Trigger

[![CI](https://github.com/Al-AnAti/ghost-trigger-hitl/actions/workflows/ghost-trigger.yml/badge.svg)](https://github.com/Al-AnAti/ghost-trigger-hitl/actions/workflows/ghost-trigger.yml)

This project connects a GitHub Actions CI/CD pipeline to a physical Windows desktop. It allows a cloud workflow to trigger a local Python script that opens a desktop app, performs a visible action using PyAutoGUI, takes a screenshot, and uploads the image back to GitHub.

## Why I Built This

Standard GitHub runners (like `windows-latest`) run in headless environments. If you install a local GitHub runner on a Windows machine as a background service, it runs in "Session 0 Isolation." Session 0 has no graphical rendering context, meaning you cannot run PyAutoGUI, OpenCV, or any UI tests against a screen because the screen doesn't exist.

I built this project to figure out how to bridge a cloud pipeline to an actual, unlocked physical display so I could automate native Windows GUI applications.

## How It Works

1. **Trigger:** A push to `main` or a manual workflow dispatch fires in GitHub.
2. **Routing:** The job targets a specific physical machine using a custom `[self-hosted, hitl-windows]` runner label.
3. **Cleanup:** A local Python script (`run_automation.py`) starts and forcefully closes any lingering instances of the target application to ensure a clean state.
4. **Execution:** The script launches the target app (e.g., Notepad), finds its window handle (HWND), and forces it to the foreground.
5. **Interaction:** PyAutoGUI types a verification string and captures a screenshot of the desktop.
6. **Teardown:** The app is closed to reset the environment for the next run.
7. **Extraction:** The screenshot is uploaded back to the GitHub Actions UI as an artifact.

## Technical Challenges & Solutions

Getting physical desktop automation to run reliably from a cloud trigger required working around a few Windows-specific quirks.

**Windows 11 UWP Stubs and PID Tracking**
Modern Windows apps often launch as a lightweight stub that immediately hands execution over to a UWP process. If the Python script just tracks the initial process ID (PID) from `subprocess.Popen`, it loses track of the actual application window. To fix this, I used `psutil` to scan for active processes by name rather than relying on the launch PID, and then used Win32 APIs to map those processes to the correct HWND.

**Forcing Window Focus**
Windows actively tries to prevent background scripts from stealing focus (Foreground Lock Timeout). If standard Win32 `SetForegroundWindow` calls fail, the script uses a fallback method: it dispatches an Alt keypress via `WScript.Shell` to bypass the OS lock and bring the window forward before PyAutoGUI attempts to type.

**Environment State Management**
GUI automation breaks easily if unexpected windows or prompts are open. I wrote a `ProcessManager` class that checks for and kills the target application both before the script starts and in a `finally` block after it finishes. This prevents the pipeline from failing due to zombie processes left over from a previously canceled run.

## Technologies Used
* **CI/CD:** GitHub Actions (Self-hosted runner configured for interactive sessions)
* **Automation:** Python 3.11, PyAutoGUI, Pillow
* **System APIs:** `psutil`, `pywin32` (`win32gui`, `win32process`)

## Proof of Execution

*This image is generated on the physical hardware and extracted to the cloud upon a successful pipeline run.*

![Verification Screenshot](assets/verification.png)
"""Safe desktop action executor for the Screen-Aware Copilot.

Copies generated text/code to the clipboard and optionally switches back to
the user's previous window to paste it automatically (human-in-the-loop).
"""

import platform
import time
import pyperclip

try:
    import pyautogui
    pyautogui.FAILSAFE = True  # Move mouse to top-left corner to abort anytime
except Exception:
    pyautogui = None


def copy_to_clipboard(text: str) -> None:
    """Copy text to the system clipboard."""
    pyperclip.copy(text)


def insert_into_previous_window(text: str, delay_seconds: float = 0.45) -> str:
    """Copy text, switch back to the previously active app, and paste it."""
    if not text.strip():
        return "Nothing to insert."

    pyperclip.copy(text)

    if pyautogui is None:
        return "Copied to clipboard (PyAutoGUI unavailable for auto-paste)."

    system = platform.system()
    time.sleep(delay_seconds)

    if system == "Darwin":  # macOS
        pyautogui.hotkey("command", "tab")
        time.sleep(0.35)
        pyautogui.hotkey("command", "v")
    else:  # Windows & Linux
        pyautogui.hotkey("alt", "tab")
        time.sleep(0.35)
        pyautogui.hotkey("ctrl", "v")

    return "Inserted directly into your previous window!"

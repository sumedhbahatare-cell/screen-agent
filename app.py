"""Always-on-top Screen-Aware Desktop Copilot UI (built with Python tkinter)."""

import threading
import time
import tkinter as tk
from tkinter import scrolledtext

from agent import CopilotResult, analyze_screen, capture_screen
from executor import copy_to_clipboard, insert_into_previous_window


class ScreenCopilotApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Screen-Aware Copilot")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#111827")

        # Position cleanly on the right side of the screen
        screen_w = self.root.winfo_screenwidth()
        win_w, win_h = 390, 620
        x_pos = max(20, screen_w - win_w - 24)
        self.root.geometry(f"{win_w}x{win_h}+{x_pos}+60")
        self.root.minsize(340, 500)

        self.latest_result: CopilotResult | None = None
        self.demo_var = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self) -> None:
        # Header
        header = tk.Frame(self.root, bg="#1F2937", padx=14, pady=12)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="Screen-Aware Copilot",
            bg="#1F2937",
            fg="#F9FAFB",
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")

        self.context_label = tk.Label(
            header,
            text="Ready — sees your screen without copy-paste",
            bg="#1F2937",
            fg="#93C5FD",
            font=("Segoe UI", 9),
        )
        self.context_label.pack(anchor="w", pady=(2, 0))

        # Quick Agentic Action Buttons
        quick_frame = tk.Frame(self.root, bg="#111827", padx=14, pady=10)
        quick_frame.pack(fill=tk.X)

        tk.Label(
            quick_frame,
            text="ONE-CLICK SCREEN ACTIONS",
            bg="#111827",
            fg="#9CA3AF",
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        btn_grid = tk.Frame(quick_frame, bg="#111827")
        btn_grid.pack(fill=tk.X)

        quick_actions = [
            ("Fix Error", "Find the error or bug on my screen and write the exact corrected code."),
            ("Draft Reply", "Read the email or message on my screen and draft a polite, concise reply."),
            ("Explain Screen", "Explain what is on my screen clearly and summarize the key points."),
            ("Action Steps", "Identify what I am working on and give me the next 3 concrete steps."),
        ]

        for idx, (label, prompt) in enumerate(quick_actions):
            r, c = divmod(idx, 2)
            btn = tk.Button(
                btn_grid,
                text=label,
                command=lambda p=prompt: self.run_copilot(p),
                bg="#1E3A8A",
                fg="#FFFFFF",
                activebackground="#2563EB",
                activeforeground="#FFFFFF",
                relief=tk.FLAT,
                font=("Segoe UI", 9, "bold"),
                pady=6,
                cursor="hand2",
            )
            btn.grid(row=r, column=c, sticky="ew", padx=3, pady=3)

        btn_grid.columnconfigure(0, weight=1)
        btn_grid.columnconfigure(1, weight=1)

        # Custom Prompt Input
        prompt_frame = tk.Frame(self.root, bg="#111827", padx=14, pady=4)
        prompt_frame.pack(fill=tk.X)

        tk.Label(
            prompt_frame,
            text="OR ASK ANYTHING ABOUT YOUR SCREEN",
            bg="#111827",
            fg="#9CA3AF",
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w", pady=(0, 4))

        input_row = tk.Frame(prompt_frame, bg="#111827")
        input_row.pack(fill=tk.X)

        self.prompt_entry = tk.Entry(
            input_row,
            bg="#1F2937",
            fg="#F9FAFB",
            insertbackground="#F9FAFB",
            relief=tk.FLAT,
            font=("Segoe UI", 10),
        )
        self.prompt_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 6))
        self.prompt_entry.insert(0, "What is on my screen and how can I improve it?")
        self.prompt_entry.bind("<Return>", lambda _e: self.run_copilot(self.prompt_entry.get()))

        self.ask_btn = tk.Button(
            input_row,
            text="Scan & Ask",
            command=lambda: self.run_copilot(self.prompt_entry.get()),
            bg="#10B981",
            fg="#06281E",
            activebackground="#34D399",
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=6,
            cursor="hand2",
        )
        self.ask_btn.pack(side=tk.RIGHT)

        # Demo mode toggle
        tk.Checkbutton(
            prompt_frame,
            text="Demo Mode (test UI without API key)",
            variable=self.demo_var,
            bg="#111827",
            fg="#9CA3AF",
            selectcolor="#1F2937",
            activebackground="#111827",
            activeforeground="#F9FAFB",
            font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(4, 0))

        # Response Area
        out_frame = tk.Frame(self.root, bg="#111827", padx=14, pady=8)
        out_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            out_frame,
            text="COPILOT ANALYSIS",
            bg="#111827",
            fg="#9CA3AF",
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w", pady=(0, 4))

        self.output_box = scrolledtext.ScrolledText(
            out_frame,
            wrap=tk.WORD,
            bg="#0F172A",
            fg="#E5E7EB",
            relief=tk.FLAT,
            font=("Segoe UI", 10),
            padx=10,
            pady=8,
            height=10,
        )
        self.output_box.pack(fill=tk.BOTH, expand=True)
        self.output_box.insert(
            tk.END,
            "Click any Quick Action or 'Scan & Ask'.\n\n"
            "This window hides briefly, captures your active screen, "
            "and lets you insert the result straight back into your app.",
        )
        self.output_box.configure(state=tk.DISABLED)

        # Action Execution Bar (Human-in-the-loop)
        action_frame = tk.Frame(self.root, bg="#1F2937", padx=14, pady=10)
        action_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.insert_btn = tk.Button(
            action_frame,
            text="Insert Into Previous Window",
            command=self.handle_insert,
            bg="#2563EB",
            fg="#FFFFFF",
            activebackground="#3B82F6",
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            pady=7,
            state=tk.DISABLED,
            cursor="hand2",
        )
        self.insert_btn.pack(fill=tk.X, pady=(0, 6))

        self.copy_btn = tk.Button(
            action_frame,
            text="Copy Action Text Only",
            command=self.handle_copy,
            bg="#374151",
            fg="#F9FAFB",
            activebackground="#4B5563",
            relief=tk.FLAT,
            font=("Segoe UI", 9),
            pady=5,
            state=tk.DISABLED,
            cursor="hand2",
        )
        self.copy_btn.pack(fill=tk.X)

        self.status_label = tk.Label(
            action_frame,
            text="Safety tip: move mouse to top-left corner to cancel auto-paste.",
            bg="#1F2937",
            fg="#9CA3AF",
            font=("Segoe UI", 8),
        )
        self.status_label.pack(anchor="w", pady=(6, 0))

    def _set_output(self, text: str) -> None:
        self.output_box.configure(state=tk.NORMAL)
        self.output_box.delete("1.0", tk.END)
        self.output_box.insert(tk.END, text)
        self.output_box.configure(state=tk.DISABLED)

    def run_copilot(self, prompt: str) -> None:
        prompt = prompt.strip()
        if not prompt:
            self.status_label.config(text="Please enter a request first.")
            return

        self.ask_btn.config(state=tk.DISABLED)
        self.insert_btn.config(state=tk.DISABLED)
        self.copy_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Capturing screen...")

        # Hide copilot briefly so it captures only the user's workspace
        self.root.withdraw()
        self.root.update()
        time.sleep(0.25)

        screenshot = None
        capture_error = None
        if not self.demo_var.get():
            try:
                screenshot = capture_screen()
            except Exception as exc:
                capture_error = str(exc)

        self.root.deiconify()
        self.root.attributes("-topmost", True)

        if capture_error:
            self._set_output(f"Could not capture screen:\n{capture_error}")
            self.status_label.config(text="Screen capture failed — check OS permissions.")
            self.ask_btn.config(state=tk.NORMAL)
            return

        self.status_label.config(text="Thinking with Gemini Vision...")
        self._set_output("Analyzing your screen...")

        worker = threading.Thread(
            target=self._worker_analyze,
            args=(prompt, screenshot, self.demo_var.get()),
            daemon=True,
        )
        worker.start()

    def _worker_analyze(self, prompt: str, screenshot, demo_mode: bool) -> None:
        try:
            result = analyze_screen(prompt, screenshot=screenshot, demo_mode=demo_mode)
            self.root.after(0, lambda: self._on_success(result))
        except Exception as exc:
            err = str(exc)
            self.root.after(0, lambda: self._on_error(err))

    def _on_success(self, result: CopilotResult) -> None:
        self.latest_result = result
        self.context_label.config(text=f"Detected: {result.detected_context}")

        display = (
            f"{result.explanation}\n\n"
            f"--- Ready to Insert ({result.action_label}) ---\n"
            f"{result.action_text}"
        )
        self._set_output(display)

        self.insert_btn.config(text=result.action_label, state=tk.NORMAL)
        self.copy_btn.config(state=tk.NORMAL)
        self.ask_btn.config(state=tk.NORMAL)
        self.status_label.config(text="Done! Click the blue button to insert into your app.")

    def _on_error(self, err: str) -> None:
        self._set_output(
            f"API Error:\n{err}\n\n"
            "Tip: Check that your .env file has a valid GEMINI_API_KEY, "
            "or check 'Demo Mode' to test offline."
        )
        self.status_label.config(text="Error calling Gemini API.")
        self.ask_btn.config(state=tk.NORMAL)

    def handle_insert(self) -> None:
        if not self.latest_result:
            return
        self.status_label.config(text="Switching back & inserting...")
        self.root.update()
        msg = insert_into_previous_window(self.latest_result.action_text)
        self.status_label.config(text=msg)

    def handle_copy(self) -> None:
        if not self.latest_result:
            return
        copy_to_clipboard(self.latest_result.action_text)
        self.status_label.config(text="Copied action text to clipboard!")


def main() -> None:
    root = tk.Tk()
    ScreenCopilotApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

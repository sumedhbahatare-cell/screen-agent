"""Always-on-top Screen-Aware Desktop Copilot UI (3D Glassmorphic Edition).

Uses CustomTkinter for sleek rounded pill buttons and translucent dark glass
styling when installed (`python -m pip install customtkinter`), and smoothly
falls back to enhanced translucent tkinter so the app never crashes.
"""

import threading
import time

from agent import CopilotResult, analyze_screen, capture_screen
from executor import copy_to_clipboard, insert_into_previous_window

try:
    import customtkinter as ctk

    HAS_CTK = True
except ImportError:
    import tkinter as tk
    from tkinter import scrolledtext

    HAS_CTK = False


QUICK_ACTIONS = [
    ("Fix Error", "Find the error or bug on my screen and write the exact corrected code."),
    ("Draft Reply", "Read the email or message on my screen and draft a polite, concise reply."),
    ("Explain Screen", "Explain what is on my screen clearly and summarize the key points."),
    ("Action Steps", "Identify what I am working on and give me the next 3 concrete steps."),
]


if HAS_CTK:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    class ScreenCopilotApp:
        def __init__(self, root: ctk.CTk) -> None:
            self.root = root
            self.root.title("Screen-Aware Copilot")
            self.root.attributes("-topmost", True)
            self.root.attributes("-alpha", 0.94)  # Frosted floating glass feel
            self.root.configure(fg_color="#0B1120")

            screen_w = self.root.winfo_screenwidth()
            win_w, win_h = 410, 660
            x_pos = max(20, screen_w - win_w - 24)
            self.root.geometry(f"{win_w}x{win_h}+{x_pos}+54")
            self.root.minsize(360, 540)

            self.latest_result: CopilotResult | None = None
            self.demo_var = ctk.BooleanVar(value=False)

            self._build_ui()

        def _build_ui(self) -> None:
            # Outer glass frame with subtle cyan-blue rim lighting
            shell = ctk.CTkFrame(
                self.root,
                fg_color="#0F172A",
                border_color="#1E3A8A",
                border_width=2,
                corner_radius=20,
            )
            shell.pack(fill="both", expand=True, padx=10, pady=10)

            # Top Glowing Context Status Pill
            self.context_pill = ctk.CTkLabel(
                shell,
                text="Detected: Ready — Screen-Aware Mode",
                fg_color="#0E3A5F",
                text_color="#7DD3FC",
                corner_radius=18,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                height=34,
                padx=14,
            )
            self.context_pill.pack(fill="x", padx=16, pady=(16, 10))

            # 2x2 Grid of 3D-style Rounded Quick Action Buttons
            btn_grid = ctk.CTkFrame(shell, fg_color="transparent")
            btn_grid.pack(fill="x", padx=16, pady=(2, 10))
            btn_grid.columnconfigure(0, weight=1)
            btn_grid.columnconfigure(1, weight=1)

            for idx, (label, prompt) in enumerate(QUICK_ACTIONS):
                r, c = divmod(idx, 2)
                btn = ctk.CTkButton(
                    btn_grid,
                    text=label,
                    command=lambda p=prompt: self.run_copilot(p),
                    fg_color="#1E293B",
                    hover_color="#1D4ED8",
                    border_color="#334155",
                    border_width=1,
                    text_color="#F8FAFC",
                    corner_radius=14,
                    height=40,
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                )
                btn.grid(row=r, column=c, sticky="ew", padx=4, pady=4)

            # Custom Prompt Row
            prompt_row = ctk.CTkFrame(shell, fg_color="transparent")
            prompt_row.pack(fill="x", padx=16, pady=(0, 6))

            self.prompt_entry = ctk.CTkEntry(
                prompt_row,
                placeholder_text="Ask anything about your screen...",
                fg_color="#111827",
                border_color="#334155",
                text_color="#F8FAFC",
                corner_radius=12,
                height=38,
                font=ctk.CTkFont(family="Segoe UI", size=12),
            )
            self.prompt_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
            self.prompt_entry.bind("<Return>", lambda _e: self.run_copilot(self.prompt_entry.get()))

            self.ask_btn = ctk.CTkButton(
                prompt_row,
                text="Scan",
                width=74,
                height=38,
                corner_radius=12,
                fg_color="#059669",
                hover_color="#10B981",
                text_color="#FFFFFF",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                command=lambda: self.run_copilot(
                    self.prompt_entry.get() or "Explain what is on my screen and suggest improvements."
                ),
            )
            self.ask_btn.pack(side="right")

            # Demo Mode Switch
            ctk.CTkSwitch(
                shell,
                text="Demo Mode (offline UI test)",
                variable=self.demo_var,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color="#94A3B8",
                progress_color="#2563EB",
            ).pack(anchor="w", padx=18, pady=(2, 8))

            # Frosted Analysis Preview Card
            self.output_box = ctk.CTkTextbox(
                shell,
                fg_color="#0B1220",
                border_color="#1E293B",
                border_width=1,
                text_color="#E2E8F0",
                corner_radius=14,
                font=ctk.CTkFont(family="Segoe UI", size=13),
                wrap="word",
            )
            self.output_box.pack(fill="both", expand=True, padx=16, pady=(0, 12))
            self._set_output(
                "Click any Quick Action or press Scan.\n\n"
                "This floating panel hides briefly, reads your active screen with Gemini Vision, "
                "and lets you insert the fix directly back into your app."
            )

            # Luminous Blue Primary CTA Pill
            self.insert_btn = ctk.CTkButton(
                shell,
                text="Insert Into Previous Window",
                command=self.handle_insert,
                fg_color="#2563EB",
                hover_color="#3B82F6",
                text_color="#FFFFFF",
                corner_radius=20,
                height=44,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                state="disabled",
            )
            self.insert_btn.pack(fill="x", padx=16, pady=(0, 6))

            self.copy_btn = ctk.CTkButton(
                shell,
                text="Copy Action Text Only",
                command=self.handle_copy,
                fg_color="#1E293B",
                hover_color="#334155",
                text_color="#CBD5E1",
                corner_radius=14,
                height=32,
                font=ctk.CTkFont(family="Segoe UI", size=12),
                state="disabled",
            )
            self.copy_btn.pack(fill="x", padx=16, pady=(0, 6))

            self.status_label = ctk.CTkLabel(
                shell,
                text="Safety: move mouse to top-left corner to cancel auto-paste.",
                text_color="#64748B",
                font=ctk.CTkFont(family="Segoe UI", size=10),
            )
            self.status_label.pack(anchor="w", padx=18, pady=(0, 10))

        def _set_output(self, text: str) -> None:
            self.output_box.configure(state="normal")
            self.output_box.delete("1.0", "end")
            self.output_box.insert("1.0", text)
            self.output_box.configure(state="disabled")

        def run_copilot(self, prompt: str) -> None:
            prompt = prompt.strip()
            if not prompt:
                self.status_label.configure(text="Please enter a request first.")
                return

            self.ask_btn.configure(state="disabled")
            self.insert_btn.configure(state="disabled")
            self.copy_btn.configure(state="disabled")
            self.status_label.configure(text="Capturing active screen...")

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
                self.status_label.configure(text="Screen capture failed — check OS permissions.")
                self.ask_btn.configure(state="normal")
                return

            self.status_label.configure(text="Analyzing with Gemini Vision...")
            self._set_output("Reading your screen...")

            threading.Thread(
                target=self._worker_analyze,
                args=(prompt, screenshot, self.demo_var.get()),
                daemon=True,
            ).start()

        def _worker_analyze(self, prompt: str, screenshot, demo_mode: bool) -> None:
            try:
                result = analyze_screen(prompt, screenshot=screenshot, demo_mode=demo_mode)
                self.root.after(0, lambda: self._on_success(result))
            except Exception as exc:
                err = str(exc)
                self.root.after(0, lambda: self._on_error(err))

        def _on_success(self, result: CopilotResult) -> None:
            self.latest_result = result
            self.context_pill.configure(text=f"Detected: {result.detected_context}")

            display = (
                f"{result.explanation}\n\n"
                f"--- Ready to Insert ({result.action_label}) ---\n"
                f"{result.action_text}"
            )
            self._set_output(display)
            self.insert_btn.configure(text=result.action_label, state="normal")
            self.copy_btn.configure(state="normal")
            self.ask_btn.configure(state="normal")
            self.status_label.configure(text="Ready! Click the blue pill to insert into your app.")

        def _on_error(self, err: str) -> None:
            self._set_output(
                f"API Error:\n{err}\n\n"
                "Tip: Verify GEMINI_API_KEY in .env, or toggle Demo Mode to test offline."
            )
            self.status_label.configure(text="Error calling Gemini API.")
            self.ask_btn.configure(state="normal")

        def handle_insert(self) -> None:
            if not self.latest_result:
                return
            self.status_label.configure(text="Switching back & inserting...")
            self.root.update()
            msg = insert_into_previous_window(self.latest_result.action_text)
            self.status_label.configure(text=msg)

        def handle_copy(self) -> None:
            if not self.latest_result:
                return
            copy_to_clipboard(self.latest_result.action_text)
            self.status_label.configure(text="Copied action text to clipboard!")

else:
    # Enhanced translucent tkinter fallback if customtkinter is not yet installed
    class ScreenCopilotApp:
        def __init__(self, root: tk.Tk) -> None:
            self.root = root
            self.root.title("Screen-Aware Copilot")
            self.root.attributes("-topmost", True)
            self.root.attributes("-alpha", 0.94)
            self.root.configure(bg="#0B1120")

            screen_w = self.root.winfo_screenwidth()
            win_w, win_h = 400, 640
            x_pos = max(20, screen_w - win_w - 24)
            self.root.geometry(f"{win_w}x{win_h}+{x_pos}+54")
            self.root.minsize(350, 520)

            self.latest_result: CopilotResult | None = None
            self.demo_var = tk.BooleanVar(value=False)
            self._build_ui()

        def _build_ui(self) -> None:
            header = tk.Frame(self.root, bg="#0F172A", padx=14, pady=12)
            header.pack(fill=tk.X)

            self.context_pill = tk.Label(
                header,
                text="Detected: Ready — Screen-Aware Mode",
                bg="#0E3A5F",
                fg="#7DD3FC",
                font=("Segoe UI", 10, "bold"),
                pady=6,
            )
            self.context_pill.pack(fill=tk.X)

            btn_grid = tk.Frame(self.root, bg="#0B1120", padx=14, pady=10)
            btn_grid.pack(fill=tk.X)
            btn_grid.columnconfigure(0, weight=1)
            btn_grid.columnconfigure(1, weight=1)

            for idx, (label, prompt) in enumerate(QUICK_ACTIONS):
                r, c = divmod(idx, 2)
                tk.Button(
                    btn_grid,
                    text=label,
                    command=lambda p=prompt: self.run_copilot(p),
                    bg="#1E293B",
                    fg="#F8FAFC",
                    activebackground="#2563EB",
                    activeforeground="#FFFFFF",
                    relief=tk.FLAT,
                    font=("Segoe UI", 10, "bold"),
                    pady=8,
                    cursor="hand2",
                ).grid(row=r, column=c, sticky="ew", padx=4, pady=4)

            prompt_row = tk.Frame(self.root, bg="#0B1120", padx=14, pady=4)
            prompt_row.pack(fill=tk.X)

            self.prompt_entry = tk.Entry(
                prompt_row,
                bg="#111827",
                fg="#F8FAFC",
                insertbackground="#F8FAFC",
                relief=tk.FLAT,
                font=("Segoe UI", 10),
            )
            self.prompt_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7, padx=(0, 6))
            self.prompt_entry.insert(0, "What is on my screen and how can I improve it?")
            self.prompt_entry.bind("<Return>", lambda _e: self.run_copilot(self.prompt_entry.get()))

            self.ask_btn = tk.Button(
                prompt_row,
                text="Scan",
                command=lambda: self.run_copilot(self.prompt_entry.get()),
                bg="#059669",
                fg="#FFFFFF",
                activebackground="#10B981",
                relief=tk.FLAT,
                font=("Segoe UI", 10, "bold"),
                padx=14,
                pady=6,
                cursor="hand2",
            )
            self.ask_btn.pack(side=tk.RIGHT)

            tk.Checkbutton(
                self.root,
                text="Demo Mode (install customtkinter for rounded 3D pills)",
                variable=self.demo_var,
                bg="#0B1120",
                fg="#94A3B8",
                selectcolor="#1E293B",
                activebackground="#0B1120",
                activeforeground="#F8FAFC",
                font=("Segoe UI", 8),
            ).pack(anchor="w", padx=14, pady=(2, 6))

            self.output_box = scrolledtext.ScrolledText(
                self.root,
                wrap=tk.WORD,
                bg="#0F172A",
                fg="#E2E8F0",
                relief=tk.FLAT,
                font=("Segoe UI", 10),
                padx=12,
                pady=10,
            )
            self.output_box.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 10))
            self._set_output("Click any Quick Action or Scan to analyze your screen.")

            action_bar = tk.Frame(self.root, bg="#0F172A", padx=14, pady=12)
            action_bar.pack(fill=tk.X, side=tk.BOTTOM)

            self.insert_btn = tk.Button(
                action_bar,
                text="Insert Into Previous Window",
                command=self.handle_insert,
                bg="#2563EB",
                fg="#FFFFFF",
                activebackground="#3B82F6",
                relief=tk.FLAT,
                font=("Segoe UI", 10, "bold"),
                pady=9,
                state=tk.DISABLED,
                cursor="hand2",
            )
            self.insert_btn.pack(fill=tk.X, pady=(0, 6))

            self.copy_btn = tk.Button(
                action_bar,
                text="Copy Action Text Only",
                command=self.handle_copy,
                bg="#1E293B",
                fg="#CBD5E1",
                relief=tk.FLAT,
                font=("Segoe UI", 9),
                pady=6,
                state=tk.DISABLED,
                cursor="hand2",
            )
            self.copy_btn.pack(fill=tk.X)

            self.status_label = tk.Label(
                action_bar,
                text="Tip: run 'python -m pip install customtkinter' for full rounded 3D glass UI.",
                bg="#0F172A",
                fg="#64748B",
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
                return
            self.ask_btn.config(state=tk.DISABLED)
            self.insert_btn.config(state=tk.DISABLED)
            self.copy_btn.config(state=tk.DISABLED)
            self.status_label.config(text="Capturing active screen...")

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
                self.ask_btn.config(state=tk.NORMAL)
                return

            self.status_label.config(text="Analyzing with Gemini Vision...")
            self._set_output("Reading your screen...")
            threading.Thread(
                target=self._worker_analyze,
                args=(prompt, screenshot, self.demo_var.get()),
                daemon=True,
            ).start()

        def _worker_analyze(self, prompt: str, screenshot, demo_mode: bool) -> None:
            try:
                result = analyze_screen(prompt, screenshot=screenshot, demo_mode=demo_mode)
                self.root.after(0, lambda: self._on_success(result))
            except Exception as exc:
                err = str(exc)
                self.root.after(0, lambda: self._on_error(err))

        def _on_success(self, result: CopilotResult) -> None:
            self.latest_result = result
            self.context_pill.config(text=f"Detected: {result.detected_context}")
            self._set_output(
                f"{result.explanation}\n\n"
                f"--- Ready to Insert ({result.action_label}) ---\n"
                f"{result.action_text}"
            )
            self.insert_btn.config(text=result.action_label, state=tk.NORMAL)
            self.copy_btn.config(state=tk.NORMAL)
            self.ask_btn.config(state=tk.NORMAL)
            self.status_label.config(text="Ready! Click the blue button to insert.")

        def _on_error(self, err: str) -> None:
            self._set_output(f"API Error:\n{err}")
            self.ask_btn.config(state=tk.NORMAL)

        def handle_insert(self) -> None:
            if not self.latest_result:
                return
            msg = insert_into_previous_window(self.latest_result.action_text)
            self.status_label.config(text=msg)

        def handle_copy(self) -> None:
            if not self.latest_result:
                return
            copy_to_clipboard(self.latest_result.action_text)
            self.status_label.config(text="Copied action text to clipboard!")


def main() -> None:
    root = ctk.CTk() if HAS_CTK else tk.Tk()
    ScreenCopilotApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
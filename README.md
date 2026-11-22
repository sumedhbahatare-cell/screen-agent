# Screen-Aware Desktop Copilot (Hackathon Starter)

An always-on-top Python desktop copilot that reads your active screen with Gemini Vision and inserts fixes, replies, or summaries straight back into your active app—eliminating manual copy-paste.

## Quick Start in VS Code

1. Open this folder in **VS Code** (`File -> Open Folder`).
2. Open the VS Code terminal (`Ctrl + ~` or `Terminal -> New Terminal`).
3. Create and activate a virtual environment:
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Rename `.env.example` to `.env` and paste your free Gemini API key from https://aistudio.google.com/app/apikey.
6. Run the app:
   ```bash
   python app.py
   ```

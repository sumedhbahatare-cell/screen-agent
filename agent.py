"""Screen capture and Gemini multimodal agentic brain."""

import json
import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from PIL import Image

load_dotenv()

SYSTEM_PROMPT = """You are a Screen-Aware Desktop Copilot helping a user directly inside their workflow.
Look closely at the user's screenshot and their request.
Respond ONLY with valid JSON matching this exact schema:
{
  "detected_context": "Short 3-6 word label of the app and task visible on screen",
  "explanation": "Clear, concise 2-4 sentence answer or diagnosis of what is on screen",
  "action_label": "Short 2-4 word button label (e.g., Insert Fixed Code, Insert Draft Reply, Copy Summary)",
  "action_text": "The exact clean text, code fix, or reply ready to paste directly into the user's app with NO markdown backticks"
}
"""


@dataclass
class CopilotResult:
    detected_context: str
    explanation: str
    action_label: str
    action_text: str
    used_demo_mode: bool = False


def capture_screen(max_width: int = 1280) -> Image.Image:
    """Capture the primary monitor as a resized PIL Image for fast API upload."""
    import mss

    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Primary display
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.rgb)

    if img.width > max_width:
        ratio = max_width / float(img.width)
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    return img


def _parse_json_response(raw_text: str) -> CopilotResult:
    """Safely parse the model's JSON response even if wrapped in code fences."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        data = json.loads(cleaned)
        return CopilotResult(
            detected_context=str(data.get("detected_context", "Active Desktop Window")),
            explanation=str(data.get("explanation", cleaned)),
            action_label=str(data.get("action_label", "Insert Into App")),
            action_text=str(data.get("action_text", cleaned)),
        )
    except json.JSONDecodeError:
        return CopilotResult(
            detected_context="Active Desktop Window",
            explanation=cleaned,
            action_label="Insert Response",
            action_text=cleaned,
        )


def _demo_response(user_prompt: str) -> CopilotResult:
    """Offline demo fallback so you can test the UI without an API key."""
    return CopilotResult(
        detected_context="Demo Mode (No API Key Yet)",
        explanation=(
            f"Demo Mode is active! You asked: '{user_prompt}'. "
            "Add your free GEMINI_API_KEY to the .env file and uncheck Demo Mode "
            "to analyze your real screen with Gemini."
        ),
        action_label="Insert Demo Text",
        action_text="Hello from your Screen-Aware Desktop Copilot! (Demo Mode)",
        used_demo_mode=True,
    )


def analyze_screen(
    user_prompt: str,
    screenshot: Optional[Image.Image] = None,
    demo_mode: bool = False,
) -> CopilotResult:
    """Send the screenshot + prompt to Gemini and return structured agentic output."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if demo_mode or not api_key or api_key == "your_api_key_here":
        return _demo_response(user_prompt)

    from google import genai
    from google.genai import types

    if screenshot is None:
        screenshot = capture_screen()

    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model_name,
        contents=[
            f"User request: {user_prompt}",
            screenshot,
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )

    return _parse_json_response(response.text or "")

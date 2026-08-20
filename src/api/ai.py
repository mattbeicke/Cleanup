"""Local AI analysis using Ollama."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from .models import ItemInfo

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_MODEL = "devstral-32k:latest"

MAX_FILE_SAMPLE = 12000


def _read_file_sample(path: Path) -> str:
    """Read a small text sample when possible, without loading the whole file."""
    if not path.is_file():
        return ""

    try:
        with path.open("r", encoding="utf-8", errors="replace") as file:
            return file.read(MAX_FILE_SAMPLE)
    except (OSError, UnicodeError):
        return ""


def _build_context(item: ItemInfo) -> dict[str, Any]:
    context: dict[str, Any] = {
        "path": str(item.path),
        "name": item.path.name,
        "kind": item.kind,
        "extension": item.path.suffix.lower(),
        "size_bytes": item.size_bytes,
        "relative_path": str(item.relative_path),
        "sample_contents": list(item.sample),
    }

    file_sample = _read_file_sample(item.path)
    if file_sample:
        context["text_sample"] = file_sample

    return context


def _extract_json(text: str) -> dict[str, Any]:
    """Extract a JSON object from the model response."""
    text = text.strip()

    # First try the entire response.
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    # Qwen may occasionally wrap JSON in markdown fences.
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            cleaned = part.strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

            try:
                value = json.loads(cleaned)
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                continue

    # Last resort: find the outermost JSON object.
    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:
        try:
            value = json.loads(text[start:end + 1])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            pass

    raise ValueError("The AI returned an invalid response.")


def analyze_item(item: ItemInfo) -> dict[str, Any]:
    """Ask the local Ollama model to analyze one filesystem item."""

    context = _build_context(item)

    system_prompt = """
You are the file-analysis component of a Windows computer cleanup application.

Your job is to determine what a file or folder appears to be and whether it is
reasonable for the user to remove it.

IMPORTANT:
- Do not blindly recommend deletion.
- If the purpose is uncertain, recommend "Review before removing".
- Never claim something is safe merely because its name looks temporary.
- Personal files, application data, configuration, source code, databases,
  save files, and user-created files should generally be kept unless there
  is strong evidence they are disposable.
- Cache, temporary files, logs, build output, and regenerated data may be
  removable when the evidence supports that conclusion.
- The application only moves files to the Windows Recycle Bin.
- The AI does NOT perform deletion.

Return ONLY valid JSON matching this structure:

{
  "classification": "short description of what this is",
  "recommendation": "Safe to remove | Likely removable | Review before removing | Do not remove | Unknown",
  "risk": "low | medium | high | unknown",
  "confidence": 0.0,
  "summary": "One or two sentences explaining what the item appears to be.",
  "reason": "Explain why it should or should not be removed.",
  "recreated": true
}

The "recreated" field means whether the item would likely be recreated
automatically by the associated application or system.
"""

    user_prompt = (
        "Analyze this filesystem item. Use the path, name, location, type, "
        "size, directory contents, and text sample when available.\n\n"
        + json.dumps(context, indent=2, ensure_ascii=False)
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "stream": False,
                "format": "json",
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
            },
            timeout=120,
        )
        response.raise_for_status()

        payload = response.json()
        content = payload.get("message", {}).get("content", "")

        if not content:
            raise ValueError("Ollama returned an empty response.")

        result = _extract_json(content)

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Ollama is not running. Start Ollama and make sure "
            f"{OLLAMA_MODEL} is installed."
        ) from None
    except requests.exceptions.Timeout:
        raise RuntimeError("The AI analysis timed out.") from None
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from None
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(f"The AI returned an invalid response: {exc}") from None

    # Validate/default the fields so the frontend always receives predictable data.
    return {
        "classification": str(result.get("classification", "Unknown")),
        "recommendation": str(
            result.get("recommendation", "Review before removing")
        ),
        "risk": str(result.get("risk", "unknown")),
        "confidence": float(result.get("confidence", 0)),
        "summary": str(result.get("summary", "The AI could not determine the purpose of this item.")),
        "reason": str(result.get("reason", "There is not enough evidence to recommend removal.")),
        "recreated": bool(result.get("recreated", False)),
        "source": f"Ollama ({OLLAMA_MODEL})",
    }
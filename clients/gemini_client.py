from dotenv import load_dotenv
load_dotenv()

import os
from typing import Optional, Dict, Any
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
PRIMARY_MODEL  = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
FALLBACK_MODEL = "gemini-1.5-flash"

class GeminiClient:
    """Minimal Gemini wrapper: auth, model selection, fallback, generate()."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        key = api_key or GEMINI_API_KEY
        if not key:
            raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) is missing in environment.")
        genai.configure(api_key=key)
        self.model_name = model or PRIMARY_MODEL
        self.model = genai.GenerativeModel(self.model_name)

    def _set_model(self, name: str):
        self.model_name = name
        self.model = genai.GenerativeModel(name)

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Return dict: text + model + candidates + safety (no channel knowledge)."""
        try:
            resp = self.model.generate_content(prompt, **kwargs)
        except ResourceExhausted:
            if self.model_name != FALLBACK_MODEL:
                self._set_model(FALLBACK_MODEL)
                resp = self.model.generate_content(prompt, **kwargs)
            else:
                raise
        except GoogleAPIError as e:
            raise RuntimeError(f"Gemini error: {e}")

        text = (getattr(resp, "text", None) or "").replace("```", "").strip()
        return {
            "text": text,
            "model": self.model_name,
            "candidates": len(getattr(resp, "candidates", []) or []),
            "safety": getattr(resp, "prompt_feedback", None),
        }

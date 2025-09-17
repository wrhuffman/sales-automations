from dotenv import load_dotenv
load_dotenv()

import os
from typing import Optional
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
PRIMARY_MODEL  = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
FALLBACK_MODEL = "gemini-1.5-flash"

class GeminiClient:
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

    def draft_post(self, subject: str, company_name: Optional[str] = None,
                   link: Optional[str] = None, tone: str = "professional, concise, engaging",
                   max_chars: int = 700, add_hashtags: bool = True) -> str:
        prompt = f"""You are drafting a LinkedIn post.

Subject/topic: {subject}
Company/person mentioned: {company_name or "N/A"}
Reference link: {link or "N/A"}
Tone: {tone}

Write 1 LinkedIn post draft in plain text.
- Keep it under {max_chars} characters.
- Short paragraphs with line breaks.
- Strong hook first line, light CTA at end.
- {"Include 3–6 relevant hashtags." if add_hashtags else "Do not add hashtags."}
- No markdown or code fences.
"""
        try:
            resp = self.model.generate_content(prompt)
        except ResourceExhausted:
            if self.model_name != FALLBACK_MODEL:
                self._set_model(FALLBACK_MODEL)
                resp = self.model.generate_content(prompt)
            else:
                raise
        txt = (resp.text or "").replace("```", "").strip()
        return txt

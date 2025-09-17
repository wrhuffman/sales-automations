import os, requests
from typing import Optional, Dict, Any

API_BASE = "https://api.linkedin.com/v2"

class LinkedInPosterClient:
    def __init__(self, access_token: Optional[str] = None, member_urn: Optional[str] = None):
        self.access_token = access_token or os.getenv("LINKEDIN_ACCESS_TOKEN")
        if not self.access_token:
            raise RuntimeError("LINKEDIN_ACCESS_TOKEN is missing in environment.")
        self._member_urn = member_urn

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def get_member_urn(self) -> str:
        # 1) env override
        if self._member_urn:
            return self._member_urn
        env_urn = os.getenv("LINKEDIN_MEMBER_URN")
        if env_urn:
            self._member_urn = env_urn
            return env_urn

        try:
            r = requests.get(f"{API_BASE}/me", headers=self.headers, timeout=20)
            if r.status_code == 200:
                pid = r.json().get("id")
                if pid:
                    self._member_urn = f"urn:li:person:{pid}"
                    return self._member_urn
        except Exception:
            pass

        r2 = requests.get(f"{API_BASE}/userinfo", headers=self.headers, timeout=20)
        r2.raise_for_status()
        sub = r2.json().get("sub")
        if not sub:
            raise RuntimeError("Unable to resolve member id from /userinfo.")
        self._member_urn = f"urn:li:person:{sub}"
        return self._member_urn

    def create_text_post(self, text: str, visibility: str = "PUBLIC") -> Dict[str, Any]:
        author = self.get_member_urn()
        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": visibility},
        }
        r = requests.post(f"{API_BASE}/ugcPosts", headers=self.headers, json=payload, timeout=30)
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise RuntimeError(f"Member post failed: HTTP {r.status_code} – {detail}")
        return r.json()

import os, json, time, requests
from typing import Optional, Dict, Any
from utils import SESSION, SERP_ZONE, DATASET_ID, google_query_url, backoff_sleep, log

# Bright Data endpoints
API_SERP     = "https://api.brightdata.com/request"
API_SCRAPE   = "https://api.brightdata.com/datasets/v3/scrape"
API_TRIGGER  = "https://api.brightdata.com/datasets/v3/trigger"
API_SNAPSHOT = "https://api.brightdata.com/datasets/v3/snapshots/"

# LinkedIn API
API_BASE = "https://api.linkedin.com/v2"

class LinkedInClient:
    """
    All LinkedIn operations:
    - SERP discovery (company URL)
    - Bright Data scrape (company payload -> website)
    - LinkedIn member ops (resolve member URN, create text post)
    """

    def __init__(self, access_token: Optional[str] = None, member_urn: Optional[str] = None):
        self.access_token = access_token or os.getenv("LINKEDIN_ACCESS_TOKEN")
        if not self.access_token:
            raise RuntimeError("LINKEDIN_ACCESS_TOKEN is missing in environment.")
        self._member_urn = member_urn

    # ---------- LinkedIn headers ----------
    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    # ---------- Discovery via SERP ----------
    def business_to_profile_url(self, business_name: str) -> Optional[str]:
        return self._serp_first_linkedin_company(business_name)

    def _serp_first_linkedin_company(self, business_name: str) -> Optional[str]:
        query = f"site:linkedin.com/company {business_name}"
        payload = {"zone": SERP_ZONE, "url": google_query_url(query), "format": "raw"}

        for attempt in range(4):
            r = SESSION.post(API_SERP, json=payload, timeout=60)
            if r.ok:
                try:
                    data = r.json()
                except Exception:
                    data = json.loads(r.text or "{}")

                for item in data.get("organic", []):
                    link = item.get("link") or item.get("url")
                    if link and "linkedin.com/company" in link:
                        clean = link.split("?")[0]
                        log.debug(f"[SERP] {business_name} → {clean}")
                        return clean
                log.info(f"[SERP] No linkedin.com/company result for: {business_name}")
                return None

            log.warning(f"[SERP] attempt {attempt+1} HTTP {r.status_code}; backing off…")
            backoff_sleep(attempt)

        log.error(f"[SERP] failed for: {business_name}")
        return None

    def find_official_website_via_serp(self, business_name: str) -> Optional[str]:
        query = f'{business_name} official site -site:linkedin.com'
        payload = {"zone": SERP_ZONE, "url": google_query_url(query), "format": "raw"}
        for attempt in range(4):
            r = SESSION.post(API_SERP, json=payload, timeout=60)
            if r.ok:
                try:
                    data = r.json()
                except Exception:
                    data = json.loads(r.text or "{}")
                for item in data.get("organic", []):
                    link = item.get("link") or item.get("url")
                    if link and "linkedin.com" not in link and link.startswith("http"):
                        return link.split("?")[0]
                return None
            backoff_sleep(attempt)
        return None

    # ---------- Company scrape via Bright Data ----------
    def collect_company_payload(self, linkedin_company_url: str) -> Dict[str, Any]:
        return self._collect_linkedin_company(linkedin_company_url)

    def _collect_linkedin_company(self, linkedin_company_url: str) -> Dict[str, Any]:
        for attempt in range(2):
            resp = self._scrape_now(linkedin_company_url)
            if resp.get("status") not in ("error", "pending"):
                return resp
            log.warning(f"[BD] scrape error/pend (try {attempt+1}): {resp}")
            backoff_sleep(attempt)

        log.info("[BD] switching to trigger fallback…")
        for attempt in range(2):
            resp = self._scrape_trigger(linkedin_company_url)
            if resp.get("status") not in ("error", "pending"):
                return resp
            log.warning(f"[BD] trigger error/pend (try {attempt+1}): {resp}")
            backoff_sleep(attempt)

        return {"status": "error", "detail": "Both scrape and trigger failed"}

    def _scrape_now(self, url: str) -> Dict[str, Any]:
        body = {"dataset_id": DATASET_ID, "input": [{"url": url}]}
        r = SESSION.post(API_SCRAPE, json=body, timeout=60)
        if r.status_code == 200:
            try:
                return r.json()
            except Exception:
                return {"raw": r.text}
        if r.status_code == 202:
            snap = r.json().get("snapshot_id")
            log.info(f"[BD] snapshot queued: {snap}")
            return self._poll_snapshot(snap)
        return {"status": "error", "http": r.status_code, "body": (r.text or "")[:600]}

    def _scrape_trigger(self, url: str) -> Dict[str, Any]:
        body = {"dataset_id": DATASET_ID, "input": [{"url": url}]}
        r = SESSION.post(API_TRIGGER, json=body, timeout=60)
        if r.status_code in (200, 201, 202):
            snap = None
            try:
                snap = r.json().get("snapshot_id")
            except Exception:
                pass
            if snap:
                log.info(f"[BD] trigger snapshot: {snap}")
                return self._poll_snapshot(snap)
            try:
                return r.json()
            except Exception:
                return {"raw": r.text}
        return {"status": "error", "http": r.status_code, "body": (r.text or "")[:600]}

    def _poll_snapshot(self, snapshot_id: str, ttl_secs: int = 60) -> Dict[str, Any]:
        deadline = time.time() + ttl_secs
        while time.time() < deadline:
            s = requests.get(f"{API_SNAPSHOT}{snapshot_id}", timeout=60)
            if s.status_code == 200:
                try:
                    return s.json()
                except Exception:
                    return {"raw": s.text}
            time.sleep(3)
        return {"status": "pending", "snapshot_id": snapshot_id}

    # ---------- Website extraction from payload ----------
    def extract_company_website(self, company_payload: Dict[str, Any]) -> str:
        return self._extract_company_website(company_payload)

    def _first(self, obj, keys):
        for k in keys:
            if isinstance(obj, dict) and obj.get(k):
                return obj[k]
        return None

    def _drill_for_website(self, obj) -> str:
        if not isinstance(obj, dict):
            return ""
        site = self._first(obj, ("website", "company_website", "site", "official_website", "companyWebsite", "siteUrl"))
        if site:
            return str(site).strip()
        for container in ("results", "data", "items", "payload", "records"):
            arr = obj.get(container)
            if isinstance(arr, list) and arr:
                first = arr[0]
                site = self._first(first, ("website", "company_website", "site", "official_website", "companyWebsite", "siteUrl"))
                if site:
                    return str(site).strip()
        return ""

    def _extract_company_website(self, company_payload: Dict[str, Any]) -> str:
        site = self._drill_for_website(company_payload)
        if site and not site.startswith("http"):
            site = "https://" + site.lstrip("/")
        return site

    # ---------- High-level enrichment ----------
    def enrich_business(self, business_name: str) -> Dict[str, Any]:
        li = self.business_to_profile_url(business_name)
        if not li:
            website = self.find_official_website_via_serp(business_name) or ""
            return {
                "business_name": business_name,
                "linkedin_company_url": "",
                "website": website,
                "status": "no_linkedin_but_site_fallback"
            }

        payload = self.collect_company_payload(li)
        website = self.extract_company_website(payload)
        if not website:
            website = self.find_official_website_via_serp(business_name) or ""

        return {
            "business_name": business_name,
            "linkedin_company_url": li,
            "website": website,
            "status": "ok" if website else "no_website_found"
        }

    # ---------- LinkedIn posting ----------
    def get_member_urn(self) -> str:
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

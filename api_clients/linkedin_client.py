import json, time
from typing import Dict, Any, Optional, List
from utils import SESSION, SERP_ZONE, DATASET_ID, google_query_url, backoff_sleep, log

API_SERP     = "https://api.brightdata.com/request"
API_SCRAPE   = "https://api.brightdata.com/datasets/v3/scrape"
API_TRIGGER  = "https://api.brightdata.com/datasets/v3/trigger"
API_SNAPSHOT = "https://api.brightdata.com/datasets/v3/snapshots/"

class LinkedInClient:
    def business_to_profile_url(self, business_name: str) -> Optional[str]:
        return self._serp_first_linkedin_company(business_name)

    def collect_company_payload(self, linkedin_company_url: str) -> Dict[str, Any]:
        return self._collect_linkedin_company(linkedin_company_url)

    def extract_company_website(self, company_payload: Dict[str, Any]) -> str:
        return self._extract_company_website(company_payload)

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

    def _poll_snapshot(self, snapshot_id: str, ttl_secs: int = 60) -> Dict[str, Any]:
        deadline = time.time() + ttl_secs
        while time.time() < deadline:
            s = SESSION.get(f"{API_SNAPSHOT}{snapshot_id}", timeout=60)
            if s.status_code == 200:
                try:
                    return s.json()
                except Exception:
                    return {"raw": s.text}
            time.sleep(3)
        return {"status": "pending", "snapshot_id": snapshot_id}

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
        if not isinstance(company_payload, dict):
            return ""
        site = self._drill_for_website(company_payload)
        if site and not site.startswith("http"):
            site = "https://" + site.lstrip("/")
        return site

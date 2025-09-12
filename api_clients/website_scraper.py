import re
from typing import Dict, List, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from utils import BROWSER, log

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?)?\d{3,4}[\s.\-]?\d{4})")
COMMON_PATHS = ["", "/contact", "/contact-us", "/contacts", "/about", "/about-us", "/impressum", "/support", "/help"]

class WebsiteScraper:
    def _safe_get(self, url: str) -> str:
        try:
            resp = BROWSER.get(url, timeout=20)
            if 200 <= resp.status_code < 300 and resp.text:
                return resp.text
        except Exception as e:
            log.debug(f"[GET] {url} failed: {e}")
        return ""

    def _extract_from_html(self, html: str, base_url: str = "") -> Dict[str, Set[str]]:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text("\n", strip=True)

        emails = set(EMAIL_RE.findall(text))
        phones = set(PHONE_RE.findall(text))

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.lower().startswith("mailto:"):
                emails.add(href.split(":", 1)[1])
            if href.lower().startswith("tel:"):
                phones.add(href.split(":", 1)[1])

        contact_link = None
        for a in soup.find_all("a", href=True):
            txt = (a.get_text() or "").lower()
            href = a["href"]
            if any(k in txt for k in ["contact", "support", "help"]) and not href.startswith("mailto:"):
                contact_link = urljoin(base_url, href)
                break

        return {
            "emails": emails,
            "phones": phones,
            "contact_link": contact_link
        }

    def _normalize_site(self, url: str) -> str:
        if not url:
            return ""
        u = url.strip()
        if not u.startswith("http"):
            u = "https://" + u.lstrip("/")
        return u.rstrip("/")

    def fetch_site_contacts(self, website_url: str) -> Dict[str, List[str]]:
        site = self._normalize_site(website_url)
        if not site:
            return {"emails": [], "phones": []}

        emails, phones = set(), set()
        parsed = urlparse(site)
        base = f"{parsed.scheme}://{parsed.netloc}"

        for path in COMMON_PATHS:
            url = site if path == "" else urljoin(base + "/", path.lstrip("/"))
            html = self._safe_get(url)
            if not html:
                continue
            found = self._extract_from_html(html, base)
            emails |= found["emails"]
            phones |= found["phones"]

        home_html = self._safe_get(site)
        if home_html:
            found = self._extract_from_html(home_html, base)
            clink = found.get("contact_link")
            if clink:
                html = self._safe_get(clink)
                if html:
                    f2 = self._extract_from_html(html, base)
                    emails |= f2["emails"]
                    phones |= f2["phones"]

        clean_emails = sorted({e.strip().strip(".") for e in emails if "@" in e})
        clean_phones = sorted({re.sub(r"\s{2,}", " ", p).strip() for p in phones})
        return {"emails": clean_emails, "phones": clean_phones}

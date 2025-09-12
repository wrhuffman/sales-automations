import os, time, requests, urllib.parse, logging
from dotenv import load_dotenv

load_dotenv()
API_KEY    = os.getenv("BRIGHTDATA_API_KEY")
SERP_ZONE  = os.getenv("BRIGHTDATA_API_ZONE")
DATASET_ID = os.getenv("BD_COMPANY_DATASET_ID")

if not API_KEY or not SERP_ZONE or not DATASET_ID:
    raise RuntimeError("Missing BRIGHTDATA_API_KEY / BRIGHTDATA_API_ZONE / BD_COMPANY_DATASET_ID in .env")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
})

BROWSER = requests.Session()
BROWSER.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36"
})

def google_query_url(q: str) -> str:
    return f"https://www.google.com/search?q={urllib.parse.quote(q)}&brd_json=1"

def backoff_sleep(attempt: int):
    time.sleep(min(2 ** attempt, 30))

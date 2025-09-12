import os, json, urllib.parse, requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("BRIGHTDATA_API_KEY")
ZONE    = os.getenv("BRIGHTDATA_API_ZONE")

assert API_KEY, "Missing BRIGHTDATA_API_KEY in .env"
assert ZONE,    "Missing BRIGHTDATA_API_ZONE in .env"

print(".env loaded")
session = requests.Session()
session.headers.update({"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})

q = urllib.parse.quote("site:linkedin.com/company Bright Data")
url = f"https://www.google.com/search?q={q}&brd_json=1"
payload = {"zone": ZONE, "url": url, "format": "raw"}

r = session.post("https://api.brightdata.com/request", json=payload, timeout=60)
print("HTTP", r.status_code)
print("Payload snippet:", (r.text or "")[:300])
try:
    data = r.json()
    org = data.get("organic", [])
    if org:
        print("First result:", org[0].get("link") or org[0].get("url"))
    else:
        print("No organic results in response JSON.")
except Exception:
    print("Response was not JSON (check zone type / permissions / balance).")

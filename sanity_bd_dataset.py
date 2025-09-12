import os, requests, json
from dotenv import load_dotenv

load_dotenv()
API_KEY  = os.getenv("BRIGHTDATA_API_KEY")
DATASET  = os.getenv("BD_COMPANY_DATASET_ID")
assert API_KEY and DATASET, "Missing API key or dataset id"

s = requests.Session()
s.headers.update({"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})

body = {"dataset_id": DATASET, "input": [{"url": "https://www.linkedin.com/company/fitness-19"}]}
r = s.post("https://api.brightdata.com/datasets/v3/scrape", json=body, timeout=60)
print("HTTP", r.status_code)
print((r.text or "")[:800])

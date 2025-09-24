import json
import pandas as pd
from clients.linkedin_client import LinkedInClient
from clients.website_client import WebsiteClient

def run_from_csv(input_csv="sample_names.csv", output_csv="output.csv"):
    df = pd.read_csv(input_csv)
    names = df["business_name"].dropna().astype(str).tolist()

    li = LinkedInClient()
    ws = WebsiteClient()

    results = []
    for name in names:
        print(f"\n {name}")
        info = li.enrich_business(name)
        website = info.get("website", "")

        emails, phones = [], []
        if website:
            print("Crawling website for contact info…")
            contacts = ws.fetch_site_contacts(website)
            emails = contacts["emails"]
            phones = contacts["phones"]

        results.append({
            "business_name": name,
            "linkedin_company_url": info.get("linkedin_company_url", ""),
            "website": website,
            "emails": emails,
            "phones": phones,
            "status": info.get("status", "")
        })

    out = pd.DataFrame(results)
    out.to_csv(output_csv, index=False)
    print(f"\n Saved results to {output_csv}")
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    print("search_by_name running…")
    run_from_csv()

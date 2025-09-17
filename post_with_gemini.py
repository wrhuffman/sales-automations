from dotenv import load_dotenv
load_dotenv()

import argparse, textwrap
from api_clients.gemini_client import GeminiClient
from api_clients.linkedin_poster_client import LinkedInPosterClient

def run(subject: str, name: str = None, link: str = None, auto: bool = False):
    gem = GeminiClient()
    draft = gem.draft_post(subject=subject, company_name=name, link=link)

    print("\n--- Draft Post ---\n")
    print(textwrap.fill(draft, width=100, replace_whitespace=False))
    print("\n------------------\n")

    if not auto:
        if input("Post this? (y/n): ").strip().lower() != "y":
            print("Cancelled.")
            return

    li = LinkedInPosterClient()
    print("Author URN:", li.get_member_urn())

    res = li.create_text_post(draft)
    print("Posted successfully.\nResponse:\n", res)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--subject", required=True)
    p.add_argument("--name")
    p.add_argument("--link")
    p.add_argument("--auto", action="store_true")
    args = p.parse_args()
    run(subject=args.subject, name=args.name, link=args.link, auto=args.auto)

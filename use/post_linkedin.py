from dotenv import load_dotenv
load_dotenv()

import argparse, textwrap
from clients.gemini_client import GeminiClient
from clients.linkedin_client import LinkedInClient

def build_linkedin_prompt(subject: str,
                          company_name: str | None = None,
                          link: str | None = None,
                          tone: str = "professional, concise, engaging",
                          max_chars: int = 700,
                          add_hashtags: bool = True) -> str:
    """Prompt stays in 'use' layer (not inside the Gemini client)."""
    return f"""You are drafting a LinkedIn post.

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

def run(subject: str, name: str = None, link: str = None, auto: bool = False):
    # 1) Draft with Gemini
    gem = GeminiClient()
    prompt = build_linkedin_prompt(subject=subject, company_name=name, link=link)
    gen = gem.generate(prompt)
    draft = gen["text"]

    # 2) Show draft, ask confirmation
    print("\n--- Draft Post ---\n")
    print(textwrap.fill(draft, width=100, replace_whitespace=False))
    print("\n------------------\n")

    if not auto:
        if input("Post this? (y/n): ").strip().lower() != "y":
            print("Cancelled.")
            return

    # 3) Post to LinkedIn
    li = LinkedInClient()
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

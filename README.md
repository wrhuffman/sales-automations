# LinkedInAPI — Quick Start Guide

This guide shows you **exactly** how to:
1) **Search by business name** → find LinkedIn company page → find official website → extract **emails/phones**.
2) **Draft a LinkedIn post with Gemini** → **confirm** → **publish** to LinkedIn (or auto-post).


## 0) Repo Layout

```
.
├─ clients/                 # pure, reusable clients (no prompts here)
│  ├─ gemini_client.py
│  ├─ linkedin_client.py
│  └─ website_client.py
├─ use/                     # "use cases" (scripts) with prompts/orchestration
│  ├─ post_linkedin.py      # build prompt → draft → confirm → post
│  └─ search_by_name.py     # CSV → enrich (LI URL + website + contacts) → CSV
├─ utils.py                 # shared HTTP sessions, logging, Bright Data helpers
├─ sample_names.csv         # example input (must have column: business_name)
├─ output.csv               # last enrichment output (auto-created)
├─ requirements.txt
└─ .env                     # your secrets (see below)
```

---

## 1) Requirements

- **Python 3.10+**
- Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 2) Environment Variables (`.env`)

Create a **`.env`** file at the repo root with:

```ini
# --- Bright Data (SERP + Dataset scraping) ---
BRIGHTDATA_API_KEY=YOUR_BRIGHTDATA_API_KEY
BRIGHTDATA_API_ZONE=YOUR_SERP_ZONE_ID
BD_COMPANY_DATASET_ID=YOUR_DATASET_ID

# --- LinkedIn API (for posting) ---
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_REDIRECT_URI=
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_ACCESS_TOKEN=
# LINKEDIN_MEMBER_URN=urn:li:person:xxxxxxxxxxxxxxxx

# --- Gemini (for drafting copy) ---
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
# Optional:
GEMINI_MODEL=gemini-1.5-flash

---

## 3) Use Case A — Search by Name (enrichment)

### What it does
- Reads **`sample_names.csv`** (must contain a column named `business_name`).
- For each business name:
  - Finds the **LinkedIn company URL** (via Bright Data SERP).
  - Retrieves a **company payload** (via Bright Data Dataset).
  - Extracts the **official website** (or falls back to SERP).
  - Crawls common pages on the site to collect **emails** and **phone numbers**.
- Writes results to **`output.csv`** and prints JSON to the console.

### Input CSV format
`sample_names.csv` should look like:

```csv
business_name
Acme Fitness Paris
Hidev Mobile
Cool Beans Coffee
```

### Run it (from repo root)

```bash
python -m use.search_by_name
```

This uses the defaults:
- **Input:** `sample_names.csv` at the repo root  
- **Output:** `output.csv` at the repo root

> If you see `FileNotFoundError: sample_names.csv`, you’re likely running from the wrong working directory. Run the command **from the project root** (folder that contains `sample_names.csv`).

---

## 4) Use Case B — Draft & Post to LinkedIn (Gemini → Confirm → Post)

### What it does
- Builds a **LinkedIn-style prompt** (the prompt lives **inside** `use/post_linkedin.py`).
- Calls **Gemini** to generate a **draft**.
- Shows the draft and asks: **“Post this? (y/n)”**
- If `y`, posts to LinkedIn through the API.

### Run it (from repo root)

```bash
python -m use.post_linkedin --subject "Still testing projects with Gemini" --name "Hi Dev" --link "https://www.hidevmobile.com/"
```

**Auto-post** (skip confirmation prompt):

```bash
python -m use.post_linkedin --subject "Daily ship notes" --auto
```

> **PowerShell gotcha:** If you paste only `--subject ...` without `python ...` first, PowerShell throws `Missing expression after unary operator '--'`. Always start with `python ...`.

---

## 5) Prompt (where to edit)

Prompts **do not** live in the Gemini client.  
Edit the LinkedIn prompt directly in **`use/post_linkedin.py`**:

```python
def build_linkedin_prompt(subject, company_name=None, link=None, tone="professional, concise, engaging", max_chars=700, add_hashtags=True):
    # customize style, constraints, etc.
    ...
```

This keeps **clients** generic and **use** scripts channel-specific.

---

## 6) Automation (Windows Task Scheduler)

You can automate posting (e.g., daily status with `--auto`).

1. Open **Task Scheduler** → **Create Basic Task…**
2. Name it (e.g., “LinkedIn Auto Post”).
3. Trigger: **Daily** (pick time).
4. Action: **Start a program**
   - **Program/script:** `python`
   - **Add arguments:** `-m use.post_linkedin --subject "Daily update" --name "Hi Dev" --link "https://www.hidevmobile.com/" --auto`
   - **Start in:** full path to your repo folder (e.g., `C:\Users\Anwar\PycharmProjects\LinkedInAPI`)
5. Finish.

> Alternative: create a `.bat` file that runs the command above and schedule the `.bat`.

---

## 7) Troubleshooting

**A) `FileNotFoundError: sample_names.csv`**  
- Run from the repo root: `python -m use.search_by_name`  
- Make sure `sample_names.csv` exists and has column `business_name`.

**B) LinkedIn 401 / 403**  
- `LINKEDIN_ACCESS_TOKEN` expired or lacks scope.  
- Verify token in `.env`. If needed, refresh your token via your OAuth process.

**C) Bright Data errors**  
- Check `BRIGHTDATA_API_KEY`, `BRIGHTDATA_API_ZONE`, `BD_COMPANY_DATASET_ID`.  
- SERP or Dataset may be pending; the client retries with backoff.  
- If rate-limited: wait a bit and retry.

**D) Gemini issues**  
- `GEMINI_API_KEY` missing/invalid → set it in `.env`.  
- `ResourceExhausted` → client auto-falls back to the fallback model; try again.

**E) PowerShell parsing flags**  
- Always start commands with `python -m use.script_name ...`

---

## 8) Notes & Limits

- **Clients** are intentionally generic:
  - `clients/gemini_client.py` — no LinkedIn/WhatsApp logic inside.
  - `clients/linkedin_client.py` — all LinkedIn ops (discovery + scrape + posting).
  - `clients/website_client.py` — generic site fetch & contact extraction.
- **Use scripts** own the **prompts** and **composition**.
- Respect **LinkedIn posting limits** and best practices. Consider a cooldown between posts if you automate frequently.

---

## 9) One-Page Quick Start

```bash
# 1) Install
pip install -r requirements.txt

# 2) Set secrets in .env (Bright Data, LinkedIn, Gemini)

# 3) Enrich companies from CSV
python -m use.search_by_name

# 4) Draft + post on LinkedIn (confirm interactively)
python -m use.post_linkedin --subject "Testing Gemini" --name "Hi Dev" --link "https://www.hidevmobile.com/"

# 5) Auto-post (no prompt)
python -m use.post_linkedin --subject "Automated daily update" --auto
```

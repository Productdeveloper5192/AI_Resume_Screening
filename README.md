# AI Resume Screener

A Streamlit web app that screens resumes against your own hiring requirements using Claude.

You set the requirements and upload resumes. For each candidate, Claude checks every requirement (Met / Partial / Not met, with evidence quoted from the resume), gives a score from 0 to 100 and writes interview questions. The app then decides **SHORTLISTED** or **NOT SHORTLISTED** and tells you why.

---

## 1. Features

| Feature | What it does |
|---|---|
| Custom requirements | Must-have skills, nice-to-have skills, minimum years of experience, education, other criteria, and an optional job description |
| Bulk upload | Many resumes at once: PDF, DOCX or TXT. Up to 4 are screened in parallel. |
| Requirement check | One row per requirement: ✅ Met / 🟡 Partial / ❌ Not met, with evidence from the resume |
| Shortlist decision | Shortlisted only if **every must-have is Met** and **score ≥ threshold** (default 70). Otherwise the app lists the reasons. |
| Score and ranking | A score from 0 to 100 and a fit label (Strong / Good / Possible / Not a fit). Candidates are ranked by score. |
| Interview questions | 4–6 questions per candidate that check claimed strengths and probe gaps |
| Export | Excel report (Candidates + Requirement checks sheets), CSV of all candidates, CSV of the shortlist |
| Templates | Save requirements for a role and reload them later in one click |
| Demo mode | One button screens 6 sample resumes against a sample "Data Scientist" role |
| History | Every run is saved as JSON in `screening_history/` and logged to the console |

---

## 2. How it works (end to end)

```
 ┌──────────────┐   requirements + resumes   ┌──────────────┐
 │  Browser UI  │ ─────────────────────────▶ │    app.py    │  Streamlit
 │ (Streamlit)  │ ◀───────────────────────── │              │
 └──────────────┘   verdicts, tables, files  └──────┬───────┘
                                                    │ for each resume (4 in parallel)
                                                    ▼
                                ┌────────────────────────────────────┐
                                │ parsers.py                         │
                                │  PDF  → sent to Claude as-is       │
                                │  DOCX → text (python-docx)         │
                                │  TXT  → text                       │
                                └──────────────┬─────────────────────┘
                                               ▼
                                ┌────────────────────────────────────┐
                                │ screener.py                        │
                                │  system prompt = requirements      │
                                │  (cached, reused for every resume) │
                                │  user message  = the resume        │
                                │  output = strict JSON schema       │
                                └──────────────┬─────────────────────┘
                                               ▼
                                   Claude (Azure Foundry or Claude API)
                                               │
                                               ▼  JSON: score, requirement checks,
                                                  strengths, concerns, questions
                                ┌────────────────────────────────────┐
                                │ app.py — shortlist rule            │
                                │  all must-haves Met AND            │
                                │  score ≥ threshold → SHORTLISTED   │
                                └──────────────┬─────────────────────┘
                                               ▼
                     UI results  ·  export.py (Excel/CSV)  ·  screening_history/*.json
```

1. **Input.** The recruiter fills in requirements in the sidebar (or loads a template) and uploads resumes.
2. **Parsing.** `parsers.py` turns each file into a Claude content block. PDFs go to Claude natively, so tables and multi-column layouts survive.
3. **Screening.** `screener.py` sends one request per resume:
   - The **system prompt** holds the scoring rules and your requirements. It is marked for prompt caching, so later resumes in the batch cost less.
   - The **output** is constrained to a JSON schema, so the response always parses.
   - The prompt tells Claude to judge on evidence only, ignore keyword stuffing, ignore protected characteristics, and cap the score at 60 if any must-have is missing.
4. **Decision.** `app.py` applies the shortlist rule: every must-have is Met **and** score ≥ threshold.
5. **Output.** The app shows ranked results and verdicts, offers downloads (`export.py`), and saves a JSON history file.

---

## 3. Project structure

```
resume_screener/
├── app.py                  # Streamlit UI, shortlist rule, demo, history
├── screener.py             # Claude client, prompt, JSON schema, screen_resume()
├── parsers.py              # PDF / DOCX / TXT → Claude content blocks
├── export.py               # CSV and Excel exports
├── templates.py            # Save / load / delete requirement templates
├── templates.json          # Saved templates (created automatically)
├── screening_history/      # One JSON file per screening run (created automatically)
├── test_data/
│   ├── generate_test_data.py   # Builds the sample resumes + sample template
│   ├── README.md               # Expected results for the sample data
│   └── resumes/                # 6 sample resumes (PDF, DOCX, TXT)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 4. Data storage (is there a database?)

**There is no database.** The app stores everything as plain files:

| Data | Where it lives | Lifetime |
|---|---|---|
| Uploaded resumes | Memory only (Streamlit session). They are sent to Claude but **never written to disk**. | Until the browser tab closes |
| Current results | Memory only (`st.session_state`) | Until the browser tab closes or new files are uploaded |
| Requirement templates | `templates.json` | Permanent |
| Screening history | `screening_history/<timestamp>.json` (requirements, threshold, every result and verdict) | Permanent |
| API credentials | `.env` | Permanent |

This works for a single user or a small team. For multi-user production use, swap the JSON files for a database such as SQLite or PostgreSQL. `templates.py` and `save_history()` in `app.py` are the only places that would change.

---

## 5. Setup

### Prerequisites
- Python 3.10+
- One of these:
  - **Microsoft Foundry** (Azure) with a Claude deployment
  - an **Anthropic API key**

### Install

```powershell
cd resume_screener
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Configure credentials (`.env`)

The `.env` file can sit in `resume_screener/` or in any parent folder.

**Option A: Microsoft Foundry**
```
CLAUDE_API_KEY=your-foundry-key
CLAUDE_ENDPOINT=https://<resource>.services.ai.azure.com/anthropic
CLAUDE_MODEL_NAME=claude-opus-4-7
```

**Option B: Claude API**
```
ANTHROPIC_API_KEY=sk-ant-...
```
With Option B, leave `CLAUDE_ENDPOINT` unset. The default model is `claude-opus-5-5`.

---

## 6. Run

```powershell
.venv\Scripts\streamlit.exe run app.py
```

Open **http://localhost:8501**.

---

## 7. Quick test with the sample data

Click **🧪 Run demo with 6 sample resumes**. This loads the "Data Scientist (Test)" requirements and screens every file in `test_data/resumes/`.

Expected outcome (scores vary by a few points between runs):

| Candidate | Expected | Why |
|---|---|---|
| Ananya Iyer | 🟢 Shortlisted (~94) | Meets everything |
| Karthik Reddy | 🟢 Shortlisted (~82) | Meets all must-haves |
| Mohammed Faisal | 🔴 Not shortlisted (~58) | AWS and deployment only Partial |
| Sneha Patel | 🔴 Not shortlisted (~55) | Uses GCP, not AWS |
| Arjun Mehta | 🔴 Not shortlisted (~40) | 1 year of experience |
| Divya Nair | 🔴 Not shortlisted (~15) | Keywords listed, no evidence of using them |

To regenerate the sample files:

```powershell
pip install fpdf2
.venv\Scripts\python.exe test_data\generate_test_data.py
```

---

## 8. Screening your own resumes

1. **Set requirements** in the sidebar. You can also pick a template under **Load template**.
   - *Must-have skills:* comma separated, e.g. `Python, SQL, AWS`
   - *Nice-to-have skills:* raise the score but are never required
   - *Minimum years* and *Education:* treated as must-haves
   - *Other criteria:* free text, e.g. "Must have team-lead experience"
   - *Job description (optional):* Claude also derives requirements from it
2. Optionally click **💾 Save** to keep these requirements as a template.
3. **Upload resumes** (PDF / DOCX / TXT). Old `.doc` files must be saved as `.docx` first.
4. Click **🔍 Screen resumes**.
5. Read the results. Each candidate shows a ✅ SHORTLISTED or ❌ NOT SHORTLISTED banner with the reasons, the requirement table, strengths, concerns and interview questions.
6. **Download** the Excel or CSV report.
7. Move the **Shortlist threshold** slider to re-apply the rule instantly. No new API calls are made.

---

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| "No hiring requirements set" | Fill at least one sidebar field or load a template |
| "Invalid or missing Anthropic API key" / "No API key found" | Check the `.env` variable names in section 5 |
| `python-dotenv could not parse statement` in the console | A line in `.env` isn't `KEY=value`. Comment it out with `#`. This is harmless. |
| "Unsupported file type" | Use PDF, DOCX or TXT |
| "No text could be extracted" | The DOCX is empty or image-only. Export it as PDF instead. |
| Results disappeared | Uploading a different set of files clears the old results. Earlier runs are in `screening_history/`. |

---

## 10. Responsible use

Treat the scores as **decision support**, not the final decision. The prompt tells Claude to ignore protected characteristics (name, gender, age, nationality, photos) and to judge only on evidence. A human should still review every shortlist and rejection before acting on it.

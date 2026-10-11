"""AI Resume Screener - Streamlit UI."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from export import requirement_checks_dataframe, results_dataframe, to_csv, to_excel
from screener import Requirements, ScreeningResult, get_client, get_model, screen_resume
from templates import delete_template, load_templates, save_template

load_dotenv()  # searches this folder, then parent folders, for a .env file

MAX_PARALLEL = 4
APP_DIR = Path(__file__).parent
SAMPLE_DIR = APP_DIR / "test_data" / "resumes"
SAMPLE_TEMPLATE = "Data Scientist (Test)"
HISTORY_DIR = APP_DIR / "screening_history"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("screener")

STATUS_ICON = {"Met": "✅", "Partial": "🟡", "Not met": "❌"}
# Widget keys that make up a requirements template
FIELDS = {
    "role_title": "",
    "must_have": "",
    "nice_to_have": "",
    "min_years": 0,
    "education": "",
    "other": "",
    "job_description": "",
}


def split_list(text: str) -> list[str]:
    """Split comma- or newline-separated input into a clean list."""
    return [s.strip() for s in text.replace("\n", ",").split(",") if s.strip()]


def apply_template() -> None:
    name = st.session_state["template_choice"]
    values = load_templates().get(name, {}) if name else {}
    for key, default in FIELDS.items():
        st.session_state[key] = values.get(key, default)


def on_save_template() -> None:
    name = st.session_state["template_name"].strip()
    if not name:
        st.session_state["template_msg"] = ("warning", "Enter a template name first.")
        return
    save_template(name, {key: st.session_state[key] for key in FIELDS})
    st.session_state["template_choice"] = name
    st.session_state["template_name"] = ""
    st.session_state["template_msg"] = ("success", f"Saved template '{name}'.")


def start_demo() -> None:
    """Load the sample requirements template and flag a run on the sample resumes."""
    values = load_templates().get(SAMPLE_TEMPLATE)
    if values is None:
        st.session_state["template_msg"] = (
            "error",
            "Sample template missing. Run: .venv\\Scripts\\python.exe test_data\\generate_test_data.py",
        )
        return
    st.session_state["template_choice"] = SAMPLE_TEMPLATE
    for key, default in FIELDS.items():
        st.session_state[key] = values.get(key, default)
    st.session_state["run_demo"] = True


def save_history(results: list[ScreeningResult], requirements: Requirements, threshold: int) -> Path:
    """Write the run to screening_history/ and log each verdict to the console."""
    HISTORY_DIR.mkdir(exist_ok=True)
    rows = []
    for r in results:
        verdict = "ERROR" if r.error else (
            "SHORTLISTED" if r.score >= threshold and r.must_haves_met else "NOT SHORTLISTED"
        )
        log.info("%-16s %-28s score=%-3s %s", verdict, r.filename, r.score, r.error or "")
        rows.append({"verdict": verdict, **asdict(r)})
    path = HISTORY_DIR / f"{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(
        json.dumps(
            {"threshold": threshold, "requirements": asdict(requirements), "results": rows},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def on_delete_template() -> None:
    name = st.session_state["template_choice"]
    if name:
        delete_template(name)
        st.session_state["template_choice"] = ""
        st.session_state["template_msg"] = ("success", f"Deleted template '{name}'.")


st.set_page_config(page_title="AI Resume Screener", page_icon="📄", layout="wide")
for key, default in FIELDS.items():
    st.session_state.setdefault(key, default)

st.title("📄 AI Resume Screener")
st.caption("Set your hiring requirements, upload resumes, and Claude checks every candidate against them.")

with st.sidebar:
    st.header("Requirement templates")
    templates = load_templates()
    st.selectbox(
        "Load template",
        [""] + sorted(templates),
        key="template_choice",
        format_func=lambda n: n or "— New / blank —",
        on_change=apply_template,
    )
    st.text_input("Save current requirements as", key="template_name", placeholder="e.g. Senior Data Scientist")
    b1, b2 = st.columns(2)
    b1.button("💾 Save", on_click=on_save_template, use_container_width=True)
    b2.button(
        "🗑️ Delete",
        on_click=on_delete_template,
        disabled=not st.session_state["template_choice"],
        use_container_width=True,
    )
    if msg := st.session_state.pop("template_msg", None):
        getattr(st, msg[0])(msg[1])

    st.divider()
    st.header("Hiring requirements")
    st.text_input("Role title", key="role_title", placeholder="e.g. Senior Data Scientist")
    st.text_area(
        "Must-have skills",
        key="must_have",
        placeholder="Python, SQL, Machine Learning, AWS",
        help="Comma or newline separated",
    )
    st.text_area(
        "Nice-to-have skills",
        key="nice_to_have",
        placeholder="PyTorch, Docker, LLMs",
        help="Comma or newline separated",
    )
    st.number_input("Minimum years of experience", min_value=0, max_value=40, key="min_years")
    st.text_input("Education requirement", key="education", placeholder="e.g. Bachelor's in CS or related field")
    st.text_area(
        "Other criteria",
        key="other",
        placeholder="e.g. Must be open to relocate to Bangalore; team-lead experience preferred",
    )
    threshold = st.slider("Shortlist threshold (score)", 0, 100, 70)
    st.caption(f"Model: `{get_model()}`")

st.text_area(
    "Job description (optional — adds context on top of the requirements)",
    key="job_description",
    height=150,
    placeholder="Paste the full job description...",
)
uploads = st.file_uploader(
    "Resumes (PDF, DOCX or TXT)",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=True,
)

requirements = Requirements(
    role_title=st.session_state["role_title"],
    must_have_skills=split_list(st.session_state["must_have"]),
    nice_to_have_skills=split_list(st.session_state["nice_to_have"]),
    min_years_experience=int(st.session_state["min_years"]),
    education=st.session_state["education"],
    other_criteria=st.session_state["other"],
    job_description=st.session_state["job_description"],
)

upload_signature = sorted((f.name, f.size) for f in uploads or [])
if st.session_state.get("results_for") != upload_signature:
    st.session_state.pop("results", None)  # results belong to a different set of files

if uploads and not st.session_state.get("results"):
    st.info(f"{len(uploads)} resume(s) ready. Click **Screen resumes** to check who gets shortlisted.")

b_screen, b_demo = st.columns([1, 1])
screen_clicked = b_screen.button("🔍 Screen resumes", type="primary", use_container_width=True)
b_demo.button(
    f"🧪 Run demo with {len(list(SAMPLE_DIR.glob('*.*'))) if SAMPLE_DIR.exists() else 0} sample resumes",
    on_click=start_demo,
    use_container_width=True,
    help="Loads the 'Data Scientist (Test)' requirements and screens the resumes in test_data/resumes",
)
run_demo = st.session_state.pop("run_demo", False)

if screen_clicked or run_demo:
    if run_demo:
        files = [(p.name, p.read_bytes()) for p in sorted(SAMPLE_DIR.iterdir()) if p.is_file()]
        st.info(f"Demo: screening {len(files)} sample resumes against the '{SAMPLE_TEMPLATE}' requirements.")
    else:
        problems = []
        if requirements.is_empty():
            problems.append(
                "No hiring requirements set. Fill in the sidebar (must-have skills, experience, ...) "
                "or pick a saved template under **Load template**."
            )
        if not uploads:
            problems.append("No resumes uploaded.")
        for p in problems:
            st.warning(p)
        if problems:
            st.stop()
        files = [(f.name, f.getvalue()) for f in uploads]

    try:
        client = get_client()
    except RuntimeError as e:
        st.error(str(e))
        st.stop()
    log.info("Screening %d resume(s): %s", len(files), ", ".join(n for n, _ in files))
    results: list[ScreeningResult] = []

    progress = st.progress(0.0, text=f"Screening 0 of {len(files)}...")
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        futures = [
            pool.submit(screen_resume, client, requirements, name, data)
            for name, data in files
        ]
        for i, future in enumerate(as_completed(futures), start=1):
            results.append(future.result())
            progress.progress(i / len(files), text=f"Screening {i} of {len(files)}...")
    progress.empty()

    st.session_state["results"] = results
    st.session_state["results_for"] = upload_signature
    saved = save_history(results, requirements, threshold)
    st.caption(f"Saved to `{saved.relative_to(APP_DIR)}`")

results: list[ScreeningResult] = st.session_state.get("results", [])
if results:
    ok = sorted((r for r in results if not r.error), key=lambda r: r.score, reverse=True)
    failed = [r for r in results if r.error]
    shortlisted = [r for r in ok if r.score >= threshold and r.must_haves_met]

    c1, c2, c3 = st.columns(3)
    c1.metric("Screened", len(ok))
    c2.metric("Shortlisted", len(shortlisted))
    c3.metric("Not shortlisted", len(ok) - len(shortlisted))

    if ok:
        summary_df = results_dataframe(ok, shortlisted)
        checks_df = requirement_checks_dataframe(ok)
        role = st.session_state["role_title"].strip().replace(" ", "_") or "screening"
        d1, d2, d3 = st.columns(3)
        d1.download_button(
            "⬇️ Excel report (all candidates)",
            to_excel(summary_df, checks_df),
            file_name=f"{role}_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        d2.download_button(
            "⬇️ CSV (all candidates)",
            to_csv(summary_df),
            file_name=f"{role}_results.csv",
            mime="text/csv",
            use_container_width=True,
        )
        d3.download_button(
            "⬇️ CSV (shortlist only)",
            to_csv(summary_df[summary_df["Status"] == "Shortlisted"]),
            file_name=f"{role}_shortlist.csv",
            mime="text/csv",
            disabled=not shortlisted,
            use_container_width=True,
        )

    st.subheader("Ranked candidates")
    for rank, r in enumerate(ok, start=1):
        badge = "🟢 Shortlisted" if r in shortlisted else "🔴 Not shortlisted"
        # Expand automatically when only one resume was screened
        with st.expander(
            f"#{rank} · {r.candidate_name} — {r.score}/100 · {r.recommendation} · {badge}",
            expanded=len(ok) == 1,
        ):
            if r in shortlisted:
                st.success(
                    f"✅ **SHORTLISTED** — meets every must-have and scored {r.score} "
                    f"(threshold {threshold})."
                )
            else:
                reasons = [
                    f"must-have **{c['requirement']}** is {c['status'].lower()}"
                    for c in r.requirement_checks
                    if c["priority"] == "Must-have" and c["status"] != "Met"
                ]
                if r.score < threshold:
                    reasons.append(f"score {r.score} is below the threshold of {threshold}")
                st.error("❌ **NOT SHORTLISTED** — " + "; ".join(reasons) + ".")
            st.markdown(f"**File:** {r.filename} · **Relevant experience:** {r.years_experience} years")
            st.progress(r.score / 100)
            st.write(r.summary)

            st.markdown("**Requirement check**")
            st.table(
                [
                    {
                        "Requirement": c["requirement"],
                        "Priority": c["priority"],
                        "Status": f"{STATUS_ICON[c['status']]} {c['status']}",
                        "Evidence": c["evidence"],
                    }
                    for c in r.requirement_checks
                ]
            )

            left, right = st.columns(2)
            with left:
                st.markdown("**💪 Strengths**")
                for s in r.strengths:
                    st.markdown(f"- {s}")
            with right:
                st.markdown("**⚠️ Concerns**")
                for c in r.concerns:
                    st.markdown(f"- {c}")

            st.markdown("**🎤 Suggested interview questions**")
            for i, q in enumerate(r.interview_questions, start=1):
                st.markdown(f"{i}. {q}")

    for r in failed:
        st.error(f"{r.filename}: {r.error}")

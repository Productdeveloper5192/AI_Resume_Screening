"""Build CSV and Excel exports of screening results."""

import io

import pandas as pd

from screener import ScreeningResult


def results_dataframe(ranked: list[ScreeningResult], shortlisted: list[ScreeningResult]) -> pd.DataFrame:
    rows = []
    for rank, r in enumerate(ranked, start=1):
        gaps = [c["requirement"] for c in r.requirement_checks if c["status"] != "Met"]
        rows.append(
            {
                "Rank": rank,
                "Candidate": r.candidate_name,
                "File": r.filename,
                "Score": r.score,
                "Recommendation": r.recommendation,
                "Status": "Shortlisted" if r in shortlisted else "Rejected",
                "All must-haves met": "Yes" if r.must_haves_met else "No",
                "Relevant experience (yrs)": r.years_experience,
                "Gaps": "; ".join(gaps),
                "Summary": r.summary,
                "Strengths": "; ".join(r.strengths),
                "Concerns": "; ".join(r.concerns),
                "Interview questions": "\n".join(r.interview_questions),
            }
        )
    return pd.DataFrame(rows)


def requirement_checks_dataframe(ranked: list[ScreeningResult]) -> pd.DataFrame:
    rows = [
        {
            "Candidate": r.candidate_name,
            "File": r.filename,
            "Requirement": c["requirement"],
            "Priority": c["priority"],
            "Status": c["status"],
            "Evidence": c["evidence"],
        }
        for r in ranked
        for c in r.requirement_checks
    ]
    return pd.DataFrame(rows)


def to_csv(df: pd.DataFrame) -> bytes:
    # utf-8-sig so Excel opens it with the right encoding
    return df.to_csv(index=False).encode("utf-8-sig")


def to_excel(summary: pd.DataFrame, checks: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Candidates", index=False)
        checks.to_excel(writer, sheet_name="Requirement checks", index=False)
        for sheet in writer.sheets.values():
            for col in sheet.columns:
                width = max(len(str(cell.value or "")) for cell in col[:50])
                sheet.column_dimensions[col[0].column_letter].width = min(max(width, 10), 60)
    return buf.getvalue()

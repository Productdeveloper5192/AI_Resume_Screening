"""Score a resume against the recruiter's requirements with Claude."""

import json
import os
from dataclasses import dataclass, field

import anthropic

from parsers import resume_to_content

DEFAULT_MODEL = "claude-opus-5-5"


def get_model() -> str:
    return os.environ.get("CLAUDE_MODEL_NAME") or DEFAULT_MODEL


def uses_foundry() -> bool:
    return bool(os.environ.get("CLAUDE_ENDPOINT"))


def get_client() -> anthropic.Anthropic:
    """Microsoft Foundry when CLAUDE_ENDPOINT is set, otherwise the Claude API.

    Raises RuntimeError if no credentials are configured.
    """
    if uses_foundry():
        api_key = os.environ.get("CLAUDE_API_KEY")
        if not api_key:
            raise RuntimeError("CLAUDE_ENDPOINT is set but CLAUDE_API_KEY is missing from .env")
        return anthropic.AnthropicFoundry(api_key=api_key, base_url=os.environ["CLAUDE_ENDPOINT"])
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise RuntimeError("No API key found. Set ANTHROPIC_API_KEY (or CLAUDE_ENDPOINT + CLAUDE_API_KEY) in .env")
    return anthropic.Anthropic()

SYSTEM_PROMPT = """You are an experienced technical recruiter screening resumes against the hiring requirements below.

Check the resume against every listed requirement and judge it strictly on evidence in the resume: \
skills actually used in roles or projects, experience depth and recency, education and certifications, \
and measurable achievements. Do not reward keyword stuffing, and do not let name, gender, age, \
nationality, photos or other protected characteristics influence the assessment.

Must-have requirements dominate the score. A candidate who clearly misses any must-have \
cannot score above 60. Nice-to-haves only move the score within its band.

Scoring guide (0-100):
- 85-100: meets all must-haves and most nice-to-haves; strong evidence
- 70-84: meets the must-haves with minor gaps
- 50-69: partial match; notable gaps a hiring manager should weigh
- 0-49: missing core requirements

{requirements}"""

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "candidate_name": {
            "type": "string",
            "description": "Full name from the resume, or 'Unknown' if absent",
        },
        "score": {"type": "integer", "description": "Overall match score from 0 to 100"},
        "recommendation": {
            "type": "string",
            "enum": ["Strong fit", "Good fit", "Possible fit", "Not a fit"],
        },
        "years_experience": {
            "type": "string",
            "description": "Relevant years of experience, e.g. '5' or 'unclear'",
        },
        "summary": {"type": "string", "description": "2-3 sentence assessment"},
        "requirement_checks": {
            "type": "array",
            "description": "One entry per listed requirement, in the order given",
            "items": {
                "type": "object",
                "properties": {
                    "requirement": {"type": "string"},
                    "priority": {"type": "string", "enum": ["Must-have", "Nice-to-have"]},
                    "status": {"type": "string", "enum": ["Met", "Partial", "Not met"]},
                    "evidence": {
                        "type": "string",
                        "description": "Short quote or fact from the resume, or 'No evidence found'",
                    },
                },
                "required": ["requirement", "priority", "status", "evidence"],
                "additionalProperties": False,
            },
        },
        "strengths": {"type": "array", "items": {"type": "string"}},
        "concerns": {"type": "array", "items": {"type": "string"}},
        "interview_questions": {
            "type": "array",
            "description": "4-6 questions tailored to this candidate: verify claimed strengths, "
            "and probe Partial/Not met requirements and concerns",
            "items": {"type": "string"},
        },
    },
    "required": [
        "candidate_name",
        "score",
        "recommendation",
        "years_experience",
        "summary",
        "requirement_checks",
        "strengths",
        "concerns",
        "interview_questions",
    ],
    "additionalProperties": False,
}


@dataclass
class Requirements:
    role_title: str = ""
    must_have_skills: list[str] = field(default_factory=list)
    nice_to_have_skills: list[str] = field(default_factory=list)
    min_years_experience: int = 0
    education: str = ""
    other_criteria: str = ""
    job_description: str = ""

    def is_empty(self) -> bool:
        return not (
            self.must_have_skills
            or self.nice_to_have_skills
            or self.min_years_experience
            or self.education.strip()
            or self.other_criteria.strip()
            or self.job_description.strip()
        )

    def to_prompt(self) -> str:
        lines = ["<requirements>"]
        if self.role_title.strip():
            lines.append(f"Role: {self.role_title.strip()}")
        must = list(self.must_have_skills)
        if self.min_years_experience:
            must.append(f"At least {self.min_years_experience} years of relevant experience")
        if self.education.strip():
            must.append(f"Education: {self.education.strip()}")
        if must:
            lines.append("Must-have:")
            lines += [f"- {m}" for m in must]
        if self.nice_to_have_skills:
            lines.append("Nice-to-have:")
            lines += [f"- {n}" for n in self.nice_to_have_skills]
        if self.other_criteria.strip():
            lines.append(f"Other criteria (must-have unless stated otherwise):\n{self.other_criteria.strip()}")
        lines.append("</requirements>")
        if self.job_description.strip():
            lines.append(
                "<job_description>\n"
                f"{self.job_description.strip()}\n"
                "</job_description>\n"
                "Also derive the key requirements from the job description and include them in requirement_checks."
            )
        return "\n".join(lines)


@dataclass
class ScreeningResult:
    filename: str
    candidate_name: str = ""
    score: int = 0
    recommendation: str = ""
    years_experience: str = ""
    summary: str = ""
    requirement_checks: list[dict] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)
    interview_questions: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def must_haves_met(self) -> bool:
        return all(
            c["status"] == "Met" for c in self.requirement_checks if c["priority"] == "Must-have"
        )


def screen_resume(
    client: anthropic.Anthropic, requirements: Requirements, filename: str, data: bytes
) -> ScreeningResult:
    try:
        resume_block = resume_to_content(filename, data)
        model = get_model()
        extra = {}
        if not uses_foundry() and model in ("claude-opus-5-5", "claude-opus-5", "claude-fable-5-1"):
            # If a safety classifier declines, the Claude API retries on a fallback model.
            extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
        response = client.beta.messages.create(
            model=model,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={
                "effort": "medium",
                "format": {"type": "json_schema", "schema": RESULT_SCHEMA},
            },
            **extra,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT.format(requirements=requirements.to_prompt()),
                    # Same requirements for every resume in the batch, so cache them.
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        resume_block,
                        {"type": "text", "text": "Screen this resume against the requirements."},
                    ],
                }
            ],
        )
    except ValueError as e:
        return ScreeningResult(filename=filename, error=str(e))
    except anthropic.AuthenticationError:
        return ScreeningResult(filename=filename, error="Invalid or missing Anthropic API key.")
    except anthropic.RateLimitError:
        return ScreeningResult(filename=filename, error="Rate limited by the API. Try again shortly.")
    except anthropic.APIStatusError as e:
        return ScreeningResult(filename=filename, error=f"API error {e.status_code}: {e.message}")
    except anthropic.APIConnectionError:
        return ScreeningResult(filename=filename, error="Could not connect to the Anthropic API.")

    if response.stop_reason == "refusal":
        return ScreeningResult(filename=filename, error="The model declined to screen this resume.")
    if response.stop_reason == "max_tokens":
        return ScreeningResult(filename=filename, error="Response was cut off (max_tokens).")

    text = next(b.text for b in response.content if b.type == "text")
    parsed = json.loads(text)
    parsed["score"] = max(0, min(100, int(parsed["score"])))
    return ScreeningResult(filename=filename, **parsed)

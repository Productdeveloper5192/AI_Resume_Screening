"""Save and load requirement templates as JSON next to the app."""

import json
from pathlib import Path

TEMPLATES_FILE = Path(__file__).parent / "templates.json"


def load_templates() -> dict[str, dict]:
    if not TEMPLATES_FILE.exists():
        return {}
    try:
        return json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_template(name: str, values: dict) -> None:
    templates = load_templates()
    templates[name] = values
    TEMPLATES_FILE.write_text(json.dumps(templates, indent=2), encoding="utf-8")


def delete_template(name: str) -> None:
    templates = load_templates()
    templates.pop(name, None)
    TEMPLATES_FILE.write_text(json.dumps(templates, indent=2), encoding="utf-8")

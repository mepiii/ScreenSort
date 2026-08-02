"""Purpose: classifier taxonomy loading. Callers: classifier and tests. Deps: dataclasses, json, pathlib. API: Taxonomy, load_taxonomy, default prompt constants. Side effects: reads optional taxonomy JSON file."""
import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CATEGORY_PROMPTS: dict[str, str] = {
    "work": "a screenshot related to work",
    "personal": "a personal screenshot",
    "social media": "a social media screenshot",
    "documentation": "a screenshot of documentation",
    "shopping": "a screenshot of shopping",
    "finance": "a screenshot of finance",
    "code": "a screenshot of code",
}

DEFAULT_TAG_PROMPTS: dict[str, str] = {
    "meeting": "meeting",
    "important": "important",
    "recipe": "recipe",
    "error": "error message",
    "invoice": "invoice",
    "chat": "chat conversation",
    "article": "article",
    "design": "design mockup",
    "terminal": "terminal",
}


@dataclass(frozen=True)
class Taxonomy:
    category_prompts: dict[str, str]
    tag_prompts: dict[str, str]


def _validate_prompts(name: str, prompts: object, require_values: bool) -> dict[str, str]:
    if not isinstance(prompts, dict):
        raise ValueError(f"{name} must be an object")
    if require_values and not prompts:
        raise ValueError(f"{name} must not be empty")
    values = {str(label).strip(): str(prompt).strip() for label, prompt in prompts.items()}
    if any(not label or not prompt for label, prompt in values.items()):
        raise ValueError(f"{name} labels and prompts must not be blank")
    return values


def load_taxonomy(path: str | Path | None) -> Taxonomy:
    if path is None:
        return Taxonomy(DEFAULT_CATEGORY_PROMPTS, DEFAULT_TAG_PROMPTS)
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError("taxonomy must be an object")
    return Taxonomy(
        category_prompts=_validate_prompts("categories", data.get("categories", {}), True),
        tag_prompts=_validate_prompts("tags", data.get("tags", {}), False),
    )

"""Purpose: classifier taxonomy tests. Callers: pytest. Deps: json, app taxonomy service. API: test functions. Side effects: writes temporary taxonomy files."""
import json

import pytest

from app.services.taxonomy import DEFAULT_CATEGORY_PROMPTS, DEFAULT_TAG_PROMPTS, load_taxonomy


def test_load_taxonomy_uses_defaults_when_path_missing():
    taxonomy = load_taxonomy(None)

    assert taxonomy.category_prompts == DEFAULT_CATEGORY_PROMPTS
    assert taxonomy.tag_prompts == DEFAULT_TAG_PROMPTS


def test_load_taxonomy_reads_custom_prompt_file(tmp_path):
    path = tmp_path / "taxonomy.json"
    path.write_text(json.dumps({
        "categories": {"bug report": "a screenshot of a software bug"},
        "tags": {"urgent": "urgent issue"},
    }))

    taxonomy = load_taxonomy(path)

    assert taxonomy.category_prompts == {"bug report": "a screenshot of a software bug"}
    assert taxonomy.tag_prompts == {"urgent": "urgent issue"}


def test_load_taxonomy_rejects_empty_categories(tmp_path):
    path = tmp_path / "taxonomy.json"
    path.write_text(json.dumps({"categories": {}, "tags": {"urgent": "urgent issue"}}))

    with pytest.raises(ValueError, match="categories"):
        load_taxonomy(path)


def test_load_taxonomy_rejects_blank_prompt(tmp_path):
    path = tmp_path / "taxonomy.json"
    path.write_text(json.dumps({"categories": {"bug": ""}, "tags": {}}))

    with pytest.raises(ValueError, match="blank"):
        load_taxonomy(path)

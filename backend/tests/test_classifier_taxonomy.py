"""Purpose: classifier taxonomy integration tests. Callers: pytest. Deps: PIL, app classifier. API: test functions. Side effects: none."""
from PIL import Image

from app.services.classifier import PromptClassifier
from app.services.taxonomy import Taxonomy


def test_prompt_classifier_uses_injected_taxonomy(monkeypatch, tmp_path):
    image_path = tmp_path / "shot.png"
    Image.new("RGB", (4, 4), color="white").save(image_path)
    seen_prompts = []

    def fake_score(self, image, prompts):
        seen_prompts.append(prompts)
        return {label: index + 1 for index, label in enumerate(prompts)}

    monkeypatch.setattr(PromptClassifier, "_score_prompts", fake_score)
    classifier = PromptClassifier(taxonomy=Taxonomy(
        category_prompts={"invoice": "a screenshot of an invoice"},
        tag_prompts={"tax": "tax document"},
    ))

    result = classifier.classify(image_path)

    assert result.category == "invoice"
    assert result.tags == ["tax"]
    assert seen_prompts == [
        {"invoice": "a screenshot of an invoice"},
        {"tax": "tax document"},
    ]

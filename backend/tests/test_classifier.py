"""Purpose: classifier label selection tests. Callers: pytest. Deps: app.services.classifier. API: test functions. Side effects: none."""
from app.services.classifier import pick_labels


def test_pick_labels_chooses_best_category_and_top_tags():
    result = pick_labels(
        category_scores={"work": 0.2, "code": 0.9, "personal": 0.1},
        tag_scores={"terminal": 0.8, "error": 0.7, "recipe": 0.1},
        tag_threshold=0.5,
    )

    assert result.category == "code"
    assert result.confidence == 0.9
    assert result.tags == ["terminal", "error"]


def test_pick_labels_falls_back_to_top_three_tags():
    result = pick_labels(
        category_scores={"work": 0.6},
        tag_scores={"terminal": 0.3, "error": 0.2, "recipe": 0.1, "chat": 0.05},
        tag_threshold=0.5,
    )

    assert result.tags == ["terminal", "error", "recipe"]

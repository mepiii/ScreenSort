"""Purpose: CLIP prompt classification. Callers: upload API and tests. Deps: torch, Pillow, transformers, taxonomy. API: pick_labels, PromptClassifier. Side effects: lazy model downloads/loads and image reads during classification."""
from functools import cached_property
from pathlib import Path

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from app.models import ClassificationResult
from app.services.taxonomy import Taxonomy, load_taxonomy


def pick_labels(
    category_scores: dict[str, float],
    tag_scores: dict[str, float],
    tag_threshold: float = 0.25,
) -> ClassificationResult:
    category, confidence = max(category_scores.items(), key=lambda item: item[1])
    ranked_tags = sorted(tag_scores.items(), key=lambda item: item[1], reverse=True)
    tags = [tag for tag, score in ranked_tags if score >= tag_threshold] or [tag for tag, _ in ranked_tags[:3]]
    return ClassificationResult(category=category, confidence=confidence, tags=tags[:5])


class PromptClassifier:
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32", taxonomy: Taxonomy | None = None, taxonomy_path: str | Path | None = None) -> None:
        self.model_name = model_name
        self.taxonomy = taxonomy if taxonomy is not None else load_taxonomy(taxonomy_path)

    @cached_property
    def processor(self) -> CLIPProcessor:
        return CLIPProcessor.from_pretrained(self.model_name)

    @cached_property
    def model(self) -> CLIPModel:
        model = CLIPModel.from_pretrained(self.model_name)
        model.eval()
        return model

    def classify(self, image_path: Path) -> ClassificationResult:
        image = Image.open(image_path).convert("RGB")
        category_scores = self._score_prompts(image, self.taxonomy.category_prompts)
        tag_scores = self._score_prompts(image, self.taxonomy.tag_prompts)
        return pick_labels(category_scores, tag_scores)

    def _score_prompts(self, image: Image.Image, prompts: dict[str, str]) -> dict[str, float]:
        labels = list(prompts)
        text = [prompts[label] for label in labels]
        inputs = self.processor(text=text, images=image, return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = outputs.logits_per_image.softmax(dim=1)[0].tolist()
        return dict(zip(labels, probs, strict=True))

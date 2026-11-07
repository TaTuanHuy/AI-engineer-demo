import json
from pathlib import Path

from app.module.dataset.service import DatasetService


async def seed_datasets() -> None:
    source = Path(__file__).parent / "outputs" / "dataset_scoring_question_complexity.json"
    value = json.loads(source.read_text(encoding="utf-8"))
    await DatasetService.upsert(
        module="multi_model_smart",
        key="dataset_scoring_question_complexity",
        value=value,
    )


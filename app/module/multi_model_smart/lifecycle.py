import json
import logging
from pathlib import Path

from app.module.dataset.service import DatasetService


logger = logging.getLogger(__name__)


async def seed_datasets() -> None:
    source = Path(__file__).parent / "outputs" / "dataset_scoring_question_complexity.json"
    if not source.is_file():
        logger.warning("Skipping optional dataset seed because file is missing: %s", source)
        return

    value = json.loads(source.read_text(encoding="utf-8"))
    await DatasetService.upsert(
        module="multi_model_smart",
        key="dataset_scoring_question_complexity",
        value=value,
    )


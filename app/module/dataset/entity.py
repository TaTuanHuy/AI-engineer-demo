from typing import Any

from beanie import Document
from pymongo import ASCENDING, IndexModel


class DatasetEntity(Document):
    module: str
    key: str
    value: Any

    class Settings:
        name = "dataset"
        indexes = [
            IndexModel([("module", ASCENDING), ("key", ASCENDING)], unique=True)
        ]


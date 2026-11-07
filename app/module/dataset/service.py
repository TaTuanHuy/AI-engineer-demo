from typing import Any

from beanie import PydanticObjectId
from beanie.odm.queries.update import UpdateResponse

from app.module.dataset.entity import DatasetEntity


class DatasetService:
    """Shared CRUD operations for documents in the `dataset` collection."""

    @staticmethod
    async def create(module: str, key: str, value: Any) -> DatasetEntity:
        entity = DatasetEntity(module=module, key=key, value=value)
        await entity.insert()
        return entity

    @staticmethod
    async def get_by_id(entity_id: PydanticObjectId) -> DatasetEntity | None:
        return await DatasetEntity.get(entity_id)

    @staticmethod
    async def get_by_key(module: str, key: str) -> DatasetEntity | None:
        # Beanie 2 / Pydantic 2 no longer exposes document fields as class
        # attributes (``DatasetEntity.module`` raises AttributeError). Use a
        # Mongo query mapping so this works consistently across Beanie versions.
        return await DatasetEntity.find_one({"module": module, "key": key})

    @staticmethod
    async def list_by_module(module: str) -> list[DatasetEntity]:
        return await DatasetEntity.find({"module": module}).to_list()

    @staticmethod
    async def update_by_key(
        module: str, key: str, value: Any
    ) -> DatasetEntity | None:
        entity = await DatasetService.get_by_key(module, key)
        if entity is None:
            return None
        entity.value = value
        await entity.save()
        return entity

    @staticmethod
    async def upsert(module: str, key: str, value: Any) -> DatasetEntity:
        entity = await DatasetEntity.find_one({"module": module, "key": key}).upsert(
            {"$set": {"value": value}},
            on_insert=DatasetEntity(module=module, key=key, value=value),
            response_type=UpdateResponse.NEW_DOCUMENT,
        )
        if not isinstance(entity, DatasetEntity):
            raise RuntimeError(f"Could not upsert dataset {module}/{key}")
        return entity

    @staticmethod
    async def delete_by_key(module: str, key: str) -> bool:
        entity = await DatasetService.get_by_key(module, key)
        if entity is None:
            return False
        await entity.delete()
        return True


from pydantic import BaseModel


class PublicCategory(BaseModel):
    id: str
    slug: str
    name: str
    description: str | None = None
    parentId: str | None = None
    sortOrder: int


class PublicCategoryList(BaseModel):
    items: list[PublicCategory]
    nextCursor: str | None = None


class PublicCategoryEnvelope(BaseModel):
    data: PublicCategoryList


class PublicProviderList(BaseModel):
    items: list[dict]
    nextCursor: str | None = None


class PublicProviderListEnvelope(BaseModel):
    data: PublicProviderList


class PublicProviderDetailEnvelope(BaseModel):
    data: dict

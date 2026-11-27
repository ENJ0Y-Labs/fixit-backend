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


class PublicProviderList(BaseModel):
    items: list[dict]
    nextCursor: str | None = None


class PublicProviderResponse(BaseModel):
    data: dict

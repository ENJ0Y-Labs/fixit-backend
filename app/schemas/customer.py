from datetime import date, time
from decimal import Decimal
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


def _urgency(value: str | None) -> str | None:
    if value is None:
        return value
    normalized = value.strip().upper()
    return {"ASAP": "URGENT", "URGENT": "URGENT", "NORMAL": "NORMAL"}.get(
        normalized, normalized
    )


class CustomerProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    displayName: str | None = Field(default=None, min_length=1, max_length=120)
    defaultCity: str | None = Field(default=None, max_length=100)
    defaultState: str | None = Field(default=None, max_length=100)

    @field_validator("displayName")
    @classmethod
    def clean_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Display name cannot be blank.")
        return value

    @field_validator("defaultCity", "defaultState")
    @classmethod
    def clean_location(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    title: str = Field(min_length=5, max_length=160)
    category: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=10, max_length=5000)
    urgency: Literal["LOW", "NORMAL", "HIGH", "URGENT"] = "NORMAL"
    preferredDate: date | None = Field(
        default=None, validation_alias=AliasChoices("preferredDate", "date")
    )
    preferredTime: time | None = Field(
        default=None, validation_alias=AliasChoices("preferredTime", "time")
    )
    serviceLocation: str = Field(
        min_length=3,
        max_length=240,
        validation_alias=AliasChoices("serviceLocation", "location"),
    )
    budget: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)

    @field_validator("title", "description", "serviceLocation")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("category")
    @classmethod
    def strip_category(cls, value: str) -> str:
        return value.strip()

    @field_validator("urgency", mode="before")
    @classmethod
    def normalize_urgency(cls, value: str) -> str:
        return _urgency(value)


class JobUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    title: str | None = Field(default=None, min_length=5, max_length=160)
    category: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    urgency: Literal["LOW", "NORMAL", "HIGH", "URGENT"] | None = None
    preferredDate: date | None = Field(
        default=None, validation_alias=AliasChoices("preferredDate", "date")
    )
    preferredTime: time | None = Field(
        default=None, validation_alias=AliasChoices("preferredTime", "time")
    )
    serviceLocation: str | None = Field(
        default=None,
        min_length=3,
        max_length=240,
        validation_alias=AliasChoices("serviceLocation", "location"),
    )
    budget: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)

    @field_validator("title", "description", "serviceLocation")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("category")
    @classmethod
    def strip_optional_category(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("urgency", mode="before")
    @classmethod
    def normalize_optional_urgency(cls, value: str | None) -> str | None:
        return _urgency(value)


class BidSummary(BaseModel):
    id: str
    amountKobo: int
    message: str
    estimatedDays: int
    status: str
    provider: dict


class FavoriteProvider(BaseModel):
    id: str
    displayName: str
    headline: str | None = None
    avatarUrl: str | None = None
    category: dict | None = None
    serviceAreas: list[dict] = Field(default_factory=list)

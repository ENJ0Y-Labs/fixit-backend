from datetime import date, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CustomerProfileUpdate(BaseModel):
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
    title: str = Field(min_length=5, max_length=160)
    category: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=10, max_length=5000)
    urgency: Literal["LOW", "NORMAL", "HIGH", "URGENT"] = "NORMAL"
    preferredDate: date | None = None
    preferredTime: time | None = None
    serviceLocation: str = Field(min_length=3, max_length=240)
    budget: int | None = Field(default=None, gt=0)

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


class JobUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=5, max_length=160)
    category: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    urgency: Literal["LOW", "NORMAL", "HIGH", "URGENT"] | None = None
    preferredDate: date | None = None
    preferredTime: time | None = None
    serviceLocation: str | None = Field(default=None, min_length=3, max_length=240)
    budget: int | None = Field(default=None, gt=0)

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

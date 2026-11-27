from datetime import time
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProviderProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    displayName: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, min_length=10, max_length=32)
    headline: str | None = Field(default=None, max_length=160)
    bio: str | None = Field(default=None, max_length=600)
    serviceAreaCity: str | None = Field(default=None, max_length=100)
    serviceAreaState: str | None = Field(default=None, max_length=100)

    @field_validator("displayName", "headline", "bio", "serviceAreaCity", "serviceAreaState")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned and value == "":
            return ""
        return cleaned

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = "".join(char for char in value if char not in " ()-")
        if not (normalized.startswith("+234") and len(normalized) == 14
                or normalized.startswith("0") and len(normalized) == 11):
            raise ValueError("Enter a valid Nigerian phone number.")
        return normalized


class ProviderServiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    serviceId: UUID
    description: str = Field(min_length=5, max_length=1000)
    pricingMode: Literal["from", "fixed", "quote"] = "quote"
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Description cannot be blank.")
        return value

    @model_validator(mode="after")
    def validate_price(self):
        if self.pricingMode == "quote" and self.price is not None:
            raise ValueError("Quote-based listings must not include a price.")
        if self.pricingMode != "quote" and self.price is None:
            raise ValueError("A positive price is required for this pricing mode.")
        return self


class ProviderServiceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str | None = Field(default=None, min_length=5, max_length=1000)
    pricingMode: Literal["from", "fixed", "quote"] | None = None
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)

    @model_validator(mode="after")
    def validate_price(self):
        if self.pricingMode == "quote" and self.price is not None:
            raise ValueError("Quote-based listings must not include a price.")
        if self.pricingMode in {"from", "fixed"} and self.price is None:
            raise ValueError("A positive price is required for this pricing mode.")
        return self


class AvailabilityDayInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    weekday: int = Field(ge=0, le=6)
    enabled: bool
    start: time | None = None
    end: time | None = None

    @model_validator(mode="after")
    def validate_hours(self):
        if self.enabled and (
            self.start is None or self.end is None or self.start >= self.end
        ):
            raise ValueError("Enabled days need a start time before the end time.")
        return self


class AvailabilityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    isAvailable: bool
    timezone: str = Field(default="Africa/Lagos", min_length=1, max_length=64)
    schedule: list[AvailabilityDayInput] = Field(max_length=7)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Choose a valid IANA timezone.") from exc
        return value

    @model_validator(mode="after")
    def validate_schedule(self):
        weekdays = [item.weekday for item in self.schedule]
        if len(weekdays) != len(set(weekdays)):
            raise ValueError("Each weekday may appear only once.")
        return self


class ProviderBidCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: Literal["NGN"] = "NGN"
    message: str = Field(min_length=1, max_length=2000)
    proposedSchedule: str | None = Field(default=None, max_length=40)

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A quote message is required.")
        return value


class ProviderJobProgressUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transition: Literal["COMPLETE"]
    expectedUpdatedAt: str | None = None

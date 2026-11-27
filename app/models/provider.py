import uuid
from datetime import time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ProviderAvailability(TimestampMixin, Base):
    __tablename__ = "provider_availability"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("provider_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Africa/Lagos"
    )

    days: Mapped[list["ProviderAvailabilityDay"]] = relationship(
        back_populates="availability", cascade="all, delete-orphan"
    )


class ProviderAvailabilityDay(TimestampMixin, Base):
    __tablename__ = "provider_availability_days"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_provider_day_weekday"),
        CheckConstraint(
            "NOT is_enabled OR (start_time IS NOT NULL AND end_time IS NOT NULL "
            "AND start_time < end_time)",
            name="ck_provider_day_hours",
        ),
        UniqueConstraint("provider_id", "weekday", name="uq_provider_availability_day"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("provider_availability.provider_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)

    availability: Mapped["ProviderAvailability"] = relationship(back_populates="days")

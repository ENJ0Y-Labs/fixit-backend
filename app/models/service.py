import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.profile import ProviderProfile
    from app.models.service_category import ServiceCategory


class Service(TimestampMixin, Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("service_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(140), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    category: Mapped["ServiceCategory"] = relationship(back_populates="services")
    provider_listings: Mapped[list["ProviderService"]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )


class ProviderService(TimestampMixin, Base):
    __tablename__ = "provider_services"
    __table_args__ = (
        CheckConstraint(
            "pricing_mode IN ('from', 'fixed', 'quote')",
            name="ck_provider_services_pricing_mode",
        ),
        CheckConstraint(
            "price_kobo IS NULL OR price_kobo > 0",
            name="ck_provider_services_price_positive",
        ),
        UniqueConstraint("provider_id", "service_id", name="uq_provider_services_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("provider_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    pricing_mode: Mapped[str] = mapped_column(
        String(12), nullable=False, default="quote"
    )
    price_kobo: Mapped[int | None] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    provider: Mapped["ProviderProfile"] = relationship(back_populates="services")
    service: Mapped["Service"] = relationship(back_populates="provider_listings")

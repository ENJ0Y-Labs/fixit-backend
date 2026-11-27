import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.service_category import ServiceCategory
    from app.models.user import User


class CustomerProfile(TimestampMixin, Base):
    __tablename__ = "customer_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    default_city: Mapped[str | None] = mapped_column(String(100))
    default_state: Mapped[str | None] = mapped_column(String(100))

    user: Mapped["User"] = relationship(back_populates="customer_profile")


class ProviderProfile(TimestampMixin, Base):
    __tablename__ = "provider_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    headline: Mapped[str | None] = mapped_column(String(160))
    bio: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(String(2048))
    service_area_city: Mapped[str | None] = mapped_column(String(100))
    service_area_state: Mapped[str | None] = mapped_column(String(100))
    hourly_rate_kobo: Mapped[int | None] = mapped_column(BigInteger)
    primary_category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("service_categories.id", ondelete="SET NULL"),
    )

    user: Mapped["User"] = relationship(back_populates="provider_profile")
    primary_category: Mapped["ServiceCategory | None"] = relationship(
        back_populates="providers"
    )


class AdminProfile(TimestampMixin, Base):
    __tablename__ = "admin_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str | None] = mapped_column(String(100))

    user: Mapped["User"] = relationship(back_populates="admin_profile")

import uuid

from sqlalchemy import CheckConstraint, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('customer', 'provider', 'admin')", name="ck_users_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    customer_profile: Mapped["CustomerProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    provider_profile: Mapped["ProviderProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    admin_profile: Mapped["AdminProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )

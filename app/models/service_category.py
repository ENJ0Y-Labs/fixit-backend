import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ServiceCategory(TimestampMixin, Base):
    __tablename__ = "service_categories"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("service_categories.id", ondelete="SET NULL")
    )
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    parent: Mapped["ServiceCategory | None"] = relationship(
        back_populates="children", remote_side="ServiceCategory.id"
    )
    children: Mapped[list["ServiceCategory"]] = relationship(back_populates="parent")
    providers: Mapped[list["ProviderProfile"]] = relationship(
        back_populates="primary_category"
    )

import uuid
from datetime import date, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.service_category import ServiceCategory
    from app.models.user import User


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "urgency IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')",
            name="ck_jobs_urgency",
        ),
        CheckConstraint(
            "status IN ('AWAITING_BIDS', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
            name="ck_jobs_status",
        ),
        CheckConstraint(
            "budget_kobo IS NULL OR budget_kobo >= 0",
            name="ck_jobs_budget",
        ),
        CheckConstraint(
            "agreed_price_kobo IS NULL OR agreed_price_kobo >= 0",
            name="ck_jobs_agreed_price",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("service_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    urgency: Mapped[str] = mapped_column(String(16), nullable=False, default="NORMAL")
    preferred_date: Mapped[date | None] = mapped_column(Date)
    preferred_time: Mapped[time | None] = mapped_column(Time)
    service_location: Mapped[str] = mapped_column(String(240), nullable=False)
    budget_kobo: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="AWAITING_BIDS", index=True
    )
    accepted_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    agreed_price_kobo: Mapped[int | None] = mapped_column(BigInteger)

    category: Mapped["ServiceCategory"] = relationship()
    bids: Mapped[list["Bid"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class Bid(TimestampMixin, Base):
    __tablename__ = "bids"
    __table_args__ = (
        CheckConstraint("amount_kobo > 0", name="ck_bids_amount_positive"),
        CheckConstraint("estimated_days > 0", name="ck_bids_estimated_days_positive"),
        CheckConstraint(
            "status IN ('PENDING', 'ACCEPTED', 'DECLINED')",
            name="ck_bids_status",
        ),
        UniqueConstraint("job_id", "provider_id", name="uq_bids_job_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount_kobo: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_days: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PENDING", index=True
    )

    job: Mapped["Job"] = relationship(back_populates="bids")
    provider: Mapped["User"] = relationship(foreign_keys=[provider_id])


class Favorite(TimestampMixin, Base):
    __tablename__ = "customer_favorites"
    __table_args__ = (
        UniqueConstraint(
            "customer_id", "provider_id", name="uq_customer_favorites_pair"
        ),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

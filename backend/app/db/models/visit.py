from sqlalchemy import Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from app.db.base import Base


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bath_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("baths.id"))
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    message_id: Mapped[int | None] = mapped_column(BigInteger)
    chat_id: Mapped[int | None] = mapped_column(BigInteger)
    # draft | pending | confirmed | disputed | cancelled
    status: Mapped[str] = mapped_column(String(32), default="draft")
    visited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    flag_long: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_ultraunique: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    bath = relationship("Bath", back_populates="visits")
    creator = relationship("User", back_populates="visits_created", foreign_keys=[created_by])
    participants = relationship("VisitParticipant", back_populates="visit", cascade="all, delete-orphan")
    point_logs = relationship("PointLog", back_populates="visit", cascade="all, delete-orphan")


class VisitParticipant(Base):
    __tablename__ = "visit_participants"

    visit_id: Mapped[int] = mapped_column(Integer, ForeignKey("visits.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), primary_key=True)

    visit = relationship("Visit", back_populates="participants")
    user = relationship("User", back_populates="participations")


class PointLog(Base):
    __tablename__ = "point_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    visit_id: Mapped[int] = mapped_column(Integer, ForeignKey("visits.id"))
    points: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="point_logs")
    visit = relationship("Visit", back_populates="point_logs")

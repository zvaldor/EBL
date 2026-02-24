from sqlalchemy import Integer, String, Float, Boolean, DateTime, ForeignKey, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from app.db.base import Base


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    code: Mapped[str | None] = mapped_column(String(10))

    regions = relationship("Region", back_populates="country")
    baths = relationship("Bath", back_populates="country")


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("countries.id"))
    name: Mapped[str] = mapped_column(String(255))

    country = relationship("Country", back_populates="regions")
    baths = relationship("Bath", back_populates="region")


class Bath(Base):
    __tablename__ = "baths"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(512))
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    country_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("countries.id"))
    region_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("regions.id"))
    city: Mapped[str | None] = mapped_column(String(255))
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(String(2048))
    url: Mapped[str | None] = mapped_column(String(512))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    canonical_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("baths.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    country = relationship("Country", back_populates="baths")
    region = relationship("Region", back_populates="baths")
    visits = relationship("Visit", back_populates="bath")
    canonical = relationship("Bath", remote_side="Bath.id", foreign_keys=[canonical_id])

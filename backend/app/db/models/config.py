from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class PointConfig(Base):
    __tablename__ = "point_config"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(String(256), default="")


DEFAULT_CONFIG = {
    "base_points": (1.0, "Базовые очки за любой визит"),
    "long_bonus": (1.0, "Бонус за длительное посещение (>150 мин)"),
    "region_bonus": (1.0, "Бонус за новый регион в текущем сезоне"),
    "country_bonus": (1.0, "Бонус за новую страну в текущем сезоне"),
    "ultraunique_bonus": (1.0, "Бонус за ультрауникальную баню"),
}

"""Modelos ORM (detalhe de infraestrutura — não vazam para o domínio)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base


class InspectionModel(Base):
    __tablename__ = "inspections"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    image_width: Mapped[int] = mapped_column(Integer)
    image_height: Mapped[int] = mapped_column(Integer)
    impurity_count: Mapped[int] = mapped_column(Integer, index=True)
    impurity_area_ratio: Mapped[float] = mapped_column(Float)
    quality: Mapped[str] = mapped_column(String(16), index=True)
    processing_time_ms: Mapped[float] = mapped_column(Float)
    original_image_key: Mapped[str] = mapped_column(String(255))
    annotated_image_key: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    impurities: Mapped[list["ImpurityModel"]] = relationship(
        back_populates="inspection",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ImpurityModel.id",
    )


class ImpurityModel(Base):
    __tablename__ = "impurities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_id: Mapped[str] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), index=True
    )
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float, nullable=True)

    inspection: Mapped[InspectionModel] = relationship(back_populates="impurities")

import inspect
import sys
from typing import Optional

from pydantic import EmailStr

from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector as PGVector

from .config import ServiceBase as Base


class PDF_Queue(Base):
    filename: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    queue_position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="Queued")
    status_description: Mapped[str] = mapped_column(String, nullable=False, default="Pending")
    user_email: Mapped[EmailStr] = mapped_column(String, nullable=False)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DocumentEmbedding(Base):
    file_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[PGVector] = mapped_column(PGVector(1024))
    meta_data: Mapped[str] = mapped_column(String, nullable=True)


class GlobalEmbedding(Base):
    text: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[PGVector] = mapped_column(PGVector(1024))
    meta_data: Mapped[str] = mapped_column(String, nullable=True)


class FieldSynonym(Base):
    field_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    synonym: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding: Mapped[PGVector] = mapped_column(PGVector(1024), nullable=True)
    created_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    extra: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isclass(obj) and obj.__module__ == __name__
]

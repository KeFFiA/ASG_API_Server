import inspect
import sys
from typing import Optional

from pydantic import EmailStr

from sqlalchemy import String, Integer, Float, UniqueConstraint, Index, event, DDL, Computed
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID
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
    meta_data: Mapped[dict] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("file_name", "chunk_index", name="uq_document_chunk"),
        Index("ix_document_file_name", "file_name"),
    )


class GlobalEmbedding(Base):
    text: Mapped[str] = mapped_column(String, nullable=False)
    text_hash: Mapped[UUID] = mapped_column(
        UUID,
        Computed("md5(text)::uuid", persisted=True),
        unique=True,
    )
    embedding: Mapped[PGVector] = mapped_column(PGVector(1024))
    meta_data: Mapped[dict] = mapped_column(JSONB, nullable=True)


class FieldSynonym(Base):
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    synonym: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding: Mapped[PGVector] = mapped_column(PGVector(1024))
    created_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    extra: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("field_name", "synonym", name="uq_field_synonym"),
        Index("ix_field_synonym_field_name", "field_name"),
    )


class DremioViews(Base):
    table_name: Mapped[str] = mapped_column(String, nullable=False)
    view_name: Mapped[str] = mapped_column(String, nullable=False)
    vds_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    path: Mapped[list] = mapped_column(ARRAY(String), nullable=False)



# DocumentEmbedding
event.listen(
    DocumentEmbedding.__table__,
    "after_create",
    DDL("""
    CREATE INDEX IF NOT EXISTS idx_document_embedding_ivf
    ON ai12_service.public.documentembeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
    """)
)

# GlobalEmbedding
event.listen(
    GlobalEmbedding.__table__,
    "after_create",
    DDL("""
    CREATE INDEX IF NOT EXISTS idx_global_embedding_ivf
    ON ai12_service.public.globalembeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
    """)
)



_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isclass(obj) and obj.__module__ == __name__
]

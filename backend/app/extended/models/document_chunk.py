"""
13. 文件分段模組 (Document Chunk Module)

- DocumentChunk: 文件分段 Embedding (段落級向量搜尋)

Version: 1.0.0
Created: 2026-03-15
"""
from ._base import *


class DocumentChunk(Base):
    """文件分段 — 段落級 Embedding 提升 RAG 長文件召回精度"""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所屬公文 ID",
    )
    chunk_index = Column(Integer, nullable=False, comment="分段序號 (0-based)")
    chunk_text = Column(Text, nullable=False, comment="分段文字內容")
    start_char = Column(Integer, nullable=True, comment="起始字元位置")
    end_char = Column(Integer, nullable=True, comment="結束字元位置")
    token_count = Column(Integer, nullable=True, comment="Token 估計數")
    created_at = Column(DateTime, server_default=func.now(), comment="建立時間")

    if Vector is not None:
        embedding = deferred(Column(
            Vector(768),
            nullable=True,
            comment="分段向量嵌入 (768D)",
        ))

    document = relationship("OfficialDocument", backref=backref(
        "chunks", cascade="all, delete-orphan", lazy="dynamic",
    ))

    __table_args__ = (
        Index("ix_doc_chunks_doc_idx", "document_id", "chunk_index"),
        {"comment": "文件分段 Embedding 表"},
    )

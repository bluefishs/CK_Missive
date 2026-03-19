"""
16. 知識庫分段模組 (Knowledge Base Chunk Module)

- KBChunk: 知識庫 Markdown 文件分段 Embedding (向量搜尋)

Version: 1.0.0
Created: 2026-03-19
"""
from ._base import *


class KBChunk(Base):
    """知識庫文件分段 — Markdown 文件向量搜尋"""
    __tablename__ = "kb_chunks"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(
        String(500),
        nullable=False,
        index=True,
        comment="相對路徑 e.g. knowledge-map/api/overview.md",
    )
    filename = Column(String(200), nullable=False, comment="檔案名稱")
    section_title = Column(String(500), nullable=True, comment="章節標題")
    content = Column(Text, nullable=False, comment="分段文字內容")
    chunk_index = Column(
        Integer, default=0, comment="同檔案內的分段索引"
    )
    created_at = Column(DateTime, server_default=func.now(), comment="建立時間")
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新時間",
    )

    if Vector is not None:
        embedding = deferred(Column(
            Vector(768),
            nullable=True,
            comment="nomic-embed-text 768D 向量嵌入",
        ))

    __table_args__ = (
        Index("ix_kb_chunks_file_path_idx", "file_path", "chunk_index"),
        {"comment": "知識庫 Markdown 文件分段 Embedding 表"},
    )

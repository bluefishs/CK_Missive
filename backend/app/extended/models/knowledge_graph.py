"""
9. 知識圖譜正規化模型 (Knowledge Graph Canonical Models)

Phase 2: 正規化實體 + 時態關係 + 入圖事件

- CanonicalEntity: 正規化實體（去重合併後的唯一實體）
- EntityAlias: 實體別名（多個表面名稱 → 同一正規實體）
- DocumentEntityMention: 公文中的實體提及（連結到正規實體）
- EntityRelationship: 正規化的實體關係（含時態追蹤）
- GraphIngestionEvent: 入圖事件日誌（Episode 層）

Version: 1.0.0
Created: 2026-02-24
"""
from ._base import *


class CanonicalEntity(Base):
    """正規化實體（去重合併後的唯一實體）"""
    __tablename__ = "canonical_entities"

    id = Column(Integer, primary_key=True, index=True)
    canonical_name = Column(String(300), nullable=False, comment="正規化名稱")
    entity_type = Column(
        String(50), nullable=False, index=True,
        comment="實體類型: org/person/project/location/topic",
    )
    description = Column(Text, nullable=True, comment="實體描述")

    # pgvector embedding（僅 PGVECTOR_ENABLED=true 時定義）
    if Vector is not None:
        embedding = deferred(Column(Vector(384), nullable=True, comment="實體名稱 embedding"))

    alias_count = Column(Integer, default=1, comment="別名數量")
    mention_count = Column(Integer, default=0, comment="總被提及次數")
    first_seen_at = Column(DateTime, server_default=func.now(), comment="首次出現")
    last_seen_at = Column(DateTime, server_default=func.now(), comment="最近出現")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 關聯
    aliases = relationship("EntityAlias", back_populates="canonical_entity", cascade="all, delete-orphan")
    mentions = relationship("DocumentEntityMention", back_populates="canonical_entity", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("canonical_name", "entity_type", name="uq_canonical_name_type"),
        Index("ix_canonical_entity_name_trgm", "canonical_name"),
    )

    def __repr__(self):
        return f"<CanonicalEntity {self.entity_type}:{self.canonical_name}>"


class EntityAlias(Base):
    """實體別名（多個表面名稱 → 同一正規實體）"""
    __tablename__ = "entity_aliases"

    id = Column(Integer, primary_key=True, index=True)
    alias_name = Column(String(300), nullable=False, index=True, comment="別名文字")
    canonical_entity_id = Column(
        Integer,
        ForeignKey("canonical_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source = Column(
        String(50), default="auto",
        comment="來源: auto/manual/llm",
    )
    confidence = Column(Float, default=1.0, comment="匹配信心度")
    created_at = Column(DateTime, server_default=func.now())

    # 關聯
    canonical_entity = relationship("CanonicalEntity", back_populates="aliases")

    __table_args__ = (
        UniqueConstraint("alias_name", "canonical_entity_id", name="uq_alias_canonical"),
        Index("ix_entity_alias_name", "alias_name"),
    )

    def __repr__(self):
        return f"<EntityAlias {self.alias_name} → entity#{self.canonical_entity_id}>"


class DocumentEntityMention(Base):
    """公文中的實體提及（連結到正規實體）"""
    __tablename__ = "document_entity_mentions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    canonical_entity_id = Column(
        Integer,
        ForeignKey("canonical_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mention_text = Column(String(300), nullable=False, comment="原始提取文字")
    confidence = Column(Float, default=1.0, comment="提取信心度")
    context = Column(String(500), nullable=True, comment="上下文片段")
    created_at = Column(DateTime, server_default=func.now())

    # 關聯
    document = relationship("OfficialDocument")
    canonical_entity = relationship("CanonicalEntity", back_populates="mentions")

    __table_args__ = (
        Index("ix_doc_mention_doc_entity", "document_id", "canonical_entity_id"),
    )

    def __repr__(self):
        return f"<DocumentEntityMention doc#{self.document_id} → entity#{self.canonical_entity_id}>"


class EntityRelationship(Base):
    """正規化的實體關係（含時態追蹤）"""
    __tablename__ = "entity_relationships"

    id = Column(Integer, primary_key=True, index=True)
    source_entity_id = Column(
        Integer,
        ForeignKey("canonical_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_entity_id = Column(
        Integer,
        ForeignKey("canonical_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type = Column(String(100), nullable=False, index=True, comment="關係類型")
    relation_label = Column(String(100), nullable=True, comment="顯示文字")
    weight = Column(Float, default=1.0, comment="關係權重（佐證公文數）")

    # 時態追蹤
    valid_from = Column(DateTime, nullable=True, comment="關係起始時間")
    valid_to = Column(DateTime, nullable=True, comment="關係結束時間（NULL=仍有效）")
    invalidated_at = Column(DateTime, nullable=True, comment="軟刪除時間（永不實際刪除）")

    first_document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        comment="首次出現的公文",
    )
    document_count = Column(Integer, default=1, comment="佐證公文數")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 關聯
    source_entity = relationship("CanonicalEntity", foreign_keys=[source_entity_id])
    target_entity = relationship("CanonicalEntity", foreign_keys=[target_entity_id])
    first_document = relationship("OfficialDocument")

    __table_args__ = (
        Index("ix_entity_relationship_src_tgt", "source_entity_id", "target_entity_id"),
        Index("ix_entity_relationship_type", "relation_type"),
        Index("ix_entity_relationship_valid", "valid_from", "valid_to"),
    )

    def __repr__(self):
        return f"<EntityRelationship #{self.source_entity_id} --[{self.relation_type}]--> #{self.target_entity_id}>"


class GraphIngestionEvent(Base):
    """入圖事件日誌（Episode 層）"""
    __tablename__ = "graph_ingestion_events"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(
        String(50), nullable=False,
        comment="事件類型: extract/re-extract/merge/resolve",
    )
    entities_found = Column(Integer, default=0, comment="找到的實體數")
    entities_new = Column(Integer, default=0, comment="新建的正規實體數")
    entities_merged = Column(Integer, default=0, comment="合併到既有實體數")
    relations_found = Column(Integer, default=0, comment="找到的關係數")
    llm_provider = Column(String(20), nullable=True, comment="使用的 LLM 提供者")
    processing_ms = Column(Integer, default=0, comment="處理耗時 (ms)")
    status = Column(
        String(20), default="completed",
        comment="處理狀態: completed/failed/skipped",
    )
    error_message = Column(Text, nullable=True, comment="錯誤訊息")
    created_at = Column(DateTime, server_default=func.now())

    # 關聯
    document = relationship("OfficialDocument")

    def __repr__(self):
        return f"<GraphIngestionEvent {self.event_type} doc#{self.document_id} status={self.status}>"

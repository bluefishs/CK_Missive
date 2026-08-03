"""
8. AI 實體提取模組 (Entity Extraction Module)

- DocumentEntity: 從公文文本提取的命名實體
- EntityRelation: 實體間的關聯關係

Phase 1: NER 實體提取，用 Groq/Ollama LLM 從公文 subject/sender/receiver/content
自動提取人名、機關、專案、地點等實體，豐富知識圖譜。

Version: 1.0.0
Created: 2026-02-24
"""
from ._base import *


class DocumentEntity(Base):
    """公文提取實體"""
    __tablename__ = "document_entities"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="來源公文 ID",
    )
    entity_name = Column(String(200), nullable=False, comment="實體名稱")
    entity_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="實體類型: org/person/project/location/date/topic",
    )
    confidence = Column(Float, default=1.0, comment="提取信心度 0.0~1.0")
    context = Column(String(500), nullable=True, comment="實體出現的上下文片段")
    extracted_at = Column(DateTime, server_default=func.now(), comment="提取時間")

    # 關聯
    document = relationship("OfficialDocument", backref=backref("entities", lazy="dynamic", passive_deletes=True))

    __table_args__ = (
        Index("ix_doc_entities_name_type", "entity_name", "entity_type"),
        Index("ix_doc_entities_doc_type", "document_id", "entity_type"),
    )

    def __repr__(self):
        return f"<DocumentEntity {self.entity_type}:{self.entity_name}>"


class EntityRelation(Base):
    """實體間關聯（⚠️ 已停止寫入，2026-06-16 起）。

    **系統有兩張關係表，這張是舊的那張。**

      entity_relations（本表）  2162 筆   最後寫入 2026-06-16   name 字串關聯
      entity_relationships      10231 筆  每日 03:00 更新       entity_id 外鍵

    真正在成長的圖是 `EntityRelationship`（`knowledge_graph.py`）——
    程式結構關係（imports / calls / serves_route / has_method / maps_to）全在那裡。

    2026-08-03 查證時發現 `kg_stats_metrics` 的 KG 邊數指標讀的是本表，
    於是那個 Prometheus 指標 48 天固定不動、卻因為「有數字」而看起來正常（已修）。

    **新的關聯請一律寫進 `EntityRelationship`。** 本表尚有 4 個消費端未收斂，
    刪除需逐一確認，故暫時保留；不要再往這裡新增寫入路徑。
    """
    __tablename__ = "entity_relations"

    id = Column(Integer, primary_key=True, index=True)
    source_entity_name = Column(String(200), nullable=False, comment="來源實體名稱")
    source_entity_type = Column(String(50), nullable=False, comment="來源實體類型")
    target_entity_name = Column(String(200), nullable=False, comment="目標實體名稱")
    target_entity_type = Column(String(50), nullable=False, comment="目標實體類型")
    relation_type = Column(String(100), nullable=False, comment="關係類型 (如 issues_permit, belongs_to)")
    relation_label = Column(String(100), nullable=True, comment="關係顯示標籤")
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="提取來源公文 ID",
    )
    confidence = Column(Float, default=1.0, comment="提取信心度 0.0~1.0")
    extracted_at = Column(DateTime, server_default=func.now(), comment="提取時間")

    # 關聯
    document = relationship("OfficialDocument", backref=backref("entity_relations", lazy="dynamic", passive_deletes=True))

    __table_args__ = (
        Index("ix_entity_rel_source", "source_entity_name", "source_entity_type"),
        Index("ix_entity_rel_target", "target_entity_name", "target_entity_type"),
        Index("ix_entity_rel_type", "relation_type"),
    )

    def __repr__(self):
        return f"<EntityRelation {self.source_entity_name} --[{self.relation_type}]--> {self.target_entity_name}>"

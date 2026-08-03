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
    """實體間關聯 —— **文件級（原始抽取層）**。

    ⚠️ 2026-08-03 更正：本 docstring 一度寫成「已停止寫入／請改用
    EntityRelationship」，**那是錯的**。當時只看到「最後寫入 2026-06-16」就下結論，
    實際是上游 NER 的關係抽取壞了（`relation` vs `relation_type` 欄位名對不上），
    不是這張表被廢棄。修好後隨即恢復寫入。

    ## 兩張關係表是兩層管線，不是重複

    | | `entity_relations`（本表） | `entity_relationships` |
    |---|---|---|
    | 層級 | **文件級**：某份公文「提到」的關係 | **canonical 級**：圖譜中確立的關係 |
    | 端點 | source/target 是**字串名** | source/target 是 **entity_id 外鍵** |
    | 附帶 | `document_id` + `confidence` | `weight` / `document_count` / `valid_from` |
    | 寫入 | NER `extract_entities_for_document` | `graph_ingestion_pipeline` 聚合本表，
    |      |                                    | 另加程式碼/DB/ERP 結構 ingest |

    資料流：公文文本 →（NER）→ **本表** →（GraphIngestionPipeline 正規化、
    合併同義實體、累計 weight）→ `EntityRelationship`。

    所以「公文抽出的業務關係」本來就該寫這裡；程式結構關係（imports/calls/
    serves_route/has_method/maps_to）則只存在於 canonical 表，不經過本層。

    ## 已知缺口（2026-08-03）

    `ExtractionScheduler` 對**已有 document_entities 的公文一律跳過**，
    而跳過就不會走到聚合管線。NER 覆蓋率 99.1%，所以欄位名 bug 修復後，
    **存量公文的關係不會自動補回來** —— 需要一次 force 重抽的 backfill。
    canonical 層的業務語意關係最後更新停在 2026-06-02 即為此故。
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

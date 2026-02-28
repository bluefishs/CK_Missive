"""
10. AI 分析持久化模組 (Document AI Analysis Persistence)

- DocumentAIAnalysis: 公文 AI 分析結果（摘要/分類/關鍵字）

一文一記錄設計：三種分析共用相同輸入，更新時一起失效。
NER 實體提取結果仍存放於 document_entities / entity_relations。

Version: 1.0.0
Created: 2026-02-28
"""
from ._base import *


class DocumentAIAnalysis(Base):
    """公文 AI 分析結果持久化"""
    __tablename__ = "document_ai_analyses"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="公文 ID（一文一記錄）",
    )

    # === 摘要 ===
    summary = Column(Text, nullable=True, comment="AI 生成摘要")
    summary_confidence = Column(Float, nullable=True, comment="摘要信心度 0.0-1.0")

    # === 分類 ===
    suggested_doc_type = Column(String(50), nullable=True, comment="AI 建議公文類型")
    doc_type_confidence = Column(Float, nullable=True, comment="類型信心度")
    suggested_category = Column(String(20), nullable=True, comment="AI 建議收發類別")
    category_confidence = Column(Float, nullable=True, comment="類別信心度")
    classification_reasoning = Column(Text, nullable=True, comment="分類判斷理由")

    # === 關鍵字 ===
    keywords = Column(JSONB, nullable=True, comment="關鍵字陣列 ['kw1','kw2']")
    keywords_confidence = Column(Float, nullable=True, comment="關鍵字信心度")

    # === 元資料 ===
    llm_provider = Column(String(20), nullable=True, comment="LLM 提供者: groq/ollama")
    llm_model = Column(String(100), nullable=True, comment="使用的模型名稱")
    processing_ms = Column(Integer, default=0, comment="總處理耗時 (ms)")
    source_text_hash = Column(
        String(64), nullable=True,
        comment="輸入文本 SHA256（用於偵測公文修改後過期）",
    )
    analysis_version = Column(String(20), default="1.0.0", comment="分析版本")

    # === 狀態 ===
    status = Column(
        String(20), default="completed",
        comment="狀態: pending/processing/completed/partial/failed",
    )
    error_message = Column(Text, nullable=True, comment="失敗時的錯誤訊息")
    is_stale = Column(Boolean, default=False, index=True, comment="公文內容變更後是否已過期")

    # === 時間戳 ===
    analyzed_at = Column(DateTime, server_default=func.now(), comment="分析完成時間")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 關聯
    document = relationship(
        "OfficialDocument",
        backref=backref("ai_analysis", uselist=False, lazy="select"),
    )

    __table_args__ = (
        Index("ix_doc_ai_analysis_status", "status"),
        Index("ix_doc_ai_analysis_analyzed_at", "analyzed_at"),
    )

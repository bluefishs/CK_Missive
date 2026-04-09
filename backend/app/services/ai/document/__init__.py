"""
AI 文件處理模組

公文 AI 服務、NER 實體提取、文件分段、附件索引。
"""

__all__ = [
    "DocumentAIService",
    "DocumentAnalysisService",
    "AttachmentContentIndexer",
    "ExtractionScheduler",
    "get_extraction_scheduler",
]


def __getattr__(name: str):
    if name == "DocumentAIService":
        from .document_ai_service import DocumentAIService
        return DocumentAIService
    if name == "DocumentAnalysisService":
        from .document_analysis_service import DocumentAnalysisService
        return DocumentAnalysisService
    if name == "AttachmentContentIndexer":
        from .attachment_content_indexer import AttachmentContentIndexer
        return AttachmentContentIndexer
    if name in ("ExtractionScheduler", "get_extraction_scheduler"):
        from . import extraction_scheduler
        return getattr(extraction_scheduler, name)
    if name == "EngineeringDiagramService":
        from .engineering_diagram_service import EngineeringDiagramService
        return EngineeringDiagramService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

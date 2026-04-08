"""
AI 圖譜模組

知識圖譜 (KG)、程式碼圖譜 (Code Graph)、ERP 圖譜相關服務。
"""

# Lazy __init__ — only import when accessed via `from app.services.ai.graph import X`
# Individual modules can still be imported directly: `from app.services.ai.graph.graph_query_service import ...`

__all__ = [
    "GraphQueryService",
    "GraphStatisticsService",
    "GraphTraversalService",
    "RelationGraphService",
    "CanonicalEntityService",
    "CanonicalEntityResolver",
    "CanonicalEntityMatcher",
    "GraphIngestionPipeline",
    "GraphMergeStrategy",
    "GraphEntityGraphBuilder",
    "GraphCodeWikiService",
    "CodeGraphIngestionService",
    "CodeGraphIngestService",
    "PythonASTAnalyzer",
    "CodeEntity",
    "CodeRelation",
    "CODE_GRAPH_LABEL",
    "EndpointExtractorMixin",
    "SchemaReflectorService",
    "TypeScriptExtractor",
    "ErpGraphIngestService",
    "ErpEntity",
    "ErpRelation",
    "ERP_ENTITY_TYPES",
    "ERP_RELATION_TYPES",
]


def __getattr__(name: str):
    """Lazy imports to avoid circular dependency at import time."""
    # KG services
    if name == "GraphQueryService":
        from .graph_query_service import GraphQueryService
        return GraphQueryService
    if name == "GraphStatisticsService":
        from .graph_statistics_service import GraphStatisticsService
        return GraphStatisticsService
    if name == "GraphTraversalService":
        from .graph_traversal_service import GraphTraversalService
        return GraphTraversalService
    if name == "RelationGraphService":
        from .relation_graph_service import RelationGraphService
        return RelationGraphService
    if name == "CanonicalEntityService":
        from .canonical_entity_service import CanonicalEntityService
        return CanonicalEntityService
    if name == "CanonicalEntityResolver":
        from .canonical_entity_resolver import CanonicalEntityResolver
        return CanonicalEntityResolver
    if name == "CanonicalEntityMatcher":
        from .canonical_entity_matcher import CanonicalEntityMatcher
        return CanonicalEntityMatcher
    if name == "GraphIngestionPipeline":
        from .graph_ingestion_pipeline import GraphIngestionPipeline
        return GraphIngestionPipeline
    if name == "GraphMergeStrategy":
        from .graph_merge_strategy import GraphMergeStrategy
        return GraphMergeStrategy
    if name == "GraphEntityGraphBuilder":
        from .graph_entity_graph_builder import GraphEntityGraphBuilder
        return GraphEntityGraphBuilder
    if name == "GraphCodeWikiService":
        from .graph_code_wiki_service import GraphCodeWikiService
        return GraphCodeWikiService
    # Code Graph
    if name == "CodeGraphIngestionService":
        from .code_graph_service import CodeGraphIngestionService
        return CodeGraphIngestionService
    if name == "CodeGraphIngestService":
        from .code_graph_ingest import CodeGraphIngestService
        return CodeGraphIngestService
    if name == "PythonASTAnalyzer":
        from .code_graph_ast_analyzer import PythonASTAnalyzer
        return PythonASTAnalyzer
    if name in ("CodeEntity", "CodeRelation", "CODE_GRAPH_LABEL"):
        from . import code_graph_types
        return getattr(code_graph_types, name)
    if name == "EndpointExtractorMixin":
        from .ast_endpoint_extractor import EndpointExtractorMixin
        return EndpointExtractorMixin
    if name == "SchemaReflectorService":
        from .schema_reflector import SchemaReflectorService
        return SchemaReflectorService
    if name == "TypeScriptExtractor":
        from .ts_extractor import TypeScriptExtractor
        return TypeScriptExtractor
    # ERP Graph
    if name == "ErpGraphIngestService":
        from .erp_graph_ingest import ErpGraphIngestService
        return ErpGraphIngestService
    if name in ("ErpEntity", "ErpRelation", "ERP_ENTITY_TYPES", "ERP_RELATION_TYPES"):
        from . import erp_graph_types
        return getattr(erp_graph_types, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

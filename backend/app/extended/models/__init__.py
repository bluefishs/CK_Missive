"""
CK_Missive ORM 模型套件

將原本 891 行的 models.py 拆分為 7 個模組：
1. associations - 關聯表
2. core - 基礎實體 (User, ContractProject, GovernmentAgency, PartnerVendor)
3. document - 公文模組 (OfficialDocument, DocumentAttachment)
4. calendar - 行事曆模組 (DocumentCalendarEvent, EventReminder)
5. system - 系統+AI 模組 (SystemNotification, UserSession, etc.)
6. staff - 專案人員模組 (ProjectAgencyContact, StaffCertification)
7. taoyuan - 桃園派工模組 (TaoyuanProject, TaoyuanDispatchOrder, etc.)

所有模型透過此 __init__.py 統一匯出，維持既有 import 路徑不變：
    from app.extended.models import OfficialDocument, ContractProject, ...
"""

# 1. 關聯表
from .associations import (
    project_vendor_association,
    project_user_assignment,
)

# 2. 基礎實體
from .core import (
    PartnerVendor,
    ContractProject,
    GovernmentAgency,
    User,
)

# 3. 公文模組
from .document import (
    OfficialDocument,
    DocumentAttachment,
)

# 4. 行事曆模組
from .calendar import (
    DocumentCalendarEvent,
    EventReminder,
)

# 5. 系統 + AI 模組
from .system import (
    SystemNotification,
    UserSession,
    SiteNavigationItem,
    SiteConfiguration,
    AIPromptVersion,
    AISearchHistory,
    AIConversationFeedback,
    AISynonym,
)

# 6. 專案人員模組
from .staff import (
    ProjectAgencyContact,
    StaffCertification,
)

# 7. 桃園派工模組
from .taoyuan import (
    TaoyuanProject,
    TaoyuanDispatchOrder,
    TaoyuanDispatchProjectLink,
    TaoyuanDispatchDocumentLink,
    TaoyuanDocumentProjectLink,
    TaoyuanContractPayment,
    TaoyuanDispatchAttachment,
    TaoyuanDispatchWorkType,
    TaoyuanWorkRecord,
)

# 8. AI 實體提取模組
from .entity import (
    DocumentEntity,
    EntityRelation,
)

# 9. 知識圖譜正規化模組
from .knowledge_graph import (
    CanonicalEntity,
    EntityAlias,
    DocumentEntityMention,
    EntityRelationship,
    GraphIngestionEvent,
)

# 10. AI 分析持久化模組
from .ai_analysis import (
    DocumentAIAnalysis,
)

# 匯出 Base 供 Alembic 等工具使用
from ._base import Base

__all__ = [
    # Base
    "Base",
    # 關聯表
    "project_vendor_association",
    "project_user_assignment",
    # 基礎實體
    "PartnerVendor",
    "ContractProject",
    "GovernmentAgency",
    "User",
    # 公文
    "OfficialDocument",
    "DocumentAttachment",
    # 行事曆
    "DocumentCalendarEvent",
    "EventReminder",
    # 系統
    "SystemNotification",
    "UserSession",
    "SiteNavigationItem",
    "SiteConfiguration",
    "AIPromptVersion",
    "AISearchHistory",
    "AIConversationFeedback",
    "AISynonym",
    # 專案人員
    "ProjectAgencyContact",
    "StaffCertification",
    # 桃園派工
    "TaoyuanProject",
    "TaoyuanDispatchOrder",
    "TaoyuanDispatchProjectLink",
    "TaoyuanDispatchDocumentLink",
    "TaoyuanDocumentProjectLink",
    "TaoyuanContractPayment",
    "TaoyuanDispatchAttachment",
    "TaoyuanDispatchWorkType",
    "TaoyuanWorkRecord",
    # AI 實體提取
    "DocumentEntity",
    "EntityRelation",
    # 知識圖譜正規化
    "CanonicalEntity",
    "EntityAlias",
    "DocumentEntityMention",
    "EntityRelationship",
    "GraphIngestionEvent",
    # AI 分析持久化
    "DocumentAIAnalysis",
]

"""
桃園查估派工管理系統 - Pydantic Schemas

拆分自 app.schemas.taoyuan_dispatch，統一 re-export 所有 schemas。
"""

# Constants
from app.schemas.taoyuan.constants import LinkTypeEnum, WORK_TYPES

# Project schemas
from app.schemas.taoyuan.project import (
    TaoyuanProjectBase,
    TaoyuanProjectCreate,
    TaoyuanProjectUpdate,
    TaoyuanProject,
    TaoyuanProjectListQuery,
    TaoyuanProjectListResponse,
    LinkedProjectItem,
    ExcelImportRequest,
    ExcelImportResult,
)

# Dispatch schemas
from app.schemas.taoyuan.dispatch import (
    DispatchOrderBase,
    DispatchOrderCreate,
    DispatchOrderUpdate,
    DispatchOrder,
    DispatchOrderListQuery,
    DispatchOrderListResponse,
    DocumentHistoryItem,
    DocumentHistoryMatchRequest,
    DocumentHistoryResponse,
    DispatchOrderWithHistory,
    DispatchAttachmentBase,
    DispatchAttachment,
    DispatchAttachmentListResponse,
    DispatchAttachmentUploadResult,
    DispatchAttachmentDeleteResult,
    DispatchAttachmentVerifyResult,
)

# Link schemas
from app.schemas.taoyuan.links import (
    ProjectDispatchLink,
    ProjectDocumentLink,
    TaoyuanProjectWithLinks,
    DispatchDocumentLink,
    DispatchDocumentLinkCreate,
    BaseLinkResponse,
    DispatchLinkResponse,
    ProjectLinkResponse,
    DocumentDispatchLinkResponse,
    DocumentProjectLinkResponse,
)

# Payment schemas
from app.schemas.taoyuan.payment import (
    WorkPayment,
    ContractPaymentBase,
    ContractPaymentCreate,
    ContractPaymentUpdate,
    ContractPayment,
    ContractPaymentListResponse,
    PaymentControlItem,
    PaymentControlResponse,
    MasterControlItem,
    MasterControlQuery,
    MasterControlResponse,
)

# Statistics schemas
from app.schemas.taoyuan.statistics import (
    ProjectStatistics,
    DispatchStatistics,
    PaymentStatistics,
    TaoyuanStatisticsResponse,
)

__all__ = [
    # Constants
    "LinkTypeEnum",
    "WORK_TYPES",
    # Project
    "TaoyuanProjectBase",
    "TaoyuanProjectCreate",
    "TaoyuanProjectUpdate",
    "TaoyuanProject",
    "TaoyuanProjectListQuery",
    "TaoyuanProjectListResponse",
    "LinkedProjectItem",
    "ExcelImportRequest",
    "ExcelImportResult",
    # Dispatch
    "DispatchOrderBase",
    "DispatchOrderCreate",
    "DispatchOrderUpdate",
    "DispatchOrder",
    "DispatchOrderListQuery",
    "DispatchOrderListResponse",
    "DocumentHistoryItem",
    "DocumentHistoryMatchRequest",
    "DocumentHistoryResponse",
    "DispatchOrderWithHistory",
    "DispatchAttachmentBase",
    "DispatchAttachment",
    "DispatchAttachmentListResponse",
    "DispatchAttachmentUploadResult",
    "DispatchAttachmentDeleteResult",
    "DispatchAttachmentVerifyResult",
    # Links
    "ProjectDispatchLink",
    "ProjectDocumentLink",
    "TaoyuanProjectWithLinks",
    "DispatchDocumentLink",
    "DispatchDocumentLinkCreate",
    "BaseLinkResponse",
    "DispatchLinkResponse",
    "ProjectLinkResponse",
    "DocumentDispatchLinkResponse",
    "DocumentProjectLinkResponse",
    # Payment
    "WorkPayment",
    "ContractPaymentBase",
    "ContractPaymentCreate",
    "ContractPaymentUpdate",
    "ContractPayment",
    "ContractPaymentListResponse",
    "PaymentControlItem",
    "PaymentControlResponse",
    "MasterControlItem",
    "MasterControlQuery",
    "MasterControlResponse",
    # Statistics
    "ProjectStatistics",
    "DispatchStatistics",
    "PaymentStatistics",
    "TaoyuanStatisticsResponse",
]

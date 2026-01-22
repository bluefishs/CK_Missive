"""
桃園派工管理 API 共用模組

包含所有子模組共用的導入、模型和常數

@version 1.0.0
@date 2026-01-22
"""
import logging
import os
import uuid
import hashlib
import aiofiles
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, distinct
from sqlalchemy.orm import selectinload
import pandas as pd
import io

from app.db.database import get_async_db
from app.core.dependencies import require_auth
from app.core.config import settings
from app.extended.models import (
    TaoyuanProject,
    TaoyuanDispatchOrder,
    TaoyuanDispatchProjectLink,
    TaoyuanDispatchDocumentLink,
    TaoyuanDocumentProjectLink,
    TaoyuanContractPayment,
    TaoyuanDispatchAttachment,
    OfficialDocument as Document,
    ContractProject,
)
from app.schemas.taoyuan_dispatch import (
    # Project schemas
    TaoyuanProjectCreate,
    TaoyuanProjectUpdate,
    TaoyuanProject as TaoyuanProjectSchema,
    TaoyuanProjectListQuery,
    TaoyuanProjectListResponse,
    LinkedProjectItem,
    TaoyuanProjectWithLinks,
    ProjectDispatchLink,
    ProjectDocumentLink,
    # Dispatch schemas
    DispatchOrderCreate,
    DispatchOrderUpdate,
    DispatchOrder as DispatchOrderSchema,
    DispatchOrderListQuery,
    DispatchOrderListResponse,
    DispatchDocumentLinkCreate,
    DispatchDocumentLink,
    # Payment schemas
    ContractPaymentCreate,
    ContractPaymentUpdate,
    ContractPayment as ContractPaymentSchema,
    ContractPaymentListResponse,
    PaymentControlItem,
    PaymentControlResponse,
    # Control schemas
    MasterControlQuery,
    MasterControlResponse,
    MasterControlItem,
    ExcelImportRequest,
    ExcelImportResult,
    WORK_TYPES,
    # Statistics schemas
    ProjectStatistics,
    DispatchStatistics,
    PaymentStatistics,
    TaoyuanStatisticsResponse,
    # Attachment schemas
    DispatchAttachment,
    DispatchAttachmentListResponse,
    DispatchAttachmentUploadResult,
    DispatchAttachmentDeleteResult,
    DispatchAttachmentVerifyResult,
)
from app.schemas.common import PaginationMeta

# Import safe converters from utils
from app.api.endpoints.utils.safe_converters import _safe_int, _safe_float

# Logger
logger = logging.getLogger(__name__)

# Export all shared elements
__all__ = [
    # Logger
    "logger",
    # Standard library
    "os",
    "uuid",
    "hashlib",
    "aiofiles",
    "re",
    "datetime",
    "date",
    # Type hints
    "Optional",
    "List",
    "Dict",
    "Any",
    # FastAPI
    "APIRouter",
    "Depends",
    "HTTPException",
    "UploadFile",
    "File",
    "Form",
    "Body",
    "StreamingResponse",
    "FileResponse",
    # SQLAlchemy
    "AsyncSession",
    "select",
    "func",
    "and_",
    "or_",
    "distinct",
    "selectinload",
    # Data processing
    "pd",
    "io",
    # Database
    "get_async_db",
    # Config
    "settings",
    # Auth
    "require_auth",
    # Models
    "TaoyuanProject",
    "TaoyuanDispatchOrder",
    "TaoyuanDispatchProjectLink",
    "TaoyuanDispatchDocumentLink",
    "TaoyuanDocumentProjectLink",
    "TaoyuanContractPayment",
    "TaoyuanDispatchAttachment",
    "Document",
    "ContractProject",
    # Project schemas
    "TaoyuanProjectCreate",
    "TaoyuanProjectUpdate",
    "TaoyuanProjectSchema",
    "TaoyuanProjectListQuery",
    "TaoyuanProjectListResponse",
    "LinkedProjectItem",
    "TaoyuanProjectWithLinks",
    "ProjectDispatchLink",
    "ProjectDocumentLink",
    # Dispatch schemas
    "DispatchOrderCreate",
    "DispatchOrderUpdate",
    "DispatchOrderSchema",
    "DispatchOrderListQuery",
    "DispatchOrderListResponse",
    "DispatchDocumentLinkCreate",
    "DispatchDocumentLink",
    # Payment schemas
    "ContractPaymentCreate",
    "ContractPaymentUpdate",
    "ContractPaymentSchema",
    "ContractPaymentListResponse",
    "PaymentControlItem",
    "PaymentControlResponse",
    # Control schemas
    "MasterControlQuery",
    "MasterControlResponse",
    "MasterControlItem",
    "ExcelImportRequest",
    "ExcelImportResult",
    "WORK_TYPES",
    # Statistics schemas
    "ProjectStatistics",
    "DispatchStatistics",
    "PaymentStatistics",
    "TaoyuanStatisticsResponse",
    # Attachment schemas
    "DispatchAttachment",
    "DispatchAttachmentListResponse",
    "DispatchAttachmentUploadResult",
    "DispatchAttachmentDeleteResult",
    "DispatchAttachmentVerifyResult",
    # Common schemas
    "PaginationMeta",
    # Utilities
    "_safe_int",
    "_safe_float",
]

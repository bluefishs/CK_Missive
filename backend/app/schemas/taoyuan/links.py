"""
桃園查估派工 - 關聯 Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime

from app.schemas.taoyuan.constants import LinkTypeEnum
from app.schemas.taoyuan.project import TaoyuanProject


class ProjectDispatchLink(BaseModel):
    """工程關聯的派工單簡要資訊"""
    link_id: int = Field(..., description="關聯記錄 ID")
    dispatch_order_id: int = Field(..., description="派工單 ID")
    dispatch_no: Optional[str] = Field(None, description="派工單號")
    work_type: Optional[str] = Field(None, description="作業類別")

    model_config = ConfigDict(from_attributes=True)


class ProjectDocumentLink(BaseModel):
    """工程關聯的公文簡要資訊"""
    link_id: int = Field(..., description="關聯記錄 ID")
    document_id: int = Field(..., description="公文 ID")
    doc_number: Optional[str] = Field(None, description="公文字號")
    link_type: str = Field(..., description="關聯類型 (agency_incoming/company_outgoing)")

    model_config = ConfigDict(from_attributes=True)


class TaoyuanProjectWithLinks(TaoyuanProject):
    """轄管工程完整資訊（包含關聯）"""
    linked_dispatches: List[ProjectDispatchLink] = Field(default_factory=list, description="關聯派工單")
    linked_documents: List[ProjectDocumentLink] = Field(default_factory=list, description="關聯公文")

    model_config = ConfigDict(from_attributes=True)


# 派工-公文關聯 Schemas
class DispatchDocumentLink(BaseModel):
    """派工-公文關聯"""
    id: int
    dispatch_order_id: int
    document_id: int
    link_type: LinkTypeEnum = Field(..., description="關聯類型：agency_incoming(機關來函) / company_outgoing(乾坤發文)")
    created_at: Optional[datetime] = None

    # 公文資訊
    doc_number: Optional[str] = None
    doc_date: Optional[date] = None
    subject: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DispatchDocumentLinkCreate(BaseModel):
    """建立派工-公文關聯 (dispatch_order_id 由 URL path 提供)"""
    document_id: int
    link_type: LinkTypeEnum = Field(..., description="關聯類型：agency_incoming(機關來函) / company_outgoing(乾坤發文)")


# 統一關聯回應 Schemas (SSOT)
class BaseLinkResponse(BaseModel):
    """基礎關聯回應 (所有關聯類型共用)"""
    link_id: int = Field(..., description="關聯記錄 ID")
    link_type: Optional[LinkTypeEnum] = Field(None, description="關聯類型")
    created_at: Optional[datetime] = Field(None, description="建立時間")


class DispatchLinkResponse(BaseLinkResponse):
    """派工單關聯回應"""
    dispatch_order_id: int = Field(..., description="派工單 ID")
    dispatch_no: str = Field(..., description="派工單號")
    project_name: Optional[str] = Field(None, description="工程名稱")
    work_type: Optional[str] = Field(None, description="作業類別")


class ProjectLinkResponse(BaseLinkResponse):
    """工程關聯回應"""
    project_id: int = Field(..., description="工程 ID")
    project_name: str = Field(..., description="工程名稱")


class DocumentDispatchLinkResponse(DispatchLinkResponse):
    """公文關聯的派工單回應 (完整版)"""
    link_type: LinkTypeEnum = Field(..., description="關聯類型")
    sub_case_name: Optional[str] = Field(None, description="分案名稱")
    deadline: Optional[str] = Field(None, description="工作期限")
    case_handler: Optional[str] = Field(None, description="案件承辦")
    survey_unit: Optional[str] = Field(None, description="查估單位")
    contact_note: Optional[str] = Field(None, description="聯繫備註")
    cloud_folder: Optional[str] = Field(None, description="雲端資料夾")
    project_folder: Optional[str] = Field(None, description="專案資料夾")
    agency_doc_number: Optional[str] = Field(None, description="機關函文文號")
    company_doc_number: Optional[str] = Field(None, description="乾坤函文文號")

    model_config = ConfigDict(from_attributes=True)


class DocumentProjectLinkResponse(ProjectLinkResponse):
    """公文關聯的工程回應 (完整版)"""
    notes: Optional[str] = Field(None, description="備註")
    district: Optional[str] = Field(None, description="行政區")
    review_year: Optional[int] = Field(None, description="審議年度")
    case_type: Optional[str] = Field(None, description="案件類型")
    sub_case_name: Optional[str] = Field(None, description="分案名稱")
    case_handler: Optional[str] = Field(None, description="案件承辦")
    survey_unit: Optional[str] = Field(None, description="查估單位")

    model_config = ConfigDict(from_attributes=True)

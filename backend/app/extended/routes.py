"""
擴展API路由 - 四大功能模組
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.extended.models import ContractProject, OfficialDocument, GovernmentAgency, PartnerVendor

router = APIRouter()

# 承攬案件路由
@router.get("/projects")
async def get_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    year: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """獲取承攬案件列表"""
    query = db.query(ContractProject)
    
    if year:
        query = query.filter(ContractProject.year == year)
    if status:
        query = query.filter(ContractProject.status == status)
    
    projects = query.offset(skip).limit(limit).all()
    return projects

@router.get("/projects/{project_id}")
async def get_project(project_id: int, db: Session = Depends(get_db)):
    """獲取單個承攬案件"""
    project = db.query(ContractProject).filter(ContractProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="案件不存在")
    return project

# 公文管理路由 - 已移至 app.api.endpoints.documents
# @router.get("/documents")
# async def get_documents(
#     skip: int = Query(0, ge=0),
#     limit: int = Query(100, ge=1, le=1000),
#     doc_type: Optional[str] = Query(None),
#     db: Session = Depends(get_db)
# ):
#     """獲取公文列表"""
#     query = db.query(OfficialDocument)
#
#     if doc_type:
#         query = query.filter(OfficialDocument.doc_type == doc_type)
#
#     documents = query.offset(skip).limit(limit).all()
#     return documents

# @router.get("/documents/{document_id}")
# async def get_document(document_id: int, db: Session = Depends(get_db)):
#     """獲取單個公文"""
#     document = db.query(OfficialDocument).filter(OfficialDocument.id == document_id).first()
#     if not document:
#         raise HTTPException(status_code=404, detail="公文不存在")
#     return document

# 機關單位路由
@router.get("/agencies")
async def get_agencies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """獲取機關單位列表"""
    agencies = db.query(GovernmentAgency).offset(skip).limit(limit).all()
    return agencies

@router.get("/agencies/{agency_id}")
async def get_agency(agency_id: int, db: Session = Depends(get_db)):
    """獲取單個機關單位"""
    agency = db.query(GovernmentAgency).filter(GovernmentAgency.id == agency_id).first()
    if not agency:
        raise HTTPException(status_code=404, detail="機關單位不存在")
    return agency

# 協力廠商路由
@router.get("/vendors")
async def get_vendors(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    rating: Optional[int] = Query(None, ge=1, le=5),
    db: Session = Depends(get_db)
):
    """獲取協力廠商列表"""
    query = db.query(PartnerVendor)
    
    if rating:
        query = query.filter(PartnerVendor.rating == rating)
    
    vendors = query.offset(skip).limit(limit).all()
    return vendors

@router.get("/vendors/{vendor_id}")
async def get_vendor(vendor_id: int, db: Session = Depends(get_db)):
    """獲取單個協力廠商"""
    vendor = db.query(PartnerVendor).filter(PartnerVendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="協力廠商不存在")
    return vendor

# 統計路由
@router.get("/stats/overview")
async def get_statistics(db: Session = Depends(get_db)):
    """獲取系統統計"""
    total_projects = db.query(ContractProject).count()
    total_documents = db.query(OfficialDocument).count()
    total_agencies = db.query(GovernmentAgency).count()
    total_vendors = db.query(PartnerVendor).count()
    
    return {
        "total_projects": total_projects,
        "total_documents": total_documents,
        "total_agencies": total_agencies,
        "total_vendors": total_vendors
    }

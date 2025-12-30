"""
擴展CRUD操作
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from app.extended.models import ContractProject, OfficialDocument, GovernmentAgency, PartnerVendor

class ProjectCRUD:
    @staticmethod
    def get_projects(db: Session, skip: int = 0, limit: int = 100) -> List[ContractProject]:
        return db.query(ContractProject).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_project(db: Session, project_id: int) -> Optional[ContractProject]:
        return db.query(ContractProject).filter(ContractProject.id == project_id).first()

class DocumentCRUD:
    @staticmethod
    def get_documents(db: Session, skip: int = 0, limit: int = 100) -> List[OfficialDocument]:
        return db.query(OfficialDocument).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_document(db: Session, document_id: int) -> Optional[OfficialDocument]:
        return db.query(OfficialDocument).filter(OfficialDocument.id == document_id).first()

class AgencyCRUD:
    @staticmethod
    def get_agencies(db: Session, skip: int = 0, limit: int = 100) -> List[GovernmentAgency]:
        return db.query(GovernmentAgency).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_agency(db: Session, agency_id: int) -> Optional[GovernmentAgency]:
        return db.query(GovernmentAgency).filter(GovernmentAgency.id == agency_id).first()

class VendorCRUD:
    @staticmethod
    def get_vendors(db: Session, skip: int = 0, limit: int = 100) -> List[PartnerVendor]:
        return db.query(PartnerVendor).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_vendor(db: Session, vendor_id: int) -> Optional[PartnerVendor]:
        return db.query(PartnerVendor).filter(PartnerVendor.id == vendor_id).first()

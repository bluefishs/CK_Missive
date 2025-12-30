"""
Pydantic schemas for Partner Vendors
"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class VendorBase(BaseModel):
    vendor_name: str = Field(..., max_length=200)
    vendor_code: Optional[str] = Field(None, max_length=50)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=300)
    email: Optional[str] = Field(None, max_length=100)
    business_type: Optional[str] = Field(None, max_length=100)
    rating: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class VendorCreate(VendorBase):
    pass

class VendorUpdate(BaseModel):
    vendor_name: Optional[str] = Field(None, max_length=200)
    vendor_code: Optional[str] = Field(None, max_length=50)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=300)
    email: Optional[str] = Field(None, max_length=100)
    business_type: Optional[str] = Field(None, max_length=100)
    rating: Optional[int] = None

class Vendor(VendorBase):
    id: int
    created_at: datetime
    updated_at: datetime

"""知識庫瀏覽器 API Schema"""

from pydantic import BaseModel


class FileRequest(BaseModel):
    path: str


class FileInfo(BaseModel):
    name: str
    path: str


class SectionInfo(BaseModel):
    name: str
    path: str
    files: list[FileInfo]


class TreeResponse(BaseModel):
    success: bool
    sections: list[SectionInfo]


class FileContentResponse(BaseModel):
    success: bool
    content: str
    filename: str


class AdrInfo(BaseModel):
    number: str
    title: str
    status: str
    date: str
    path: str


class AdrListResponse(BaseModel):
    success: bool
    items: list[AdrInfo]


class DiagramInfo(BaseModel):
    name: str
    path: str
    title: str


class DiagramListResponse(BaseModel):
    success: bool
    items: list[DiagramInfo]

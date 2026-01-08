# -*- coding: utf-8 -*-
"""
統一服務回應結構

提供標準化的服務層回應格式，確保 API 回應一致性。
"""
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional


@dataclass
class ServiceResponse:
    """統一服務回應結構"""
    success: bool
    data: Any = None
    message: str = ""
    code: str = ""
    errors: List[Dict] = field(default_factory=list)
    warnings: List[Dict] = field(default_factory=list)

    @classmethod
    def ok(cls, data: Any = None, message: str = "操作成功") -> "ServiceResponse":
        """建立成功回應"""
        return cls(success=True, data=data, message=message, code="OK")

    @classmethod
    def fail(cls, message: str, code: str = "ERROR", errors: List = None) -> "ServiceResponse":
        """建立失敗回應"""
        return cls(success=False, message=message, code=code, errors=errors or [])

    @classmethod
    def partial(cls, data: Any, warnings: List, message: str = "部分成功") -> "ServiceResponse":
        """建立部分成功回應"""
        return cls(success=True, data=data, message=message, code="PARTIAL", warnings=warnings)

    def to_dict(self) -> Dict:
        """轉換為字典格式"""
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "code": self.code,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class ImportRowResult:
    """單筆匯入結果"""
    row: int
    status: str  # 'inserted', 'updated', 'skipped', 'error'
    message: str
    doc_number: str = ""
    doc_id: Optional[int] = None

    def to_dict(self) -> Dict:
        return {
            "row": self.row,
            "status": self.status,
            "message": self.message,
            "doc_number": self.doc_number,
            "doc_id": self.doc_id,
        }


@dataclass
class ImportResult:
    """匯入結果總計"""
    success: bool
    filename: str
    total_rows: int
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: List[ImportRowResult] = field(default_factory=list)
    warnings: List[ImportRowResult] = field(default_factory=list)
    details: List[ImportRowResult] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def success_count(self) -> int:
        return self.inserted + self.updated

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "filename": self.filename,
            "total_rows": self.total_rows,
            "inserted": self.inserted,
            "updated": self.updated,
            "skipped": self.skipped,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "details": [d.to_dict() for d in self.details],
        }

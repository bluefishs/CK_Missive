"""
服務層基礎模組

提供服務層的基礎架構，包括:
- BaseService: 泛型 CRUD 基類
- UnitOfWork: 交易管理單元
- ImportBaseService: 匯入服務基類
- ServiceResponse: 統一回應結構
- Validators: 資料驗證器
"""
from app.services.base_service import BaseService
from app.services.base.unit_of_work import UnitOfWork, get_uow, unit_of_work
from app.services.base.import_base import ImportBaseService
from app.services.base.response import ServiceResponse, ImportResult, ImportRowResult
from app.services.base.validators import DocumentValidators, StringCleaners, DateParsers

__all__ = [
    # 基礎服務
    'BaseService',
    'UnitOfWork',
    'get_uow',
    'unit_of_work',
    # 匯入服務
    'ImportBaseService',
    # 回應結構
    'ServiceResponse',
    'ImportResult',
    'ImportRowResult',
    # 驗證器
    'DocumentValidators',
    'StringCleaners',
    'DateParsers',
]

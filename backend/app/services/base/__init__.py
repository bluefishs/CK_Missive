"""
服務層基礎模組

提供服務層的基礎架構，包括:
- BaseService: 泛型 CRUD 基類
- UnitOfWork: 交易管理單元
"""
from app.services.base_service import BaseService
from app.services.base.unit_of_work import UnitOfWork, get_uow, unit_of_work

__all__ = [
    'BaseService',
    'UnitOfWork',
    'get_uow',
    'unit_of_work',
]

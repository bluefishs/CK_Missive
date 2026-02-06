"""
服務層基礎模組

提供服務層的基礎架構，包括:
- UnitOfWork: 交易管理單元
- ImportBaseService: 匯入服務基類
- ServiceResponse: 統一回應結構
- Validators: 資料驗證器
- QueryHelper: 統一查詢助手
- PaginationHelper: 分頁助手
- FilterBuilder: 篩選條件建構器
- StatisticsHelper: 統計查詢助手
- DeleteCheckHelper: 刪除檢查助手
"""
from app.services.base.unit_of_work import UnitOfWork, get_uow, unit_of_work
from app.services.base.import_base import ImportBaseService
from app.services.base.response import ServiceResponse, ImportResult, ImportRowResult
from app.services.base.validators import DocumentValidators, StringCleaners, DateParsers
from app.services.base.query_helper import (
    QueryHelper,
    PaginationHelper,
    FilterBuilder,
    StatisticsHelper,
    DeleteCheckHelper
)

__all__ = [
    # 基礎服務
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
    # 查詢助手
    'QueryHelper',
    'PaginationHelper',
    'FilterBuilder',
    'StatisticsHelper',
    'DeleteCheckHelper',
]

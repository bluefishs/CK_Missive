"""
服務層基礎模組

提供服務層的基礎架構，包括:
- UnitOfWork: 交易管理單元 (延遲載入，避免循環依賴)
- ImportBaseService: 匯入服務基類
- ServiceResponse: 統一回應結構
- Validators: 資料驗證器
- QueryHelper: 統一查詢助手
- PaginationHelper: 分頁助手
- FilterBuilder: 篩選條件建構器
- StatisticsHelper: 統計查詢助手
- DeleteCheckHelper: 刪除檢查助手
"""
# 立即載入：不依賴業務服務的基礎模組
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

# UnitOfWork 延遲載入：避免 base → unit_of_work → vendor_service → base 循環
# 使用 __getattr__ 確保 `from app.services.base import UnitOfWork` 仍可正常運作
_UOW_NAMES = {'UnitOfWork', 'get_uow', 'unit_of_work'}


def __getattr__(name: str):
    if name in _UOW_NAMES:
        from app.services.base.unit_of_work import UnitOfWork, get_uow, unit_of_work
        _cache = {'UnitOfWork': UnitOfWork, 'get_uow': get_uow, 'unit_of_work': unit_of_work}
        # 寫入 globals 避免重複觸發 __getattr__
        globals().update(_cache)
        return _cache[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    # 基礎服務（延遲載入）
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

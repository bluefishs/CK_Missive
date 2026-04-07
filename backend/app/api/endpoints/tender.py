"""
標案檢索 API 端點 (POST-only)

已拆分至 tender_module/ 子模組:
  - search.py        搜尋/詳情/推薦/即時
  - graph_case.py    圖譜/建案
  - subscriptions.py 訂閱/書籤/廠商關注
  - analytics.py     分析儀表板

Version: 2.0.0 (模組化拆分)
"""
from app.api.endpoints.tender_module import router  # noqa: F401

"""
後端集中常數定義

所有業務常數統一在此定義，供 schemas、models、endpoints 引用
避免硬編碼和重複定義

@version 1.1.0
@date 2026-01-26
@updated 2026-03-22 — KG Federation entity/relation types
"""
from typing import List, FrozenSet

# ============================================================================
# 承攬案件相關常數
# ============================================================================

# 案件狀態
PROJECT_STATUS_OPTIONS: List[str] = ['待執行', '執行中', '已結案', '未得標']
PROJECT_STATUS_DEFAULT: str = '執行中'

# 計畫類別
PROJECT_CATEGORY_OPTIONS: List[str] = [
    '01委辦招標',
    '02承攬報價',
]

# 作業性質
CASE_NATURE_OPTIONS: List[str] = [
    '01地面測量',
    '02LiDAR掃描',
    '03UAV空拍',
    '04航空測量',
    '05安全檢測',
    '06建物保存',
    '07建築線測量',
    '08透地雷達',
    '09資訊系統',
    '10技師簽證',
    '11其他類別',
]

# ============================================================================
# 協力廠商相關常數
# ============================================================================

# 廠商角色
VENDOR_ROLE_OPTIONS: List[str] = [
    '測量業務',
    '系統業務',
    '查估業務',
    '其他類別',
]

# ============================================================================
# 承辦同仁相關常數
# ============================================================================

# 同仁角色
STAFF_ROLE_OPTIONS: List[str] = [
    '計畫主持',
    '計畫協同',
    '專案PM',
    '職安主管',
]

# 部門選項：已改為 DB 驅動（POST /users/departments），不再硬編碼

# ============================================================================
# 公文相關常數
# ============================================================================

# 公文處理狀態
DOC_STATUS_OPTIONS: List[str] = [
    '收文完成',
    '使用者確認',
    '收文異常',
]

# 公文類型
DOC_TYPE_OPTIONS: List[str] = [
    '函',
    '開會通知單',
    '會勘通知單',
]

# 發文形式
DELIVERY_METHOD_OPTIONS: List[str] = [
    '電子交換',
    '紙本郵寄',
]

# ============================================================================
# 桃園派工模組常數
# ============================================================================

# 桃園市府委外查估派工專案 contract_project_id
TAOYUAN_PROJECT_ID: int = 21

# ============================================================================
# 機關相關常數
# ============================================================================

# 機關類型
AGENCY_TYPE_OPTIONS: List[str] = [
    '中央機關',
    '地方機關',
    '民間單位',
    '其他',
]

# ============================================================================
# 知識圖譜 — 程式碼實體類型 (SSOT)
# ============================================================================

# 程式碼圖譜使用的實體類型，用於將公文圖譜與程式碼圖譜邏輯分離
CODE_ENTITY_TYPES: frozenset[str] = frozenset({
    'py_module', 'py_class', 'py_function', 'db_table',
    'ts_module', 'ts_component', 'ts_hook',
    # Infrastructure types (v2.0 — inspired by Understand-Anything)
    'api_endpoint', 'service', 'repository', 'schema', 'config', 'middleware',
})

# ============================================================================
# 知識圖譜 — 跨專案聯邦實體類型 (KG Federation, v1.1.0)
# ============================================================================

# 來源專案識別碼
KG_SOURCE_PROJECTS: FrozenSet[str] = frozenset({
    'ck-missive', 'ck-lvrland', 'ck-tunnel',
})

# 跨專案實體類型（與公文/程式碼圖譜邏輯分離）
CROSS_PROJECT_ENTITY_TYPES: FrozenSet[str] = frozenset({
    'land_parcel',       # LvrLand: 地段 (land_no14)
    'development_zone',  # LvrLand: 開發區/都更案
    'transaction',       # LvrLand: 不動產交易
    'tunnel',            # Tunnel: 隧道
    'crack_defect',      # Tunnel: 裂縫缺陷
    'inspection',        # Tunnel: 檢查紀錄
    'contractor',        # Cross-domain: 承包商/承攬廠商
})

# 跨專案關係類型
CROSS_PROJECT_RELATION_TYPES: FrozenSet[str] = frozenset({
    'located_at',        # entity → land_parcel (位於地段)
    'contracted_by',     # project/inspection → contractor (承攬)
    'detected_in',       # crack_defect → tunnel (偵測於)
    'affects_parcel',    # development_zone → land_parcel (影響地段)
    'part_of_project',   # tunnel/inspection → project (隸屬專案)
    'transacted_at',     # transaction → land_parcel (交易於)
    'commissioned_by',   # project/tunnel → agency (委託)
})

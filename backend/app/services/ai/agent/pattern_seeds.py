"""
Pattern Learner Cold-Start Seed Data

CK_Missive 公文管理系統常見查詢模式種子資料。
在 Redis 無任何已學習模式時，載入這些種子以提供基線路由能力。

每筆種子包含：
- question: 代表性的使用者查詢（繁體中文）
- tools: 成功回答該查詢所需的工具序列
- category: 分類標籤（供日後分析）

Version: 1.0.0
Created: 2026-03-15
"""

from typing import Any, Dict, List

SEED_PATTERNS: List[Dict[str, Any]] = [
    # ── 公文查詢 (doc) ──
    {
        "question": "最近的公文有哪些",
        "tools": ["search_documents"],
        "category": "doc",
    },
    {
        "question": "找工務局的公文",
        "tools": ["search_documents"],
        "category": "doc",
    },
    {
        "question": "這個月的收文統計",
        "tools": ["get_statistics"],
        "category": "doc",
    },
    {
        "question": "有關道路養護的公文",
        "tools": ["search_documents"],
        "category": "doc",
    },
    {
        "question": "最近收到的函有哪些",
        "tools": ["search_documents"],
        "category": "doc",
    },
    {
        "question": "今年發文給交通局的公文",
        "tools": ["search_documents"],
        "category": "doc",
    },
    {
        "question": "跟這份公文類似的有哪些",
        "tools": ["find_similar"],
        "category": "doc",
    },
    # ── 知識圖譜 / 實體查詢 (graph) ──
    {
        "question": "工務局和交通局有什麼關係",
        "tools": ["search_entities", "explore_entity_path"],
        "category": "graph",
    },
    {
        "question": "知識圖譜中的淨零排碳",
        "tools": ["search_entities", "get_entity_detail"],
        "category": "graph",
    },
    {
        "question": "帶我到工務局的關聯圖",
        "tools": ["search_entities", "navigate_graph"],
        "category": "graph",
    },
    {
        "question": "這個實體的詳細資訊",
        "tools": ["get_entity_detail"],
        "category": "graph",
    },
    {
        "question": "知識圖譜有多少實體",
        "tools": ["get_statistics"],
        "category": "graph",
    },
    {
        "question": "幫我生成這個實體的摘要",
        "tools": ["summarize_entity"],
        "category": "graph",
    },
    # ── 派工單查詢 (dispatch) ──
    {
        "question": "最近的派工單有哪些",
        "tools": ["search_dispatch_orders"],
        "category": "dispatch",
    },
    {
        "question": "道路工程的派工紀錄",
        "tools": ["search_dispatch_orders"],
        "category": "dispatch",
    },
    {
        "question": "測量作業的派工單",
        "tools": ["search_dispatch_orders"],
        "category": "dispatch",
    },
    {
        "question": "這份派工單的收發文對應",
        "tools": ["find_correspondence"],
        "category": "dispatch",
    },
    # ── 專案管理查詢 (pm) ──
    {
        "question": "目前執行中的案件有哪些",
        "tools": ["search_projects"],
        "category": "pm",
    },
    {
        "question": "這個案件的詳細資訊",
        "tools": ["get_project_detail"],
        "category": "pm",
    },
    {
        "question": "案件進度有沒有逾期的",
        "tools": ["get_project_progress"],
        "category": "pm",
    },
    {
        "question": "今年度合約金額統計",
        "tools": ["get_contract_summary"],
        "category": "pm",
    },
    # ── 廠商查詢 (vendor) ──
    {
        "question": "測量公司有哪些",
        "tools": ["search_vendors"],
        "category": "vendor",
    },
    {
        "question": "這家廠商的聯絡資訊",
        "tools": ["get_vendor_detail"],
        "category": "vendor",
    },
    # ── 系統 / 視覺化 (system) ──
    {
        "question": "系統目前的健康狀態",
        "tools": ["get_system_health"],
        "category": "system",
    },
    {
        "question": "畫出資料庫的 ER 圖",
        "tools": ["draw_diagram"],
        "category": "system",
    },
    # ── 跨域複合查詢 (mixed) ──
    {
        "question": "這個案件相關的公文和派工單",
        "tools": ["search_documents", "search_dispatch_orders"],
        "category": "mixed",
    },
    {
        "question": "工務局委託的案件和對應公文",
        "tools": ["search_projects", "search_documents"],
        "category": "mixed",
    },
    {
        "question": "這個廠商承接了哪些案件",
        "tools": ["get_vendor_detail", "search_projects"],
        "category": "mixed",
    },
    {
        "question": "最近的派工單和相關工程進度",
        "tools": ["search_dispatch_orders", "get_project_progress"],
        "category": "mixed",
    },
]

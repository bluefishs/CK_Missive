"""
Agent Benchmark Suite — 50 題標準問答品質追蹤

5 大領域 × 10 題:
- 公文 (doc): 搜尋/摘要/配對/統計
- 派工 (dispatch): 工程/時間軸/進度
- ERP (erp): 報價/請款/帳務
- 標案 (tender): 搜尋/分析/推薦
- 跨域 (cross): 機關關係/案件全貌/比較

每題包含:
- question: 自然語言問題
- domain: 領域標籤
- expected_tools: 預期使用的工具
- keywords: 回答中應包含的關鍵詞
- difficulty: easy/medium/hard

用法:
  python -m pytest tests/benchmarks/agent_benchmark.py -v --tb=short
  python tests/benchmarks/agent_benchmark.py --dry-run  # 僅列出題目

Version: 1.0.0
Created: 2026-04-13
"""

BENCHMARK_QUESTIONS = [
    # =========================================================================
    # 公文 (10 題)
    # =========================================================================
    {
        "id": "doc-01",
        "question": "桃園市政府工務局最近一個月發了哪些公文給我們？",
        "domain": "doc",
        "expected_tools": ["query_documents"],
        "keywords": ["桃園", "工務局", "收文"],
        "difficulty": "easy",
    },
    {
        "id": "doc-02",
        "question": "今年度收發文件數量各是多少？",
        "domain": "doc",
        "expected_tools": ["query_documents"],
        "keywords": ["收文", "發文", "件"],
        "difficulty": "easy",
    },
    {
        "id": "doc-03",
        "question": "文號 桃工用字第1150013287號 這份公文的主旨是什麼？",
        "domain": "doc",
        "expected_tools": ["query_documents"],
        "keywords": ["桃工用字"],
        "difficulty": "easy",
    },
    {
        "id": "doc-04",
        "question": "南投縣政府跟我們往來的公文集中在哪些案件？",
        "domain": "doc",
        "expected_tools": ["query_documents", "wiki_search"],
        "keywords": ["南投", "案件"],
        "difficulty": "medium",
    },
    {
        "id": "doc-05",
        "question": "有沒有跟地籍圖重測相關的公文？列出最近 5 筆",
        "domain": "doc",
        "expected_tools": ["query_documents"],
        "keywords": ["地籍圖", "重測"],
        "difficulty": "medium",
    },
    {
        "id": "doc-06",
        "question": "哪些公文已逾期未處理？",
        "domain": "doc",
        "expected_tools": ["query_documents"],
        "keywords": ["逾期"],
        "difficulty": "medium",
    },
    {
        "id": "doc-07",
        "question": "今年發文數量最多的前 3 個機關是？",
        "domain": "doc",
        "expected_tools": ["query_documents"],
        "keywords": ["機關", "發文"],
        "difficulty": "medium",
    },
    {
        "id": "doc-08",
        "question": "上個月桃園用地取得案有哪些來函？彙整重點",
        "domain": "doc",
        "expected_tools": ["query_documents", "wiki_search"],
        "keywords": ["桃園", "用地", "來函"],
        "difficulty": "hard",
    },
    {
        "id": "doc-09",
        "question": "找出所有跟「道路拓寬工程」相關的收文，按機關分類",
        "domain": "doc",
        "expected_tools": ["query_documents"],
        "keywords": ["道路拓寬", "機關"],
        "difficulty": "hard",
    },
    {
        "id": "doc-10",
        "question": "比較 112 年度與 113 年度的收發文件趨勢",
        "domain": "doc",
        "expected_tools": ["query_documents"],
        "keywords": ["112", "113", "趨勢"],
        "difficulty": "hard",
    },

    # =========================================================================
    # 派工 (10 題)
    # =========================================================================
    {
        "id": "dispatch-01",
        "question": "目前有多少筆派工單？",
        "domain": "dispatch",
        "expected_tools": ["dispatch_query"],
        "keywords": ["派工", "筆"],
        "difficulty": "easy",
    },
    {
        "id": "dispatch-02",
        "question": "112年_派工單號001 的工程名稱和承辦是誰？",
        "domain": "dispatch",
        "expected_tools": ["dispatch_query", "wiki_search"],
        "keywords": ["派工單號001"],
        "difficulty": "easy",
    },
    {
        "id": "dispatch-03",
        "question": "桃園開口契約案目前有哪些派工在執行中？",
        "domain": "dispatch",
        "expected_tools": ["dispatch_query"],
        "keywords": ["桃園", "派工"],
        "difficulty": "medium",
    },
    {
        "id": "dispatch-04",
        "question": "新屋區中華南路道路拓寬工程的完整公文時間軸",
        "domain": "dispatch",
        "expected_tools": ["dispatch_query", "wiki_search"],
        "keywords": ["新屋", "中華南路", "公文"],
        "difficulty": "medium",
    },
    {
        "id": "dispatch-05",
        "question": "哪些派工單有逾期風險？",
        "domain": "dispatch",
        "expected_tools": ["dispatch_query"],
        "keywords": ["逾期", "派工"],
        "difficulty": "medium",
    },
    {
        "id": "dispatch-06",
        "question": "各作業類別的派工單數量分佈",
        "domain": "dispatch",
        "expected_tools": ["dispatch_query"],
        "keywords": ["作業類別"],
        "difficulty": "medium",
    },
    {
        "id": "dispatch-07",
        "question": "115年度桃園用地案的所有派工單和對應工程清單",
        "domain": "dispatch",
        "expected_tools": ["dispatch_query", "wiki_search"],
        "keywords": ["115", "桃園", "用地", "工程"],
        "difficulty": "hard",
    },
    {
        "id": "dispatch-08",
        "question": "邊坡光達計畫第七期目前執行進度如何？",
        "domain": "dispatch",
        "expected_tools": ["dispatch_query", "project_analytics"],
        "keywords": ["邊坡", "光達", "第七期"],
        "difficulty": "hard",
    },
    {
        "id": "dispatch-09",
        "question": "比較開口契約和後續擴充兩案的派工單密度",
        "domain": "dispatch",
        "expected_tools": ["dispatch_query", "project_analytics"],
        "keywords": ["開口契約", "後續擴充", "派工"],
        "difficulty": "hard",
    },
    {
        "id": "dispatch-10",
        "question": "整理中壢區所有工程的公文和派工時間軸",
        "domain": "dispatch",
        "expected_tools": ["dispatch_query", "wiki_search"],
        "keywords": ["中壢", "工程", "時間軸"],
        "difficulty": "hard",
    },

    # =========================================================================
    # ERP (10 題)
    # =========================================================================
    {
        "id": "erp-01",
        "question": "目前有多少筆報價紀錄？總金額多少？",
        "domain": "erp",
        "expected_tools": ["erp_query"],
        "keywords": ["報價", "金額"],
        "difficulty": "easy",
    },
    {
        "id": "erp-02",
        "question": "CK2025_01_03_001 這個案子的報價金額是多少？",
        "domain": "erp",
        "expected_tools": ["erp_query"],
        "keywords": ["CK2025", "金額"],
        "difficulty": "easy",
    },
    {
        "id": "erp-03",
        "question": "今年的請款狀態如何？已收多少？",
        "domain": "erp",
        "expected_tools": ["erp_query"],
        "keywords": ["請款", "收款"],
        "difficulty": "medium",
    },
    {
        "id": "erp-04",
        "question": "哪些案件的請款率低於 50%？",
        "domain": "erp",
        "expected_tools": ["erp_query", "project_analytics"],
        "keywords": ["請款率"],
        "difficulty": "medium",
    },
    {
        "id": "erp-05",
        "question": "帳本裡最大筆的支出是什麼？",
        "domain": "erp",
        "expected_tools": ["erp_query"],
        "keywords": ["支出", "帳本"],
        "difficulty": "medium",
    },
    {
        "id": "erp-06",
        "question": "費用報銷的案件分佈如何？",
        "domain": "erp",
        "expected_tools": ["erp_query"],
        "keywords": ["費用", "報銷"],
        "difficulty": "medium",
    },
    {
        "id": "erp-07",
        "question": "整理桃園開口契約案的完整財務狀況 (報價/請款/開票/帳本)",
        "domain": "erp",
        "expected_tools": ["erp_query", "project_analytics"],
        "keywords": ["桃園", "開口契約", "財務"],
        "difficulty": "hard",
    },
    {
        "id": "erp-08",
        "question": "所有案件的營收排行 (依合約金額)",
        "domain": "erp",
        "expected_tools": ["erp_query", "project_analytics"],
        "keywords": ["營收", "排行"],
        "difficulty": "hard",
    },
    {
        "id": "erp-09",
        "question": "有沒有異常的帳務紀錄？例如重複入帳或金額不一致",
        "domain": "erp",
        "expected_tools": ["erp_query"],
        "keywords": ["異常", "帳務"],
        "difficulty": "hard",
    },
    {
        "id": "erp-10",
        "question": "預估下個月需要請款的案件有哪些？",
        "domain": "erp",
        "expected_tools": ["erp_query", "project_analytics"],
        "keywords": ["請款", "預估"],
        "difficulty": "hard",
    },

    # =========================================================================
    # 標案 (10 題)
    # =========================================================================
    {
        "id": "tender-01",
        "question": "最近有什麼跟測量相關的標案？",
        "domain": "tender",
        "expected_tools": ["search_tenders"],
        "keywords": ["測量", "標案"],
        "difficulty": "easy",
    },
    {
        "id": "tender-02",
        "question": "桃園市政府最近招標的案件有哪些？",
        "domain": "tender",
        "expected_tools": ["search_tenders"],
        "keywords": ["桃園", "招標"],
        "difficulty": "easy",
    },
    {
        "id": "tender-03",
        "question": "地籍圖整合相關的標案預算範圍通常是多少？",
        "domain": "tender",
        "expected_tools": ["search_tenders"],
        "keywords": ["地籍圖", "預算"],
        "difficulty": "medium",
    },
    {
        "id": "tender-04",
        "question": "南投縣政府今年有什麼適合我們的標案？",
        "domain": "tender",
        "expected_tools": ["search_tenders"],
        "keywords": ["南投", "標案"],
        "difficulty": "medium",
    },
    {
        "id": "tender-05",
        "question": "我們的主要競爭對手在哪些機關得標最多？",
        "domain": "tender",
        "expected_tools": ["search_tenders"],
        "keywords": ["競爭", "得標"],
        "difficulty": "hard",
    },
    {
        "id": "tender-06",
        "question": "空間測量類標案的平均決標金額和得標率",
        "domain": "tender",
        "expected_tools": ["search_tenders"],
        "keywords": ["空間測量", "決標", "得標率"],
        "difficulty": "hard",
    },
    {
        "id": "tender-07",
        "question": "推薦我們應該關注的 3 個標案，說明理由",
        "domain": "tender",
        "expected_tools": ["search_tenders"],
        "keywords": ["推薦", "關注"],
        "difficulty": "hard",
    },
    {
        "id": "tender-08",
        "question": "交通部公路局的標案近兩年趨勢如何？",
        "domain": "tender",
        "expected_tools": ["search_tenders"],
        "keywords": ["交通部", "公路局", "趨勢"],
        "difficulty": "hard",
    },
    {
        "id": "tender-09",
        "question": "比較政府採購網和 ezbid 搜尋結果的差異",
        "domain": "tender",
        "expected_tools": ["search_tenders"],
        "keywords": ["政府採購", "ezbid"],
        "difficulty": "hard",
    },
    {
        "id": "tender-10",
        "question": "我們在公路局系統的歷史投標紀錄和得標率",
        "domain": "tender",
        "expected_tools": ["search_tenders"],
        "keywords": ["公路局", "投標", "得標"],
        "difficulty": "hard",
    },

    # =========================================================================
    # 跨域 (10 題)
    # =========================================================================
    {
        "id": "cross-01",
        "question": "桃園市政府工務局跟我們的完整往來概況",
        "domain": "cross",
        "expected_tools": ["wiki_search", "query_documents", "project_analytics"],
        "keywords": ["桃園", "工務局", "公文", "案件"],
        "difficulty": "medium",
    },
    {
        "id": "cross-02",
        "question": "CK2023_01_01_001 案件的全貌 (公文/派工/財務)",
        "domain": "cross",
        "expected_tools": ["wiki_search", "project_analytics", "dispatch_query", "erp_query"],
        "keywords": ["CK2023_01_01_001"],
        "difficulty": "medium",
    },
    {
        "id": "cross-03",
        "question": "南投縣和桃園市哪個案件量比較大？各自的特點？",
        "domain": "cross",
        "expected_tools": ["wiki_search", "query_documents"],
        "keywords": ["南投", "桃園", "比較"],
        "difficulty": "hard",
    },
    {
        "id": "cross-04",
        "question": "我們公司目前最忙的 3 個案件是什麼？依據什麼判斷？",
        "domain": "cross",
        "expected_tools": ["project_analytics", "dispatch_query"],
        "keywords": ["最忙", "案件"],
        "difficulty": "hard",
    },
    {
        "id": "cross-05",
        "question": "整理我們和交通部公路局中區分局的完整合作歷程",
        "domain": "cross",
        "expected_tools": ["wiki_search", "query_documents", "project_analytics"],
        "keywords": ["交通部", "公路局", "合作"],
        "difficulty": "hard",
    },
    {
        "id": "cross-06",
        "question": "本月的重點工作和待辦有哪些？",
        "domain": "cross",
        "expected_tools": ["query_documents", "dispatch_query"],
        "keywords": ["本月", "重點", "待辦"],
        "difficulty": "hard",
    },
    {
        "id": "cross-07",
        "question": "知識圖譜中跟「地上物查估」相關的實體有哪些？和哪些機關連結？",
        "domain": "cross",
        "expected_tools": ["kg_query", "wiki_search"],
        "keywords": ["地上物", "查估", "實體"],
        "difficulty": "hard",
    },
    {
        "id": "cross-08",
        "question": "哪些案件同時有派工單和標案紀錄？交叉比對",
        "domain": "cross",
        "expected_tools": ["dispatch_query", "search_tenders", "project_analytics"],
        "keywords": ["派工", "標案", "交叉"],
        "difficulty": "hard",
    },
    {
        "id": "cross-09",
        "question": "給我一份本季度的經營概況報告",
        "domain": "cross",
        "expected_tools": ["project_analytics", "erp_query", "query_documents"],
        "keywords": ["經營", "概況"],
        "difficulty": "hard",
    },
    {
        "id": "cross-10",
        "question": "如果下季要投標桃園市新的用地取得案，我們需要準備什麼？",
        "domain": "cross",
        "expected_tools": ["search_tenders", "wiki_search", "project_analytics"],
        "keywords": ["投標", "桃園", "準備"],
        "difficulty": "hard",
    },
]


def get_benchmark_stats():
    """統計 benchmark 分佈"""
    by_domain = {}
    by_difficulty = {}
    for q in BENCHMARK_QUESTIONS:
        by_domain[q["domain"]] = by_domain.get(q["domain"], 0) + 1
        by_difficulty[q["difficulty"]] = by_difficulty.get(q["difficulty"], 0) + 1
    return {
        "total": len(BENCHMARK_QUESTIONS),
        "by_domain": by_domain,
        "by_difficulty": by_difficulty,
    }


if __name__ == "__main__":
    import sys
    stats = get_benchmark_stats()
    print(f"Agent Benchmark Suite: {stats['total']} questions")
    print(f"  Domains: {stats['by_domain']}")
    print(f"  Difficulty: {stats['by_difficulty']}")
    if "--dry-run" in sys.argv:
        print("\nQuestions:")
        for q in BENCHMARK_QUESTIONS:
            print(f"  [{q['id']}] ({q['difficulty']}) {q['question']}")

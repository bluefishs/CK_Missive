"""
AI 服務相關 Pydantic Schema

拆分為功能子模組，各消費者直接從子模組匯入。
此 __init__.py 僅保留 __all__ 宣告供文件化參考。

子模組：
  - search: 搜尋意圖、自然語言搜尋
  - endpoints: AI 端點 (摘要/分類/關鍵字/機關匹配)
  - synonyms: 同義詞管理
  - common: 通用回應型別 (SuccessResponse, OkResponse)
  - search_history: 搜尋歷史與統計
  - graph: 知識圖譜 (GraphNode, GraphEdge, Embedding)
  - prompts: Prompt 模板管理
  - entity: 實體提取
  - ollama: Ollama 模型管理
  - rag: RAG 問答與 Agent 查詢
  - analysis: 文件 AI 分析

Version: 3.0.0
Created: 2026-02-05
Updated: 2026-03-11 - 移除 re-export，各消費者已改用子模組路徑
"""

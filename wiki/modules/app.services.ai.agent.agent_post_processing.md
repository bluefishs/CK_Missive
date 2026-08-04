---
title: app.services.ai.agent.agent_post_processing
kg_entity_id: 799807
type: module
module_lines: 476
module_relations: 28
file_path: /app/app/services/ai/agent/agent_post_processing.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.services.ai.agent.agent_post_processing

## 概述
該模組負責處理由 `agent_orchestrator.py` 提取的查詢完成後的非核心任務，包括引用核實、品質自省、對話記憶儲存與摘要壓縮、使用者偏好萃取、追蹤持久化、模式學習以及查詢興趣追蹤和自我評估。

## 主要類別
- **PostProcessingContext**

## 公開函數
- `self_talk`
- `self_evaluate_and_evolve`
- `run_post_synthesis`

## 依賴關係
- `app.services.ai.agent.agent_synthesis`
- `app.services.ai.agent.agent_pattern_learner`
- `app.services.ai.core.agent_utils`
- `app.services.ai.misc.user_preference_extractor`
- `app.services.ai.misc.user_query_tracker`
- `app.db.database`
- `app.repositories.agent_learning_repository`
- `app.services.ai.tools.tool_result_formatter`
- `app.services.ai.agent.agent_self_evaluator`
- `app.services.contracts.facades.memory`

---

**Version:** 1.0.0  
**Created:** 202
```

This markdown document provides a structured overview of the specified Python module, including its main components and dependencies.

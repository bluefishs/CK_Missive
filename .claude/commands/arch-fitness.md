---
description: 架構 Fitness Functions 本地執行（零 CI 費用）— 月度覆盤或大重構前使用
---

# /arch-fitness — 架構 Fitness Functions 本地跑

本地手動執行 architecture fitness checks，**不使用 GitHub Actions**（規範：不產生 CI 費用）。

## 執行

```bash
bash scripts/checks/run_fitness.sh            # warning 模式（預設）
bash scripts/checks/run_fitness.sh --strict   # 超標即 exit 1
```

## 檢查項

依序跑：
1. `scripts/checks/service_dir_entropy.py` — `services/` 頂層散戶比例
   - 閾值：20%（STANDARD_REFERENCE §12）
   - 現況約 29.5%（85 散戶 / 288 總）→ warning
2. `scripts/checks/config_dead_reader_scan.py` — yaml config dead reader
   - 掃 `backend/app/services/ai/core/ai_config.py`
   - 現況：2 dead（`inference_profiles` / `get_preferred_providers`）→ warning
3. 架構標準化文件存在性：
   - `docs/architecture/STANDARD_REFERENCE.md`（12 章跨 repo 參考）
   - `docs/architecture/SERVICE_CONTEXT_MAP.md`（85 散戶映射）

## 建議頻率

- 🟢 每月架構覆盤
- 🟢 大重構前（services/ 遷移、dead config 清理）
- 🔴 **不**加到 pre-commit（避免干擾開發）
- 🔴 **不**加到 GitHub Actions（規範禁止 CI 費用）

## 觸發情境

- `/arch-fitness` — 手動呼叫（本 slash command）
- 月會前人工跑 → 產出現況快照
- 接到 CK_AaaP 的覆盤 sprint

## 修復建議

若散戶比例超標 → 看 `docs/architecture/SERVICE_CONTEXT_MAP.md` §2 Phase 2 遷移路線
若 dead config 警告 → 三選一（接線 / 刪除 / 加 TODO 註記）
若 docs 缺失 → 從 git 還原（不應被刪除）

## 關聯

- `docs/architecture/STANDARD_REFERENCE.md` §12 — Fitness Functions 章節
- `memory/baseline_quality_recovery_20260424.md` — dead config 審計起點
- `memory/feedback_ddd_over_line_count.md` — 領域驅動拆分原則

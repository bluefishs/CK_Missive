# Alembic Migration Wave 錨點記錄

> **目的**：112+ migration 累積後缺乏 rollback anchor。每月末 cut tag 作為「批次 rollback 安全錨」。
> **約定**（STANDARD_REFERENCE §9.2）：當週 > 10 個 migration → 必須記錄；月末 cut `db-YYYY-MMw` tag。
> **首次建立**：2026-05-06（P2-2，回補 2026-03 / 2026-04 兩個 wave）

---

## 使用方式

### 場景 1 — Rollback 整個 wave

```bash
# 想退回 2026-03 月底狀態（不要 4 月任何 migration）
cd backend
alembic downgrade $(git rev-parse db-2026-03w | xargs -I{} git show {}:backend/alembic/versions/* | grep -m1 down_revision)
# 或更簡單：找到該 tag 對應的 head revision，downgrade 到該點
```

### 場景 2 — 對比兩 wave 之間 schema 變動

```bash
git diff db-2026-03w..db-2026-04w -- backend/alembic/versions/
git diff db-2026-03w..db-2026-04w -- backend/app/extended/models/
```

### 場景 3 — 月末 cut 新 wave（每月例行）

```bash
# 取得當月最後一個 migration 對應的 commit
LAST_COMMIT=$(git log --oneline --all --diff-filter=A --pretty=format:"%H" \
  -- 'backend/alembic/versions/2026MM*' | head -1)

# 寫摘要 + cut tag
git tag -a db-2026-MMw -m "DB wave anchor: end-of-2026-MM (NN migrations, last=<short>)
- 主要主題 1
- 主要主題 2
" $LAST_COMMIT
```

---

## Wave 記錄

### `db-2026-03w` — 2026-03 月底
**Commit**：`df6aef43` (Tue Mar 31 23:32:42 2026 +0800)
**Migrations**：26 個（2026-03-12 ~ 2026-03-31）
**主要主題**：
- ERP 模組大擴張：營運帳目（operational accounts）、資產、發票、應付/應收
- 多通道整合：LINE/Telegram/Discord 共用 audit Mixin + 派發策略
- FK 索引補強：N+1 防禦
- 數位分身（digital_twin）拆分
- agent 安全強化 + 圖譜隔離

### `db-2026-04w` — 2026-04 月底
**Commit**：`b04ceb0c` (Tue Apr 29 11:37:11 2026 +0800)
**Migrations**：25 個（2026-04-08 ~ 2026-04-29）
**主要主題**：
- 派工查詢領域複合索引（按 query pattern 設計）
- 標案多源統一（ADR-0032）— PCC + ezbid + g0v
- 行事曆來源追蹤（calendar_source_tracking）
- canonical_user_id + merge_log（user alias 治理）
- 晨報三表：delivery_log + snapshots + subscriptions
- 派工 work_type_id + deadline（per-type 進度追蹤）
- KG entity_version_control + graph_domain 隔離
- pgvector embedding + HNSW 維度修正

---

## 注意事項

1. **單一 head 約定**：跨 wave 必須維持 single head（merge_heads_and_add_remaining_indexes 過去處理過分支衝突 — 不再讓它發生）。
2. **Bisect anchor**：`git bisect` 在 wave tag 之間做最快，每月 cut 一次保持 wave 大小可控。
3. **Tag 不可刪除**：tag 一旦推到 origin 不可重寫；若 wave 內容後續發現缺漏，新增「補丁 tag」如 `db-2026-04w-hotfix1`，原 tag 不動。
4. **與 ADR 對齊**：重大 schema 變動的 ADR 應在該 wave 範圍內 ship 完整（migration + model + service + test）。

---

## 月度 SOP（每月 1 號 owner 執行）

```bash
# 1. 列上個月 migration 數
ls backend/alembic/versions/2026<MM>*.py | wc -l

# 2. 取最後一個 commit
LAST_COMMIT=$(git log --oneline --all --diff-filter=A --pretty=format:"%H" \
  -- "backend/alembic/versions/2026<MM>*" | head -1)

# 3. cut tag
git tag -a db-2026-<MM>w -m "..." $LAST_COMMIT

# 4. 推到 origin（避免 local-only）
git push origin db-2026-<MM>w

# 5. 補本檔記錄
```

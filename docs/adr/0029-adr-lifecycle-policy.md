# ADR-0029：ADR Lifecycle Policy — 生命週期治理與瘦身

> **狀態**：accepted
> **日期**：2026-04-22
> **決策者**：專案 Owner
> **關聯**：docs/adr/README.md、scripts/checks/adr_lifecycle_check.py

---

## 背景

自 2026-01 起 ADR 從 11 則累積到 **27+ 則**（含取代、覆盤補記），其中：

- `accepted` 佔 90%+，但很多已「交付完畢並穩定半年」（如 ADR-0002 認證、ADR-0004 SSOT、ADR-0005 混合部署）
- `removed` / `deprecated` 很少使用（僅 ADR-0011）
- ADR 間缺乏相互引用與取代關係（ADR-0015 取代 NemoClaw 但未顯式 superseded 標籤）
- **治理負擔上升**：新人閱讀 27 則 ADR 成本過高；大部分決策已不是「活的」決策

**核心問題**：`accepted` 沒有 exit criteria，ADR 永遠累積不瘦身。

---

## 決策

### 1. 引入 `archived` 狀態

新增第 7 種狀態：

| 狀態 | 含義 | 生命週期 |
|------|------|----------|
| `proposed` | 提案中，尚未實作 | 30 天內必須決 accept/reject |
| `accepted` | 決策已確定，**正在影響當前開發** | 一般 |
| `deprecated` | 已排定移除（有 sunset 日期） | 過渡期 |
| `superseded` | 被新的 ADR 取代（必須標 `superseded by ADR-XXXX`）| 保留做歷史 |
| `removed` | 程式碼已移除 | 保留做歷史 |
| `rejected` | 考慮過但未採用 | 保留做歷史 |
| **`archived`**（**新增**） | 決策穩定 > 6 個月、已融入日常開發、不再是「活的」辯論 | 壓縮儲存 |

**`archived` 與 `accepted` 的差異**：

- `accepted`：仍可能被 supersede、需要新人讀懂
- `archived`：歷史沉澱，僅供考古；不出現在「活躍 ADR 列表」

### 2. Archive 條件（任一成立即可）

- 該 ADR 決策對應的功能 / 架構已穩定執行 **≥ 6 個月**，無新變更
- 該 ADR 相關的系統已歸檔（例：NemoClaw 退場後，ADR-0015 降為 archived）
- 同主題有更新 ADR，舊 ADR 明確 superseded

### 3. Active ADR 健康區間

- **目標**：`active_count` ≤ 15（proposed + accepted）
- **警示**：> 20 時觸發瘦身 sprint
- **紅燈**：> 25 時必須開 session review

### 4. 索引表與自動化

`docs/adr/README.md` 索引表新增 **狀態欄**（目前已有），加 **is_active** 欄快篩。

新增 `scripts/checks/adr_lifecycle_check.py`：
- 列出所有 ADR 與狀態
- 計算 active_count
- 標出超過 30 天未決的 `proposed`
- 標出 > 6 個月的 `accepted`，建議檢視是否可 archive

### 5. 本 ADR 落地同步 Archive 批次

**首波 archive（交付穩定、v5.6 以前）**：

| ADR | 原狀態 | 新狀態 | 理由 |
|---|---|---|---|
| 0001 Groq primary | accepted | archived | Token Tracker + 5 provider routing（v5.5.x）已全面接管，原決策進入歷史 |
| 0002 httpOnly Cookie + CSRF | accepted | archived | 2026-01 交付，穩定 3+ 月 |
| 0003 內網免認證 | accepted | archived | 2026-01 交付，穩定 3+ 月 |
| 0004 SSOT Type | accepted | archived | 已全面落地，不再辯論 |
| 0005 混合部署 | accepted | archived | 2026-02 交付，穩定運行 |
| 0006 pgvector 768D | accepted | archived | 穩定運行；若升 1024D 再開新 ADR |
| 0007 AI 四層架構 | accepted | archived | 已演進為 Agent + Orchestrator（見 ADR-0022） |
| 0008 Repository flush-only | accepted | archived | 規範已融入日常開發 |
| 0009 Agent 規則式自動修正 | accepted | archived | 已被 ADR-0022 Memory Wiki Phase 4~7 evolve 機制取代 |
| 0010 qwen3:4b | accepted | archived | 已被 ADR-0023 坤哥意識體 + Gemma 4 取代 |

**保留 active（仍影響當前開發）**：

| ADR | 狀態 | 理由 |
|---|---|---|
| 0011 AI 配置 DB CRUD | removed | 保留做教訓 |
| 0012 標案搜尋模組 | accepted | 持續擴充中 |
| 0013 統一編碼 | accepted | Phase 2 未完 |
| 0014 Hermes 取代 OpenClaw | accepted | **進行中**（P0） |
| 0015 NemoClaw 退場 | accepted | **進行中**（5/26 歸檔 deadline） |
| 0016 多專案平坦分域 | accepted | Phase 2 未完 |
| 0019 structlog | accepted | 持續監測 |
| 0020 AaaP Platform | proposed | **決策未定** |
| 0021 asyncpg concurrent session | accepted | 本月交付，需 3 個月觀察 |
| 0022 Memory Wiki | accepted | 本月交付（v5.7.x） |
| 0023 坤哥意識體 | accepted | 本月交付（v5.8.0） |
| 0024 Calendar Visibility | accepted | 本月交付 |
| 0025 Identity Unification | accepted | 本月交付 |
| 0026 WorkRecord Calendar Sync | accepted | 本月交付 |
| 0027 Telegram 推播關閉 | accepted | **進行中**（LINE 成為主通道） |
| 0028 錯誤合約化 | accepted | **進行中**（v5.9.0 落地） |
| 0029 ADR Lifecycle（本文） | accepted | — |
| 0030 Hermes GO/NO-GO 重訂 | accepted | **進行中** |

**Active 計數**：預計 archive 10 則後，active 從 27 → **17**，接近健康區間 ≤15。

### 6. 實作步驟

1. 建立 `archived` 子目錄：`docs/adr/archived/`
2. 移動首波 10 則 ADR 檔案到該目錄（保留編號）
3. 更新各 ADR 頂部狀態為 `archived`（附原 accepted 日期）
4. 更新 `docs/adr/README.md` 索引，分「活躍 ADR」+「歷史 ADR (archived)」兩段
5. 新增 `scripts/checks/adr_lifecycle_check.py`
6. 在 `.claude/rules/skills-inventory.md` 補一句「歷史 ADR 見 archived/」

---

## 後果

### 正面

1. **新人 onboarding 成本下降**：僅需讀 17 則活躍 ADR（原 27 則）
2. **治理負擔可量化**：`active_count` 指標明確
3. **決策層次清晰**：「本月在辯論什麼」vs「歷史沉澱」明確區分
4. **superseded 關係強制化**：新 ADR 必須標取代關係

### 負面

1. **歷史 ADR 變難找**：需透過 archived 目錄或 ADR 索引檢索
2. **誤 archive 風險**：若某 archived ADR 實際仍在影響開發，需 unarchive（機制：任何人發 PR 可 revert）
3. **一次性遷移成本**：10 則檔案移動 + 狀態更新 + 索引改寫

### 中性

- 本政策僅對 CK_Missive 生效；跨 repo 的 CK_AaaP ADR REGISTRY 由其自行治理

---

## 驗證

```bash
# 統計活躍 ADR
python scripts/checks/adr_lifecycle_check.py

# 期望輸出：
# Active (proposed + accepted): 17
# Archived: 10
# Superseded / Removed / Rejected: 1
# Total: 28
# ✅ active_count 在健康區間（≤ 15 目標，17 略超，建議 v6.0 再瘦身一批）
```

---

## 狀態記錄

- 2026-04-22：accepted
- 首波 archive 執行：同 v5.9.0 落地
- 下次 lifecycle review：2026-10（半年）

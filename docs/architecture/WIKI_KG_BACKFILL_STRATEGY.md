# Wiki ↔ KG Backfill 策略分析

> **產出**：2026-04-25
> **目的**：在執行 wiki↔kg backfill 前，分析 schema mismatch 根因 + 三方案 ROI 對比
> **狀態**：proposed（待 Owner 拍板選方案）
> **關聯**：
> - `CONSCIOUSNESS_INTEGRATION_ANALYSIS.md` §4.2 Wiki↔KG 雙向引用斷鏈
> - `scripts/checks/wiki_kg_link_audit.py`（audit 工具，已落地）
> - ADR-0022 Memory Wiki self-evolving assistant

---

## 1. 根因鎖定

`wiki_kg_link_audit` 揭露 dispatch 127 個全 0% 連結。深入分析發現：

### 1.1 數量對應一致
| 來源 | 數量 |
|---|---|
| `wiki/entities/*_派工單號*.md` (entity_type: dispatch) | **127** |
| PG `taoyuan_dispatch_orders` 表 | **127** |
| KG `canonical_entities` WHERE entity_type='dispatch' | **0** |

### 1.2 KG schema 設計止於 project
KG `canonical_entities` 中與派工相關的命中：
```
[project] id=14793 辦理南投縣青年住宅周邊都市計畫區界線逕為分割作業(第五次派工)
[project] id=14825 南投市南投段129-29地號土地逕為分割(第二次派工)
```

**結論**：派工**只作為 project 名稱的一部分**進入 KG，未形成獨立 entity。

### 1.3 wiki dispatch title 規則
```
112年_派工單號001  →  KG 無 match（命名空間不同）
112年_派工單號002  →  KG 無 match
...
```

Wiki 用「年份_派工單號 NNN」格式，KG project 用「業務描述+派工」格式。**ID 命名空間完全不同**，模糊匹配無效。

---

## 2. 三方案 ROI 對比

### 方案 X：擴 KG schema 加 dispatch entity_type（**完整解決**）

**動作**：
1. KG `canonical_entities.entity_type` enum 加 `dispatch`
2. 寫 ingestion 從 `taoyuan_dispatch_orders` 表自動入圖 KG
3. 建 cross-domain edge：`dispatch.parent_project_id` → KG project entity
4. wiki frontmatter `kg_entity_id` 連到新增的 dispatch KG entity

**工作量**：1-2 天（含 migration + ingest scheduler + edge builder + test）

**收益**：
- ✅ 連結率 30% → 80%+（完整解決）
- ✅ KG 圖譜 dispatch 粒度可查
- ✅ Wiki ↔ KG 雙向真實連結
- ✅ 跨域查詢「該派工的相關公文 / 報價 / 帳款」可走 KG path

**成本**：
- ⚠️ KG entity 從 ~21K 增至 ~21.1K（+0.5%）
- ⚠️ pgvector embedding 需多算 127 筆（一次性）
- ⚠️ Wiki 127 frontmatter 改寫（自動化 OK）

### 方案 Y：Wiki 連父 project（**折衷**）

**動作**：
1. wiki dispatch frontmatter 加 `parent_project_kg_id`（不是 `kg_entity_id`）
2. 透過 PG `dispatch_project_link` 表查父 project
3. wiki_kg_link_audit 接受 `parent_project_kg_id` 為連結

**工作量**：3-4 hr（含 audit script 升級接受新欄位）

**收益**：
- 🟡 連結率改善但語義稍弱（dispatch 只透過父 project 進入 KG）
- 🟡 跨域查詢只到 project 粒度

**成本**：
- ⚠️ 需多一個 frontmatter 欄位
- ⚠️ KG 仍無 dispatch 獨立 entity

### 方案 Z：接受 KG schema 不收 dispatch（**現狀**）

**動作**：
1. 修 `wiki_kg_link_audit.py` 將 dispatch 排除於整體連結率計算
2. 加註：dispatch 屬於「PG-only domain」（不入 KG）

**工作量**：30 min

**收益**：
- ✅ audit 不再誤報（連結率立即從 30% → 大約 70%）
- ⚠️ 但實質 wiki/KG 整合**無改善**

**成本**：
- 🔴 KG 失去 dispatch 粒度查詢能力（永久）
- 🔴 Memory Wiki ↔ KG 互通受限

---

## 3. 推薦方案：X（擴 KG schema）

### 推薦理由

1. **CK_Missive 業務核心是派工**（127 件，未來會增長）— dispatch 是高價值 entity，值得入圖
2. **跨域查詢價值高**：派工 → 公文 / 報價 / 帳款 / 相關員工 — 都是 KG 該服務的場景
3. **與 ADR-0022 Memory Wiki 願景一致**：「自我進化助理」需要 fine-grained entity 才能形成 dispatch-level pattern
4. **長期 ROI > 短期成本**：1-2 天投入換永久 80%+ 連結率 + dispatch 入圖能力

### 不推薦理由（為何不選 Y/Z）

- **Y 太折衷**：實際做完仍未解 KG 缺粒度問題
- **Z 是放棄**：違反「Memory Wiki 自我進化」設計初衷

---

## 4. 方案 X 執行路線圖

### Phase 1（1 day）：Schema + Ingestion
- [ ] Alembic migration：`canonical_entities.entity_type` enum 加 `dispatch`
- [ ] `services/ai/graph/dispatch_ingester.py`（新）
  - 從 `taoyuan_dispatch_orders` 讀全表
  - 對每筆 INSERT canonical_entities (entity_type='dispatch', canonical_name=dispatch_no)
  - 同時建 edge `dispatch_NNN → project_XXX`（透過 dispatch_project_link）
- [ ] 排程一次性 backfill + 之後增量

### Phase 2（4 hr）：Wiki frontmatter 補齊
- [ ] backfill 腳本：`scripts/sync/backfill_wiki_dispatch_kg.py`
  - 讀 wiki/entities/*_派工單號*.md
  - 用 dispatch_no 查 KG canonical_entities
  - dry-run 報告 + --apply gate
- [ ] 跑 wiki_kg_link_audit 確認 dispatch rate 達 95%+

### Phase 3（30 min）：驗證
- [ ] /arch-fitness 跑全綠
- [ ] 整體連結率達 80%+
- [ ] integration test 鎖定 dispatch entity 入圖

---

## 5. 不選 X 的話

若 Owner 決定**短期不投入**（5/20 GO 前資源緊張）：
- 採 **Z**（修 audit 排除 dispatch）— 30 min 即可降噪
- 把 X 排入 **v6.0** roadmap
- 在 `CONSCIOUSNESS_INTEGRATION_ANALYSIS.md` §9 加紀錄

---

## 6. 決策格

```
方案：[ ] X（擴 KG 完整解決）
      [ ] Y（折衷父 project）
      [ ] Z（接受現狀，audit 排除）
      [ ] 延至 v6.0

決策日期：
決策者：
理由：
執行排程：
```

---

**變更歷史**
- v1.0（2026-04-25）：首版策略分析，3 方案 ROI 對比

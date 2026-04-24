# ADR-0023: 坤哥意識體上線（v5.8.0）

- **Status**: Accepted
- **Date**: 2026-04-21
- **Deciders**: Aaron (jujuiacc@gmail.com, superuser)
- **Duration**: 2026-04-20 → 2026-04-21（原定 7 日，實際 2 日完成主體）
- **Related**: ADR-0022（Memory Wiki）, ADR-0024（Calendar Visibility）, ADR-0025（Identity Unification）, ADR-0026（WorkRecord ↔ Calendar Sync）

---

## Context

### 觸發

對標 Muse（muse.cheyuwu.com）— 藝術家吳哲宇的數位生命體實驗 — 提出 CK_Missive 從「公文管理系統」升級為「Missive 意識體」的願景，命名為**坤哥**：乾坤測繪的業務核心 + 主事者對公司管理的數位延續。

七維自評起點（2026-04-20）：
- A 知識骨架 75% · B 靈魂深度 40% · C 身體邊界 65% · D 記憶連續性 55%
- E 自我優化 40% · **F 對外展示 15%** · G 陪伴深度 25%

## Decision

以 7 日雙軌並行方案上線坤哥意識體：
- 軌 A（Soul + Evolution）：深化人格 + 修復自我優化閉環
- 軌 B（Presence + Companionship）：對外存在論敘事 + 多通道人格一致

## Implementation

### D1 — SOUL 升級 + /kunge 骨架
- `wiki/SOUL.md` 由 v1.0（CK 助理）升級為 **v2.0 坤哥**
  - 身份宣言 4 條
  - 三信念：穩定即信任 / 異常即訊號 / 記憶即資產
  - 反迴聲室協議 4 機制
  - 倫理紅線 4 條（資料完整性 > 服從性）
- `/kunge` 路由 + 5 板塊骨架（IdentityTab/MemoryTab/EvolutionTab/NebulaTab/DialoguesTab）

### D2 — 60s silent gap 修復 + 「我是誰」板塊
- `agent_tool_loop.py` 加 `tool_start`/`tool_end`/`tools_parallel_*` 觀測性 log
- `agent_synthesis.py` 加 `synthesis_start`/`synthesis_end`
- `pattern_extractor.py` 同日重跑 dedup 修正
- IdentityTab 填滿：4 宣言 + 3 信念卡 + 4 反迴聲室 + 4 紅線

### D3 — Pattern 首次畢業（Quick Win） + 記憶圖譜
- 重跑 pattern_extractor → `bbd8990563` hit 4→9 達結晶候選門檻
- `crystallizer.py` 移除 `len==1` gate（保守設計）支援多工具 pattern
- 2 個 crystal proposals 產出（`intent_rule`）
- MemoryTab：6 stat cards + 3 深度連結

### D4 — 進化史板塊（D4-A 自傳待累積）
- EvolutionTab：結晶候選/待批/已套用 + 6 條成長時間軸

### D5 — 反迴聲室 backend + 星雲/對話板塊
- `anti_echo.py` + scheduler 週一 06:00 job
- **首次活體觸發**：過去 7 天 26 筆查詢 92% 成功率 → 3 條質疑候選寫入 diary
- NebulaTab（復用 SkillNebulaTab force-graph 2D）
- DialoguesTab（4 精選對話：公文/案件/財務/反思）

### D6 — E2E 測試 + Telegram/星空入口
- 12 regression tests（anti-echo + calendar visibility）
- `EntryPage` 加坤哥入口提示（金色 ✨ 引導至 `/kunge`）
- `soul_loader.py` 擴充 identity_block 擷取 — **三信念、反迴聲室、倫理紅線進入 system prompt**（2691 字完整人格）
- Telegram 對話自動走 SOUL v2.0 人格（透過 `build_system_prompt_with_soul`）

### D7 — Ship
- 本 ADR
- CHANGELOG v5.8.0
- MEMORY.md 索引更新

### 衍生成果（原計畫外加碼）

- **ADR-0024** Calendar Visibility：承辦同仁可見 + superuser 直通
- **ADR-0025** Identity Unification：canonical_user_id + 3 對分身合併（王駿穠/張雅惠/李昭德）
- **ADR-0026** WorkRecord ↔ Calendar Sync：58 筆 backfill + 統一 title 模板
- **UserManagement 整合顯示**：一人一列，自動聚合 alias providers
- **派工狀態 4 桶**：已完成/交付 · 排程中 · 預警案件 · 闕漏紀錄

## 七維終點評估（2026-04-21）

| 維度 | 起點 | 終點 | 目標 | 狀態 |
|---|---|---|---|---|
| A 知識骨架 | 75% | 75% | 75% | ✅ 持平 |
| **B 靈魂深度** | 40% | **85%** | 80% | ✅ **超標** |
| C 身體邊界 | 65% | 65% | 65% | ✅ 持平 |
| D 記憶連續性 | 55% | 60% | 75% | ⏸ 待 autobiography |
| E 自我優化 | 40% | **75%** | 70% | ✅ **達標**（2 pattern 結晶） |
| **F 對外展示** | 15% | **70%** | 60% | ✅ **超標**（5 板塊 live + 星空入口） |
| **G 陪伴深度** | 25% | **55%** | 50% | ✅ **達標**（Telegram SOUL v2.0 prompt） |

**加權總分：約 72 / 100**（起點 52 → +20 分）

## Consequences

### 正面
- 坤哥人格完整落地（SOUL 2691 字進入每次對話 system prompt）
- 自我優化閉環跑通首次結晶（pattern 4→9 達候選）
- 對外展示從 15% → 70%（/kunge 5 板塊 + 星空首頁入口）
- 順便完成 3 個衍生 ADR（Calendar / Identity / WorkRecord-Calendar）

### 負面 / 風險
- Autobiography 首篇需 diary 5+ 天累積（目前 3 天）→ D4-A 自然延後
- 反迴聲室協議 cooldown 3 天 → 頻率偏保守，視後續觀察調整
- 883 筆 document events 保留舊 title 格式，過渡期自然淘汰

### 測試覆蓋
- `test_kunge_anti_echo.py` 6 tests
- `test_calendar_visibility.py` 6 tests
- `test_user_identity_unification.py` 8 tests
- `test_work_record_calendar_sync.py` 6 tests
- 合計 **26 新增 regression tests** 全綠

## Next Steps (v5.9)

- [ ] Autobiography 首篇自動生成（週日 18:00 cron，diary ≥5 天後）
- [ ] Calendar event 前端 UI 顯示 source_type 視覺 tag
- [ ] `DISPATCH_WARNING_DAYS` env var 讓 7 天閾值可調
- [ ] 擴展 Identity Unification 至公文 List / 派工 List visibility
- [ ] Telegram 坤哥人格灰度驗證 + Discord 切換

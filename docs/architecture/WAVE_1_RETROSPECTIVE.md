# Wave 1 Services DDD 遷移 — 回顧（Retrospective）

> **完成日期**：2026-04-27（v5.9.9）
> **總工時**：約 6 小時（單一 dynamic /loop session 跨 6 輪迭代）
> **執行者**：Claude Code（Opus 4.7）+ Owner 授權 commit
> **範圍**：6 bounded contexts × 28 檔遷移 + Playbook v1.3 完整化
> **適用對象**：CKProject 任何子專案準備執行類似 DDD 遷移時的參考案例

---

## 0. 執行摘要

從「散戶 service 平鋪 services/ 根目錄」到「6 bounded context 子包 + 向後相容 stub」，
全程**零行為變更**（461 tests passed / 7 pre-existing failed）。最重要的不是程式碼改動，
而是**從 4 次踩雷淬鍊出可被其他 repo 直接套用的 SOP**。

---

## 1. 數字結果

| 指標 | 數值 |
|---|---|
| 遷移檔數 | 28 檔（含 1 single-file pilot dispatcher）|
| Bounded contexts 落地 | 6 個（audit / notification / vendor / agency / contract / document）|
| 新建子模組 | 28 個 |
| 保留 stub | 28 個（含 DeprecationWarning + re-export）|
| Production import 點 | ~95 個（透過 stub 機制持續 work，0 改動）|
| mock.patch 字串修正 | 13 處（6 contract + 6 vendor/agency + 1 document）|
| 內部循環 import 改 relative | 5 處（document sub-batch）|
| Tests 跑過 | **461 passed / 7 pre-existing failed** |
| Commits | 9 個（每個 sub-batch 獨立 commit + playbook updates）|
| Service entropy | 29.4% → 26.9%（短期下降有限，stub 仍算散戶）|
| Playbook 升級 | v1.0 → v1.1 → v1.2 → v1.3（4 次踩雷皆收錄）|

---

## 2. 執行節奏（dynamic /loop 自我節奏）

| 輪次 | 範圍 | 主要產出 | 耗時 |
|---|---|---|---|
| 1 | KG/Wiki/SLO/範本指南 | 6 任務完成 + 3 commits | ~1.5 hr |
| 2 | CHANGELOG + Wave 1 single-file pilot | 1 commit + SOP 驗證 | ~30 min |
| 3 | Wave 1 sub-batch C (audit + notification 6 檔) | 1 commit + name collision SOP | ~40 min |
| 4 | Wave 1 sub-batch B 部分 (vendor + agency 4 檔) | 1 commit + mock.patch SOP | ~30 min |
| 5 | Wave 1 sub-batch B 完整 (contract 6 檔) | 1 commit + multi-line patch SOP | ~30 min |
| 6 | Wave 1 sub-batch A (document 11 檔) | 2 commits + 循環 import SOP | ~45 min |

**節奏觀察**：每輪 25 min wakeup 給 user 25 min review window，避免一次推太多。
單輪聚焦 1 個 sub-batch 是最佳粒度 — 太大難 review，太小 SOP 沒驗證價值。

---

## 3. 4 次踩雷與淬鍊

### 雷 1：Class name collision（sub-batch C）
- **症狀**：`notification.service` 與 `notification.template` 都定義 `NotificationType`
  → `__init__.py` wildcard re-export 互相覆蓋
- **解法**：`__init__.py` 改採 explicit re-export 主類別策略
- **Playbook**：§4.4

### 雷 2：mock.patch 路徑遷移失效（sub-batch B vendor+agency）
- **症狀**：`patch("app.services.foo_service.X")` 在 service 搬走後失效
- **解法**：批次 sed 改 `app.services.foo.core.X`
- **Playbook**：§4.3

### 雷 3：Multi-line patch grep 漏抓（sub-batch B contract）
- **症狀**：`grep` 同行模式找到 0 處，但實際 6 處 multi-line 寫法
- **解法**：必用 `rg --multiline` 或 `grep -P`
- **Playbook**：§4.3 補充

### 雷 4：內部循環 import 死鎖（sub-batch A document）
- **症狀**：stub 載入時呼叫 __init__.py，__init__.py 載入子模組，子模組 lazy import 走 stub → 死鎖
- **解法**：子模組間互引用必改 relative import（不走 stub）
- **Playbook**：§4.5

**關鍵教訓**：每次踩雷成本約 10-20 min（debug + 修正），但寫入 Playbook 後**永久避免**，
且其他 repo 移植時直接受益。**踩雷的價值不是修好就算，是寫進 SOP**。

---

## 4. 範本化等級驗證

`TEMPLATE_EXTRACTION.md` 把 Wave 1 playbook 列為 **L2 Reference Implementation**，
但本次 6 輪實測證明：

- **Playbook v1.3** 已從 L2 升級至 **L1+ 已驗證**
- 4 次踩雷皆已預先警示 → 後續 repo 套用時可直接避雷
- Sub-batch 切片建議（C → B → A）順序在實測中確實是最低風險路徑
  - C 最簡單（依賴少）→ 驗證 SOP
  - B 中等（business 核心但無循環）
  - A 最複雜（document 11 檔互相依賴）

---

## 5. 下一波建議（Wave 2 候選）

當前散戶仍 85 檔（stub 算散戶 + 未遷移 context）。剩餘 context：

| Context | 檔數 | 優先級 | 理由 |
|---|---|---|---|
| `tender` | 9~10 | 中 | 業務獨立，依賴可控 |
| `erp` | 10 | 中-高 | 已有 erp/ 子目錄但部分 service 還散在頂層 |
| `integration` (line/telegram/discord) | 8 | 中 | 通道抽象已建好，集中可降複雜度 |
| `calendar` | 5 | 低 | 已有 calendar/ 子目錄但鬆散 |
| `ai` | (已 11 sub-package) | 低 | 已是 DDD 結構 |
| `wiki / memory` | 5 | 低 | 較新功能，重構需求小 |
| `taoyuan` | (已 taoyuan/ 子目錄) | 低 | 已 DDD |

**Wave 2 推薦**：先做 erp 收斂（把頂層 erp_* 散戶都進 erp/ 子包），
再做 integration 集中（把 line/telegram/discord 各檔進 integration/<channel>/ 子包）。

---

## 6. v6.0 計畫：stub 移除

當前所有 stub 都會發 `DeprecationWarning`。預計 **2026-Q3** 統一移除，給內部 import 3 個月遷移時間：

```bash
# Q3 前要做：grep 確認無使用方
for old in document_service notification_dispatcher audit_service ...; do
  grep -rn "from app.services.${old} import" backend/ && echo "WARNING: still used: $old"
done

# 確認後 rm -rf stubs，commit "refactor: 移除 wave 1 deprecated stubs"
```

移除後 service entropy 才會大幅下降（85 → ~57 散戶）。

---

## 7. 給其他 repo 用本範本的 5 個建議

1. **先做 single-file pilot**（依賴最少的 1 檔）— 驗證 SOP 不破測試
2. **按依賴從淺到深切片**（無 circular → 中等 → 業務核心 → 複雜互引用）
3. **每個 sub-batch 獨立 commit** — 出問題易回滾
4. **每次跑全套相關 test + stash 對比** — 確認 failure 是 pre-existing 不是新 regression
5. **踩雷必寫 SOP** — playbook 才是真正的範本，程式碼只是過程

---

## 8. 引用資訊

```
@reference{ck_missive_wave1_retrospective_2026,
  title = {Wave 1 Services DDD Migration — Retrospective},
  repo = {CK_Missive},
  fqid = {CK_Missive#WAVE_1_RETROSPECTIVE_v1.0},
  version = {v5.9.9},
  date = {2026-04-27},
  status = {accepted}
}
```

跨 repo 引用此檔請用 FQID `CK_Missive#WAVE_1_RETROSPECTIVE_v1.0`。

---

> 維護者：Project Owner
> 此檔為 Wave 1 結案文件，後續 Wave 2/3 將另立 retrospective。

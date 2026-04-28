# Wave 2-7 Services DDD 遷移 — 連續收斂回顧

> **完成日期**：2026-04-28（v5.10.0）
> **執行範圍**：6 個 Wave 連續執行（Wave 2-7）
> **總工時**：約 4 小時（單一 dynamic /loop session 第 9-12 輪）
> **執行者**：Claude Code（Opus 4.7）+ Owner 持續授權
> **適用對象**：CKProject 任何子專案準備執行類似 DDD 遷移時的延伸案例
> **前置文件**：`WAVE_1_RETROSPECTIVE.md`（首波 28 檔經驗）

---

## 0. 執行摘要

承接 Wave 1（28 檔，6 contexts），Wave 2-7 連續執行**再遷 42 檔，累計 70/85 = 82%**，
落地 5 個額外 contexts。Playbook 從 v1.4 升級至 v2.0（補 §4.7、§4.8 兩條 SOP）。

**最重要的不是擴張的 42 檔，而是 SOP 在多 Wave 連續驗證下成熟為 6 條完整工序**。

---

## 1. 數字結果

| Wave | Context | 檔數 | 累計 | 主要 SOP 驗證/新增 |
|---|---|---|---|---|
| 2 | erp（expense+finance+invoice） | 9 | 37 | §4.6 Private function re-export（NEW） |
| 3 | integration（line/telegram/discord/共用） | 10 | 47 | §4.7 Production caller 同步（NEW） |
| 4 | tender（search/cache/scrapers/analytics） | 10 | 57 | §4.8 Multi-line patch sed 失效（NEW） |
| 5 | calendar（document_calendar+reminder） | 5 | 62 | SOP 全綠驗證（無新踩雷） |
| 6 | wiki（compiler/coverage/formatter/service） | 4 | 66 | SOP 全綠驗證 |
| 7 | 散戶收尾（google/project_notification/financial） | 4 | **70** | SOP 全綠驗證 |

**全程驗證**：`pytest tests/` = 3550 passed / 20 failed / 7 skipped，
與 baseline (stash) **diff = 0** → **0 regression**。

---

## 2. 三次踩雷與淬鍊（補 Wave 1 的 4 次踩雷）

### 雷 5：Private function re-export（Wave 2）

Python `from module import *` **不 import** 底線開頭的名字。

```python
# ❌ stub 只 wildcard，_parse_head_qr 不被 export
from .erp.invoice_recognizer import *

# ✅ stub 必須 explicit 列出私有函數
from .erp.invoice_recognizer import *
from .erp.invoice_recognizer import _parse_head_qr, _parse_detail_qr, ...
```

**SOP**：grep `"from app.services.<old> import _"` 找出所有私有 import，
補進 stub 的 explicit re-export 清單。

### 雷 6：Production caller 路徑同步（Wave 3）

最深入的踩雷。stub 機制的「向後相容」設計在 mock.patch 場景**會失效**。

```
test:        @patch("app.services.integration.line_bot.get_line_bot_service")
production:  from app.services.line_bot_service import ...  # 走 stub
             dispatcher 用的 reference 在 stub namespace
             ↓
             patch 命中 integration.line_bot.X 但 dispatcher 用 stub.X
             → patch 失效！
```

**解法**：sub-batch 完成後，**production code 也批次 sed 改用新路徑**，
不再走 stub。違反「pure stub 零變更」但**必須**。

**Wave 3 實測**：23 個 regression 全消（修 production caller 後）。

### 雷 7：Multi-line patch sed 失效（Wave 4）

sed 是 line-based 工具，但 Python 慣用法：

```python
with patch(
    "app.services.<old>.<Cls>"   # 字串獨立一行
) as MockSvc:
```

sed 對「同行 word boundary」的判斷在 quoted string 內可能失誤。

**SOP**：sed 替換後**必跑 `rg --multiline` 找殘留**，逐個 manual Edit。

---

## 3. SOP 連續驗證的價值

Wave 1 驗證 4 SOP，Wave 2-4 驗證 + 補 3 SOP，**Wave 5-7 全綠運行 SOP（0 新踩雷）**。

→ Playbook v2.0 達到「**穩定 SOP 套裝**」狀態，可直接給其他 repo cherry-pick 使用。

---

## 4. 跨 Wave 連續執行的時間與精神成本

| Wave | 預估（playbook） | 實際 | 主要 overhead |
|---|---|---|---|
| 2 erp | 1.5-2 hr | ~50 min | Facade 內 17 處 circular import |
| 3 integration | 1 hr | ~60 min | 35+ mock.patch + production caller |
| 4 tender | 30-40 min | ~25 min | 22 處 circular import + 5 multi-line patch |
| 5 calendar | 30 min | ~20 min | SOP 完全沒踩雷 |
| 6 wiki | 30 min | ~15 min | SOP 完全沒踩雷 |
| 7 散戶 | 30 min | ~15 min | SOP 完全沒踩雷 |

**觀察**：Wave 5+ 後**明顯加速**，因為 SOP 已完整。
範本提取的核心價值正在這 — 後人不需踩雷，按 SOP 跑即可。

---

## 5. 給其他 repo 的 5 個建議（升級 Wave 1 retro 的 5 點）

1. **依賴從淺到深排序 sub-batch**（Wave 1 經驗）
2. **每個 sub-batch 獨立 commit + stash 對比 baseline**（Wave 1）
3. **SOP 完整版（v2.0 6 條）優先 cherry-pick**（Wave 2-7 新增）
4. **Wave 3 之後 production caller 必同步**（不再純 stub），否則 mock test 會大量失敗
5. **若涉及 Facade 模式（互相 import）**，先做 §4.5 relative import 改造再 git mv

---

## 6. v6.0 計畫：stub 移除（Wave 1+2-7 全涵蓋）

當前 70 個 stub 全帶 `DeprecationWarning`。預計 **2026-Q3** 統一移除：

```bash
# Q3 前驗證腳本
for old in $(cat docs/architecture/stub_inventory.txt); do
  count=$(grep -rn "from app.services.${old} import" backend/ | wc -l)
  if [ $count -gt 0 ]; then echo "STILL USED: $old ($count usages)"; fi
done

# 確認後 rm -rf 70 stubs
git commit -m "refactor: 移除 wave 1-7 deprecated stubs (70 檔)"
```

**Service entropy 預估**：23.7% → ~12%（達 GREEN < 20%）

---

## 7. 範本化等級 — 從 Wave 1 提升

| Wave 1 retro | 等級 |
|---|---|
| Playbook v1.0 | L1+ 已驗證 |

| Wave 2-7 retro | 等級 |
|---|---|
| Playbook v2.0（6 SOP） | **L1++ 多次驗證、跨 5+ context 模式適用** |
| install-template-to.sh | **L4 Plug-and-Play** |
| 30-min quick-start checklist | **L4 Plug-and-Play** |

→ CKProject 任何子專案現在都可在 30 分鐘內「裝」上 CK_Missive 的治理底座。

---

## 8. 引用資訊

```
@reference{ck_missive_wave2to7_retrospective_2026,
  title = {Wave 2-7 Services DDD Migration — Continuous Consolidation Retrospective},
  repo = {CK_Missive},
  fqid = {CK_Missive#WAVE_2_TO_7_RETROSPECTIVE_v1.0},
  version = {v5.10.0},
  date = {2026-04-28},
  status = {accepted}
}
```

---

> 維護者：Project Owner
> Wave 1 retro: `WAVE_1_RETROSPECTIVE.md`
> 連續 Wave 2-7 結案文件，後續 Wave 8+（misc/ 評估）將另立 retrospective。

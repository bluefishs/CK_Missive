# Missive-Specific Lessons — CK_Missive 業務 / meta-治理 lessons

> **分類原則**：含 CK_Missive 業務脈絡（Facade B 方案 / Hermes baseline / ezbid 業務）或 meta-治理層
> **對外推薦度**：L3 特定 — 不外推（對齊 L58 + L59 + L60）
> **建立日期**：2026-05-30（L58 立法配套）

---

## 6 條 missive-specific lessons

| Lesson | 主題 | CK_Missive 脈絡 |
|---|---|---|
| L50 | multi-source identifier link | ezbid × PCC 業務匹配（CK_Missive 標案模組）|
| L53 | Facade over-engineering 30 天裁判 | ADR-0036 / Facade B 方案 13→3 |
| L54 | 套用 ≠ 落實（雙層 audit）| cross-repo install-template 場景 |
| L58 | 治理範本污染風險 | 132 檔強推 4 子專案的反思 |
| L59 | 治理架構倒置 | CK_AaaP audit 缺口 / CK_Missive 反向治理 |
| L60 | 平衡 = 結構正常化 | PileMgmt R18 真活反治理驗證 |

---

## 為何不外推

對齊 L58 揭發：
- L53 涉及 Facade 抽象（子專案可能沒這抽象）
- L54 涉及 cross-repo 治理（子專案視角不同）
- L58/L59/L60 是 meta-治理（上游視角）
- L50 是 CK_Missive 業務（其他 repo 業務不同）

**子專案可參考但不建議直接 copy**。

---

## 跨 repo 部署

```bash
# 預設 NOT 推薦 — 僅 monorepo 或 opt-in
bash scripts/install-template-to.sh ../<repo> --tier=full
# 上述會套全部含 L3 — 子專案 owner 確認後執行

# 推薦：opt-out 機制
# 子專案 .template-policy.yml 加:
#   template_excluded:
#     - L53_*.md
#     - L58_*.md
#     - L59_*.md
#     - L60_*.md
```

---

## 對應 v6.12 立法句

| Lesson | v6.12 立法句 |
|---|---|
| L53 | 第 4 句（修法不可逆 → 60 天 trial）|
| L54 | 第 5 句（執行 ≠ 落實）|
| L58 | 第 6 句（範本是參考不是強制 → 過度套用就是污染）|
| L59 | 第 7 句（上游缺機制 = 治理倒置）|
| L60 | 第 8 句（平衡不在中間 在結構正常化）|

各句立法對應一個真實 lesson 案例。

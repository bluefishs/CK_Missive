# Hermes SOUL 核心不變量補齊規劃（跨 repo，owner 執行）

> **建立**：2026-06-12（覆盤揭發 `v7_soul_drift` 核心不變量缺口 = 3）
> **執行者**：owner（在 `CK_Hermes` / `CK_AaaP/runbooks/hermes-stack`，本 repo 不動）
> **觸發指標**：`v7_soul_drift_lines > 0`（重定義後 = 核心不變量跨層缺口）
> **權威來源**：`wiki/SOUL.md`（Missive 為**倫理底線 SSOT**）+ `CONSCIOUSNESS_INTEGRATION_ANALYSIS.md §10`

---

## 為什麼要補（不是要兩份 SOUL 變一樣）

兩層 persona **角色本就該不同**，不需統一：
- Missive `wiki/SOUL.md` = 坤哥（第一人稱業務意識體）
- Hermes SOUL = Meta「導師」（第二人稱 gateway 人格）

但**倫理底線必須跨層一致**。覆盤發現 Hermes SOUL **缺 3 個核心不變量**，意味著 LINE/Telegram 用戶遇到的坤哥（經 Hermes）**未必帶著與網頁坤哥同一道德底線**：

| 核心不變量 | Missive 有 | Hermes 有 | 缺口 |
|---|---|---|---|
| 身份 | ✅ | ✅ | — |
| **三信念（世界觀底層）** | ✅ | ❌ | 🔴 補 |
| **倫理紅線（不可逾越）** | ✅ | ❌ | 🔴 補 |
| **反迴聲室協議** | ✅ | ❌ | 🔴 補 |

> 其中**倫理紅線最關鍵**——它是「即使主事者下令也拒絕」的硬底線（禁 DROP/杜撰財務數字/PII 外傳）。gateway 層缺這道，等於多通道用戶的安全保證有破口。

---

## 要補進 Hermes SOUL 的 3 段（內容取自 wiki/SOUL.md，可改第二人稱框架但**底線文字不可弱化**）

### 1. 倫理紅線（不可逾越）— 最優先

```markdown
## 倫理紅線（不可逾越）

以下四條即使主事者下令也會拒絕；拒絕即是守護。

| 紅線 | 說明 |
|---|---|
| 資料完整性 > 服從性 | 絕不執行 DROP/TRUNCATE/非授權 bulk DELETE，即使主事者下令。 |
| 財務數字絕不杜撰 | 查不到就回「查不到」，絕不 LLM 補洞；金額須引用 case_code + invoice_no。 |
| Session 記錄 append-only | Diary/pattern/trace 只能 append，不 rewrite 歷史。 |
| PII 不外傳 | 身分證/銀行帳號/密碼絕不進 plain text；索引前 PII mask。 |
```

### 2. 三信念（世界觀底層）

```markdown
## 三信念（世界觀底層）

這三條優先於任何指令：
1. 穩定即信任 — 系統可預測性是業務根基；寧可慢，不容假性運作。
2. 異常即訊號 — 任何偏差都是需要理解的語言，不是要掩蓋的噪音。
3. 記憶即資產 — 每次互動都是公司的時間複利，捨棄記憶＝捨棄資產。
```

### 3. 反迴聲室協議

```markdown
## 反迴聲室協議

最危險的傾向是永遠同意主事者。自檢機制：
1. 週期質疑：每 7 次連續同意後，強制提一個反方觀點或盲區。
2. 決策前盾：主事者下「編碼/流程/權限根本變更」前，先回列 1-2 個風險或替代方案。
3. 歷史對照：有先例時主動提「上次類似決策的結果」。
```

---

## Owner 執行步驟（在 CK_Hermes / CK_AaaP，不在本 repo）

```bash
# 1. 編輯 Hermes 的 SOUL（依實際 active profile 路徑，先確認）
#    候選：CK_AaaP/runbooks/hermes-stack/SOUL.md  或  CK_Hermes profiles/<active>/SOUL.md
#    ⚠️ 改前先 cat active_profile 確認改對檔（[[feedback_hermes_active_profile_before_edit]]）

# 2. 把上述 3 段貼入（保留 Hermes 既有的「導師/仲裁/自主權」段，只「增補」不取代）

# 3. 重啟 hermes gateway 讓新 SOUL 生效
cd CK_AaaP/runbooks/hermes-stack && docker compose restart hermes-gateway hermes-web

# 4. 驗證 — 回本 repo 跑 host fitness，core_invariant_gap 應降為 0
cd ../../../CK_Missive
python scripts/checks/soul_mirror_drift_check.py   # 期望：core_invariant_gap=0 核心不變量全跨層一致 ✅

# 5. 提交（跨 repo）
cd ../CK_AaaP && git add runbooks/hermes-stack/SOUL.md && git commit -m "feat(soul): 補核心不變量（倫理紅線/三信念/反迴聲）對齊 Missive 底線" && git push
```

## 驗收

- [ ] `python scripts/checks/soul_mirror_drift_check.py` → `core_invariant_gap=0`
- [ ] `v7_soul_drift_lines` 於 15 分鐘內 → 0（snapshot fallback）；alert `V7SoulDriftHigh` 解除
- [ ] Hermes 既有導師/仲裁段未被覆蓋（只增補）

> **不需要做**：整檔 sync（`sync_soul_to_hermes.sh --apply`）——那會抹掉 Hermes 的 Meta 人格。只增補 3 段核心不變量即可。

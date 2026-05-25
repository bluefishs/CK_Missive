# ADR 半接通防範 SOP

> **強制等級**：所有新 ADR 上線必走
> **觸發**：建立或大改 ADR（status: proposed → accepted）時
> **適用**：cross-team 協作 + Owner 自管 ADR
> **建立日期**：2026-05-06（觸發事件：ADR-0025 13 天 dormant bug）
> **權威參考**：`docs/architecture/ADR_HALF_WIRED_AUDIT_20260506.md`

---

## 為何需要這份 SOP

2026-04-21 ADR-0025 Identity Unification 上線後，3 筆初始 cleanup 都成功執行，但 RLS 從未展開 alias group → 13 天 dormant bug 直到單一身份用戶觸發才暴雷。詳見 `wiki/memory/failures/failure-adr-0025-rls-half-wired.md`。

審計 17 個 active ADR，**65% 有半接通風險**。這不是個案疏漏，是結構性問題：
- ADR 強調「為什麼做」而非「做完所有層」
- Code review 看 PR 不看 ADR
- Test 偏 unit/regression > integration/E2E
- Owner 永遠是 admin，繞過 staff/user 邊角

---

## ADR 上線檢查清單（強制）

新 ADR 從 `proposed` → `accepted` 前必須完成：

### A. 程式碼接通完整度
- [ ] **主路徑實作**（service / API / UI / DB schema）
- [ ] **下游消費端對齊**：哪些既有模組需要感知這個新概念？逐一列出 + 修
- [ ] **讀取/權限/RLS** 是否有變動？若是，全部 endpoint 重新檢視
- [ ] **寫入面 vs 讀取面** 是否對稱？例如 merge 寫了 canonical_user_id 但 RLS 沒展開 = 半接通

### B. 自動驗證機制
- [ ] **至少 1 個 unit test** 鎖定核心邏輯
- [ ] **至少 1 個 integration test** 涵蓋邊角組合
- [ ] **fitness function** 月跑驗證（若該 ADR 邏輯可能 silent stale）
- [ ] **Prometheus alert rule** 若邏輯產生 metric

### C. 邊角組合識別（防 dormant）
- [ ] **列出本 ADR 的「最不容易繞過」用戶身份組合**
  - 例：staff role + 多帳號 + 訪問 alias 那邊 PUA
  - 例：未綁 SSO 的 admin（IdP outage 時失去管理通道）
- [ ] 該組合**有對應 fitness/integration test**
- [ ] **Owner 切到該身份實測 1 次** + 寫 wiki diary 紀錄體感

### D. 上線後 7 天追蹤
- [ ] 第 7 天 owner check-in：該身份用戶有沒有 friction
- [ ] 觀察相關 metric / alert 有無觸發
- [ ] 若有則寫 critique；無 friction 7 天 → 真活宣告 + 寫 evolution

### E. 文件對齊
- [ ] 寫入 `wiki/memory/diary/` 上線當天紀錄
- [ ] 更新 `docs/architecture/ADR_HALF_WIRED_AUDIT_*.md` 對應條目
- [ ] CHANGELOG 標明「ADR-NNNN 接通完整度級別」

---

## 接通完整度分級（自評）

| 級別 | 描述 | 範例 |
|---|---|---|
| **L1** | 文件型不需驗證（純 governance / convention） | ADR-0011 教訓性文件 |
| **L2** | 完整接通：程式碼 + 自動驗證 fitness/E2E | ADR-0028 錯誤合約化（3 守護腳本） |
| **L3** | 半接通風險：程式碼接通但無自動驗證 | ADR-0014 Hermes 取代 OpenClaw |
| **L4** | 高風險：複雜邊角 + 無/不足驗證 | ADR-0022 Memory Wiki / ADR-0033 |

**目標**：所有新 ADR 必須達 L2，否則需在 ADR 內註明「待補驗證」+ owner 14 天內補完。

---

## 「真活」定義

**真活 ≠ commit message 寫的「真活」** —

> **「真活」是該身份用戶實際操作不出 friction 才算。**

判斷標準：
1. 該 ADR 影響的最不容易繞過身份組合，**owner 親自實測過 1 次**
2. 上線後 7 天，**該身份用戶沒有反饋 friction**
3. 對應 metric / fitness 連續 7 天綠燈
4. **沒有任何 silent failure 在 backend log 出現**

---

## 同類事故對照（學習用）

| 事故 | 半接通位置 | dormant 天數 | 觸發條件 |
|---|---|---|---|
| ADR-0025 Identity Unification | RLS 沒展開 alias group | 13 天 | staff role + 多帳號 + 跨 alias 訪問 |
| ADR-0014 Hermes（推測） | Hermes baseline 累積但 GO/NO-GO 邏輯未觸發 | 30 天+ | dogfooding 不足 |
| ADR-0022 Memory Wiki | diary 寫入鏈 silent stall | < 1 天（被 owner 體感察覺） | 任何 cron 失敗 |
| GENERIC_ADMIN_KEYWORDS regex | 業務術語撞通用過濾關鍵字 | 多週/月 | 公文 subject 含「系統建置/工作計畫」等業務詞 |

詳見：
- `docs/architecture/ADR_HALF_WIRED_AUDIT_20260506.md` §3 殘留盤點
- `wiki/memory/failures/failure-adr-0025-rls-half-wired.md`
- `wiki/memory/failures/failure-generic-admin-regex-overmatch.md`

---

## 過濾性程式碼設計守則（Regex / Keyword / Filter）

> 觸發事故：`failure-generic-admin-regex-overmatch.md`（5/06）
> 通用過濾 regex 用業務術語當關鍵字，誤殺 5 筆業務公文，dormant 多週。

### 守則 1：黑名單 vs 白名單 — default 用白名單

| 模式 | 預期效果 | False-positive 代價 |
|---|---|---|
| 黑名單（過濾掉 X） | 隱藏 X，顯示其他 | **用戶資料消失** — 高代價 |
| 白名單（保留 X） | 只顯示 X | 多看到無關項，但**可見** — 低代價 |

**Default**：使用白名單。不得已用黑名單時，pattern 必須**極度精確**。

### 守則 2：Pattern 必須附「設計依據 + 預期 match 比例」註解

```typescript
// ❌ Bad — 沒依據、沒預期、單字 OR 過寬
const ADMIN_KEYWORDS = /契約|保險|採購|計畫/;

// ✅ Good — 限定詞、附依據、附預期
// 純行政文件關鍵字（與業務查估/丈量無關的單據）。
// 來源：5/06 fix — 縮小 over-match dispatch 業務公文（failure-generic-admin-regex-overmatch）
// 預期：對 documents.subject 命中率應 < 1%（fitness step 19 monthly check）
const PURE_ADMIN_KEYWORDS = /契約書印鑑|履約保證|意外保險|投標保證|押標金|印鑑卡/;
```

### 守則 3：每加一個過濾關鍵字必須跑 false-positive 驗證

加 keyword 流程：
1. 從既有資料樣本（DB 或 fixture）取 N ≥ 100 筆
2. 對該樣本跑 regex
3. **人工抽驗 match 樣本**：是否真的都該被過濾？
4. False-positive rate ≤ 1% 才能 commit

加 unit test 鎖定：
```python
def test_pure_admin_keywords_no_false_positive():
    """確保業務性公文 subject 不被誤判為純行政"""
    BUSINESS_SAMPLES = [
        "檢送系統建置作業工作計畫書...",
        "道路專案系統建置之工作計畫書審查會議...",
        # 加更多真實 case
    ]
    for s in BUSINESS_SAMPLES:
        assert not PURE_ADMIN_KEYWORDS.search(s), f"誤殺業務公文: {s}"
```

### 守則 4：偏好限定詞 + 雙字組合，禁用單字 OR

| 形式 | 評價 |
|---|---|
| `/契約\|保險\|採購/` 單字 OR | ❌ 太寬，必然誤殺 |
| `/契約書印鑑\|履約保證/` 雙字組合限定詞 | ✅ 範圍可控 |
| `/^(履約保證\|意外保險)申請$/` anchor + 完整 phrase | ✅✅ 最精確 |

### 守則 5：黑名單性 regex 必須對應 fitness audit

每個 active 黑名單 regex 必須在 `scripts/checks/generic_filter_audit.py` 註冊，月跑驗證 false-positive rate。

---

## 與既有規範的關係

| 規範 | 強調點 | 與本 SOP 關係 |
|---|---|---|
| `MANDATORY_CHECKLIST.md` | 開發前檢查（路由 / API / 型別等）| **互補** — 本 SOP 強調 ADR 級「整合完整度」 |
| `architecture-backend.md` | DDD/RLS/Repository 模式 | **承接** — 本 SOP 確保新 ADR 整合到既有模式 |
| ADR-0028 錯誤合約 | silent failure 政策 | **延伸** — 本 SOP 把「半接通 silent dormant」也納入 |
| ADR-0029 ADR Lifecycle | active ADR 數量治理 | **配套** — 半接通的 ADR 應降級 archive |

---

## 自查工具

```bash
# 月度執行
bash scripts/checks/run_fitness.sh                # 18 step 全跑
python scripts/checks/adr_lifecycle_check.py     # ADR 數量治理
python scripts/checks/sso_coverage_check.py      # ADR-0033 配套
python scripts/checks/idp_connectivity_check.py  # ADR-0033 配套
python scripts/checks/alias_rls_e2e_check.py     # ADR-0025 配套
python scripts/checks/memory_diary_freshness_check.py  # ADR-0022 配套
```

每季更新一次 `docs/architecture/ADR_HALF_WIRED_AUDIT_*.md`：
- 新 ADR 加入評估
- 已修 ADR 升級級別
- 新發現的半接通寫入 failures/

---

## 觸發本 SOP 的訊號

當 owner 或維護者觀察到下列訊號，就該翻出本 SOP 對 ADR 重新審計：

1. **「為什麼這個帳號看不到 X？」** — 可能是 RLS / alias / 路由半接通
2. **「commit 都寫了真活但用戶說沒感受」** — 標準 dormant 訊號
3. **「某 ADR 上線後該功能 silent 沒人用」** — 可能寫了但實際路徑沒接通
4. **某用戶身份觸發異常但其他人正常** — 邊角條件未驗證
5. **fitness step 全綠但用戶報問題** — fitness 沒涵蓋該邊角

---

> **SOP 核心精神**：**寫程式碼很容易；接通整體系統 + 驗證每個用戶身份體感才是 ADR 真正落地。**
> 半接通的 ADR 對企業是技術債，對 staff/user 是無聲的權限剝奪。

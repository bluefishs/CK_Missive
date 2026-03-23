# /security-audit — CSO 等級資安審計

> **版本**: 2.0.0 (升級自 gstack /cso 理念)
> **建立日期**: 2026-01-15 | **升級日期**: 2026-03-23
> **用途**: 系統化資安合規審計 — OWASP Top 10 + STRIDE 威脅建模

---

## 使用方式

```
/security-audit              # 完整 8 階段審計
/security-audit quick         # 快速掃描（Phase 1-3 only）
/security-audit diff          # 僅審計 git diff 變更
```

---

## Phase 1: 攻擊面映射

列出所有外部入口點：

```bash
# API 端點清單
grep -rn "@router\.\(get\|post\|put\|delete\|patch\)" backend/app/api/endpoints/ --include="*.py"

# WebSocket 端點
grep -rn "WebSocket" backend/app/ --include="*.py"

# 公開端點（無認證）
grep -rn "public\|no_auth\|skip_auth" backend/app/api/ --include="*.py"
```

**輸出**: 攻擊面清單表格（端點 | 方法 | 認證要求 | 輸入類型）

## Phase 2: OWASP Top 10 系統性走查

逐項檢查，每項附帶 CK_Missive 專案特定檢查點：

| # | 風險類型 | 檢查內容 | CK_Missive 重點 |
|---|---------|---------|-----------------|
| A01 | 存取控制失效 | 越權存取、IDOR | `require_auth()` 覆蓋率、link_id 驗證 |
| A02 | 加密失敗 | 密碼雜湊、TLS、敏感資料 | JWT Secret 強度、.env 敏感值 |
| A03 | 注入攻擊 | SQL/NoSQL/OS/LDAP 注入 | SQLAlchemy ORM 使用、`text()` 參數化 |
| A04 | 不安全設計 | 業務邏輯漏洞 | 費用審核繞過、狀態機跳躍 |
| A05 | 安全設定錯誤 | CORS、debug mode、預設密碼 | `CORS_ORIGINS`、`DEBUG` 模式 |
| A06 | 脆弱過時元件 | 已知漏洞依賴 | `npm audit`、`pip audit` |
| A07 | 身份認證失敗 | Session 管理、暴力破解 | Google OAuth、LINE Login、JWT 過期 |
| A08 | 軟體與資料完整性 | 不安全反序列化、CI/CD | LLM 輸出信任、YAML/JSON 反序列化 |
| A09 | 日誌與監控不足 | 審計追蹤 | Agent trace 完整性、敏感操作日誌 |
| A10 | SSRF | 伺服器端請求偽造 | MOF API 呼叫、Federation Client |

**每項評分**: Pass / Fail / N/A，附帶證據（檔案:行號）

## Phase 3: STRIDE 威脅建模

對核心元件執行 STRIDE 分析：

| 威脅 | 說明 | CK_Missive 檢查重點 |
|------|------|---------------------|
| **S**poofing | 身份偽造 | OAuth token 驗證、API Key 保護 |
| **T**ampering | 資料竄改 | 費用金額修改、公文狀態篡改 |
| **R**epudiation | 否認操作 | 審計日誌完整性、操作追蹤 |
| **I**nformation Disclosure | 資訊洩漏 | 錯誤訊息、API 回應過度曝露 |
| **D**enial of Service | 阻斷服務 | Rate limiting、大量上傳防護 |
| **E**levation of Privilege | 權限提升 | 角色檢查、admin 端點保護 |

## Phase 4: 資料分級

根據資料敏感度分類：

| 級別 | 定義 | CK_Missive 範例 |
|------|------|-----------------|
| RESTRICTED | 洩漏造成重大損害 | JWT Secret、API Keys、DB 密碼 |
| CONFIDENTIAL | 洩漏造成中度損害 | 用戶個資、公文內容、財務金額 |
| INTERNAL | 限內部使用 | 專案代碼、機關名稱、派工資料 |
| PUBLIC | 公開資訊 | 系統狀態、API 文件 |

**檢查**: 每個級別的資料是否有對應的保護措施（加密、存取控制、日誌）

## Phase 5: 假陽性過濾

### 自動排除規則（不報告）

1. 測試檔案中的硬編碼密碼（`tests/`, `test_*.py`, `*.test.ts`）
2. 範例/文件中的 placeholder（`example`, `placeholder`, `xxx`）
3. 環境變數讀取語句（`os.getenv()`, `process.env.`）
4. Type hints 和 Schema 定義中的 `password` / `secret` 字串
5. 日誌格式字串中的 `token` / `key` 參數名
6. `.gitignore` 中已排除的檔案
7. `alembic/versions/` 中的遷移檔案
8. 第三方套件的已知 pattern（`node_modules/`, `site-packages/`）
9. 註解中的安全說明（`# Security note:`, `// SECURITY:`）
10. Mock/Fixture 中的測試用資料

### 信心閾值

**只有信心 >= 8/10 的發現才會報告**。評分標準：

| 因素 | 加分 |
|------|------|
| 在生產路徑中 | +3 |
| 涉及用戶輸入 | +2 |
| 涉及敏感資料操作 | +2 |
| 無防護措施 | +2 |
| 已有文件記錄 | +1 |
| 在測試/範例中 | -5 |
| 已有中間件保護 | -3 |
| 使用 ORM/框架安全功能 | -2 |

## Phase 6: 獨立驗證

對每個高信心發現，使用 Agent 子任務**獨立交叉驗證**：

1. 追蹤資料流 — 從用戶輸入到資料庫/回應的完整路徑
2. 檢查是否有上游中間件已提供保護
3. 確認漏洞在真實請求下是否可觸發
4. 排除理論上存在但實際不可達的路徑

## Phase 7: POST-only 合規 + 專案特定檢查

### POST-only API 合規

```bash
grep -rn "@router.get" backend/app/api/endpoints/ --include="*.py" | grep -v "health\|debug\|public\|monitoring"
```

### CK_Missive 專項

- [ ] 所有業務 API 使用 POST（安全政策）
- [ ] `isAuthDisabled()` 僅在開發/內網環境生效
- [ ] CORS 不含 `"*"` wildcard
- [ ] 檔案上傳有類型白名單 + 大小限制
- [ ] 費用審核狀態機無跳躍漏洞
- [ ] Agent LLM 輸出未直接用於 SQL/系統命令
- [ ] MOF API 呼叫有 HMAC 簽名驗證
- [ ] Federation Client 有 X-Service-Token 認證
- [ ] 環境變數 (.env) 在 .gitignore 中

## Phase 8: 報告輸出

```markdown
# 資安審計報告 — YYYY-MM-DD

## 執行摘要

| 維度 | 評級 | 說明 |
|------|------|------|
| 整體安全等級 | A/B/C/D/F | 綜合評估 |
| OWASP 合規 | N/10 通過 | 各項結果 |
| STRIDE 覆蓋 | N/6 通過 | 威脅防護 |
| 資料分級 | 完善/部分/不足 | 保護措施覆蓋 |

## OWASP Top 10 逐項結果

| # | 風險 | 狀態 | 信心 | 證據 |
|---|------|------|------|------|
| A01 | 存取控制 | Pass/Fail | 9/10 | file:line |
| ... | ... | ... | ... | ... |

## STRIDE 分析結果

[各元件 STRIDE 矩陣]

## 發現問題（信心 >= 8/10）

### CRITICAL
[立即需要修復的問題]

### HIGH
[本週內應修復]

### MEDIUM
[本月內應修復]

## 修復路線圖

| 優先級 | 問題 | 建議修復 | 預估工作量 |
|--------|------|---------|-----------|
| P0 | ... | ... | 1h |
| P1 | ... | ... | 4h |
| P2 | ... | ... | 8h |

## 附錄：假陽性排除清單
[Phase 5 排除的項目及原因]
```

---

## 相關文件

- `.claude/MANDATORY_CHECKLIST.md` - 強制性開發檢查清單
- `.claude/hooks/careful-guard.ps1` - 危險命令攔截 hook
- `docs/PRODUCTION_SECURITY_CHECKLIST.md` - 生產環境安全清單

---

*CSO 等級審計 — 信心優先、零噪音*

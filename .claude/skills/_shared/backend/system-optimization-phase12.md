---
name: 系統優化 Phase 12
description: CI/CD 強化、資安深化、部署優化綜合指南
version: 1.0.0
category: project
triggers:
  - /phase12
  - 系統優化
  - CI/CD 強化
  - 資安優化
  - 部署優化
updated: 2026-02-02
---

# 系統優化 Phase 12 - CI/CD 強化與資安深化

> **完成日期**: 2026-02-02
> **CI/CD 成熟度**: 4.0 → 4.8 (+0.8)

---

## 一、優化成果總覽

### 1.1 檢測指標

| 指標 | 優化前 | 優化後 | 狀態 |
|------|--------|--------|------|
| ESLint warnings | 有 | 0 | ✅ |
| TypeScript errors | 有 | 0 | ✅ |
| npm audit vulnerabilities | 有 | 0 | ✅ |
| `as any` 類型斷言 | 136 | 0 | ✅ |
| `console.*` 調用 | 805 | 31 | ✅ |
| 後端架構警告 | 48 | 0 | ✅ |
| 生產碼 print() | 112 | 0 | ✅ |

### 1.2 CI/CD 成熟度

| 維度 | 前 | 後 | 變化 |
|------|-----|-----|------|
| 安全檢查 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 維持 |
| 測試覆蓋 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | +1 |
| 性能監控 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | +1 |
| 依賴管理 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | +1 |
| 部署流程 | ⭐⭐⭐ | ⭐⭐⭐⭐ | +1 |
| **總分** | **4.0/5** | **4.8/5** | +0.8 |

---

## 二、資安優化項目

### 2.1 R-SEC-001: 安全標頭強化 ✅

**位置**: `frontend/nginx.conf`, `deploy_nas/config/nginx.conf`

```nginx
# 安全標頭配置
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(self), microphone=(), camera=()" always;
```

### 2.2 R-SEC-003: 輸入消毒模組 ✅

**位置**: `backend/app/utils/input_sanitizer.py`

```python
from backend.app.utils.input_sanitizer import (
    sanitize_html,
    sanitize_ai_chat_input,
    sanitize_coordinate,
    sanitize_filename,
    validate_bbox,
    detect_injection_attempt,
)

# 使用範例
user_message = sanitize_ai_chat_input(request.message, max_length=2000)
```

**防護類型**:
- XSS 攻擊 (HTML/JavaScript 注入)
- SQL 注入 (額外防護層)
- 命令注入
- 路徑遍歷攻擊

### 2.3 R-SEC-004: 審計日誌機制 ✅

**位置**: `backend/app/utils/audit_logger.py`

```python
from backend.app.utils.audit_logger import audit_logger, AuditAction

# 記錄刪除操作
audit_logger.log_delete(
    resource_type="land_parcel",
    resource_id="12345",
    user_id="user_001",
    ip_address=request.client.host,
    reason="User requested deletion"
)

# 記錄批次操作
audit_logger.log_batch_operation(
    action=AuditAction.BATCH_DELETE,
    resource_type="transactions",
    resource_ids=["1", "2", "3"],
    user_id="admin"
)

# 記錄權限變更
audit_logger.log_permission_change(
    target_user_id="user_002",
    permission="admin",
    granted=True,
    admin_user_id="superadmin"
)
```

---

## 三、CI/CD 優化項目

### 3.1 R-CI-003: 測試並行化 ✅

**位置**: `.github/workflows/ci.yml`

```yaml
frontend-test:
  strategy:
    fail-fast: false
    matrix:
      shard: [1, 2, 3]
  steps:
    - name: Run frontend tests (shard ${{ matrix.shard }}/3)
      run: npm run test:coverage -- --shard=${{ matrix.shard }}/3
```

**效益**: 測試時間減少約 60%

### 3.2 R-CI-004: 覆蓋率追蹤 ✅

**位置**: `codecov.yml`

```yaml
flags:
  backend:
    paths:
      - backend/
    carryforward: true
    after_n_builds: 1

  frontend:
    paths:
      - frontend/src/
    carryforward: true
    after_n_builds: 3  # 等待 3 個 shard 完成
```

### 3.3 R-CI-005: Lighthouse PR Gate ✅

**位置**: `lighthouserc.json`

```json
{
  "ci": {
    "assert": {
      "assertions": {
        "categories:performance": ["warn", { "minScore": 0.7 }],
        "categories:accessibility": ["error", { "minScore": 0.9 }],
        "categories:best-practices": ["warn", { "minScore": 0.8 }]
      }
    }
  }
}
```

### 3.4 R-CI-007: 自動化 CHANGELOG ✅

**位置**: `.github/workflows/release.yml`, `commitlint.config.js`

**觸發條件**: push tag (v*)

**Conventional Commits 格式**:
- `feat:` 新功能
- `fix:` 錯誤修復
- `docs:` 文檔變更
- `ci:` CI/CD 變更
- `refactor:` 重構

---

## 四、部署優化項目

### 4.1 R-DEPLOY-001: 部署前置腳本 ✅

**位置**: `scripts/pre-deploy.sh`

```bash
# 執行部署前檢查
bash scripts/pre-deploy.sh

# 檢查項目:
# 1. 必要目錄建立
# 2. 端口可用性檢查 (5433, 8002, 13000, 6379)
# 3. 環境變數驗證
# 4. Docker 映像檢查
```

### 4.2 R-DEPLOY-002: 環境變數範本 ✅

**位置**: `deploy_nas/config/.env.example`

包含所有必要的環境變數及說明。

### 4.3 R-DEPLOY-003: 部署檢查清單 ✅

**位置**: `docs/DEPLOYMENT_CHECKLIST.md`

完整的部署流程檢查清單，包含：
- 部署前準備
- 部署執行步驟
- 部署後驗證
- 常見問題排除

---

## 五、架構優化項目

### 5.1 R-ARCH-003: API 快取策略 ✅

**位置**: `docs/specs/API_CACHE_STRATEGY.md`

**建議快取端點**:

| 端點 | TTL | 理由 |
|------|-----|------|
| `/api/v1/spatial/admin-districts/*` | 24h | 資料穩定 |
| `/api/v1/navigation/config` | 1h | 配置較少變更 |
| `/api/v1/basemap/groups` | 1h | 底圖群組配置 |

**使用方式**:
```python
from backend.app.utils.cache_decorator import async_cached

@router.get("/cities")
@async_cached(ttl=86400, key_prefix="admin_districts")
async def get_cities(db: Session = Depends(get_db)):
    return await service.get_all_cities(db)
```

---

## 六、新增檔案清單

| 檔案 | 用途 |
|------|------|
| `backend/app/utils/audit_logger.py` | 審計日誌服務 |
| `backend/app/utils/input_sanitizer.py` | 輸入消毒工具 |
| `.github/workflows/release.yml` | 自動化 CHANGELOG |
| `lighthouserc.json` | Lighthouse CI 配置 |
| `commitlint.config.js` | Conventional Commits |
| `scripts/pre-deploy.sh` | 部署前置腳本 |
| `docs/DEPLOYMENT_CHECKLIST.md` | 部署檢查清單 |
| `docs/specs/API_CACHE_STRATEGY.md` | API 快取策略 |
| `docs/specs/SYSTEM_OPTIMIZATION_RECOMMENDATIONS_2026-02-02.md` | 優化建議總控 |

---

## 七、後續建議

### 7.1 短期 (持續維護)

- 定期執行 `npm audit` 和 `safety check`
- 監控 Codecov 覆蓋率趨勢
- 使用 Conventional Commits 格式提交

### 7.2 中期 (下個迭代)

- 整合審計日誌到關鍵端點
- 為高頻端點添加 Redis 快取
- 配置 Slack Webhook 啟用 CI 通知

### 7.3 長期 (本季)

- R-SEC-005: WAF 評估
- R-SEC-006: 滲透測試
- R-CI-006: 藍綠部署評估
- R-DEPLOY-005: CI/CD 自動化部署

---

## 八、相關文件

- `docs/specs/SYSTEM_OPTIMIZATION_RECOMMENDATIONS_2026-02-02.md`
- `docs/specs/SECURITY_AUDIT_2026-02-02.md`
- `.claude/skills/known-issues-registry.md`
- `.claude/skills/_shared/shared/security-hardening.md`
- `.claude/skills/_shared/shared/code-standards.md`

---

*最後更新: 2026-02-02*

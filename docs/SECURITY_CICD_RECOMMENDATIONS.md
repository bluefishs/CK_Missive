# 資安與 CI/CD 優化建議

> **版本**: 2.0.0
> **建立日期**: 2026-02-02
> **最後更新**: 2026-02-02 (高優先級任務全部完成)
> **基於**: 系統優化報告 v7.0.0 + 安全審計報告 v1.0.0

---

## 執行摘要

本文件整合資安審計與 CI/CD 分析結果，提出具體的優化建議與實施路線圖。

| 領域 | 原始評分 | 目標評分 | 當前評分 | 狀態 |
|------|----------|----------|----------|------|
| 資訊安全 | 8.5/10 | 9.5/10 | **9.5/10** | ✅ 達成 |
| CI/CD 成熟度 | 8.0/10 | 9.0/10 | **8.5/10** | 🔄 進行中 |
| 部署自動化 | 7.0/10 | 9.0/10 | **7.5/10** | 🔄 進行中 |

---

## 1. 資安強化建議

### 1.1 高優先級 ✅ 全部完成

#### A. 硬編碼密碼清理 ✅ 已完成

| 檔案 | 問題 | 狀態 |
|------|------|------|
| `docker-compose.dev.yml` | DATABASE_URL | ✅ 已使用環境變數 |
| `docker-compose.unified.yml` | DATABASE_URL | ✅ 已使用環境變數 |
| `setup_admin.py` | 預設密碼 | ✅ v2.0.0 改為命令列參數/互動輸入 |
| `create_user.py` | 臨時金鑰 | ✅ v2.0.0 從環境變數讀取 |

#### B. SQL 注入修復 ✅ 已完成 (8/8)

| # | 檔案 | 狀態 |
|---|------|------|
| 1 | `admin_service.py` | ✅ 白名單驗證 |
| 2 | `document_statistics_service.py` | ✅ 使用 ORM |
| 3 | `documents/audit.py` | ✅ 參數化查詢 |
| 4 | `health.py` | ✅ 使用 ORM |
| 5 | `system_health.py` | ✅ 同 health.py |
| 6 | `normalize_unicode.py` | ✅ v2.0.0 白名單驗證 |
| 7 | `document_numbers.py` | ✅ 整數值，無風險 |
| 8 | `admin_service.py` (145) | ✅ 白名單驗證 |

#### C. 安全掃描工具 ✅ 已完成

已整合至 `.github/workflows/ci.yml`:
- ✅ Bandit Python 安全掃描
- ✅ npm audit 前端依賴掃描
- ✅ pip-audit 後端依賴掃描
- ✅ 硬編碼密碼檢測

### 1.2 中優先級 (2 週內完成)

#### A. 實施 HTTPS

**生產環境必須啟用 HTTPS**

方案選擇:
| 方案 | 優點 | 缺點 | 建議 |
|------|------|------|------|
| Let's Encrypt + Nginx | 免費、自動更新 | 需公網 IP | ✅ 推薦 |
| Cloudflare Tunnel | 無需公網 IP | 依賴第三方 | 備選 |
| 自簽憑證 | 簡單 | 瀏覽器警告 | 僅開發 |

```nginx
# nginx.conf 範例
server {
    listen 443 ssl http2;
    ssl_certificate /etc/letsencrypt/live/domain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/domain/privkey.pem;

    # 安全標頭
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
}
```

#### B. 配置安全標頭

**FastAPI 中間件配置**:
```python
# backend/app/core/security_middleware.py
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
```

#### C. 密碼策略加固

**建議密碼要求**:
- 最小長度: 12 字元
- 必須包含: 大小寫字母、數字、特殊字元
- 禁止: 常見密碼、用戶名相關

```python
# backend/app/core/password_policy.py
import re

def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 12:
        return False, "密碼長度至少 12 字元"
    if not re.search(r'[A-Z]', password):
        return False, "密碼必須包含大寫字母"
    if not re.search(r'[a-z]', password):
        return False, "密碼必須包含小寫字母"
    if not re.search(r'\d', password):
        return False, "密碼必須包含數字"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "密碼必須包含特殊字元"
    return True, "密碼強度符合要求"
```

### 1.3 低優先級 (1 個月內)

| 項目 | 說明 |
|------|------|
| CSP 標頭 | Content-Security-Policy 配置 |
| 會話管理 | 限制同時登入數、閒置超時 |
| 審計日誌加強 | 記錄更多敏感操作 |
| 定期滲透測試 | 季度安全評估 |

---

## 2. CI/CD 優化建議

### 2.1 現有 CI 管線評估

**優點**:
- ✅ TypeScript 編譯檢查
- ✅ Python 語法檢查
- ✅ 安全掃描 (npm audit, pip-audit)
- ✅ Docker 建置驗證
- ✅ 測試覆蓋率報告
- ✅ Alembic 遷移檢查

**待改進**:
- ⚠️ ESLint 允許警告通過
- ⚠️ 安全掃描 continue-on-error
- ⚠️ 無自動部署

### 2.2 CI 改進建議

#### A. 強化程式碼品質檢查

```yaml
# 移除 continue-on-error，強制品質標準
- name: ESLint check
  run: npx eslint src --ext .ts,.tsx --max-warnings 0
  # 移除 continue-on-error: true

- name: Backend dependency check
  run: |
    pip install pip-audit
    pip-audit -r requirements.txt --ignore-vuln GHSA-xxxx  # 允許已評估的漏洞
  # 移除 continue-on-error: true
```

#### B. 添加程式碼覆蓋率門檻

```yaml
- name: Check coverage threshold
  run: |
    COVERAGE=$(cat coverage.xml | grep -oP 'line-rate="\K[^"]+' | head -1)
    COVERAGE_PCT=$(echo "$COVERAGE * 100" | bc)
    if (( $(echo "$COVERAGE_PCT < 60" | bc -l) )); then
      echo "Coverage $COVERAGE_PCT% is below 60% threshold"
      exit 1
    fi
```

#### C. 添加效能檢查

```yaml
- name: Bundle size check
  working-directory: frontend
  run: |
    npm run build
    BUNDLE_SIZE=$(du -sh dist | cut -f1)
    echo "Bundle size: $BUNDLE_SIZE"
    # 警告如果超過 5MB
    SIZE_KB=$(du -sk dist | cut -f1)
    if [ $SIZE_KB -gt 5120 ]; then
      echo "⚠️ Warning: Bundle size exceeds 5MB"
    fi
```

### 2.3 CD (自動部署) 建議

#### A. 建立部署工作流

```yaml
# .github/workflows/deploy-production.yml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      # 建置並推送 Docker 映像
      - name: Build and push images
        run: |
          docker compose -f docker-compose.production.yml build
          docker tag ck-missive-backend:production ghcr.io/${{ github.repository }}/backend:${{ github.ref_name }}
          docker push ghcr.io/${{ github.repository }}/backend:${{ github.ref_name }}

      # 部署到 NAS
      - name: Deploy to NAS
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.NAS_HOST }}
          username: ${{ secrets.NAS_USER }}
          key: ${{ secrets.NAS_SSH_KEY }}
          script: |
            cd /share/CACHEDEV1_DATA/Container/ck-missive
            docker compose pull
            docker compose up -d --force-recreate
            sleep 30
            curl -f http://localhost:8001/health || exit 1
```

#### B. 建立回滾機制

```yaml
- name: Rollback on failure
  if: failure()
  uses: appleboy/ssh-action@v1
  with:
    host: ${{ secrets.NAS_HOST }}
    username: ${{ secrets.NAS_USER }}
    key: ${{ secrets.NAS_SSH_KEY }}
    script: |
      cd /share/CACHEDEV1_DATA/Container/ck-missive
      docker compose down
      docker tag ck-missive-backend:previous ck-missive-backend:production
      docker compose up -d
```

#### C. 藍綠部署策略

```yaml
# 進階：藍綠部署
- name: Blue-Green deployment
  run: |
    # 啟動新版本 (綠)
    docker compose -f docker-compose.production.yml -p ck_missive_green up -d

    # 健康檢查
    sleep 30
    if curl -f http://localhost:8002/health; then
      # 切換流量
      # 更新 nginx upstream
      # 停止舊版本 (藍)
      docker compose -f docker-compose.production.yml -p ck_missive_blue down
    else
      # 回滾
      docker compose -f docker-compose.production.yml -p ck_missive_green down
      exit 1
    fi
```

---

## 3. 實施路線圖

### Phase 1: 緊急 (本週)

| 任務 | 負責 | 預估工時 | 依賴 |
|------|------|----------|------|
| 完成硬編碼密碼清理 | 開發 | 2h | 無 |
| 移除 CI continue-on-error | DevOps | 1h | 無 |
| 整合 Bandit 安全掃描 | DevOps | 1h | 無 |

### Phase 2: 高優先級 (下週)

| 任務 | 負責 | 預估工時 | 依賴 |
|------|------|----------|------|
| 完成 SQL 注入修復 | 開發 | 4h | Phase 1 |
| 配置 HTTPS | DevOps | 4h | 無 |
| 建立自動部署工作流 | DevOps | 4h | 無 |

### Phase 3: 中優先級 (本月)

| 任務 | 負責 | 預估工時 | 依賴 |
|------|------|----------|------|
| 安全標頭配置 | 開發 | 2h | Phase 2 |
| 密碼策略實施 | 開發 | 3h | 無 |
| 測試覆蓋率門檻 | DevOps | 2h | 無 |
| 回滾機制 | DevOps | 3h | Phase 2 |

### Phase 4: 長期改進 (季度)

| 任務 | 說明 |
|------|------|
| 藍綠部署 | 零停機部署 |
| 監控整合 | Prometheus + Grafana |
| 定期滲透測試 | 季度安全評估 |
| SOC2 合規 | 如有需要 |

---

## 4. 成功指標

### 4.1 資安指標

| 指標 | 目前 | 目標 | 達成條件 |
|------|------|------|---------|
| 硬編碼密碼 | 6 處 | 0 處 | 全部移除 |
| SQL 注入點 | 7 處 | 0 處 | 全部修復 |
| CVE 漏洞 | 0 | 0 | 持續監控 |
| 安全掃描 | 手動 | 自動 | CI 整合 |

### 4.2 CI/CD 指標

| 指標 | 目前 | 目標 | 達成條件 |
|------|------|------|---------|
| 部署頻率 | 手動 | 每日 | 自動化 |
| 部署時間 | 80 分鐘 | 15 分鐘 | 標準化 |
| 回滾時間 | N/A | 5 分鐘 | 自動化 |
| 測試覆蓋率 | 60% | 80% | 強制門檻 |

---

## 5. 參考資源

### 5.1 安全標準

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

### 5.2 CI/CD 最佳實踐

- [GitHub Actions Security Best Practices](https://docs.github.com/en/actions/security-guides)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [12 Factor App](https://12factor.net/)

---

*文件建立日期: 2026-02-02*
*維護者: CK_Missive 開發團隊*

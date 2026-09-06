# GitOps 評估與實施計畫
> Version: 1.0.0 | Last Updated: 2026-02-21

> **版本**: 1.0.0
> **建立日期**: 2026-02-03
> **目標環境**: QNAP NAS (192.168.50.210)
> **技術棧**: GitHub Actions + Docker Compose + Self-hosted Runner

---

## 一、GitOps 概述

### 1.1 什麼是 GitOps

GitOps 是一種以 Git 作為單一事實來源的操作模型：
- **聲明式配置**: 基礎設施和應用配置存儲在 Git
- **自動同步**: Git 變更自動同步到生產環境
- **版本控制**: 所有變更都有完整歷史記錄
- **可審計**: 變更經過 PR 審核流程

### 1.2 GitOps 對 CK_Missive 的價值

| 價值 | 說明 |
|------|------|
| **消除部署缺口** | 解決「代碼提交 ≠ 功能上線」問題 |
| **提高可靠性** | 自動化部署減少人為錯誤 |
| **快速回滾** | Git revert 即可回滾 |
| **審計追蹤** | 所有部署都有 Git 記錄 |

---

## 二、現況評估

### 2.1 現有 CI/CD 架構

```
┌─────────────────────────────────────────────────────┐
│                  GitHub Repository                   │
├─────────────────────────────────────────────────────┤
│  Push/PR 觸發                                        │
│       ↓                                              │
│  ┌───────────────────────────────────────────────┐  │
│  │           GitHub Actions CI                    │  │
│  │  ├── frontend-check (TypeScript + ESLint)     │  │
│  │  ├── backend-check (Python + pytest)          │  │
│  │  ├── security-scan (npm audit + pip-audit)    │  │
│  │  ├── docker-build (映像建置驗證)               │  │
│  │  └── test-coverage (測試覆蓋報告)              │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  CD 工作流 (手動觸發)                                │
│       ↓                                              │
│  ┌───────────────────────────────────────────────┐  │
│  │         deploy-production.yml                  │  │
│  │  ├── validate (輸入驗證)                       │  │
│  │  ├── backup (部署前備份)                       │  │
│  │  ├── deploy (SSH 部署)                         │  │
│  │  ├── health-check (健康檢查)                   │  │
│  │  └── rollback (失敗回滾)                       │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                         ↓
                  [手動觸發缺口]
                         ↓
┌─────────────────────────────────────────────────────┐
│              QNAP NAS (192.168.50.210)              │
│  ├── Docker Compose                                 │
│  │   ├── backend (FastAPI)                          │
│  │   ├── frontend (Nginx)                           │
│  │   └── postgres (PostgreSQL)                      │
│  └── 目前需手動 git pull + restart                  │
└─────────────────────────────────────────────────────┘
```

### 2.2 現有問題

| 問題 | 影響 | 嚴重度 |
|------|------|--------|
| CD 需手動觸發 | 部署延遲 | 🟠 High |
| 無自動健康檢查 | 問題發現延遲 | 🟡 Medium |
| 無 Staging 環境 | 測試不完整 | 🟡 Medium |
| 無自動回滾 | 故障恢復慢 | 🟡 Medium |

---

## 三、GitOps 實施方案

### 3.1 方案對比

| 方案 | 優點 | 缺點 | 適合度 |
|------|------|------|--------|
| **A: Self-hosted Runner** | 內網直連、安全 | 需要維護 Runner | ⭐⭐⭐⭐⭐ |
| B: ArgoCD | 標準 GitOps 工具 | 需要 K8s | ⭐⭐ |
| C: Flux | 輕量 GitOps | 需要 K8s | ⭐⭐ |
| D: Webhook + 腳本 | 簡單 | 安全性較低 | ⭐⭐⭐ |

**推薦方案**: **A - GitHub Actions Self-hosted Runner**

### 3.2 推薦架構

```
┌─────────────────────────────────────────────────────────────┐
│                    GitOps 目標架構                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  開發者                                                     │
│    │                                                        │
│    ├── feature branch 開發                                  │
│    │         ↓                                              │
│    └── PR 到 main → CI 檢查 → 代碼審核                      │
│                              ↓                              │
│                        合併到 main                          │
│                              ↓                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │              自動觸發 CD 工作流                     │    │
│  │                                                    │    │
│  │  [Staging 部署] ────→ [E2E 測試] ────→ [確認]     │    │
│  │         ↓                    ↓           ↓        │    │
│  │      自動               自動        手動確認       │    │
│  │                                       ↓           │    │
│  │                           [生產部署]              │    │
│  │                                ↓                  │    │
│  │                           自動                    │    │
│  │                                ↓                  │    │
│  │                        [健康檢查]                 │    │
│  │                           ↓    ↓                  │    │
│  │                        通過    失敗               │    │
│  │                         ↓       ↓                 │    │
│  │                       完成   [自動回滾]           │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、實施步驟

### 4.1 階段一：基礎設施準備 (1-2 天)

#### Step 1: 在 NAS 安裝 Self-hosted Runner

```bash
# 1. SSH 連線到 NAS
ssh admin@192.168.50.210

# 2. 建立 Runner 目錄
mkdir -p /share/Container/github-runner
cd /share/Container/github-runner

# 3. 下載 Runner (Linux x64)
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

# 4. 解壓縮
tar xzf actions-runner-linux-x64-2.311.0.tar.gz

# 5. 配置 Runner (從 GitHub Settings 取得 Token)
./config.sh --url https://github.com/bluefishs/CK_Missive --token YOUR_TOKEN

# 6. 安裝為服務
sudo ./svc.sh install
sudo ./svc.sh start
```

#### Step 2: 配置 Repository Secrets

在 GitHub Repository Settings → Secrets 新增：

| Secret 名稱 | 說明 | 範例值 |
|-------------|------|--------|
| `DEPLOY_PATH` | 部署路徑 | `/share/Container/CK_Missive` |
| `DOCKER_COMPOSE_FILE` | Compose 檔案 | `docker-compose.production.yml` |
| `SLACK_WEBHOOK` | 通知 (可選) | `https://hooks.slack.com/...` |

### 4.2 階段二：CI/CD 工作流更新 (1-2 天)

#### 更新 deploy-production.yml

```yaml
# .github/workflows/deploy-production.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      skip_backup:
        description: '跳過備份'
        type: boolean
        default: false

jobs:
  # CI 檢查
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Frontend Check
        run: cd frontend && npm ci && npm run lint && npm run build
      - name: Backend Check
        run: cd backend && pip install -r requirements.txt && python -m py_compile app/main.py

  # Staging 部署 (可選)
  deploy-staging:
    needs: verify
    runs-on: self-hosted
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Staging
        run: |
          cd ${{ secrets.STAGING_PATH }}
          git pull origin main
          docker-compose -f docker-compose.staging.yml up -d --build

  # E2E 測試 (可選)
  e2e-tests:
    needs: deploy-staging
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run E2E Tests
        run: npx playwright test
        env:
          BASE_URL: ${{ secrets.STAGING_URL }}

  # 生產部署
  deploy-production:
    needs: [verify]  # 或 [e2e-tests] 若啟用 staging
    runs-on: self-hosted
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Backup (if not skipped)
        if: ${{ !inputs.skip_backup }}
        run: |
          cd ${{ secrets.DEPLOY_PATH }}
          ./scripts/backup/db_backup.sh

      - name: Deploy
        run: |
          cd ${{ secrets.DEPLOY_PATH }}
          git pull origin main
          docker-compose -f ${{ secrets.DOCKER_COMPOSE_FILE }} up -d --build

      - name: Health Check
        run: |
          sleep 30
          curl -f http://localhost:8001/health || exit 1
          curl -f http://localhost:3000 || exit 1

      - name: Rollback on Failure
        if: failure()
        run: |
          cd ${{ secrets.DEPLOY_PATH }}
          git checkout HEAD~1
          docker-compose -f ${{ secrets.DOCKER_COMPOSE_FILE }} up -d --build

  # 通知
  notify:
    needs: deploy-production
    runs-on: ubuntu-latest
    if: always()
    steps:
      - name: Notify Success
        if: ${{ needs.deploy-production.result == 'success' }}
        run: echo "✅ Deployment successful"

      - name: Notify Failure
        if: ${{ needs.deploy-production.result == 'failure' }}
        run: echo "❌ Deployment failed"
```

### 4.3 階段三：監控與告警 (1 週)

#### 部署監控儀表板

已建立 `/admin/deployment` 頁面，提供：
- 服務狀態監控
- 部署歷史記錄
- 手動觸發/回滾

#### 建議新增告警

| 告警類型 | 工具 | 說明 |
|----------|------|------|
| 部署失敗 | GitHub Actions | 自動郵件通知 |
| 服務異常 | 健康檢查 | 自動重試/回滾 |
| 效能告警 | Prometheus (可選) | 回應時間過長 |

### 4.4 階段四：完善流程 (持續)

#### 建立標準操作程序 (SOP)

1. **日常開發流程**
   ```
   feature branch → PR → Code Review → Merge → 自動部署
   ```

2. **緊急修復流程**
   ```
   hotfix branch → PR (快速審核) → Merge → 自動部署
   ```

3. **回滾流程**
   ```
   部署管理頁面 → 回滾確認 → 自動執行
   ```

---

## 五、時程安排

### 5.1 實施時程表

| 階段 | 任務 | 時程 | 負責人 |
|------|------|------|--------|
| **Phase 1** | Self-hosted Runner 安裝 | Day 1-2 | 運維 |
| **Phase 2** | Repository Secrets 配置 | Day 2 | 運維 |
| **Phase 3** | CD 工作流更新 | Day 3-4 | 開發 |
| **Phase 4** | 測試與驗證 | Day 5-7 | 全員 |
| **Phase 5** | 文件更新與培訓 | Week 2 | 全員 |

### 5.2 里程碑

| 里程碑 | 目標日期 | 驗收標準 |
|--------|----------|----------|
| M1: Runner 運作 | Day 2 | Runner 在線 |
| M2: 自動部署 | Day 5 | Push 後自動部署 |
| M3: 健康檢查 | Day 7 | 失敗自動回滾 |
| M4: 完整 GitOps | Week 2 | 文件完善 |

---

## 六、風險與緩解

### 6.1 風險評估

| 風險 | 可能性 | 影響 | 緩解措施 |
|------|--------|------|----------|
| Runner 不穩定 | 中 | 高 | 監控 + 自動重啟 |
| 部署失敗 | 低 | 高 | 自動回滾機制 |
| 安全問題 | 低 | 高 | Secrets 管理 + 審核 |
| NAS 資源不足 | 低 | 中 | 監控 + 清理策略 |

### 6.2 回滾策略

```
自動回滾觸發條件:
1. 健康檢查失敗 (連續 3 次)
2. 部署腳本錯誤退出
3. Docker 容器啟動失敗

回滾步驟:
1. git checkout HEAD~1
2. docker-compose down
3. docker-compose up -d --build
4. 通知運維
```

---

## 七、成本效益分析

### 7.1 投入成本

| 項目 | 一次性成本 | 持續成本 |
|------|------------|----------|
| Runner 安裝 | 4 人時 | 0 |
| 工作流開發 | 8 人時 | 2 人時/月 (維護) |
| 文件與培訓 | 4 人時 | 1 人時/月 |
| **總計** | **16 人時** | **3 人時/月** |

### 7.2 預期效益

| 效益 | 量化估計 |
|------|----------|
| 部署時間縮短 | 30 分鐘 → 5 分鐘 (-83%) |
| 部署頻率提升 | 每週 2 次 → 每天多次 |
| 故障恢復時間 | 30 分鐘 → 5 分鐘 (-83%) |
| 人為錯誤減少 | 預估 -90% |

### 7.3 ROI 分析

```
投入: 16 人時 (一次性) + 3 人時/月 (持續)
節省: 每次部署節省 25 分鐘 × 每月 20 次 = 8.3 人時/月

淨效益: 8.3 - 3 = 5.3 人時/月
ROI: 3 個月回本
```

---

## 八、下一步行動

### 8.1 即時行動 (本週)

- [ ] 確認 NAS 可安裝 GitHub Runner
- [ ] 從 GitHub 取得 Runner Token
- [ ] 安裝並配置 Runner

### 8.2 短期行動 (下週)

- [ ] 更新 CD 工作流
- [ ] 配置 Repository Secrets
- [ ] 測試自動部署流程

### 8.3 中期行動 (本月)

- [ ] 建立 Staging 環境 (可選)
- [ ] 整合 E2E 測試
- [ ] 完善監控告警

---

## 九、參考文件

| 文件 | 說明 |
|------|------|
| `docs/archived/2026-09-ci-disabled/GITHUB_RUNNER_SETUP.md` | Runner 安裝指南 |
| `docs/DEPLOYMENT_CHECKLIST.md` | 部署檢查清單 |
| `.github/workflows/deploy-production.yml` | CD 工作流 |
| `/admin/deployment` | 部署管理頁面 |

---

*報告產生日期: 2026-02-03*
*分析工具: Claude Opus 4.5*

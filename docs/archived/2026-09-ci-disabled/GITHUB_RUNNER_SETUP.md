# GitHub Self-hosted Runner 設置指南
> Version: 1.0.0 | Last Updated: 2026-02-21

> **版本**: 1.0.0
> **建立日期**: 2026-02-02
> **適用環境**: QNAP NAS + Container Station

---

## 概述

本指南說明如何在 QNAP NAS 上設置 GitHub Self-hosted Runner，用於自動部署 CK_Missive 系統。

### 架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                        GitHub                                │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ Push/Tag    │ -> │ Actions      │ -> │ Workflow      │  │
│  │ Event       │    │ Trigger      │    │ Dispatch      │  │
│  └─────────────┘    └──────────────┘    └───────┬───────┘  │
└─────────────────────────────────────────────────┼──────────┘
                                                  │
                                                  │ (Outbound)
                                                  ▼
┌─────────────────────────────────────────────────────────────┐
│                      QNAP NAS                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Container Station                        │   │
│  │  ┌─────────────────┐    ┌─────────────────────────┐  │   │
│  │  │ GitHub Runner   │ -> │ CK_Missive Containers   │  │   │
│  │  │ Container       │    │ (Backend + Frontend)    │  │   │
│  │  └─────────────────┘    └─────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 前置需求

- [ ] QNAP NAS 已安裝 Container Station
- [ ] Docker 版本 >= 20.10
- [ ] GitHub 帳號有 Repository 管理權限
- [ ] NAS 可連線至 GitHub (僅需出站連線)

---

## 步驟 1: 建立 GitHub Personal Access Token

1. 前往 GitHub Settings > Developer settings > Personal access tokens > Fine-grained tokens

2. 點擊 "Generate new token"

3. 設定 Token：
   - **Token name**: `ck-missive-runner`
   - **Expiration**: 90 days (或更長)
   - **Repository access**: Only select repositories → 選擇 `CK_Missive`

4. 設定權限：
   | 權限類別 | 權限項目 | 存取等級 |
   |---------|---------|---------|
   | Repository | Actions | Read and write |
   | Repository | Administration | Read and write |
   | Repository | Contents | Read |
   | Repository | Metadata | Read |

5. 點擊 "Generate token" 並**複製保存** Token

---

## 步驟 2: 在 QNAP NAS 上設置 Runner

### 方案 A: 使用 Docker Compose (推薦)

1. SSH 登入 NAS：
   ```bash
   ssh admin@your-nas-ip
   ```

2. 建立 Runner 目錄：
   ```bash
   mkdir -p /share/CACHEDEV1_DATA/Container/github-runner
   cd /share/CACHEDEV1_DATA/Container/github-runner
   ```

3. 建立 `docker-compose.yml`：
   ```yaml
   version: '3.8'

   services:
     github-runner:
       image: myoung34/github-runner:latest
       container_name: github-runner-ck-missive
       restart: always
       environment:
         # GitHub 設定
         REPO_URL: https://github.com/YOUR_ORG/CK_Missive
         ACCESS_TOKEN: ${GITHUB_RUNNER_TOKEN}
         RUNNER_NAME: qnap-nas-runner
         RUNNER_WORKDIR: /tmp/runner
         LABELS: self-hosted,linux,qnap

         # Runner 設定
         RUNNER_SCOPE: repo
         DISABLE_AUTO_UPDATE: "false"
         EPHEMERAL: "false"

       volumes:
         # Docker socket (用於執行 docker 命令)
         - /var/run/docker.sock:/var/run/docker.sock
         # 部署目錄
         - /share/CACHEDEV1_DATA/Container/ck-missive:/share/CACHEDEV1_DATA/Container/ck-missive
         # Runner 工作目錄
         - runner-workdir:/tmp/runner

       networks:
         - runner-network

   volumes:
     runner-workdir:

   networks:
     runner-network:
       driver: bridge
   ```

4. 建立 `.env` 檔案：
   ```bash
   GITHUB_RUNNER_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
   ```

5. 啟動 Runner：
   ```bash
   docker compose up -d
   ```

6. 檢查 Runner 狀態：
   ```bash
   docker logs -f github-runner-ck-missive
   ```

### 方案 B: 使用 Container Station UI

1. 開啟 Container Station

2. 點擊 "Create" > "Create Application"

3. 貼上上方的 docker-compose.yml 內容

4. 在 "Environment" 區塊添加：
   - `GITHUB_RUNNER_TOKEN`: 您的 GitHub Token

5. 點擊 "Create"

---

## 步驟 3: 驗證 Runner 連線

1. 前往 GitHub Repository > Settings > Actions > Runners

2. 確認看到您的 Runner：
   ```
   ✅ qnap-nas-runner
      Status: Idle
      Labels: self-hosted, linux, qnap
   ```

3. 測試 Runner：
   - 前往 Actions > Deploy to Production
   - 點擊 "Run workflow"
   - 選擇 branch 並執行

---

## 步驟 4: 配置 GitHub Secrets

前往 Repository > Settings > Secrets and variables > Actions

新增以下 Secrets：

| Secret 名稱 | 值 | 說明 |
|------------|-----|------|
| `DEPLOY_PATH` | `/share/CACHEDEV1_DATA/Container/ck-missive` | NAS 部署路徑 |
| `SLACK_WEBHOOK_URL` | (可選) | Slack 通知 URL |

---

## 常見問題排除

### Q1: Runner 無法連線 GitHub

**檢查**：
```bash
# 測試網路連線
docker exec github-runner-ck-missive curl -I https://github.com

# 檢查 DNS
docker exec github-runner-ck-missive nslookup github.com
```

**解決**：確認 NAS 防火牆允許出站 HTTPS (443)

### Q2: Runner 註冊失敗

**錯誤訊息**：`Http response code: Unauthorized`

**解決**：
1. 確認 Token 權限包含 `Administration: Read and write`
2. 重新生成 Token 並更新 `.env`

### Q3: 無法存取 Docker socket

**錯誤訊息**：`permission denied while trying to connect to the Docker daemon socket`

**解決**：
```bash
# 在 NAS 上執行
chmod 666 /var/run/docker.sock
```

### Q4: 部署路徑權限問題

**解決**：
```bash
# 確保 Runner 可存取部署目錄
chown -R 1000:1000 /share/CACHEDEV1_DATA/Container/ck-missive
```

---

## 維護指南

### 更新 Runner

```bash
cd /share/CACHEDEV1_DATA/Container/github-runner
docker compose pull
docker compose up -d
```

### 查看日誌

```bash
docker logs -f --tail 100 github-runner-ck-missive
```

### 重啟 Runner

```bash
docker compose restart
```

### 移除 Runner

1. 先在 GitHub 上移除 Runner 註冊
2. 停止容器：
   ```bash
   docker compose down
   ```

---

## 安全建議

| 項目 | 建議 | 重要性 |
|------|------|--------|
| Token 權限 | 使用最小權限原則 | 🔴 高 |
| Token 更新 | 定期輪換 (每 90 天) | 🔴 高 |
| 網路隔離 | Runner 使用獨立 Docker network | 🟡 中 |
| 日誌審計 | 定期檢查 Runner 日誌 | 🟡 中 |
| 映像更新 | 定期更新 Runner 映像 | 🟢 低 |

---

## 參考資源

- [GitHub Self-hosted Runners 官方文件](https://docs.github.com/en/actions/hosting-your-own-runners)
- [myoung34/github-runner Docker Image](https://github.com/myoung34/docker-github-actions-runner)
- [QNAP Container Station 文件](https://www.qnap.com/en/software/container-station)

---

*文件建立日期: 2026-02-02*
*維護者: CK_Missive 開發團隊*

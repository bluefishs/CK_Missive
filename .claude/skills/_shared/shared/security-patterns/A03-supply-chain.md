# A03 - 供應鏈安全模式

> **OWASP 類別**: A03:2025 – Software Supply Chain Failures
> **嚴重性**: High
> **適用技術**: npm, pip, Docker

---

## 常見漏洞

| 漏洞類型   | 說明                     | 影響         |
| ---------- | ------------------------ | ------------ |
| 過時依賴   | 使用有已知漏洞的版本     | 系統被入侵   |
| 惡意套件   | 安裝被植入惡意程式的套件 | 資料外洩     |
| 依賴混淆   | 內部套件名被公開套件取代 | 程式碼注入   |
| 未鎖定版本 | 自動更新到惡意版本       | 不可預期行為 |

---

## 安全模式

### 1. 依賴版本鎖定

```json
// package.json - 使用確切版本
{
  "dependencies": {
    "react": "18.2.0", // ✅ 確切版本
    "antd": "^5.0.0", // ⚠️ 可能更新到 5.x
    "lodash": "*" // ❌ 危險：任意版本
  }
}
```

```toml
# pyproject.toml - Poetry 版本鎖定
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "0.109.0"           # ✅ 確切版本
sqlalchemy = "~2.0.0"         # ⚠️ 允許 patch 更新

# 產生 lock 檔案
# poetry lock
```

### 2. 自動化漏洞掃描

```yaml
# .github/workflows/security-scan.yml
name: Security Scan

on:
  push:
    branches: [main, master]
  pull_request:
  schedule:
    - cron: '0 2 * * 1' # 每週一凌晨 2 點

jobs:
  npm-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm audit --audit-level=high
        continue-on-error: true
      - name: Upload audit report
        uses: actions/upload-artifact@v3
        with:
          name: npm-audit-report
          path: npm-audit.json

  pip-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install pip-audit
      - run: pip-audit -r backend/requirements.txt --desc
        continue-on-error: true
```

### 3. 依賴更新自動化 (Renovate/Dependabot)

```json
// renovate.json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:base"],
  "labels": ["dependencies", "automated"],
  "packageRules": [
    {
      "matchUpdateTypes": ["major"],
      "labels": ["major-update"],
      "automerge": false
    },
    {
      "matchUpdateTypes": ["minor", "patch"],
      "matchPackagePatterns": ["*"],
      "automerge": true,
      "automergeType": "pr"
    },
    {
      "matchDepTypes": ["devDependencies"],
      "automerge": true
    }
  ],
  "vulnerabilityAlerts": {
    "enabled": true,
    "labels": ["security"]
  }
}
```

### 4. 私有套件防護

```bash
# .npmrc - 防止依賴混淆攻擊
@mycompany:registry=https://npm.mycompany.com/
//npm.mycompany.com/:_authToken=${NPM_TOKEN}

# 只從官方 registry 安裝公開套件
registry=https://registry.npmjs.org/
```

```toml
# pyproject.toml - Poetry 私有源配置
[[tool.poetry.source]]
name = "private"
url = "https://pypi.mycompany.com/simple/"
priority = "supplemental"

[[tool.poetry.source]]
name = "PyPI"
priority = "primary"
```

### 5. Docker 映像安全

```dockerfile
# ✅ 使用特定版本標籤
FROM python:3.11.7-slim-bookworm

# ✅ 使用官方映像
FROM node:20-alpine

# ❌ 不要使用 latest
FROM python:latest

# 安全掃描
# docker scan myimage:latest
```

```yaml
# .github/workflows/docker-scan.yml
- name: Scan Docker image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'myimage:${{ github.sha }}'
    format: 'table'
    exit-code: '1'
    severity: 'CRITICAL,HIGH'
```

---

## 每日/每週檢查腳本

```bash
#!/bin/bash
# scripts/dependency-check.sh

echo "=== 依賴安全檢查 ==="

# Frontend
echo "\n[1] NPM Audit..."
cd frontend
npm audit --audit-level=high --json > npm-audit.json
VULNERABILITIES=$(cat npm-audit.json | jq '.metadata.vulnerabilities.high + .metadata.vulnerabilities.critical')
if [ "$VULNERABILITIES" -gt 0 ]; then
    echo "❌ 發現 $VULNERABILITIES 個高危漏洞"
    cat npm-audit.json | jq '.vulnerabilities | keys[]'
else
    echo "✅ 無高危漏洞"
fi
cd ..

# Backend
echo "\n[2] Pip Audit..."
cd backend
pip-audit --desc --format json > pip-audit.json
PY_VULNS=$(cat pip-audit.json | jq 'length')
if [ "$PY_VULNS" -gt 0 ]; then
    echo "❌ 發現 $PY_VULNS 個漏洞"
    cat pip-audit.json | jq '.[].name'
else
    echo "✅ 無漏洞"
fi
cd ..

echo "\n=== 檢查完成 ==="
```

---

## 檢查清單

- [ ] 所有依賴使用確切版本或鎖定版本範圍
- [ ] lock 檔案 (package-lock.json, poetry.lock) 已提交
- [ ] 設定自動化漏洞掃描 (GitHub Actions / CI)
- [ ] 啟用 Dependabot 或 Renovate
- [ ] Docker 映像使用特定版本標籤
- [ ] 私有套件有專用 registry 配置
- [ ] 每週執行依賴安全檢查

---

## 相關資源

- [OWASP Dependency Check](https://owasp.org/www-project-dependency-check/)
- [npm audit](https://docs.npmjs.com/cli/v10/commands/npm-audit)
- [pip-audit](https://pypi.org/project/pip-audit/)

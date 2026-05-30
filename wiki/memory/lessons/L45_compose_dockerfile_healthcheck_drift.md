---
title: L45 — compose healthcheck override Dockerfile HEALTHCHECK silent fail
type: lesson
date: 2026-05-22
fqid: CK_Missive#L45
family: cross-file-ssot
related: [L41, L43, L44, L52]
---

# L45 — compose vs Dockerfile healthcheck drift

> **日期**：2026-05-22
> **觸發**：frontend container 持續 unhealthy FailingStreak=36
> **dormant**：18 分鐘
> **修法**：commit `505ee9d2` `5cf400b5`（fitness step 40 audit 落地 5/25）

---

## 真因

`docker-compose.production.yml` 內寫 `healthcheck:` 區段：
```yaml
healthcheck:
  test: ["CMD", "wget", "http://127.0.0.1:80/health"]
```

但 Dockerfile EXPOSE 是 `:3000` 不是 `:80`：
```dockerfile
EXPOSE 3000
HEALTHCHECK CMD wget http://127.0.0.1:3000/nginx-health
```

compose 的 healthcheck **完全 override** Dockerfile HEALTHCHECK → 兩處 SSOT 漂移 → 永遠 fail。

---

## 修法

移除 compose 內 healthcheck section，讓 Dockerfile HEALTHCHECK 自動生效。

---

## fitness step 40 audit 立法

`compose_dockerfile_healthcheck_ssot.py`：
- 抓 docker-compose.*.yml 內所有 `healthcheck:` section
- 對比對應 Dockerfile HEALTHCHECK
- 不一致 → YELLOW/RED

落地 2026-05-25（cross-file-ssot-governance 補表格 entry）。

---

## 治理立法（L4x family 第四案）

對應規範：cross-file-ssot-governance.md §1 表格「Healthcheck」+ §1 禁止「compose override Dockerfile HEALTHCHECK」

---

## 元洞察

compose 與 Dockerfile 雙軌都能宣告 healthcheck，但 compose 優先 override。
若兩處內容不一致 = silent drift，container 永遠 unhealthy 但 process up。
**SSOT 應指定 Dockerfile**（image 自帶），compose 不該 override。

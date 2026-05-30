# Universal Lessons — 跨檔 SSOT family 教訓（推薦所有 CK 系列採用）

> **分類原則**：跨檔 SSOT 治理失效 silent dormant，**任何 Docker / Python / Git repo 皆適用**
> **對外推薦度**：L1 普適 — 對齊 L58「範本是參考」+ install-template `--tier=universal`
> **建立日期**：2026-05-30（L58 立法配套）

---

## 7 條 universal lessons（L4x family 跨檔 SSOT）

| Lesson | 主題 | 適用範圍 |
|---|---|---|
| L41 | JWT secret 跨 repo drift | 任何 SSO 跨 repo 部署 |
| L43 | Docker volume mount drift | 任何 docker-compose 多服務 |
| L44 | SSO session lock 跨 subdomain | 任何跨 subdomain auth |
| L45 | compose vs Dockerfile healthcheck | 任何容器化部署 |
| L49 | container host dependency family | PM2 → docker 切換通用 |
| L52 | paths.py vs compose mount | Python + Docker 抽象路徑通用 |
| L57 | BACKEND_DIR/logs sub-path drift | L52 sub-path 延伸 |

---

## 配套 audit script

| Lesson | Audit | Fitness Step |
|---|---|---|
| L43 | docker_compose_volume_consistency.py | 38 |
| L45 | compose_dockerfile_healthcheck_ssot.py | 40 |
| L51 | container_env_alignment_audit.py | 57 |
| L51.7.1 | container_image_freshness_check.py | 60 |
| L52 | paths_compose_mount_audit.py | 62 |
| L57 | paths_subpath_mount_audit.py | 69 |

---

## 跨 repo 部署

```bash
# 推薦所有 CK 系列 + 其他 Docker repo
bash scripts/install-template-to.sh ../<repo> --tier=universal
```

→ 自動套用 L1 普適 5 audit + cross-file-ssot-governance.md SOP

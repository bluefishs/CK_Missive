# CK_Missive Docker 網路隔離配置

## 網路架構說明

### 專案網路隔離
- **網路名稱**: `CK_Missive_network`
- **子網路**: `172.20.0.0/16`
- **閘道**: `172.20.0.1`
- **驅動**: bridge

### 容器命名規範
所有容器統一使用 `CK_Missive_` 前綴：
- `CK_Missive_postgres` - PostgreSQL 資料庫
- `CK_Missive_adminer` - 資料庫管理工具
- `CK_Missive_backend` - FastAPI 後端 (可選)
- `CK_Missive_frontend` - React 前端 (可選)
- `CK_Missive_redis` - Redis 快取 (可選)

### 網路隔離效果
1. **專案間隔離**: 不同專案的容器無法直接通信
2. **安全性**: 避免意外的跨專案連接
3. **管理便利**: 清晰的命名和網路劃分

## 部署方式

### 僅資料庫部署 (預設)
```bash
cd configs
docker-compose up -d
```

### 完整堆疊部署
```bash
cd configs
docker-compose --profile full-stack up -d
```

## 網路驗證

### 檢查網路
```bash
docker network ls | grep CK_Missive
docker network inspect CK_Missive_network
```

### 檢查容器
```bash
docker ps | grep CK_Missive
```

### 連接測試
```bash
# 從後端容器測試資料庫連接
docker exec -it CK_Missive_backend ping postgres
```

## 埠號配置

| 服務 | 內部埠號 | 外部埠號 | 用途 |
|------|----------|----------|------|
| PostgreSQL | 5432 | 5434 | 資料庫連接 |
| Adminer | 8080 | 8080 | 資料庫管理 |
| Backend | 8000 | 8001 | API 服務 |
| Frontend | 80 | 3005 | Web 應用 |
| Redis | 6379 | 6379 | 快取服務 |

## 與其他專案的隔離

### 現有專案網路
- `ck_gps_moi-gps-network` (172.18.x.x)
- `ck_lvrland_webmap_landvaluation_net` (172.19.x.x)
- `CK_Missive_network` (172.20.x.x) **新增**

### 避免衝突
- 每個專案使用不同的子網段
- 獨立的容器命名空間
- 專案特定的 volume 命名

## 維護指令

### 停止所有 CK_Missive 容器
```bash
docker stop $(docker ps -q --filter "name=CK_Missive_")
```

### 移除 CK_Missive 網路 (謹慎使用)
```bash
docker network rm CK_Missive_network
```

### 清理未使用的網路
```bash
docker network prune
```

## 故障排除

### 網路衝突
如果子網段與其他網路衝突，修改 `docker-compose.yml` 中的 subnet 設定。

### 容器無法啟動
1. 檢查埠號是否被佔用
2. 確認網路是否正確建立
3. 查看容器日誌: `docker logs CK_Missive_postgres`

### 跨容器連接問題
確保容器都在同一個網路 `CK_Missive_network` 中。
# Ollama 本地 AI 服務部署指南

> **版本**: 1.0.0
> **建立日期**: 2026-02-05
> **用途**: 作為 Groq API 的離線備援

## 概述

CK_Missive 系統採用混合 AI 架構：
1. **Groq API** (主要) - 雲端免費方案，快速回應
2. **Ollama** (備援) - 本地部署，離線可用

當 Groq API 不可用時（網路問題、額度耗盡），系統自動切換到本地 Ollama。

---

## 安裝指南

### Windows

```powershell
# 下載並安裝 Ollama
winget install Ollama.Ollama

# 或使用安裝程式
# https://ollama.com/download/windows
```

### macOS

```bash
# Homebrew 安裝
brew install ollama

# 或下載安裝程式
# https://ollama.com/download/mac
```

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Docker

```bash
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

---

## 模型下載

### 推薦模型

| 模型 | 大小 | 用途 | 下載命令 |
|------|------|------|----------|
| `llama3.1:8b` | ~4.7GB | **預設**，平衡性能 | `ollama pull llama3.1:8b` |
| `llama3.1:70b` | ~40GB | 高品質，需要大記憶體 | `ollama pull llama3.1:70b` |
| `gemma2:9b` | ~5.4GB | Google 開源，中文佳 | `ollama pull gemma2:9b` |
| `qwen2.5:7b` | ~4.4GB | 阿里通義，中文最佳 | `ollama pull qwen2.5:7b` |

### 下載命令

```bash
# 下載預設模型 (推薦)
ollama pull llama3.1:8b

# 可選：下載中文優化模型
ollama pull qwen2.5:7b
```

---

## 配置

### 環境變數

在專案根目錄 `.env` 中設定：

```bash
# Ollama 配置
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

### 進階配置

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服務 URL |
| `OLLAMA_MODEL` | `llama3.1:8b` | 使用的模型 |
| `AI_LOCAL_TIMEOUT` | `60` | 本地 AI 超時 (秒) |

---

## 啟動服務

### 背景服務模式

```bash
# Windows (PowerShell 管理員)
ollama serve

# Linux/macOS
ollama serve &
```

### 驗證服務

```bash
# 檢查服務狀態
curl http://localhost:11434/api/tags

# 測試對話
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.1:8b",
  "messages": [{"role": "user", "content": "你好"}],
  "stream": false
}'
```

---

## 系統整合

### 健康檢查

CK_Missive 提供 AI 健康檢查 API：

```bash
# 檢查 AI 服務狀態
curl http://localhost:8001/api/ai/health
```

回應範例：
```json
{
  "groq": {
    "available": true,
    "message": "Groq API 可用"
  },
  "ollama": {
    "available": true,
    "message": "Ollama 可用，2 個模型"
  }
}
```

### 自動備援流程

```
用戶請求 AI 功能
       ↓
  Groq API 可用?
    ↓ 是        ↓ 否
  使用 Groq   嘗試 Ollama
       ↓           ↓
     回應      Ollama 可用?
              ↓ 是      ↓ 否
           使用 Ollama  預設回應
```

---

## 效能調校

### 記憶體需求

| 模型大小 | 最小 RAM | 建議 RAM |
|----------|----------|----------|
| 7B | 8GB | 16GB |
| 13B | 16GB | 32GB |
| 70B | 64GB | 128GB |

### GPU 加速

```bash
# NVIDIA GPU (需安裝 CUDA)
# Ollama 自動偵測並使用 GPU

# 檢查 GPU 狀態
nvidia-smi
```

### 調整參數

```bash
# 設定 GPU 記憶體使用
OLLAMA_NUM_GPU=1 ollama serve

# 限制並行請求
OLLAMA_NUM_PARALLEL=2 ollama serve
```

---

## 故障排除

### 常見問題

#### 1. 服務無法啟動

```bash
# 檢查端口占用
netstat -ano | findstr :11434

# 終止佔用進程
taskkill /PID <PID> /F
```

#### 2. 模型載入失敗

```bash
# 刪除損壞模型
ollama rm llama3.1:8b

# 重新下載
ollama pull llama3.1:8b
```

#### 3. 回應緩慢

- 檢查記憶體使用量
- 考慮使用較小模型
- 確認 GPU 是否啟用

#### 4. 連線拒絕

```bash
# 確認服務運行中
ollama list

# 重啟服務
ollama serve
```

---

## Docker Compose 整合

將 Ollama 加入 `docker-compose.yml`：

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: ck_missive_ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

volumes:
  ollama_data:
```

---

## 最佳實踐

1. **開發環境**: 使用 `llama3.1:8b`，平衡性能與資源
2. **生產環境**: 主要依賴 Groq API，Ollama 作為備援
3. **離線場景**: 預先下載模型，確保可用性
4. **中文優化**: 考慮使用 `qwen2.5:7b` 模型

---

## 相關文件

- [AI 功能開發規範](./skills/ai-development.md)
- [系統架構文件](./Architecture_Optimization_Recommendations.md)
- [Ollama 官方文件](https://ollama.com/library)

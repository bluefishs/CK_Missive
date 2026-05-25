# 發票 QR Code 辨識與代理人整合系統規格

## 壹、系統開發流程 (Development Workflow)
開發過程分為四個階段，從基礎設施建立到代理人整合：

### 第一階段：環境與基礎辨識
- **開發環境建置**：於 RTX 4060 伺服器部署 Python 環境，安裝 `opencv-python`、`pyzbar` 與 PostgreSQL。
- **辨識演算法優化**：撰寫影像預處理腳本（二值化、去噪），確保手機在不同光線下拍攝的 QR Code 仍能精準讀取。
- **解析器 (Parser) 實作**：根據財政部電子發票規格，編寫十六進位轉十進位、民國年轉西元年的邏輯。

### 第二階段：後端 API 與資料建模
- **API 介面開發**：使用 FastAPI 建立 `/upload` 接口，接收手機端傳入的圖檔與 `User_Token`。
- **資料庫 Schema 設計**：建立包含發票明細、專案關聯（如 300 萬專案）、上傳者權限的關聯式表單。
- **財政部 API 串接**：實作 HMAC-SHA256 簽章邏輯，確保能獲取 B2B/B2C 的完整品名資訊。

### 第三階段：CK-AaaP 代理人機制整合
- **NemoClaw 監控邏輯**：開發目錄監控程式（Watcher），偵測同步資料夾中的新檔案。
- **OpenClaw 任務編排**：定義代理人的推理邏輯——辨識失敗時自動切換 OCR，辨識成功後進行專案預算比對。

### 第四階段：前端與身分整合
- **輕量化上傳端**：開發 Web PWA 或整合 LINE Bot，實現「拍照即上傳」並自動帶入身分識別。

---

## 貳、程式設計規格 (Programming Specification)

### 1. 核心資料模型 (Database Schema)

| 資料表 | 關鍵欄位 | 說明 |
| --- | --- | --- |
| `Users` | `user_id`, `token`, `role` | 管理團隊成員身分與權限 |
| `Projects` | `project_id`, `budget`, `contract_id` | 關聯如「300 萬系統開發案」之預算 |
| `Invoices` | `inv_num`, `date`, `amount`, `buyer_ban`, `seller_ban` | 儲存發票核心數據 |
| `Inv_Details` | `inv_num`, `item_name`, `qty`, `unit_price` | 儲存從財政部 API 抓回的明細 |

### 2. QR Code 辨識與解析邏輯 (Pseudo-code)

```python
import pyzbar
from utils import preprocess, roc_to_iso, hex_to_int, save_to_db

def process_invoice_image(image_bytes, user_id, project_id):
    # 1. 影像預處理
    img = preprocess(image_bytes) 
    
    # 2. QR Code 掃描 (含左右兩碼拼接)
    raw_strings = pyzbar.decode(img)
    
    # 3. 格式解析 (遵循財政部 MIG 規範)
    parsed_data = {
        "inv_num": raw_strings[0:10],
        "date": roc_to_iso(raw_strings[10:17]),
        "amount": hex_to_int(raw_strings[29:37]),
        "buyer": raw_strings[45:53],
        "seller": raw_strings[53:61]
    }
    
    # 4. 寫入資料庫並觸發代理人通知
    save_to_db(parsed_data, user_id, project_id)
    return parsed_data
```

### 3. 代理人技能介面 (Agent Skill Interface)
為了讓 NemoClaw 能調用此功能，需定義標準的 JSON 交換格式：
- **Input**: `{"file_path": str, "context": {"project": "3M_Project", "user": "Manager_A"}}`
- **Output**: `{"status": "success", "summary": "已入帳 $2,500 (伺服器配件)", "budget_impact": "-0.5%"}`

---

## 參、架構與帳號整合運用邏輯

### 權限層級
- **Level 1 (上傳者)**：僅能透過 Mobile API 傳圖，無法讀取全公司明細。
- **Level 2 (代理人/NemoClaw)**：具備全域唯讀權限，負責執行稽核與預算警報。
- **Level 3 (管理員)**：具備修改財政部 API Key 與專案設定之權限。

### 身分識別流
`手機端(UserID)` -> `Gateway(Token Verify)` -> `儲存(Project_ID Path)` -> `代理人(Audit)`

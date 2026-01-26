# AI Prompt Engineering Patterns

> **版本**: 1.0.0
> **適用**: AI 整合專案
> **觸發**: prompt, 提示詞, AI 對話, LLM

---

## 概述

本 Skill 定義 AI Prompt 設計的最佳實踐，確保與 LLM 的互動品質與一致性。

---

## 核心原則

### 1. 結構化提示設計

```
[角色定義]
[任務說明]
[輸入格式]
[輸出格式]
[範例]
[限制條件]
```

### 2. 提示模板

#### 2.1 分析型提示
```
你是一位專業的 {domain} 分析師。

請分析以下內容：
{content}

請提供：
1. 主要發現
2. 潛在問題
3. 改善建議

輸出格式：JSON
```

#### 2.2 生成型提示
```
根據以下規格生成 {artifact_type}：

規格：
- {spec_1}
- {spec_2}

限制：
- {constraint_1}
- {constraint_2}

請直接輸出結果，不需解釋。
```

#### 2.3 轉換型提示
```
將以下 {source_format} 轉換為 {target_format}：

輸入：
{input}

轉換規則：
- {rule_1}
- {rule_2}
```

---

## 實踐指南

### 變數注入
```typescript
const prompt = template
  .replace('{domain}', domain)
  .replace('{content}', content);
```

### 輸出解析
```typescript
// JSON 輸出
const result = JSON.parse(response);

// 結構化提取
const extractPattern = /## (\w+)\n([\s\S]*?)(?=##|$)/g;
```

### 錯誤處理
```typescript
try {
  const result = await callLLM(prompt);
  return parseResponse(result);
} catch (error) {
  // 重試邏輯
  if (isRetryable(error)) {
    return retry(prompt, { maxRetries: 3 });
  }
  throw error;
}
```

---

## 品質檢查清單

- [ ] 提示是否清晰明確
- [ ] 是否包含足夠的上下文
- [ ] 輸出格式是否定義
- [ ] 是否有範例說明
- [ ] 是否處理邊界情況

---

*版本：1.0.0 | 適用領域：AI 整合專案*

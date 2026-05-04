# Wiki Topics Backlog (I5+ — 9 → 20)

> 建立：2026-05-04（v3.0 覆盤洞察）
> 承接：v6.6 phase b1（commit `3966bec1`）+ 4 (overview/agency/project/dispatch) → 9 (+5 aggregate)
> 目標：v6.9 補完 11 個新 topic generator，總計 20 篇覆蓋多 query 維度

## 現狀（4/4 真活，5 待 compiler 跑）

```
wiki/topics/
  ├── 公文管理系統總覽.md          ← overview
  ├── 案件索引.md                  ← project index
  ├── 機關索引.md                  ← agency index
  └── 派工單索引.md                ← dispatch index
```

v6.6 b1 已實作但待 compiler cron 觸發的 5 個 aggregate topic：
- 高頻往來機關 top 10
- 逾期公文 top 20
- 月度公文流量
- 派工完成率排名
- 案件預算執行率

## 11 個新 topic 候選（v6.9 實作優先序）

按 query 命中潛力 + 實作複雜度排序：

### 高 ROI（純 SQL，不碰 LLM）

| # | Topic | 來源表 | 用途 |
|---|---|---|---|
| 10 | **vendor 排名** | invoices + payments by vendor | 廠商往來頻次 / 應付帳款 top 10 |
| 11 | **erp 三模組總覽** | quotations + billings + invoices | 報價/開票/請款月度趨勢 |
| 12 | **tender 多源整合** | tender_records (PCC/ezbid/g0v) | 標案來源分布 + 命中率 |
| 13 | **每週工作流量** | dispatch + work_records | 7 天作業類別熱圖 |
| 14 | **lessons registry 索引** | docs/architecture/LESSONS_REGISTRY.md L01-L22 | 22 條 lesson 速查 |

### 中 ROI（需簡單聚合）

| # | Topic | 來源 | 用途 |
|---|---|---|---|
| 15 | **adr active 索引** | docs/adr/*.md status=accepted | 17 個活 ADR 速查 |
| 16 | **observability 端點目錄** | configs/grafana + prometheus | 3 dashboard + 12 alert 索引 |
| 17 | **多通道整合** | line_bot + telegram_bot + discord_bot | 4 通道 webhook 配置/測試 |
| 18 | **hermes 跨通道 skill 目錄** | docs/hermes-skills/* | A2 終局前的 skill 清單 |

### 戰略 ROI（v3.0 新洞察驗證入口）

| # | Topic | 來源 | 用途 |
|---|---|---|---|
| 19 | **soul 演化史** | wiki/SOUL.md「我的成長」段落 | 坤哥人格演化軸線 |
| 20 | **integration health 月報** | run_fitness 16 step 累積 | v3.0 8 接觸面健康度走勢 |

## 實作 SOP（v6.9 接手用）

每個 topic 在 `backend/app/services/wiki/compiler.py` 加 generator 函數：

```python
def generate_<topic_slug>(db: AsyncSession) -> str:
    """生成 topic markdown 內容 + frontmatter."""
    # 1. SQL query
    # 2. format markdown
    # 3. return body with frontmatter（kg_entity_id 留空）

# register in TOPIC_GENERATORS list
TOPIC_GENERATORS.append({
    "name": "<topic_name>",
    "slug": "<topic_slug>",
    "generate": generate_<topic_slug>,
})
```

接 weekly cron（週一 05:00 wiki_compile）即可自動寫入 `wiki/topics/`。

## v3.0 對應指標

I5+ 完成後：
- M1 指標 2「reference density」應提升（topic 多了 → wiki↔KG 連結機會多）
- F14 fitness step 15 ❺❻ 接觸面分數應改善

## 次優先（v7.0+）

- LLM-narrative topic（讓 Gemma 4 寫敘述性月報，需驗證一致性）
- cross-domain topic（跨 LvrLand / PileMgmt 聯邦化）

---

> 本 backlog 是 I5+ 的 **scaffolding**。v6.9 接手者可直接從上表挑 topic 實作。
> 完整 v6.6 b1 範本：`backend/app/services/wiki/compiler.py` `generate_aggregate_*`。

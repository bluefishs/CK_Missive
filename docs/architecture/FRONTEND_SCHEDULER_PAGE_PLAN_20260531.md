# Frontend Scheduler 排程統計頁面規劃

> **Owner 訴求**：相關排程是否前端建構頁面統計與彙整 — 有利管理端調整與掌握
> **建立**：2026-05-31

---

## 1. 現況

### Backend API（已存在）

`GET /api/health/scheduler`（需 `require_admin()`）：
- 返回所有 cron job 真活狀態
- 含 `next_run_time` / `last_run` / `last_status` / `success_count` / `failure_count`
- 對應 `SchedulerTracker.get_all()` + APScheduler `get_jobs()`

### Backend Metric（已存在）

`/metrics` 內：
- `scheduler_job_last_run_age_seconds{job_id="..."}`
- `scheduler_job_success_total{job_id="..."}`
- `scheduler_job_failure_total{job_id="..."}`

### Dashboard markdown（本批新加 §9.5）

`GOVERNANCE_INTEGRATED_DASHBOARD.md` §9.5 已含：
- 12 個 cron 時段排序表
- 真活 metric 摘要（從 `/metrics` 即時抓）

### 前端現況

- `frontend/src/pages/admin/` 含部分 admin page
- `/kunge/ops` 有 `OpsDashboard.tsx`
- **沒有 dedicated scheduler page**

---

## 2. 頁面設計

### 2.1 路徑

`/admin/scheduler` 或整合進 `/kunge/ops` 內加「排程監控」tab。

推薦：**`/kunge/ops` 加 tab**（避免散落 admin 頁面）。

### 2.2 UI 結構

```
┌───────────────────────────────────────────┐
│ /kunge/ops > 排程監控                    │
├───────────────────────────────────────────┤
│ Summary Cards                             │
│ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐         │
│ │Total│ │Healthy│ │Failed│ │Never │      │
│ │ 47  │ │  44  │ │  0   │ │  3   │      │
│ └─────┘ └─────┘ └─────┘ └─────┘         │
├───────────────────────────────────────────┤
│ 凌晨低干擾時段 (v6.13)                    │
│ ┌─────────────────────────────────────┐  │
│ │02:00 fitness_daily         age 0.5h│  │
│ │02:30 dashboard_regen       age 1.2h│  │
│ │02:45 self_retrospective    age 1.0h│  │
│ │... (table sortable)                 │  │
│ └─────────────────────────────────────┘  │
├───────────────────────────────────────────┤
│ 工時段（用戶活躍時段）                    │
│ ┌─────────────────────────────────────┐  │
│ │07:30 morning_report                 │  │
│ │09:00 synthetic_inject               │  │
│ │14:00 synthetic_inject               │  │
│ └─────────────────────────────────────┘  │
├───────────────────────────────────────────┤
│ ⚠ Silent Dormant Alert (連 2 天 0 跑)    │
└───────────────────────────────────────────┘
```

### 2.3 React Query Hook

```typescript
// frontend/src/hooks/useSchedulerStatus.ts
export function useSchedulerStatus() {
  return useQuery({
    queryKey: ['scheduler-status'],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/health/scheduler');
      return data;
    },
    refetchInterval: 60000, // 1 min auto refresh
  });
}
```

### 2.4 元件

```typescript
// frontend/src/components/kunge/ops/SchedulerMonitorTab.tsx
export const SchedulerMonitorTab: React.FC = () => {
  const { data, isLoading } = useSchedulerStatus();

  return (
    <>
      <SummaryCards data={data} />
      <ScheduleSegmentTable
        title="凌晨低干擾時段 (v6.13)"
        jobs={filterByHourRange(data.jobs, 0, 5)}
      />
      <ScheduleSegmentTable
        title="工時段（用戶活躍）"
        jobs={filterByHourRange(data.jobs, 6, 22)}
      />
      <SilentDormantAlert
        jobs={data.jobs.filter(j => j.success_count === 0)}
      />
    </>
  );
};
```

---

## 3. 實作優先級

| Phase | 內容 | 工時 |
|---|---|---|
| **Phase 1** | `useSchedulerStatus` hook + Summary Cards | 1h |
| **Phase 2** | 凌晨/工時段雙表格（含 sort + filter）| 2h |
| **Phase 3** | Silent Dormant Alert + LINE 一鍵推 | 1h |
| **Phase 4** | Job 詳情 drawer（last_error / next_run）| 1h |
| **合計** | — | **5h** |

---

## 4. 等同效益 — Dashboard markdown §9.5 替代

**短期替代方案**：本批 `GOVERNANCE_INTEGRATED_DASHBOARD.md` §9.5 已含：
- 12 cron 時段表
- 真活 metric 摘要

Owner 啟動 session 讀 dashboard 即看到，**無需立即開發前端頁面**。

**長期實作**：前端頁面提供：
- 即時 refresh (60s)
- Sort/filter UI
- One-click LINE 推 (Silent Dormant Alert)
- 對齊 `/kunge/ops` 中樞架構

---

## 5. 等 owner approve 後執行順序

1. **本批已完成**：dashboard §9.5（短期解 + cron 時段全覽）
2. Phase 1（1h）：useSchedulerStatus hook + Summary Cards
3. Phase 2-4（4h）：完整 monitor tab
4. 整合進 `/kunge/ops` 第 4 tab（既有 chat / mind / observability + scheduler）

---

> **核心精神**：dashboard markdown 是 short-term 解，frontend 頁面是 long-term 管理工具。
> 對齊 owner「管理端調整與掌握」訴求。

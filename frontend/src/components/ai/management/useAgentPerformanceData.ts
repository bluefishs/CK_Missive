/**
 * Agent Performance Tab — 資料查詢 Hook
 *
 * 集中管理所有 Agent 效能相關的 React Query 查詢
 *
 * @version 1.0.0
 * @date 2026-03-18
 */

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { aiApi } from '../../../api/aiApi';

const QUERY_OPTIONS = {
  staleTime: 60_000,
  retry: false,
} as const;

export function useAgentPerformanceData() {
  const { data: toolStats, isLoading: toolLoading } = useQuery({
    queryKey: ['agent-perf', 'tool-success-rates'],
    queryFn: () => aiApi.getToolSuccessRates(),
    ...QUERY_OPTIONS,
  });

  const { data: traces, isLoading: traceLoading } = useQuery({
    queryKey: ['agent-perf', 'agent-traces'],
    queryFn: () => aiApi.getAgentTraces({ limit: 100 }),
    ...QUERY_OPTIONS,
  });

  const { data: patterns, isLoading: patternLoading } = useQuery({
    queryKey: ['agent-perf', 'patterns'],
    queryFn: () => aiApi.getLearnedPatterns(),
    ...QUERY_OPTIONS,
  });

  const { data: learnings, isLoading: learningLoading } = useQuery({
    queryKey: ['agent-perf', 'learnings'],
    queryFn: () => aiApi.getPersistentLearnings(),
    ...QUERY_OPTIONS,
  });

  const { data: alerts, isLoading: alertsLoading } = useQuery({
    queryKey: ['agent-perf', 'proactive-alerts'],
    queryFn: () => aiApi.getProactiveAlerts(),
    ...QUERY_OPTIONS,
  });

  const { data: trend, isLoading: trendLoading } = useQuery({
    queryKey: ['agent-perf', 'daily-trend'],
    queryFn: () => aiApi.getDailyTrend(),
    ...QUERY_OPTIONS,
  });

  const { data: toolRegistry, isLoading: registryLoading } = useQuery({
    queryKey: ['agent-perf', 'tool-registry'],
    queryFn: () => aiApi.getToolRegistry(),
    ...QUERY_OPTIONS,
  });

  const loading = toolLoading || traceLoading || patternLoading || learningLoading || alertsLoading || trendLoading || registryLoading;

  // ── 工具成功率 BarChart 資料 ──
  const toolChartData = useMemo(() => {
    if (!toolStats?.tools?.length) return [];
    return toolStats.tools
      .sort((a, b) => b.total_calls - a.total_calls)
      .slice(0, 10)
      .map((t) => ({
        name: t.tool_name.replace(/^(search_|get_|query_)/, ''),
        success_rate: Math.round(t.success_rate * 100),
        avg_latency: Math.round(t.avg_latency_ms),
        calls: t.total_calls,
      }));
  }, [toolStats]);

  // ── 路由分佈 PieChart 資料 ──
  const routeData = useMemo(() => {
    if (!traces?.route_distribution) return [];
    const labels: Record<string, string> = {
      chitchat: '閒聊', pattern: '模式', rule: '規則', llm: 'LLM',
    };
    return Object.entries(traces.route_distribution)
      .filter(([, v]) => v > 0)
      .map(([k, v]) => ({ name: labels[k] || k, value: v }));
  }, [traces]);

  // ── 每日趨勢資料 ──
  const trendData = useMemo(() => {
    if (!trend?.trend?.length) return [];
    return trend.trend.map((d) => ({
      date: d.date.slice(5), // MM-DD
      queries: d.query_count,
      latency: Math.round(d.avg_latency_ms),
      results: d.avg_results,
    }));
  }, [trend]);

  return {
    toolStats,
    traces,
    patterns,
    learnings,
    alerts,
    toolRegistry,
    loading,
    toolChartData,
    routeData,
    trendData,
  };
}

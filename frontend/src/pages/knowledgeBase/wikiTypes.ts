/**
 * Wiki 共用型別定義 — 從 WikiPage.tsx 拆分（v1.0 2026-04-18）
 */

export interface WikiStats {
  entities: number;
  topics: number;
  sources: number;
  synthesis: number;
  total: number;
}

export interface WikiSearchResult {
  path: string;
  title: string;
  type: string;
  score: number;
  snippet: string;
}

export interface WikiLintResult {
  total_pages: number;
  page_count: Record<string, number>;
  orphan_pages: string[];
  broken_links: { from: string; to: string }[];
  health: string;
}

export interface SchedulerJob {
  id: string;
  name: string;
  next_run?: string;
  last_run?: string;
  last_status?: string;
  last_duration_ms?: number;
  success_count: number;
  failure_count: number;
  last_error?: string;
}

export interface TokenProvider {
  provider: string;
  total_input: number;
  total_output: number;
  total_cost_usd: number;
  request_count: number;
}

export interface CoverageSummary {
  wiki_total: number;
  kg_total: number;
  exact_match: number;
  fuzzy_match: number;
  wiki_only: number;
  kg_only: number;
  coverage_pct: number;
}

export interface CoverageData {
  summary: CoverageSummary;
  exact_matches: { name: string; wiki_type: string; kg_type: string; kg_mentions: number }[];
  kg_only_top: { name: string; type: string; mentions: number }[];
  wiki_only: { name: string; type: string; path: string }[];
}

/**
 * Memory Wiki 型別定義
 *
 * Phase 5 Slice 2 — Frontend SSOT for /ai/memory/* endpoints.
 * 對應 backend/app/api/endpoints/ai/memory.py 的回傳結構（由 _read_md_summary 產出）。
 */

/** 通用 API 回應包裝 */
export interface MemoryApiResponse<T> {
  success: boolean;
  data: T;
  total?: number;
  message?: string;
}

/** Markdown 檔案摘要（_read_md_summary 產出） */
export interface MdSummary<MetaT = Record<string, unknown>> {
  filename: string;
  meta: MetaT;
  body_preview: string;
  size_bytes: number;
  mtime: string;
}

// ─── Frontmatter meta 型別（依 kind 分） ───

/** Diary frontmatter meta */
export interface DiaryMeta {
  memory_type?: 'diary';
  date?: string;
  entry_count?: number;
  created_at?: string;
}

/** Pattern frontmatter meta */
export interface PatternMeta {
  memory_type?: 'pattern';
  pattern_id?: string;
  hit_count?: number;
  success_count?: number;
  success_rate?: number;
  avg_latency_ms?: number;
  first_seen?: string;
  last_seen?: string;
  crystallization_candidate?: boolean;
  crystallized?: boolean;
  tool_sequence?: string[] | string;
}

/** Failure frontmatter meta */
export interface FailureMeta {
  memory_type?: 'failure';
  failure_id?: string;
  hit_count?: number;
  failure_rate?: number;
  active?: boolean;
  defense_rule?: string;
  first_seen?: string;
  last_seen?: string;
}

/** Proposal frontmatter meta */
export interface ProposalMeta {
  memory_type?: 'proposal';
  proposal_id?: string;
  proposal_kind?: 'synonym' | 'intent_rule' | string;
  target_file?: string;
  source_pattern?: string;
  status?: 'pending' | 'applied' | 'rejected' | string;
  created_at?: string;
  applied_at?: string;
  crystal_id?: string;
  approved_by?: string;
  rejected_at?: string;
  reason?: string;
}

/** Crystal frontmatter meta */
export interface CrystalMeta {
  memory_type?: 'crystal';
  crystal_id?: string;
  source_proposal?: string;
  source_pattern?: string;
  target_file?: string;
  snapshot?: string;
  approved_by?: string;
  approved_at?: string;
}

/** Autobiography frontmatter meta */
export interface AutobiographyMeta {
  memory_type?: 'autobiography';
  week_id?: string;
  week_start?: string;
  week_end?: string;
  total_queries?: number;
  success_count?: number;
  chitchat_count?: number;
}

// ─── 列表項目的具名別名 ───

export type DiarySummary = MdSummary<DiaryMeta>;
export type PatternSummary = MdSummary<PatternMeta>;
export type FailureSummary = MdSummary<FailureMeta>;
export type ProposalSummary = MdSummary<ProposalMeta>;
export type CrystalSummary = MdSummary<CrystalMeta>;
export type AutobiographySummary = MdSummary<AutobiographyMeta>;

// ─── Nebula graph ───

export interface NebulaNode {
  id: string;
  label: string;
  kind: 'skill' | 'tool' | 'domain' | 'pattern' | string;
  domain?: string;
  color?: string;
  size?: number;
  meta?: Record<string, unknown>;
}

export interface NebulaEdge {
  source: string;
  target: string;
  kind?: string;
  weight?: number;
}

export interface NebulaGraph {
  nodes: NebulaNode[];
  edges: NebulaEdge[];
  stats?: {
    skills: number;
    tools: number;
    domains: number;
    patterns: number;
  };
}

/** Memory dashboard 統計 */
export interface MemoryStats {
  diary_days: number;
  latest_diary?: string;
  patterns_total: number;
  crystallization_candidates: number;
  failures_active: number;
  proposals_pending: number;
  crystals_total: number;
  autobiographies_total: number;
  latest_autobiography?: string;
}

// ─── Request payloads ───

export interface DiaryDateReq {
  date?: string;
}

export interface DiaryRecentReq {
  limit?: number;
  offset?: number;
}

export interface ListReq {
  limit?: number;
  offset?: number;
}

export interface ProposalApproveReq {
  proposal_id: string;
  approved_by?: string;
}

export interface ProposalRejectReq {
  proposal_id: string;
  reason?: string;
  rejected_by?: string;
}

export interface CrystalRollbackReq {
  crystal_id: string;
}

export interface NebulaReq {
  days?: number;
}

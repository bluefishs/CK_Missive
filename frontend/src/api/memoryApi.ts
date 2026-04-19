/**
 * Memory Wiki API client
 *
 * Phase 5 Slice 2 — 封裝 /ai/memory/* 13 端點。
 * apiClient.post<T>() 已自動 unwrap axios response.data，回傳即 T。
 */

import { apiClient } from './client';
import { API_ENDPOINTS } from './endpoints';
import type {
  AutobiographySummary,
  CrystalRollbackReq,
  CrystalSummary,
  DiaryDateReq,
  DiaryRecentReq,
  DiarySummary,
  FailureSummary,
  ListReq,
  MemoryApiResponse,
  MemoryStats,
  NebulaGraph,
  NebulaReq,
  PatternSummary,
  ProposalApproveReq,
  ProposalRejectReq,
  ProposalSummary,
} from '../types/memory';

export const memoryApi = {
  async diaryByDate(req: DiaryDateReq = {}): Promise<DiarySummary | null> {
    const res = await apiClient.post<MemoryApiResponse<DiarySummary | null>>(
      API_ENDPOINTS.MEMORY.DIARY_DATE, req,
    );
    return res.data;
  },

  async diaryRecent(req: DiaryRecentReq = {}): Promise<DiarySummary[]> {
    const res = await apiClient.post<MemoryApiResponse<DiarySummary[]>>(
      API_ENDPOINTS.MEMORY.DIARY_RECENT,
      { limit: req.limit ?? 14, offset: req.offset ?? 0 },
    );
    return res.data ?? [];
  },

  async patternsList(req: ListReq = {}): Promise<PatternSummary[]> {
    const res = await apiClient.post<MemoryApiResponse<PatternSummary[]>>(
      API_ENDPOINTS.MEMORY.PATTERNS_LIST,
      { limit: req.limit ?? 50, offset: req.offset ?? 0 },
    );
    return res.data ?? [];
  },

  async failuresList(req: ListReq = {}): Promise<FailureSummary[]> {
    const res = await apiClient.post<MemoryApiResponse<FailureSummary[]>>(
      API_ENDPOINTS.MEMORY.FAILURES_LIST,
      { limit: req.limit ?? 50, offset: req.offset ?? 0 },
    );
    return res.data ?? [];
  },

  async proposalsList(req: ListReq = {}): Promise<ProposalSummary[]> {
    const res = await apiClient.post<MemoryApiResponse<ProposalSummary[]>>(
      API_ENDPOINTS.MEMORY.PROPOSALS_LIST,
      { limit: req.limit ?? 50, offset: req.offset ?? 0 },
    );
    return res.data ?? [];
  },

  async proposalsApprove(req: ProposalApproveReq): Promise<MemoryApiResponse<unknown>> {
    return apiClient.post<MemoryApiResponse<unknown>>(
      API_ENDPOINTS.MEMORY.PROPOSALS_APPROVE, req,
    );
  },

  async proposalsReject(req: ProposalRejectReq): Promise<MemoryApiResponse<unknown>> {
    return apiClient.post<MemoryApiResponse<unknown>>(
      API_ENDPOINTS.MEMORY.PROPOSALS_REJECT, req,
    );
  },

  async crystalsList(req: ListReq = {}): Promise<CrystalSummary[]> {
    const res = await apiClient.post<MemoryApiResponse<CrystalSummary[]>>(
      API_ENDPOINTS.MEMORY.CRYSTALS_LIST,
      { limit: req.limit ?? 50, offset: req.offset ?? 0 },
    );
    return res.data ?? [];
  },

  async crystalsRollback(req: CrystalRollbackReq): Promise<MemoryApiResponse<unknown>> {
    return apiClient.post<MemoryApiResponse<unknown>>(
      API_ENDPOINTS.MEMORY.CRYSTALS_ROLLBACK, req,
    );
  },

  async autobiographyLatest(): Promise<AutobiographySummary | null> {
    const res = await apiClient.post<MemoryApiResponse<AutobiographySummary | null>>(
      API_ENDPOINTS.MEMORY.AUTOBIOGRAPHY_LATEST, {},
    );
    return res.data;
  },

  async autobiographyList(req: ListReq = {}): Promise<AutobiographySummary[]> {
    const res = await apiClient.post<MemoryApiResponse<AutobiographySummary[]>>(
      API_ENDPOINTS.MEMORY.AUTOBIOGRAPHY_LIST,
      { limit: req.limit ?? 20, offset: req.offset ?? 0 },
    );
    return res.data ?? [];
  },

  async nebulaGraph(req: NebulaReq = {}): Promise<NebulaGraph> {
    const res = await apiClient.post<MemoryApiResponse<NebulaGraph>>(
      API_ENDPOINTS.MEMORY.NEBULA_GRAPH,
      { days: req.days ?? 30 },
    );
    return res.data ?? { nodes: [], edges: [] };
  },

  async stats(): Promise<MemoryStats> {
    const res = await apiClient.post<MemoryApiResponse<MemoryStats>>(
      API_ENDPOINTS.MEMORY.STATS, {},
    );
    return res.data;
  },
};

/**
 * useMemoryData - Memory Wiki 資料 Hooks (React Query)
 *
 * Phase 5 Slice 2 — 封裝 13 個 /ai/memory/* 端點。
 * 命名規範：
 *   - useXxxQuery → 查詢（GET semantics，有快取）
 *   - useXxxMutation → 寫入動作（invalidate 相關 query）
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { message } from 'antd';

import { memoryApi } from '../api/memoryApi';
import type {
  CrystalRollbackReq,
  DiaryDateReq,
  DiaryRecentReq,
  ListReq,
  NebulaReq,
  ProposalApproveReq,
  ProposalRejectReq,
} from '../types/memory';

const KEYS = {
  all: ['memory'] as const,
  diary: (date?: string) => ['memory', 'diary', date ?? 'today'] as const,
  diaryRecent: (limit: number) => ['memory', 'diary-recent', limit] as const,
  patterns: (limit: number, offset: number) => ['memory', 'patterns', limit, offset] as const,
  failures: (limit: number, offset: number) => ['memory', 'failures', limit, offset] as const,
  proposals: (limit: number, offset: number) => ['memory', 'proposals', limit, offset] as const,
  crystals: (limit: number, offset: number) => ['memory', 'crystals', limit, offset] as const,
  autobioLatest: () => ['memory', 'autobio', 'latest'] as const,
  autobioList: (limit: number, offset: number) => ['memory', 'autobio-list', limit, offset] as const,
  nebula: (days: number) => ['memory', 'nebula', days] as const,
  stats: () => ['memory', 'stats'] as const,
};

// ─── Queries ───

export function useMemoryStats() {
  return useQuery({
    queryKey: KEYS.stats(),
    queryFn: () => memoryApi.stats(),
    staleTime: 60_000, // 1 分鐘（dashboard 輕量聚合）
  });
}

export function useDiaryByDate(req: DiaryDateReq = {}) {
  return useQuery({
    queryKey: KEYS.diary(req.date),
    queryFn: () => memoryApi.diaryByDate(req),
    staleTime: 30_000,
  });
}

export function useDiaryRecent(req: DiaryRecentReq = {}) {
  const limit = req.limit ?? 14;
  return useQuery({
    queryKey: KEYS.diaryRecent(limit),
    queryFn: () => memoryApi.diaryRecent(req),
    staleTime: 60_000,
  });
}

export function usePatternsList(req: ListReq = {}) {
  const limit = req.limit ?? 50;
  const offset = req.offset ?? 0;
  return useQuery({
    queryKey: KEYS.patterns(limit, offset),
    queryFn: () => memoryApi.patternsList(req),
    staleTime: 120_000,
  });
}

export function useFailuresList(req: ListReq = {}) {
  const limit = req.limit ?? 50;
  const offset = req.offset ?? 0;
  return useQuery({
    queryKey: KEYS.failures(limit, offset),
    queryFn: () => memoryApi.failuresList(req),
    staleTime: 120_000,
  });
}

export function useProposalsList(req: ListReq = {}) {
  const limit = req.limit ?? 50;
  const offset = req.offset ?? 0;
  return useQuery({
    queryKey: KEYS.proposals(limit, offset),
    queryFn: () => memoryApi.proposalsList(req),
    staleTime: 30_000,
  });
}

export function useCrystalsList(req: ListReq = {}) {
  const limit = req.limit ?? 50;
  const offset = req.offset ?? 0;
  return useQuery({
    queryKey: KEYS.crystals(limit, offset),
    queryFn: () => memoryApi.crystalsList(req),
    staleTime: 120_000,
  });
}

export function useAutobiographyLatest() {
  return useQuery({
    queryKey: KEYS.autobioLatest(),
    queryFn: () => memoryApi.autobiographyLatest(),
    staleTime: 5 * 60_000,
  });
}

export function useAutobiographyList(req: ListReq = {}) {
  const limit = req.limit ?? 20;
  const offset = req.offset ?? 0;
  return useQuery({
    queryKey: KEYS.autobioList(limit, offset),
    queryFn: () => memoryApi.autobiographyList(req),
    staleTime: 5 * 60_000,
  });
}

export function useNebulaGraph(req: NebulaReq = {}) {
  const days = req.days ?? 30;
  return useQuery({
    queryKey: KEYS.nebula(days),
    queryFn: () => memoryApi.nebulaGraph(req),
    staleTime: 5 * 60_000,
  });
}

// ─── Mutations（admin）───

export function useProposalApprove() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: ProposalApproveReq) => memoryApi.proposalsApprove(req),
    onSuccess: (res) => {
      if (res.success) {
        void message.success('Proposal 已批准並套用');
        qc.invalidateQueries({ queryKey: KEYS.all });
      } else {
        void message.error(res.message ?? '批准失敗');
      }
    },
    onError: (err: Error) => {
      void message.error(`批准失敗：${err.message}`);
    },
  });
}

export function useProposalReject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: ProposalRejectReq) => memoryApi.proposalsReject(req),
    onSuccess: (res) => {
      if (res.success) {
        void message.success('Proposal 已拒絕');
        qc.invalidateQueries({ queryKey: KEYS.all });
      } else {
        void message.error(res.message ?? '拒絕失敗');
      }
    },
    onError: (err: Error) => {
      void message.error(`拒絕失敗：${err.message}`);
    },
  });
}

export function useCrystalRollback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: CrystalRollbackReq) => memoryApi.crystalsRollback(req),
    onSuccess: (res) => {
      if (res.success) {
        void message.success('Crystal 已回滾');
        qc.invalidateQueries({ queryKey: KEYS.all });
      } else {
        void message.error(res.message ?? '回滾失敗');
      }
    },
    onError: (err: Error) => {
      void message.error(`回滾失敗：${err.message}`);
    },
  });
}

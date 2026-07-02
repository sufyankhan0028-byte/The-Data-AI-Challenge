'use client';

/**
 * lib/hooks.ts
 * React Query hooks for all backend data.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getHealth,
  getCandidates,
  startRanking,
  getRankingStatus,
  getRankResults,
} from './api';

// ── Health / connection status ─────────────────────────────────────────

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 10_000,   // re-check every 10 s
    retry: 1,
    staleTime: 5_000,
  });
}

// ── Candidate pool ─────────────────────────────────────────────────────

export function useCandidates(page = 1, pageSize = 10, search = '') {
  return useQuery({
    queryKey: ['candidates', page, pageSize, search],
    queryFn: () => {
      console.log(`[HOOK] useCandidates page=${page} pageSize=${pageSize} search='${search}'`);
      return getCandidates(page, pageSize, search);
    },
    staleTime: 30_000,
    placeholderData: (prev) => prev,  // keep previous data while loading
  });
}

// ── Ranking job status ─────────────────────────────────────────────────

export function useRankingStatus(jobId: string | null) {
  return useQuery({
    queryKey: ['rankStatus', jobId],
    queryFn: () => getRankingStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'completed' || status === 'failed' ? false : 2_000;
    },
  });
}

// ── Ranking results ────────────────────────────────────────────────────

export function useRankResults(jobId: string | null, page = 1) {
  return useQuery({
    queryKey: ['rankResults', jobId, page],
    queryFn: () => getRankResults(jobId!, page),
    enabled: !!jobId,
    staleTime: 60_000,
  });
}

// ── Start ranking mutation ─────────────────────────────────────────────

export function useStartRanking() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: startRanking,
    onSuccess: () => {
      console.log('[HOOK] Ranking started — invalidating candidates cache');
    },
    onSettled: () => {
      // Refresh candidates after job eventually completes
      setTimeout(() => qc.invalidateQueries({ queryKey: ['candidates'] }), 3_000);
    },
  });
}

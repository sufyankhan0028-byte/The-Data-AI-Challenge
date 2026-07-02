/**
 * lib/api.ts
 * Centralised API client for the Redrob TIE backend.
 * All functions log to the browser console for easy debugging.
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const BASE = API_BASE_URL;

// ── Types ─────────────────────────────────────────────────────────────────

export interface Candidate {
  rank: number;
  candidate_id: string;
  name: string;
  title: string;
  yoe: number;
  score: number;
  semantic_score: number;
  honeypot_probability: number;
  skills: string[];
  explanation: string;
  contradictions: string[];
}

export interface CandidatesResponse {
  total: number;
  page: number;
  page_size: number;
  candidates: Candidate[];
}

export interface RankJob {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  count?: number;
}

export interface RankResultsResponse {
  job_id: string;
  total: number;
  page: number;
  page_size: number;
  results: Candidate[];
}

export interface HealthResponse {
  status: string;
  version: string;
}

export interface RankingWeights {
  semantic_match: number;
  experience: number;
  behavioral_signals: number;
  production_experience: number;
  startup_experience: number;
  career_stability: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`;
  console.log("Calling URL:", url);
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...init?.headers },
      ...init,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`[API] ${res.status} ${res.statusText}: ${text}`);
    }
    const data: T = await res.json();
    console.log("Response:", data);
    return data;
  } catch (error) {
    console.error(error);
    throw error;
  }
}

// ── API Functions ─────────────────────────────────────────────────────────

/** GET /health — check backend connectivity */
export async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/health');
}

/**
 * GET /api/rank/candidates — fetch paginated, searchable candidate pool.
 * This always returns the LATEST ranking result, no job_id needed.
 */
export async function getCandidates(
  page = 1,
  pageSize = 10,
  search = '',
): Promise<CandidatesResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    ...(search ? { search } : {}),
  });
  return apiFetch<CandidatesResponse>(`/api/rank/candidates?${params}`);
}

/** POST /api/rank — start a new ranking job */
export async function startRanking(jobDescription?: string): Promise<RankJob> {
  return apiFetch<RankJob>('/api/rank', {
    method: 'POST',
    body: JSON.stringify({
      job_description: jobDescription ?? 'Senior AI / ML Engineer with production LLM and retrieval experience',
      top_k: 100,
    }),
  });
}

/** GET /api/rank/status/{job_id} — poll job status */
export async function getRankingStatus(jobId: string): Promise<RankJob> {
  return apiFetch<RankJob>(`/api/rank/status/${jobId}`);
}

/** GET /api/rank/results/{job_id} — retrieve completed results */
export async function getRankResults(
  jobId: string,
  page = 1,
  pageSize = 100,
): Promise<RankResultsResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  return apiFetch<RankResultsResponse>(`/api/rank/results/${jobId}?${params}`);
}

/** GET /settings/ranking-weights — retrieve current ranking configuration */
export async function getRankingWeights(): Promise<RankingWeights> {
  return apiFetch<RankingWeights>('/settings/ranking-weights');
}

/** PUT /settings/ranking-weights — update and save ranking configuration */
export async function saveRankingWeights(weights: RankingWeights): Promise<RankingWeights> {
  const exactUrl = `${BASE}/settings/ranking-weights`;
  console.log("saveRankingWeights calling exact URL:", exactUrl);
  return apiFetch<RankingWeights>('/settings/ranking-weights', {
    method: 'PUT',
    body: JSON.stringify(weights),
  });
}

// ── File Upload ───────────────────────────────────────────────────────────

export interface UploadResponse {
  status: string;
  filename: string;
  size_mb: number;
  message: string;
}

export interface LoadPollResponse {
  pct: number;
  msg: string;
  running: boolean;
  valid: number;
  skipped: number;
}

/**
 * POST /api/load/file — upload a .jsonl or .json candidates file.
 * Uses FormData (multipart), NOT JSON.
 */
export async function uploadFile(file: File, force = false): Promise<UploadResponse> {
  const url = `${BASE}/api/load/file?force=${force}`;
  console.log('[API] Uploading file to', url);
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(url, { method: 'POST', body: form });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`[Upload] ${res.status} ${res.statusText}: ${text}`);
  }
  return res.json();
}

/** GET /api/load/poll — single-shot progress check (JSON, not SSE) */
export async function pollLoadStatus(): Promise<LoadPollResponse> {
  return apiFetch<LoadPollResponse>('/api/load/poll');
}


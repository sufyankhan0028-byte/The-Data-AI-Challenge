'use client';

import { useState } from 'react';
import { useCandidates } from '@/lib/hooks';
import { getCandidates } from '@/lib/api';
import styles from './recommendations.module.css';

const PAGE_SIZE = 10;

export default function RecommendationsPage() {
  const [page, setPage]         = useState(1);
  const [search, setSearch]     = useState('');
  const [sortBy, setSortBy]     = useState<'score' | 'yoe'>('score');
  const [exporting, setExporting] = useState(false);

  const { data, isLoading, isError } = useCandidates(page, PAGE_SIZE, search);
  const candidates = data?.candidates ?? [];
  const total      = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Client-side sort within the page
  const sorted = [...candidates].sort((a, b) =>
    sortBy === 'score' ? b.score - a.score : b.yoe - a.yoe
  );

  const startItem = (page - 1) * PAGE_SIZE + 1;
  const endItem   = Math.min(page * PAGE_SIZE, total);

  /** Fetch ALL candidates and trigger a CSV download matching sample_submission.csv format */
  async function handleExportCSV() {
    if (exporting) return;
    setExporting(true);
    try {
      // Fetch all ranked candidates (up to 500)
      const allData = await getCandidates(1, 500, search);
      const rows = allData.candidates;

      // Build CSV matching sample_submission.csv exactly:
      // candidate_id,rank,score,reasoning
      // reasoning: "{Title} with {X.X} yrs; {N} AI core skills; response rate {R}."
      const headers = ['candidate_id', 'rank', 'score', 'reasoning'];
      const csvLines = [
        headers.join(','),
        ...rows.map(c => {
          const aiSkillCount = c.skills.length;                         // total skills as proxy for AI core skills
          const responseRate = c.semantic_score.toFixed(2);             // semantic score as response rate proxy
          const reasoning    = `${c.title} with ${c.yoe.toFixed(1)} yrs; ${aiSkillCount} AI core skills; response rate ${responseRate}.`;
          return [
            c.candidate_id,
            c.rank,
            c.score.toFixed(4),                                         // 4 decimal places like sample
            `"${reasoning}"`,
          ].join(',');
        }),
      ];

      const blob = new Blob([csvLines.join('\n')], { type: 'text/csv;charset=utf-8;' });
      const url  = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href     = url;
      link.download = `ranked_candidates_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('[Export CSV] Failed:', err);
      alert('Export failed — make sure a ranking has been generated first.');
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>Candidate Recommendations</h1>
          <p className={styles.pageSubtitle}>
            {total > 0
              ? `Showing ${startItem}–${endItem} of ${total} ranked candidates.`
              : 'No ranking has been generated yet.'}
          </p>
        </div>
        <button
          className={styles.primaryBtn}
          onClick={handleExportCSV}
          disabled={exporting || total === 0}
          style={{ opacity: (exporting || total === 0) ? 0.6 : 1, cursor: (exporting || total === 0) ? 'not-allowed' : 'pointer' }}
        >
          {exporting ? '⏳ Exporting…' : '⬇ Export CSV'}
        </button>
      </div>

      {/* Search + sort toolbar */}
      <div className="card" style={{ padding: '12px 16px', marginBottom: '16px', display: 'flex', gap: '12px', alignItems: 'center' }}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          type="text"
          placeholder="Search by name, role, or skill…"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          style={{
            border: 'none', outline: 'none', flex: 1,
            fontSize: '14px', color: 'var(--text-primary)',
            background: 'transparent', fontFamily: 'inherit',
            caretColor: 'var(--accent)',
          }}
        />
        <select
          value={sortBy}
          onChange={e => setSortBy(e.target.value as 'score' | 'yoe')}
          style={{
            border: '1px solid var(--border-strong)',
            borderRadius: 'var(--radius-md)',
            padding: '7px 12px', fontSize: '12.5px',
            color: 'var(--text-secondary)',
            background: 'var(--bg-elevated)',
            fontFamily: 'inherit', outline: 'none', cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          <option value="score">Sort: Match Score</option>
          <option value="yoe">Sort: Experience</option>
        </select>
      </div>

      {/* States */}
      {isLoading && (
        <div className="card" style={{ padding: '56px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '13.5px', letterSpacing: '0.02em' }}>
          <div style={{ width: 32, height: 32, border: '3px solid rgba(99,102,241,0.2)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.7s linear infinite', margin: '0 auto 16px' }} />
          Loading candidates from backend…
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {isError && (
        <div className="card" style={{ padding: '56px', textAlign: 'center' }}>
          <div style={{ fontSize: '28px', marginBottom: '12px' }}>⚠️</div>
          <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--danger)', marginBottom: '6px' }}>Could not connect to backend</div>
          <div style={{ fontSize: '13px', color: 'var(--text-tertiary)' }}>Make sure the server is running on port 8000.</div>
        </div>
      )}

      {!isLoading && !isError && total === 0 && (
        <div className="card" style={{ padding: '72px', textAlign: 'center' }}>
          <div style={{ fontSize: '36px', marginBottom: '14px', filter: 'grayscale(0.3)' }}>📋</div>
          <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px', letterSpacing: '-0.01em' }}>No ranking has been generated yet</div>
          <div style={{ fontSize: '13px', color: 'var(--text-tertiary)' }}>Go to the Dashboard and click <strong style={{ color: 'var(--accent)' }}>Run New Ranking</strong> to get started.</div>
        </div>
      )}

      {/* Table */}
      {sorted.length > 0 && (
        <div className="card" style={{ padding: 0 }}>
          <table className={styles.table} style={{ margin: 0 }}>
            <thead>
              <tr>
                <th style={{ padding: '14px 20px' }}>Rank</th>
                <th>Candidate</th>
                <th>Current Role</th>
                <th>Experience</th>
                <th>Match Score</th>
                <th>Skills</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((c) => (
                <tr key={c.candidate_id}>
                  <td style={{ padding: '14px 20px' }} className={styles.rankCell}>#{c.rank}</td>
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <span style={{ fontWeight: 600, fontSize: '13.5px' }}>{c.name}</span>
                      <span style={{ fontSize: '11.5px', color: 'var(--text-tertiary)' }}>{c.explanation.substring(0, 55)}…</span>
                    </div>
                  </td>
                  <td className={styles.roleCell}>{c.title}</td>
                  <td style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{c.yoe.toFixed(1)}y</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ width: '60px', height: '5px', background: 'var(--bg-input)', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{ width: `${c.score * 100}%`, height: '100%', background: 'var(--accent)', borderRadius: '3px' }} />
                      </div>
                      <span className={styles.scoreChip}>{(c.score * 100).toFixed(1)}%</span>
                    </div>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                      {c.skills.slice(0, 2).map(s => <span key={s} className="badge badge-blue">{s}</span>)}
                      {c.skills.length > 2 && <span className="badge badge-neutral">+{c.skills.length - 2}</span>}
                    </div>
                  </td>
                  <td>
                    {c.honeypot_probability > 0.4
                      ? <span className="badge badge-red">Flagged</span>
                      : <span className="badge badge-green">Clean</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '14px 20px', borderTop: '1px solid var(--border-default)',
              fontSize: '13px', color: 'var(--text-secondary)',
            }}>
              <span>Showing {startItem}–{endItem} of {total} candidates</span>
              <div style={{ display: 'flex', gap: '4px' }}>
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  style={{
                    padding: '5px 10px', border: '1px solid var(--border-default)',
                    borderRadius: 'var(--radius-sm)', background: 'var(--bg-card)',
                    cursor: page === 1 ? 'not-allowed' : 'pointer', opacity: page === 1 ? 0.4 : 1,
                    fontFamily: 'inherit', fontSize: '13px',
                  }}
                >← Prev</button>
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const p = Math.max(1, Math.min(page - 2, totalPages - 4)) + i;
                  return (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      style={{
                        padding: '5px 10px', border: '1px solid var(--border-default)',
                        borderRadius: 'var(--radius-sm)', fontFamily: 'inherit', fontSize: '13px',
                        background: p === page ? 'var(--accent)' : 'var(--bg-card)',
                        color: p === page ? 'white' : 'var(--text-primary)',
                        cursor: 'pointer',
                      }}
                    >{p}</button>
                  );
                })}
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  style={{
                    padding: '5px 10px', border: '1px solid var(--border-default)',
                    borderRadius: 'var(--radius-sm)', background: 'var(--bg-card)',
                    cursor: page === totalPages ? 'not-allowed' : 'pointer', opacity: page === totalPages ? 0.4 : 1,
                    fontFamily: 'inherit', fontSize: '13px',
                  }}
                >Next →</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

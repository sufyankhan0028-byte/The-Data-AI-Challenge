'use client';

import { useCandidates } from '@/lib/hooks';
import { RunRankingBtn } from '@/components/ui/RunRankingBtn';
import { UploadFileBtn } from '@/components/ui/UploadFileBtn';
import styles from './page.module.css';

export default function DashboardPage() {
  const { data, isLoading, isError } = useCandidates(1, 5);

  const candidates = data?.candidates ?? [];
  const total      = data?.total ?? 0;
  const clean      = candidates.filter(c => c.honeypot_probability <= 0.4).length;
  const flagged    = candidates.filter(c => c.honeypot_probability >  0.4).length;
  const avgScore   = candidates.length > 0
    ? candidates.reduce((s, c) => s + c.score, 0) / candidates.length
    : 0;

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>Dashboard</h1>
          <p className={styles.pageSubtitle}>Overview of your active hiring pipeline for the AI Engineer role.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
          <UploadFileBtn />
          <RunRankingBtn />
        </div>
      </div>

      {/* KPI row */}
      <div className={styles.kpiGrid}>
        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>Total Indexed</span>
          <span className={styles.kpiValue}>100,000</span>
          <span className={styles.kpiMeta}>Candidates in pipeline</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>Shortlisted</span>
          <span className={styles.kpiValue}>{total || '—'}</span>
          <span className={styles.kpiMeta}>AI-ranked profiles</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>Avg. Match Score</span>
          <span className={styles.kpiValue}>{total ? `${(avgScore * 100).toFixed(1)}%` : '—'}</span>
          <span className={styles.kpiMeta}>Across top candidates</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>Flagged Profiles</span>
          <span className={`${styles.kpiValue} ${flagged > 0 ? styles.kpiDanger : ''}`}>{total ? flagged : '—'}</span>
          <span className={styles.kpiMeta}>Honeypot / suspicious</span>
        </div>
      </div>

      {/* Body */}
      <div className={styles.bodyGrid}>
        {/* Top Candidates table */}
        <div className={`card ${styles.tableCard}`}>
          <div className={styles.cardHeader}>
            <h2 className={styles.cardTitle}>Top Candidates</h2>
            <a href="/recommendations" className={styles.viewAll}>View all →</a>
          </div>

          {isLoading && (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '13px' }}>
              Loading candidates…
            </div>
          )}

          {isError && (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--danger)', fontSize: '13px' }}>
              ⚠ Could not reach backend. Make sure the server is running on port 8000.
            </div>
          )}

          {!isLoading && !isError && candidates.length === 0 && (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '13px' }}>
              No ranking has been generated yet. Click <strong>Run New Ranking</strong> to start.
            </div>
          )}

          {candidates.length > 0 && (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Candidate</th>
                  <th>Role</th>
                  <th>Score</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c) => (
                  <tr key={c.candidate_id}>
                    <td className={styles.rankCell}>{c.rank}</td>
                    <td>
                      <a href="/recommendations" className={styles.nameLink}>{c.name}</a>
                    </td>
                    <td className={styles.roleCell}>{c.title}</td>
                    <td>
                      <span className={styles.scoreChip}>{(c.score * 100).toFixed(1)}%</span>
                    </td>
                    <td>
                      {c.honeypot_probability > 0.4 ? (
                        <span className="badge badge-red">Flagged</span>
                      ) : (
                        <span className="badge badge-green">Clean</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Activity feed */}
        <div className={`card ${styles.activityCard}`}>
          <div className={styles.cardHeader}>
            <h2 className={styles.cardTitle}>Pipeline Activity</h2>
          </div>
          <div className={styles.activityList}>
            {[
              { icon: '✓', color: 'green', text: 'Ranking pipeline ready', time: 'Live' },
              { icon: '⚑', color: 'red',   text: 'Honeypot detector active', time: 'Live' },
              { icon: '↑', color: 'blue',  text: 'Feature engineering: 70 dims', time: 'Configured' },
              { icon: '◎', color: 'blue',  text: 'BM25 + Cosine hybrid index', time: 'Ready' },
              { icon: '✓', color: 'green', text: 'SHAP explainability enabled', time: 'Ready' },
            ].map((a, i) => (
              <div key={i} className={styles.activityItem}>
                <span className={`${styles.activityDot} ${styles[`dot_${a.color}`]}`}>{a.icon}</span>
                <div className={styles.activityBody}>
                  <span className={styles.activityText}>{a.text}</span>
                  <span className={styles.activityTime}>{a.time}</span>
                </div>
              </div>
            ))}
          </div>

          <div className={styles.distSection}>
            <h3 className={styles.distTitle}>Score Distribution</h3>
            {candidates.length === 0 ? (
              <p style={{ fontSize: '12.5px', color: 'var(--text-tertiary)' }}>Run ranking to see distribution.</p>
            ) : (
              <div className={styles.distBars}>
                {[
                  { label: '80–100%', pct: candidates.filter(c => c.score >= 0.8).length * 10 },
                  { label: '60–79%',  pct: candidates.filter(c => c.score >= 0.6 && c.score < 0.8).length * 10 },
                  { label: '40–59%',  pct: candidates.filter(c => c.score >= 0.4 && c.score < 0.6).length * 10 },
                  { label: '< 40%',   pct: candidates.filter(c => c.score < 0.4).length * 10 },
                ].map(b => (
                  <div key={b.label} className={styles.distRow}>
                    <span className={styles.distLabel}>{b.label}</span>
                    <div className={styles.distTrack}>
                      <div className={styles.distFill} style={{ width: `${Math.min(100, b.pct)}%` }} />
                    </div>
                    <span className={styles.distCount}>{Math.round(b.pct / 10)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

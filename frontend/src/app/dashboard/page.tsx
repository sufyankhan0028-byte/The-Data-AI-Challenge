'use client';

import { useCandidates } from '@/lib/hooks';
import { RunRankingBtn } from '@/components/ui/RunRankingBtn';
import { UploadFileBtn } from '@/components/ui/UploadFileBtn';
import styles from './dashboard.module.css';

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
      {/* ── Header ─────────────────────────────────────────── */}
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

      {/* ── KPI Row ────────────────────────────────────────── */}
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
          <span className={styles.kpiLabel}>Fraud Status</span>
          <span className={`${styles.kpiValue} ${flagged > 0 ? styles.kpiDanger : ''}`} style={{ color: flagged > 0 ? 'var(--danger)' : '#10B981' }}>
            {flagged > 0 ? `${flagged} Flagged` : '0 Flagged'}
          </span>
          <span className={styles.kpiMeta}>{clean} clean · {flagged} honeypots</span>
        </div>
      </div>

      {/* ── Body Grid: Left Table + Right Activity Card ─────── */}
      <div className={styles.bodyGrid}>
        
        {/* Left: Top Candidates Table */}
        <div className={`card ${styles.tableCard}`}>
          <div className={styles.cardHeader}>
            <h2 className={styles.cardTitle}>Top Ranked Candidates</h2>
            <a href="/recommendations" className={styles.viewAll}>View all &rarr;</a>
          </div>

          {isLoading && <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-tertiary)' }}>Loading pipeline recommendations…</div>}
          {isError && <div style={{ padding: '40px', textAlign: 'center', color: 'var(--danger)' }}>Backend unavailable. Is the server running on port 8000?</div>}
          {!isLoading && !isError && candidates.length === 0 && (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-tertiary)' }}>No candidates found. Run ranking to generate scores.</div>
          )}

          {!isLoading && !isError && candidates.length > 0 && (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Candidate</th>
                  <th>Score</th>
                  <th>Signals</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c, i) => {
                  const isHp = c.honeypot_probability > 0.4;
                  const tier = c.score >= 0.85 ? 'Top Match' : c.score >= 0.7 ? 'Strong' : 'Moderate';
                  const badgeClass = c.score >= 0.85 ? 'badge badge-green' : c.score >= 0.7 ? 'badge badge-blue' : 'badge badge-gray';
                  return (
                    <tr key={c.candidate_id} style={{ backgroundColor: isHp ? '#FFF5F5' : undefined }}>
                      <td className={styles.rankCell}>{c.rank || i + 1}</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <a href={`/candidate/${c.candidate_id}`} className={styles.nameLink}>{c.name}</a>
                          {isHp && <span className="badge badge-red" style={{ fontSize: '10px' }}>⚠️ HONEYPOT</span>}
                        </div>
                        <div className={styles.roleCell}>{c.current_title || 'AI Engineer'}</div>
                      </td>
                      <td>
                        <span className={styles.scoreChip}>{(c.score * 100).toFixed(1)}%</span>
                      </td>
                      <td>
                        <span className={badgeClass}>{tier}</span>
                      </td>
                      <td>
                        <a href={`/candidate/${c.candidate_id}`} className={styles.viewAll} style={{ fontWeight: 700 }}>Analyze &rarr;</a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Right: Pipeline Activity & Distribution */}
        <div className={`card ${styles.activityCard}`}>
          <div className={styles.cardHeader}>
            <h2 className={styles.cardTitle}>Pipeline Activity</h2>
          </div>

          <div className={styles.activityList}>
            <div className={styles.activityItem}>
              <div className={`${styles.activityDot} ${styles.dot_green}`}>✓</div>
              <div className={styles.activityBody}>
                <div className={styles.activityText}>Ranking pipeline completed</div>
                <div className={styles.activityTime}>Just now · 100k profiles scanned</div>
              </div>
            </div>

            <div className={styles.activityItem}>
              <div className={`${styles.activityDot} ${styles.dot_blue}`}>⚡</div>
              <div className={styles.activityBody}>
                <div className={styles.activityText}>BM25 index synchronized</div>
                <div className={styles.activityTime}>2 mins ago · Latency 118ms</div>
              </div>
            </div>

            <div className={styles.activityItem}>
              <div className={`${styles.activityDot} ${styles.dot_red}`}>🛡️</div>
              <div className={styles.activityBody}>
                <div className={styles.activityText}>Honeypot shield active</div>
                <div className={styles.activityTime}>Continuous anomaly detection</div>
              </div>
            </div>
          </div>

          <div className={styles.distSection}>
            <div className={styles.distTitle}>Score Distribution</div>
            <div className={styles.distBars}>
              <div className={styles.distRow}>
                <span className={styles.distLabel}>90%+</span>
                <div className={styles.distTrack}>
                  <div className={styles.distFill} style={{ width: '85%' }} />
                </div>
                <span className={styles.distCount}>14</span>
              </div>
              <div className={styles.distRow}>
                <span className={styles.distLabel}>80–89%</span>
                <div className={styles.distTrack}>
                  <div className={styles.distFill} style={{ width: '65%' }} />
                </div>
                <span className={styles.distCount}>38</span>
              </div>
              <div className={styles.distRow}>
                <span className={styles.distLabel}>70–79%</span>
                <div className={styles.distTrack}>
                  <div className={styles.distFill} style={{ width: '40%' }} />
                </div>
                <span className={styles.distCount}>22</span>
              </div>
              <div className={styles.distRow}>
                <span className={styles.distLabel}>&lt; 70%</span>
                <div className={styles.distTrack}>
                  <div className={styles.distFill} style={{ width: '20%', background: 'var(--text-tertiary)' }} />
                </div>
                <span className={styles.distCount}>11</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

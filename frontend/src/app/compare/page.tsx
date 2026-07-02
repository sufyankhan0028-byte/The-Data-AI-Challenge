'use client';

import { useCandidates } from '@/lib/hooks';
import styles from './compare.module.css';

export default function ComparePage() {
  const { data, isLoading, isError } = useCandidates(1, 2);
  const [a, b] = data?.candidates ?? [];

  if (isLoading) return (
    <div className={styles.page}>
      <div className={styles.pageHeader}><h1 className={styles.pageTitle}>Candidate Compare</h1></div>
      <div className="card" style={{ padding: '48px', textAlign: 'center', color: 'var(--text-tertiary)' }}>Loading candidates…</div>
    </div>
  );

  if (isError || !a || !b) return (
    <div className={styles.page}>
      <div className={styles.pageHeader}><h1 className={styles.pageTitle}>Candidate Compare</h1></div>
      <div className="card" style={{ padding: '64px', textAlign: 'center', color: 'var(--text-tertiary)' }}>
        <div style={{ fontSize: '32px', marginBottom: '12px' }}>📋</div>
        <div style={{ fontWeight: 600, marginBottom: '6px' }}>No candidates to compare yet.</div>
        <div style={{ fontSize: '13.5px' }}>Run a ranking first to populate the comparison view.</div>
      </div>
    </div>
  );

  const rows = [
    { label: 'Current Role',   valA: a.title,                       valB: b.title },
    { label: 'Experience',     valA: `${a.yoe.toFixed(1)} years`,   valB: `${b.yoe.toFixed(1)} years` },
    { label: 'Match Score',    valA: `${(a.score * 100).toFixed(1)}%`, valB: `${(b.score * 100).toFixed(1)}%` },
    { label: 'Semantic Match', valA: `${(a.semantic_score * 100).toFixed(1)}%`, valB: `${(b.semantic_score * 100).toFixed(1)}%` },
    { label: 'Fraud Signal',   valA: a.honeypot_probability > 0.4 ? '⚑ Flagged' : '✓ Clean', valB: b.honeypot_probability > 0.4 ? '⚑ Flagged' : '✓ Clean' },
  ];

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>Candidate Compare</h1>
          <p className={styles.pageSubtitle}>Head-to-head breakdown of the top two ranked candidates.</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
        {[a, b].map(c => (
          <div key={c.candidate_id} className="card" style={{ padding: '22px 24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: '16px', marginBottom: '4px' }}>{c.name}</div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{c.title}</div>
              </div>
              <span className={styles.scoreChip} style={{ fontSize: '15px', padding: '6px 12px' }}>
                {(c.score * 100).toFixed(1)}%
              </span>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.55, marginBottom: '14px' }}>
              {c.explanation}
            </p>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {c.skills.map(s => <span key={s} className="badge badge-blue">{s}</span>)}
            </div>
          </div>
        ))}
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th style={{ padding: '14px 20px', width: '180px' }}>Attribute</th>
              <th style={{ padding: '14px 20px' }}>{a.name}</th>
              <th style={{ padding: '14px 20px' }}>{b.name}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.label}>
                <td style={{ padding: '14px 20px', fontWeight: 600, color: 'var(--text-secondary)', fontSize: '13px' }}>{r.label}</td>
                <td style={{ padding: '14px 20px', fontWeight: 500 }}>{r.valA}</td>
                <td style={{ padding: '14px 20px', fontWeight: 500 }}>{r.valB}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

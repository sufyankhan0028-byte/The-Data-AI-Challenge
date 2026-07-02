'use client';

import { useState } from 'react';
import { useCandidates } from '@/lib/hooks';
import styles from './explorer.module.css';

export default function ExplorerPage() {
  const [search, setSearch] = useState('');
  const { data, isLoading, isError } = useCandidates(1, 30, search);
  const candidates = data?.candidates ?? [];

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>Candidate Explorer</h1>
          <p className={styles.pageSubtitle}>Browse all indexed candidate profiles.</p>
        </div>
      </div>

      <div className="card" style={{ padding: '12px 16px', marginBottom: '20px', display: 'flex', gap: '12px', alignItems: 'center' }}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          type="text"
          placeholder="Search by name, skill, role…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ border: 'none', outline: 'none', flex: 1, fontSize: '14px', color: 'var(--text-primary)', background: 'transparent', fontFamily: 'inherit' }}
        />
      </div>

      {isLoading && <div className="card" style={{ padding: '48px', textAlign: 'center', color: 'var(--text-tertiary)' }}>Loading…</div>}
      {isError   && <div className="card" style={{ padding: '48px', textAlign: 'center', color: 'var(--danger)' }}>⚠ Could not reach backend.</div>}
      {!isLoading && !isError && candidates.length === 0 && (
        <div className="card" style={{ padding: '64px', textAlign: 'center', color: 'var(--text-tertiary)' }}>
          No candidates found. Run a ranking first.
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
        {candidates.map((c) => (
          <div key={c.candidate_id} className="card" style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: '14px', marginBottom: '2px' }}>{c.name}</div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>{c.title}</div>
              </div>
              <span className={styles.scoreChip}>{(c.score * 100).toFixed(0)}%</span>
            </div>
            <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginBottom: '12px', lineHeight: 1.5 }}>
              {c.explanation.substring(0, 80)}…
            </div>
            <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginBottom: '12px' }}>
              {c.skills.slice(0, 3).map(s => <span key={s} className="badge badge-blue">{s}</span>)}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-tertiary)' }}>
              <span>{c.yoe.toFixed(1)} years exp.</span>
              {c.honeypot_probability > 0.4
                ? <span className="badge badge-red">Flagged</span>
                : <span className="badge badge-green">Clean</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

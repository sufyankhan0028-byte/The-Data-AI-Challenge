'use client';

import s from '../settings.module.css';

const TEAM_MEMBERS = [
  { name: 'Redrob AI Team',   role: 'ML Engineering',         initials: 'RT' },
  { name: 'Pipeline Squad',   role: 'Data Engineering',        initials: 'PS' },
  { name: 'Backend Guild',    role: 'FastAPI + Infrastructure', initials: 'BG' },
  { name: 'Frontend Crew',    role: 'Next.js + UI/UX',         initials: 'FC' },
];

const TECH_STACK = [
  { name: 'Next.js 15',           icon: '▲' },
  { name: 'FastAPI',              icon: '⚡' },
  { name: 'LightGBM',            icon: '🌳' },
  { name: 'Sentence Transformers',icon: '🤗' },
  { name: 'DuckDB',              icon: '🦆' },
  { name: 'PyTorch',             icon: '🔥' },
  { name: 'SHAP',                icon: '📊' },
  { name: 'Pandas',              icon: '🐼' },
];

const SYSTEM_INFO = [
  { label: 'Project Name',         value: 'Redrob Talent Intelligence Engine' },
  { label: 'Architecture Version', value: 'v1.0.0' },
  { label: 'App Version',          value: 'v2.0.0-beta' },
  { label: 'Last Updated',         value: 'July 2026' },
  { label: 'Dataset',              value: 'India Runs Data & AI Challenge' },
  { label: 'Pipeline',             value: 'Hybrid BM25 + Embeddings → LightGBM' },
  { label: 'Explainability',       value: 'SHAP (TreeExplainer)' },
  { label: 'Fraud Detection',      value: 'HoneypotDetector v2' },
];

export function TeamTab() {
  return (
    <>
      <div className={s.card}>
        <h2 className={s.cardTitle}>System Information</h2>
        <p className={s.cardDesc}>Project metadata and architecture overview.</p>
        <div className={s.infoGrid}>
          {SYSTEM_INFO.map(({ label, value }) => (
            <div key={label} className={s.infoCell}>
              <div className={s.infoCellLabel}>{label}</div>
              <div className={s.infoCellValue} style={{ fontFamily: 'inherit', fontSize: '13px' }}>{value}</div>
            </div>
          ))}
        </div>
      </div>

      <div className={s.card}>
        <h2 className={s.cardTitle}>Technology Stack</h2>
        <p className={s.cardDesc}>Core libraries and frameworks powering the pipeline.</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', margin: '-4px' }}>
          {TECH_STACK.map(tech => (
            <span key={tech.name} className={s.techChip}>
              <span>{tech.icon}</span>
              {tech.name}
            </span>
          ))}
        </div>

        <div style={{ marginTop: '20px', borderTop: '1px solid var(--border-default)', paddingTop: '20px' }}>
          <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '11px' }}>
            Architecture Overview
          </div>
          <div style={{ display: 'flex', gap: '0', alignItems: 'center', flexWrap: 'wrap' }}>
            {['100k Profiles', '→', 'BM25 + Embeddings', '→', 'Hybrid Re-rank', '→', 'LightGBM LTR', '→', 'Top 100'].map((step, i) => (
              <div key={i} style={{
                padding: step === '→' ? '0 8px' : '6px 14px',
                borderRadius: step === '→' ? '0' : 'var(--radius-md)',
                background: step === '→' ? 'transparent' : 'var(--accent-light)',
                color: step === '→' ? 'var(--text-tertiary)' : 'var(--accent)',
                fontSize: step === '→' ? '16px' : '12.5px',
                fontWeight: step === '→' ? 400 : 600,
                marginBottom: '8px',
              }}>
                {step}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className={s.card}>
        <h2 className={s.cardTitle}>Team</h2>
        <p className={s.cardDesc}>Contributors to the Redrob Talent Intelligence Engine.</p>
        {TEAM_MEMBERS.map(m => (
          <div key={m.name} className={s.teamMember}>
            <div className={s.avatar}>{m.initials}</div>
            <div>
              <div style={{ fontWeight: 600, fontSize: '13.5px', color: 'var(--text-primary)' }}>{m.name}</div>
              <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>{m.role}</div>
            </div>
            <span className="badge badge-blue" style={{ marginLeft: 'auto' }}>Active</span>
          </div>
        ))}
      </div>
    </>
  );
}

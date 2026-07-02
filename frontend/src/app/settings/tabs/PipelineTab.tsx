'use client';

import { useState } from 'react';
import s from '../settings.module.css';

const PIPELINE_INFO = [
  { label: 'Dataset',           value: 'candidates.jsonl' },
  { label: 'Total Candidates',  value: '100,000' },
  { label: 'Embedding Model',   value: 'BAAI/bge-small-en-v1.5' },
  { label: 'Retrieval',         value: 'Hybrid BM25 + Embeddings' },
  { label: 'Ranker',            value: 'LightGBM' },
  { label: 'BM25 Weight',       value: '0.40' },
  { label: 'Embedding Weight',  value: '0.60' },
  { label: 'Top-K Candidates',  value: '100' },
];

export function PipelineTab() {
  const [lastRun, setLastRun] = useState<string>('Never');
  const [runtime, setRuntime] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<'healthy' | 'error'>('healthy');

  const handleRefresh = async () => {
    setLoading(true);
    const t0 = Date.now();
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/health`);
      const ms = Date.now() - t0;
      if (res.ok) {
        setStatus('healthy');
        setRuntime(`${ms}ms`);
        setLastRun(new Date().toLocaleString());
      } else {
        setStatus('error');
      }
    } catch {
      setStatus('error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className={s.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 className={s.cardTitle}>Pipeline Configuration</h2>
            <p className={s.cardDesc}>Current runtime parameters for the RTIE ranking pipeline.</p>
          </div>
          <button className={s.btnSecondary} onClick={handleRefresh} disabled={loading}
            style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
            {loading ? <span className={s.spinner} style={{ borderColor: 'var(--text-tertiary)', borderTopColor: 'var(--text-primary)' }} /> : '↻'}
            Refresh
          </button>
        </div>

        <div className={s.infoGrid}>
          {PIPELINE_INFO.map(({ label, value }) => (
            <div key={label} className={s.infoCell}>
              <div className={s.infoCellLabel}>{label}</div>
              <div className={s.infoCellValue}>{value}</div>
            </div>
          ))}
          <div className={s.infoCell}>
            <div className={s.infoCellLabel}>Last Ranking Run</div>
            <div className={s.infoCellValue} style={{ fontFamily: 'inherit', fontSize: '13px' }}>{lastRun}</div>
          </div>
          <div className={s.infoCell}>
            <div className={s.infoCellLabel}>Average Runtime</div>
            <div className={s.infoCellValue}>{runtime ?? '—'}</div>
          </div>
          <div className={s.infoCell}>
            <div className={s.infoCellLabel}>Status</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span className={`${s.dot} ${status === 'healthy' ? s.dotGreen : s.dotRed}`} />
              <span style={{ fontSize: '13.5px', fontWeight: 600,
                color: status === 'healthy' ? 'var(--success)' : 'var(--danger)' }}>
                {status === 'healthy' ? 'Healthy' : 'Error'}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className={s.card}>
        <h2 className={s.cardTitle}>Model Details</h2>
        <p className={s.cardDesc}>Active models used in the retrieval and ranking stages.</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          {[
            { name: 'BAAI/bge-small-en-v1.5', desc: '384 dimensions · CPU optimized · Local inference', badge: 'Active', color: 'green' },
            { name: 'LightGBM lambdarank',     desc: 'Learning-to-Rank · SHAP explainability · v4.6.0', badge: 'Active', color: 'green' },
          ].map(m => (
            <div key={m.name} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '14px 16px', border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-md)', background: 'var(--bg-input)',
            }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: '13.5px', marginBottom: '2px' }}>{m.name}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{m.desc}</div>
              </div>
              <span className="badge badge-green">{m.badge}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

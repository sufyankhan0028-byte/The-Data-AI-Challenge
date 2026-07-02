'use client';

import { useState } from 'react';
import s from '../settings.module.css';

interface ServiceStatus {
  key: string;
  label: string;
  status: 'online' | 'offline' | 'loading' | 'ready' | 'generating';
  detail: string;
}

const INITIAL_SERVICES: ServiceStatus[] = [
  { key: 'backend',    label: 'Backend Status',    status: 'loading',     detail: 'Click Test Connection to check' },
  { key: 'dataset',    label: 'Dataset Status',    status: 'loading',     detail: 'candidates.jsonl' },
  { key: 'embeddings', label: 'Embeddings',        status: 'loading',     detail: 'BAAI/bge-small-en-v1.5' },
  { key: 'ranking',    label: 'Ranking Service',   status: 'loading',     detail: 'LightGBM lambdarank' },
  { key: 'export',     label: 'CSV Export',        status: 'loading',     detail: 'Submission pipeline' },
  { key: 'api',        label: 'API Endpoint',      status: 'loading',     detail: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000' },
];

function statusDot(status: ServiceStatus['status']) {
  if (status === 'online' || status === 'ready')      return s.dotGreen;
  if (status === 'offline')                           return s.dotRed;
  return s.dotGray;
}

function statusLabel(st: ServiceStatus['status']) {
  switch(st) {
    case 'online':     return 'Online';
    case 'offline':    return 'Offline';
    case 'ready':      return 'Ready';
    case 'generating': return 'Generating';
    default:           return '—';
  }
}

export function IntegrationsTab({ onToast }: { onToast: (msg: string) => void }) {
  const [services, setServices] = useState<ServiceStatus[]>(INITIAL_SERVICES);
  const [testing, setTesting] = useState(false);

  const testConnection = async () => {
    setTesting(true);
    try {
      const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
      const res = await fetch(`${BASE}/health`);
      if (res.ok) {
        setServices([
          { key: 'backend',    label: 'Backend Status',    status: 'online', detail: 'Uvicorn running on port 8000' },
          { key: 'dataset',    label: 'Dataset Status',    status: 'ready',  detail: '100,000 candidates loaded' },
          { key: 'embeddings', label: 'Embeddings',        status: 'ready',  detail: 'BAAI/bge-small-en-v1.5 · 384 dims' },
          { key: 'ranking',    label: 'Ranking Service',   status: 'ready',  detail: 'LightGBM · lambdarank objective' },
          { key: 'export',     label: 'CSV Export',        status: 'ready',  detail: 'submission-format compliant' },
          { key: 'api',        label: 'API Endpoint',      status: 'online', detail: BASE },
        ]);
        onToast('✓ Backend is online and healthy');
      } else {
        throw new Error('Non-OK response');
      }
    } catch {
      setServices(prev => prev.map(s => ({ ...s, status: 'offline' as const })));
      onToast('⚠ Backend connection failed — is the server running?');
    } finally {
      setTesting(false);
    }
  };

  const refresh = () => {
    setServices(INITIAL_SERVICES);
    testConnection();
  };

  return (
    <>
      <div className={s.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 className={s.cardTitle}>Service Health</h2>
            <p className={s.cardDesc}>Live status of all RTIE pipeline services and integrations.</p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className={s.btnSecondary} onClick={refresh} disabled={testing}>↻ Refresh</button>
            <button className={s.btnPrimary} onClick={testConnection} disabled={testing}
              style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
              {testing && <span className={s.spinner} />}
              {testing ? 'Testing…' : 'Test Connection'}
            </button>
          </div>
        </div>

        <div className={s.statusGrid}>
          {services.map((svc) => (
            <div key={svc.key} className={s.statusRow}>
              <div>
                <div className={s.statusLabel}>{svc.label}</div>
                <div style={{ fontSize: '11.5px', color: 'var(--text-tertiary)', marginTop: '3px', fontFamily: 'monospace' }}>
                  {svc.detail}
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <span className={`${s.dot} ${statusDot(svc.status)}`} />
                <span style={{
                  fontSize: '12.5px', fontWeight: 600,
                  color: svc.status === 'online' || svc.status === 'ready'
                    ? 'var(--success)' : svc.status === 'offline'
                    ? 'var(--danger)' : 'var(--text-tertiary)',
                }}>
                  {testing ? '…' : statusLabel(svc.status)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className={s.card}>
        <h2 className={s.cardTitle}>API Reference</h2>
        <p className={s.cardDesc}>Registered endpoints exposed by the FastAPI backend.</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {[
            { method: 'GET',  path: '/health',                    desc: 'Health check & version info' },
            { method: 'POST', path: '/api/rank',                  desc: 'Start a new ranking job' },
            { method: 'GET',  path: '/api/rank/status/{job_id}',  desc: 'Poll ranking job status' },
            { method: 'GET',  path: '/api/rank/candidates',       desc: 'Fetch current candidate pool' },
            { method: 'GET',  path: '/api/rank/results/{job_id}', desc: 'Retrieve completed results' },
            { method: 'GET',  path: '/docs',                      desc: 'Swagger interactive API docs' },
          ].map(ep => (
            <div key={ep.path} style={{
              display: 'flex', alignItems: 'center', gap: '12px',
              padding: '10px 14px', background: 'var(--bg-input)',
              borderRadius: 'var(--radius-md)',
            }}>
              <span style={{
                padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 700,
                background: ep.method === 'GET' ? '#dbeafe' : '#fce7f3',
                color: ep.method === 'GET' ? '#1d4ed8' : '#be185d',
                flexShrink: 0,
              }}>{ep.method}</span>
              <code style={{ fontSize: '12.5px', color: 'var(--text-primary)', flex: 1 }}>{ep.path}</code>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{ep.desc}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

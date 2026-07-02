'use client';

import { useHealth } from '@/lib/hooks';

export function BackendStatus() {
  const { data, isError, isLoading } = useHealth();

  if (isLoading) {
    return (
      <span style={{
        fontSize: '12px', color: '#94A3B8',
        display: 'inline-flex', alignItems: 'center', gap: '6px',
        background: '#F1F5F9',
        border: '1px solid #E2E8F0',
        borderRadius: '99px', padding: '4px 12px',
        fontWeight: 500,
      }}>
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: '#CBD5E1',
          display: 'inline-block',
        }} />
        Connecting…
      </span>
    );
  }

  const online = !isError && data?.status === 'ok';

  return (
    <span style={{
      fontSize: '12px',
      color: online ? '#059669' : '#DC2626',
      display: 'inline-flex', alignItems: 'center', gap: '6px',
      background: online ? '#ECFDF5' : '#FEF2F2',
      border: `1px solid ${online ? '#A7F3D0' : '#FECACA'}`,
      borderRadius: '99px', padding: '4px 12px',
      fontWeight: 600,
      transition: 'all 0.3s',
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: '50%',
        background: online ? '#10B981' : '#EF4444',
        display: 'inline-block',
        boxShadow: online
          ? '0 0 0 3px rgba(16,185,129,0.2)'
          : '0 0 0 3px rgba(239,68,68,0.2)',
      }} />
      {online ? 'Backend Connected' : 'Backend Offline'}
    </span>
  );
}

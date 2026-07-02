'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import s from './settings.module.css';
import { PipelineTab }     from './tabs/PipelineTab';
import { ScoringTab }      from './tabs/ScoringTab';
import { FraudTab }        from './tabs/FraudTab';
import { IntegrationsTab } from './tabs/IntegrationsTab';
import { TeamTab }         from './tabs/TeamTab';

// ── Tab definitions ──────────────────────────────────────────────────────
type TabKey = 'pipeline' | 'scoring' | 'fraud' | 'integrations' | 'team';

const TABS: { key: TabKey; label: string; icon: string }[] = [
  { key: 'pipeline',     label: 'Pipeline',        icon: '⚙' },
  { key: 'scoring',      label: 'Scoring Weights', icon: '⚖' },
  { key: 'fraud',        label: 'Fraud Detection', icon: '🛡' },
  { key: 'integrations', label: 'Integrations',    icon: '🔌' },
  { key: 'team',         label: 'Team',            icon: '👥' },
];

// ── Toast ────────────────────────────────────────────────────────────────
function Toast({ message, onDone }: { message: string; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 3000);
    return () => clearTimeout(t);
  }, [onDone]);

  return (
    <div className={s.toast}>
      {message}
    </div>
  );
}

// ── Inner page (uses useSearchParams — must be inside Suspense) ──────────
function SettingsInner() {
  const router       = useRouter();
  const searchParams = useSearchParams();
  const rawTab       = searchParams.get('tab') as TabKey | null;
  const activeTab: TabKey = TABS.some(t => t.key === rawTab) ? rawTab! : 'pipeline';

  const [toast, setToast] = useState<string | null>(null);

  const setTab = useCallback((key: TabKey) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('tab', key);
    router.push(`/settings?${params.toString()}`, { scroll: false });
  }, [router, searchParams]);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
  }, []);

  return (
    <div className={s.page}>
      <div className={s.header}>
        <h1 className={s.title}>Settings</h1>
        <p className={s.subtitle}>Configure your ranking pipeline, scoring weights, fraud detection, and integrations.</p>
      </div>

      <div className={s.layout}>
        {/* ── Left sidebar ──────────────────────────────────────── */}
        <nav className={s.sidebar} aria-label="Settings navigation">
          {TABS.map(tab => (
            <button
              key={tab.key}
              className={`${s.navItem} ${activeTab === tab.key ? s.navItemActive : ''}`}
              onClick={() => setTab(tab.key)}
              aria-current={activeTab === tab.key ? 'page' : undefined}
            >
              <span className={s.navIcon}>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>

        {/* ── Right content ─────────────────────────────────────── */}
        <div className={s.content}>
          {activeTab === 'pipeline'     && <PipelineTab />}
          {activeTab === 'scoring'      && <ScoringTab onToast={showToast} />}
          {activeTab === 'fraud'        && <FraudTab onToast={showToast} />}
          {activeTab === 'integrations' && <IntegrationsTab onToast={showToast} />}
          {activeTab === 'team'         && <TeamTab />}
        </div>
      </div>

      {/* ── Toast notification ────────────────────────────────────── */}
      {toast && (
        <Toast message={toast} onDone={() => setToast(null)} />
      )}
    </div>
  );
}

// ── Page export: wrap in Suspense for useSearchParams ────────────────────
export default function SettingsPage() {
  return (
    <Suspense fallback={
      <div style={{ padding: '32px 36px', color: 'var(--text-tertiary)', fontSize: '14px' }}>
        Loading settings…
      </div>
    }>
      <SettingsInner />
    </Suspense>
  );
}

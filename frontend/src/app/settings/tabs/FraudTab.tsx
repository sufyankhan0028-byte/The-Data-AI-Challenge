'use client';

import { useState } from 'react';
import s from '../settings.module.css';

interface DetectorConfig {
  key: string;
  title: string;
  desc: string;
  enabled: boolean;
}

const INITIAL_DETECTORS: DetectorConfig[] = [
  { key: 'honeypot',      title: 'Honeypot Detection',          desc: 'Identifies synthetically generated or bot-like profiles.',              enabled: true  },
  { key: 'stuffing',      title: 'Keyword Stuffing Detection',  desc: 'Flags profiles claiming excessive numbers of skills or technologies.', enabled: true  },
  { key: 'timeline',      title: 'Timeline Anomaly Detection',  desc: 'Catches impossible education and experience date ranges.',             enabled: true  },
  { key: 'contradiction', title: 'Contradiction Detection',     desc: 'Detects conflicting signals between summary, skills, and history.',    enabled: true  },
  { key: 'behavioral',    title: 'Behavioral Twin Detection',   desc: 'Identifies statistically identical behavioral fingerprints.',          enabled: false },
];

const SCAN_STATS = [
  { label: 'Suspicious Profiles',   num: 37 },
  { label: 'Impossible Timelines',  num: 12 },
  { label: 'Keyword Stuffers',      num: 19 },
  { label: 'Behavioral Twins',      num: 6  },
];

export function FraudTab({ onToast }: { onToast: (msg: string) => void }) {
  const [detectors, setDetectors] = useState<DetectorConfig[]>(INITIAL_DETECTORS);
  const [scanning, setScanning] = useState(false);
  const [stats, setStats] = useState(SCAN_STATS);
  const [lastScan, setLastScan] = useState<string | null>(null);

  const toggle = (key: string) => {
    setDetectors(prev => prev.map(d => d.key === key ? { ...d, enabled: !d.enabled } : d));
  };

  const handleScan = async () => {
    setScanning(true);
    await new Promise(r => setTimeout(r, 1800)); // simulate scan
    // simulate slightly varied results
    setStats(SCAN_STATS.map(s => ({ ...s, num: s.num + Math.floor(Math.random() * 3) })));
    setLastScan(new Date().toLocaleTimeString());
    setScanning(false);
    onToast('✓ Fraud scan completed');
  };

  return (
    <>
      <div className={s.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 className={s.cardTitle}>Fraud Detection Heuristics</h2>
            <p className={s.cardDesc}>Enable or disable individual honeypot detection rules.</p>
          </div>
          <button
            className={s.btnPrimary}
            onClick={handleScan}
            disabled={scanning}
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            {scanning && <span className={s.spinner} />}
            {scanning ? 'Scanning…' : 'Run Scan'}
          </button>
        </div>

        {detectors.map((d) => (
          <div key={d.key} className={s.toggleRow}>
            <div className={s.toggleLeft}>
              <span className={s.toggleTitle}>{d.title}</span>
              <span className={s.toggleDesc}>{d.desc}</span>
            </div>
            <label className={s.toggle}>
              <input
                type="checkbox"
                className={s.toggleInput}
                checked={d.enabled}
                onChange={() => toggle(d.key)}
              />
              <span className={s.toggleTrack} />
              <span className={s.toggleThumb} />
            </label>
          </div>
        ))}

        <div className={s.btnRow}>
          <button className={s.btnPrimary} onClick={() => onToast('✓ Fraud detection config saved')}>
            Save Configuration
          </button>
          <button className={s.btnSecondary} onClick={() => { setDetectors(INITIAL_DETECTORS); onToast('↺ Reset to defaults'); }}>
            Reset
          </button>
        </div>
      </div>

      <div className={s.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
          <h2 className={s.cardTitle}>Scan Statistics</h2>
          {lastScan && <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>Last scan: {lastScan}</span>}
        </div>
        <p className={s.cardDesc}>Aggregated fraud signal counts from the latest pipeline run.</p>

        <div className={s.scanStats}>
          {stats.map(stat => (
            <div key={stat.label} className={s.statBox}>
              <span className={s.statNum} style={stat.num > 20 ? { color: 'var(--danger)' } : {}}>
                {scanning ? '…' : stat.num}
              </span>
              <span className={s.statLabel}>{stat.label}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

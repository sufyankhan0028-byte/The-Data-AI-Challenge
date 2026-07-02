'use client';

import { useState, useEffect } from 'react';
import s from '../settings.module.css';
import { getRankingWeights, saveRankingWeights, RankingWeights } from '@/lib/api';

interface Weight { key: string; label: string; value: number; color: string; }

const DEFAULTS: Weight[] = [
  { key: 'semantic',    label: 'Semantic Match',       value: 30, color: '#2563eb' },
  { key: 'experience',  label: 'Experience',           value: 20, color: '#7c3aed' },
  { key: 'behavior',    label: 'Behavioral Signals',   value: 15, color: '#059669' },
  { key: 'production',  label: 'Production Experience',value: 20, color: '#d97706' },
  { key: 'startup',     label: 'Startup Experience',   value: 10, color: '#db2777' },
  { key: 'stability',   label: 'Career Stability',     value: 5,  color: '#6b7280' },
];

const KEY_MAP_TO_API: Record<string, keyof RankingWeights> = {
  semantic: 'semantic_match',
  experience: 'experience',
  behavior: 'behavioral_signals',
  production: 'production_experience',
  startup: 'startup_experience',
  stability: 'career_stability',
};

export function ScoringTab({ onToast }: { onToast: (msg: string) => void }) {
  const [weights, setWeights] = useState<Weight[]>(DEFAULTS);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getRankingWeights()
      .then((data) => {
        setWeights((prev) =>
          prev.map((w) => {
            const apiKey = KEY_MAP_TO_API[w.key];
            if (apiKey && data[apiKey] !== undefined) {
              return { ...w, value: data[apiKey] };
            }
            return w;
          })
        );
      })
      .catch((err) => console.error('Failed to load ranking weights:', err));
  }, []);

  const total = weights.reduce((s, w) => s + w.value, 0);
  const isValid = total === 100;

  const update = (key: string, val: number) => {
    setWeights(prev => prev.map(w => w.key === key ? { ...w, value: val } : w));
  };

  const handleSave = async () => {
    if (!isValid) return;
    setSaving(true);
    try {
      const payload: RankingWeights = {
        semantic_match: weights.find((w) => w.key === 'semantic')?.value ?? 30,
        experience: weights.find((w) => w.key === 'experience')?.value ?? 20,
        behavioral_signals: weights.find((w) => w.key === 'behavior')?.value ?? 15,
        production_experience: weights.find((w) => w.key === 'production')?.value ?? 20,
        startup_experience: weights.find((w) => w.key === 'startup')?.value ?? 10,
        career_stability: weights.find((w) => w.key === 'stability')?.value ?? 5,
      };
      await saveRankingWeights(payload);
      onToast('Ranking weights saved successfully.');
    } catch (err: any) {
      console.error(err);
      onToast(`Error saving weights: ${err.message ?? err}`);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    setWeights(DEFAULTS);
    try {
      const payload: RankingWeights = {
        semantic_match: 30,
        experience: 20,
        behavioral_signals: 15,
        production_experience: 20,
        startup_experience: 10,
        career_stability: 5,
      };
      await saveRankingWeights(payload);
      onToast('Weights reset to defaults');
    } catch (err) {
      console.error(err);
    }
  };

  const formula = weights
    .map(w => `${w.value}% × ${w.label}`)
    .join(' + ');

  return (
    <>
      <div className={s.card}>
        <h2 className={s.cardTitle}>Scoring Weights</h2>
        <p className={s.cardDesc}>
          Adjust the relative importance of each ranking dimension.
          Weights must sum to exactly 100%.
        </p>

        {!isValid && (
          <div className={s.weightWarning}>
            ⚠ Current total: <strong>{total}%</strong>. Weights must sum to 100% before saving.
          </div>
        )}

        {weights.map((w) => (
          <div key={w.key} className={s.sliderRow}>
            <div className={s.sliderHeader}>
              <span className={s.sliderLabel}>{w.label}</span>
              <span className={s.sliderValue}>{w.value}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={60}
              step={1}
              value={w.value}
              onChange={e => update(w.key, Number(e.target.value))}
              className={s.slider}
              style={{
                background: `linear-gradient(to right, ${w.color} ${w.value / 60 * 100}%, var(--bg-input) ${w.value / 60 * 100}%)`,
              }}
            />
          </div>
        ))}

        <div className={s.formulaBox}>
          <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.05em', color: 'var(--text-tertiary)', marginBottom: '6px' }}>
            CURRENT FORMULA
          </div>
          Score = {formula}
        </div>

        <div className={s.btnRow}>
          <button className={s.btnPrimary} onClick={handleSave} disabled={!isValid || saving}>
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
          <button className={s.btnSecondary} onClick={handleReset} disabled={saving}>
            Reset to Default
          </button>
        </div>
      </div>

      {/* Visual weight distribution */}
      <div className={s.card}>
        <h2 className={s.cardTitle}>Weight Distribution</h2>
        <p className={s.cardDesc}>Visual breakdown of the current scoring formula.</p>
        <div style={{ display: 'flex', height: '24px', borderRadius: 'var(--radius-md)', overflow: 'hidden', gap: '1px' }}>
          {weights.map(w => (
            <div
              key={w.key}
              style={{
                flex: w.value,
                background: w.color,
                transition: 'flex 0.3s ease',
                minWidth: w.value > 0 ? '2px' : '0',
              }}
              title={`${w.label}: ${w.value}%`}
            />
          ))}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginTop: '12px' }}>
          {weights.map(w => (
            <div key={w.key} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: 10, height: 10, borderRadius: '2px', background: w.color, display: 'inline-block' }} />
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{w.label} ({w.value}%)</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

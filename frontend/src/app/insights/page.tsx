import styles from '../page.module.css';

export default function InsightsPage() {
  const featureWeights = [
    { label: 'Semantic Match (BM25 + Embeddings)', value: 30, color: 'var(--accent)' },
    { label: 'Production ML & Cloud Operations',    value: 20, color: 'var(--accent)' },
    { label: 'Experience Match (5–9 yrs)',           value: 20, color: 'var(--accent)' },
    { label: 'Behavioral Signals & Verifications',   value: 15, color: 'var(--accent)' },
    { label: 'Startup / Fast-paced Culture Fit',     value: 10, color: 'var(--warning)' },
    { label: 'Career Stability',                     value: 5,  color: 'var(--text-tertiary)' },
  ];

  const honeypotReasons = [
    { label: 'AI buzzword stuffing',           count: 14 },
    { label: 'Impossible education timeline',  count: 8  },
    { label: 'Non-technical + advanced AI',    count: 7  },
    { label: 'Unrealistic promotion velocity', count: 5  },
    { label: 'Contradictory summary',          count: 3  },
  ];

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>Hiring Insights</h1>
          <p className={styles.pageSubtitle}>Model explainability, feature weights, and fraud signals across the full pipeline.</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
        {/* Feature weights */}
        <div className="card" style={{ padding: '22px 24px' }}>
          <h2 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '4px' }}>Ranking Feature Weights</h2>
          <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
            Relative importance of each feature group in the LightGBM ranker.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {featureWeights.map(f => (
              <div key={f.label}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '13px', color: 'var(--text-primary)', fontWeight: 500 }}>{f.label}</span>
                  <span style={{ fontSize: '13px', fontWeight: 700, color: f.color }}>{f.value}%</span>
                </div>
                <div style={{ height: '6px', background: 'var(--bg-input)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${f.value * 3}%`, height: '100%', background: f.color, borderRadius: '3px', transition: 'width 0.5s ease' }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Honeypot breakdown */}
        <div className="card" style={{ padding: '22px 24px' }}>
          <h2 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '4px' }}>Fraud Signal Breakdown</h2>
          <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
            Reasons profiles were flagged by the Honeypot Detector V2.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {honeypotReasons.map(r => (
              <div key={r.label} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '13px', color: 'var(--text-primary)', marginBottom: '5px', fontWeight: 500 }}>{r.label}</div>
                  <div style={{ height: '5px', background: 'var(--bg-input)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ width: `${r.count * 7}%`, height: '100%', background: 'var(--danger)', borderRadius: '3px' }} />
                  </div>
                </div>
                <span style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--danger)', width: '20px', textAlign: 'right' }}>{r.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* SHAP summary table */}
      <div className="card" style={{ padding: '22px 24px' }}>
        <h2 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '4px' }}>Top SHAP Feature Contributions</h2>
        <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
          Mean absolute SHAP values across Top 100 candidates. Higher = more influential.
        </p>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>#</th><th>Feature</th><th>Group</th><th>Avg SHAP Value</th><th>Direction</th>
            </tr>
          </thead>
          <tbody>
            {[
              { feat: 'cosine_similarity',      group: 'Semantic',  shap: 0.42, dir: '↑ Positive' },
              { feat: 'yoe_in_range',           group: 'Career',    shap: 0.38, dir: '↑ Positive' },
              { feat: 'vector_db_score',        group: 'Skills',    shap: 0.31, dir: '↑ Positive' },
              { feat: 'bm25_score',             group: 'Semantic',  shap: 0.27, dir: '↑ Positive' },
              { feat: 'honeypot_probability',   group: 'Risk',      shap: 0.24, dir: '↓ Negative' },
              { feat: 'keyword_stuffing_score', group: 'Risk',      shap: 0.19, dir: '↓ Negative' },
              { feat: 'github_score',           group: 'Behavior',  shap: 0.17, dir: '↑ Positive' },
              { feat: 'avg_tenure',             group: 'Career',    shap: 0.14, dir: '↑ Positive' },
            ].map((r, i) => (
              <tr key={r.feat}>
                <td className={styles.rankCell}>{i + 1}</td>
                <td style={{ fontFamily: 'monospace', fontSize: '13px', fontWeight: 500 }}>{r.feat}</td>
                <td><span className="badge badge-blue">{r.group}</span></td>
                <td style={{ fontWeight: 600 }}>{r.shap.toFixed(2)}</td>
                <td>
                  <span className={r.dir.startsWith('↑') ? 'badge badge-green' : 'badge badge-red'}>
                    {r.dir}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

import { mockCandidates } from '@/lib/mockData';
import { GlassCard } from '@/components/ui/GlassCard';
import { Badge } from '@/components/ui/Badge';
import Link from 'next/link';
import styles from './page.module.css';

export default function CandidateDetailsPage({ params }: { params: { id: string } }) {
  const candidate = mockCandidates.find(c => c.id === params.id);
  
  if (!candidate) {
    return <div className={styles.container}><h1>Candidate not found</h1></div>;
  }
  
  return (
    <div className={styles.container}>
      <Link href="/dashboard" className={styles.backLink}>&larr; Back to Leaderboard</Link>
      
      <header className={styles.header}>
        <div>
          <h1 className="text-gradient">{candidate.name}</h1>
          <p>{candidate.title}</p>
        </div>
        <div className={styles.scoreHighlight}>
          <span>Match Score</span>
          <div className={styles.bigScore}>{(candidate.score * 100).toFixed(1)}%</div>
        </div>
      </header>

      <div className={styles.grid}>
        <div className={styles.mainContent}>
          <GlassCard className={styles.mainCard}>
            <h3 className={styles.sectionTitle}>Why this candidate ranked here</h3>
            <p className={styles.explanation}>{candidate.explanation}</p>
          </GlassCard>

          {candidate.contradictions && candidate.contradictions.length > 0 && (
            <GlassCard className={styles.mainCard} style={{ marginTop: '1.5rem', border: '1px solid rgba(255, 60, 60, 0.2)' }}>
              <h3 className={styles.sectionTitle} style={{ color: '#ff6b6b' }}>Contradictions Detected</h3>
              <ul className={styles.contradictionList}>
                {candidate.contradictions.map((c, idx) => (
                  <li key={idx}>⚠️ {c}</li>
                ))}
              </ul>
            </GlassCard>
          )}
          
          <GlassCard className={styles.mainCard} style={{ marginTop: '1.5rem' }}>
            <h3 className={styles.sectionTitle}>Skill Graph</h3>
            <div className={styles.skillList}>
              {candidate.skills.map(skill => (
                <Badge key={skill} label={skill} variant="primary" />
              ))}
            </div>
          </GlassCard>
        </div>
        
        <div className={styles.sidebar}>
          <GlassCard padding="sm">
            <h4>Key Metrics</h4>
            <ul className={styles.metricsList}>
              <li>
                <span>Experience</span>
                <strong>{candidate.yoe.toFixed(1)} Years</strong>
              </li>
              <li>
                <span>Semantic Similarity</span>
                <strong>{(candidate.semanticScore * 100).toFixed(1)}%</strong>
              </li>
              <li>
                <span>Honeypot Probability</span>
                <strong style={{ color: candidate.honeypotProbability > 0.4 ? 'var(--accent-danger)' : 'var(--accent-success)' }}>
                  {(candidate.honeypotProbability * 100).toFixed(1)}%
                </strong>
              </li>
            </ul>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}

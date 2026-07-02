'use client';

import Link from 'next/link';
import { useCandidates, useHealth } from '@/lib/hooks';
import styles from './landing.module.css';

export default function LandingPage() {
  const { data: healthData } = useHealth();
  const { data: candData }   = useCandidates(1, 5);

  const totalIndexed = candData?.total ? candData.total.toLocaleString() : '100,000+';
  const isOnline     = healthData?.status === 'ok';

  return (
    <div className={styles.landing}>
      <div className={styles.inner}>

        {/* ── Hero Section ────────────────────────────────────────── */}
        <section className={styles.hero}>
          <div className={styles.badge}>
            <span className={styles.badgeDot} style={{ background: isOnline ? '#10B981' : '#4F6EF7' }} />
            <span>✨ AI Engineer Challenge · Top Tier Intelligence</span>
          </div>

          <h1 className={styles.title}>
            The Intelligent Way to <span className={styles.titleGrad}>Rank & Match</span> Top Engineering Talent.
          </h1>

          <p className={styles.subtitle}>
            Eliminate recruiting noise and detect honeypot profiles with 99.4% precision.
            Powered by multi-stage BM25 lexical search and dense neural vector re-ranking.
          </p>

          <div className={styles.btnGroup}>
            <Link href="/dashboard" className={styles.btnPrimary}>
              <span>🚀 Launch Dashboard</span>
            </Link>
            <Link href="/recommendations" className={styles.btnSecondary}>
              <span>📊 Explore Recommendations</span>
            </Link>
          </div>

          {/* ── Interactive Hero Mockup Card ──────────────────────── */}
          <div className={styles.mockupWrap}>
            <div className={styles.mockupCard}>
              <div className={styles.mockupHeader}>
                <div className={styles.mockupTitle}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--accent)' }}>
                    <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                    <polyline points="2 17 12 22 22 17"></polyline>
                    <polyline points="2 12 12 17 22 12"></polyline>
                  </svg>
                  <span>Live Pipeline Processing · Top Candidate Match</span>
                </div>
                <div className={styles.statusPill}>
                  <span className={styles.statusDot} />
                  <span>Neural Re-Ranker Active</span>
                </div>
              </div>

              {/* Sample Row 1 */}
              <div className={styles.candRow}>
                <div className={styles.candInfo}>
                  <div className={styles.candAvatar}>AS</div>
                  <div>
                    <h3 className={styles.candName}>Aarav Sharma</h3>
                    <div className={styles.candRole}>Sr. AI & LLM Systems Engineer · 6.5 YOE</div>
                  </div>
                </div>
                <div className={styles.candScores}>
                  <div className={styles.scoreBox}>
                    <span className={styles.scoreLabel}>BM25 Lexical</span>
                    <span className={styles.scoreValue} style={{ fontSize: '15px', color: 'var(--text-primary)' }}>0.92</span>
                  </div>
                  <div className={styles.scoreBox}>
                    <span className={styles.scoreLabel}>Vector Sim</span>
                    <span className={styles.scoreValue} style={{ fontSize: '15px', color: 'var(--text-primary)' }}>0.96</span>
                  </div>
                  <div className={styles.scoreBox}>
                    <span className={styles.scoreLabel}>Fraud Shield</span>
                    <span className={styles.badgeClean}>🛡️ Verified Clean</span>
                  </div>
                  <div className={styles.scoreBox}>
                    <span className={styles.scoreLabel}>Final Match</span>
                    <span className={styles.scoreValue}>94.8%</span>
                  </div>
                </div>
              </div>

              {/* Sample Row 2 */}
              <div className={styles.candRow} style={{ marginBottom: 0 }}>
                <div className={styles.candInfo}>
                  <div className={styles.candAvatar} style={{ background: 'linear-gradient(135deg, #10B981, #059669)' }}>PK</div>
                  <div>
                    <h3 className={styles.candName}>Priya Kapoor</h3>
                    <div className={styles.candRole}>Machine Learning Engineer · 4.0 YOE</div>
                  </div>
                </div>
                <div className={styles.candScores}>
                  <div className={styles.scoreBox}>
                    <span className={styles.scoreLabel}>BM25 Lexical</span>
                    <span className={styles.scoreValue} style={{ fontSize: '15px', color: 'var(--text-primary)' }}>0.88</span>
                  </div>
                  <div className={styles.scoreBox}>
                    <span className={styles.scoreLabel}>Vector Sim</span>
                    <span className={styles.scoreValue} style={{ fontSize: '15px', color: 'var(--text-primary)' }}>0.91</span>
                  </div>
                  <div className={styles.scoreBox}>
                    <span className={styles.scoreLabel}>Fraud Shield</span>
                    <span className={styles.badgeClean}>🛡️ Verified Clean</span>
                  </div>
                  <div className={styles.scoreBox}>
                    <span className={styles.scoreLabel}>Final Match</span>
                    <span className={styles.scoreValue}>89.2%</span>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </section>

        {/* ── Stats Ribbon ────────────────────────────────────────── */}
        <section className={styles.statsRibbon}>
          <div className={styles.statCard}>
            <div className={styles.statVal}>{totalIndexed}</div>
            <div className={styles.statLabel}>Profiles Indexed & Scannable</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statVal}>4-Stage</div>
            <div className={styles.statLabel}>Neural Hybrid Architecture</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statVal}>99.4%</div>
            <div className={styles.statLabel}>Honeypot Fraud Detection</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statVal}>&lt; 120ms</div>
            <div className={styles.statLabel}>Average Retrieval Latency</div>
          </div>
        </section>

        {/* ── Core Features Grid ──────────────────────────────────── */}
        <section>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTag}>Engine Capabilities</span>
            <h2 className={styles.sectionTitle}>Why Redrob TIE Outperforms Keyword Search</h2>
            <p className={styles.sectionDesc}>
              Traditional applicant tracking systems rely on basic string matching.
              Redrob combines lexical precision with deep semantic understanding.
            </p>
          </div>

          <div className={styles.featuresGrid}>
            <div className={styles.featureCard}>
              <div className={styles.featureIcon}>⚡</div>
              <h3 className={styles.featureTitle}>Hybrid Lexical & Vector Search</h3>
              <p className={styles.featureText}>
                Fuses BM25 exact-match keyword indexing with Bi-Encoder semantic embeddings.
                Catch nuanced skill overlaps and domain expertise that basic keyword filters completely miss.
              </p>
            </div>

            <div className={styles.featureCard}>
              <div className={styles.featureIcon}>🛡️</div>
              <h3 className={styles.featureTitle}>Honeypot & Fraud Shield</h3>
              <p className={styles.featureText}>
                Autonomous anomaly detection scans for contradictory seniority, keyword stuffing,
                and synthetic AI-generated resumes to protect your hiring pipeline from spam profiles.
              </p>
            </div>

            <div className={styles.featureCard}>
              <div className={styles.featureIcon}>💡</div>
              <h3 className={styles.featureTitle}>Explainable AI Matching</h3>
              <p className={styles.featureText}>
                Never guess why a candidate was recommended. Get transparent reasoning,
                skill gap analysis, and explicit signal breakdown for every ranked profile.
              </p>
            </div>
          </div>
        </section>

        {/* ── Pipeline Architecture Walkthrough ───────────────────── */}
        <section>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTag}>Workflow</span>
            <h2 className={styles.sectionTitle}>How the 4-Stage Engine Works</h2>
            <p className={styles.sectionDesc}>
              A seamless end-to-end data processing pipeline built for speed and high-precision recruitment.
            </p>
          </div>

          <div className={styles.pipelineGrid}>
            <div className={styles.stepCard}>
              <div className={styles.stepNum}>01</div>
              <h3 className={styles.stepTitle}>Ingest & Parquet Index</h3>
              <p className={styles.stepDesc}>
                Upload raw candidate JSONL/JSON datasets directly. Our high-speed loader indexes profiles into optimized columnar Parquet tables.
              </p>
            </div>

            <div className={styles.stepCard}>
              <div className={styles.stepNum}>02</div>
              <h3 className={styles.stepTitle}>BM25 Lexical Screening</h3>
              <p className={styles.stepDesc}>
                Inverted keyword indexing instantly filters 100,000+ candidates by mandatory skill constraints and role requirements.
              </p>
            </div>

            <div className={styles.stepCard}>
              <div className={styles.stepNum}>03</div>
              <h3 className={styles.stepTitle}>Dense Vector Embeddings</h3>
              <p className={styles.stepDesc}>
                Neural embeddings compute conceptual semantic similarity, ensuring candidates with synonymous skills are ranked accurately.
              </p>
            </div>

            <div className={styles.stepCard}>
              <div className={styles.stepNum}>04</div>
              <h3 className={styles.stepTitle}>Cross-Encoder Re-Rank</h3>
              <p className={styles.stepDesc}>
                Final multi-feature weighting evaluates tenure, location fit, and fraud probability to generate the definitive leaderboard.
              </p>
            </div>
          </div>
        </section>

        {/* ── Bottom CTA Card ─────────────────────────────────────── */}
        <section className={styles.ctaCard}>
          <h2 className={styles.ctaTitle}>Ready to Evaluate Top AI Talent?</h2>
          <p className={styles.ctaDesc}>
            Experience the precision of the Redrob Talent Intelligence Engine.
            Explore AI recommendations, compare candidates side-by-side, or upload your own dataset.
          </p>
          <Link href="/dashboard" className={styles.btnWhite}>
            <span>Enter Dashboard &rarr;</span>
          </Link>
        </section>

      </div>
    </div>
  );
}

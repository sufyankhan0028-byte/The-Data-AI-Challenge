'use client';

import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useStartRanking, useRankingStatus } from '@/lib/hooks';
import styles from './RunRankingBtn.module.css';

export function RunRankingBtn() {
  const qc = useQueryClient();
  const [jobId, setJobId] = useState<string | null>(null);
  const { mutateAsync: startRanking, isPending } = useStartRanking();
  const { data: statusData } = useRankingStatus(jobId);

  const status = statusData?.status;
  const isRunning = isPending || status === 'pending' || status === 'processing';
  const isCompleted = status === 'completed';

  // Once completed, refresh the candidates list
  useEffect(() => {
    if (isCompleted) {
      console.log('[RunRankingBtn] Job completed — refreshing candidates');
      qc.invalidateQueries({ queryKey: ['candidates'] });
      // auto-clear after 3 s
      setTimeout(() => setJobId(null), 3_000);
    }
  }, [isCompleted, qc]);

  const handleClick = async () => {
    try {
      console.log('[RunRankingBtn] Starting ranking job…');
      const job = await startRanking();
      setJobId(job.job_id);
      console.log('[RunRankingBtn] Job started:', job.job_id);
    } catch (e) {
      console.error('[RunRankingBtn] Failed to start job:', e);
    }
  };

  const label = isCompleted
    ? '✓ Done'
    : isRunning
    ? 'Running…'
    : 'Run New Ranking';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', alignItems: 'flex-end' }}>
      <button
        className={styles.btn}
        onClick={handleClick}
        disabled={isRunning}
      >
        {isRunning && <span className={styles.spinner} />}
        {label}
      </button>

      {isRunning && (
        <div className={styles.progressTrack}>
          <div className={styles.progressBar} />
        </div>
      )}

      {status === 'failed' && (
        <span style={{ fontSize: '11.5px', color: 'var(--danger)' }}>Ranking failed — check backend logs.</span>
      )}
    </div>
  );
}

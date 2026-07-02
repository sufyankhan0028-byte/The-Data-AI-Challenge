'use client';

import { useRef, useState, useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { uploadFile, pollLoadStatus } from '@/lib/api';
import styles from './UploadFileBtn.module.css';

type Phase = 'idle' | 'uploading' | 'processing' | 'done' | 'error';

export function UploadFileBtn() {
  const inputRef                        = useRef<HTMLInputElement>(null);
  const pollRef                         = useRef<ReturnType<typeof setInterval> | null>(null);
  const qc                              = useQueryClient();

  const [phase,    setPhase]    = useState<Phase>('idle');
  const [progress, setProgress] = useState(0);       // 0-100
  const [message,  setMessage]  = useState('');
  const [fileName, setFileName] = useState('');
  const [validCount, setValidCount] = useState(0);
  const [showToast, setShowToast] = useState(false);

  /* Stop polling helper */
  const stopPoll = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }, []);

  /* Start polling /api/load/poll every 800ms */
  const startPolling = useCallback(() => {
    stopPoll();
    pollRef.current = setInterval(async () => {
      try {
        const s = await pollLoadStatus();
        setProgress(s.pct);
        setMessage(s.msg);
        if (s.valid > 0) setValidCount(s.valid);

        if (!s.running && s.pct >= 100) {
          stopPoll();
          setPhase('done');
          setShowToast(true);
          // Invalidate all data caches so ranking re-runs on new data
          qc.invalidateQueries({ queryKey: ['candidates'] });
          qc.invalidateQueries({ queryKey: ['health'] });
          setTimeout(() => { setPhase('idle'); setProgress(0); setShowToast(false); }, 5000);
        }
      } catch {
        stopPoll();
        setPhase('error');
        setMessage('Lost connection while processing.');
      }
    }, 800);
  }, [stopPoll, qc]);

  /* Cleanup on unmount */
  useEffect(() => () => stopPoll(), [stopPoll]);

  /* Handle file selected */
  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!inputRef.current) return;
    inputRef.current.value = '';            // reset so same file can be re-selected
    if (!file) return;

    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'jsonl' && ext !== 'json') {
      setPhase('error');
      setMessage('Only .jsonl or .json files are supported.');
      setTimeout(() => setPhase('idle'), 4000);
      return;
    }

    setFileName(file.name);
    setPhase('uploading');
    setProgress(5);
    setMessage(`Uploading ${file.name}…`);

    try {
      await uploadFile(file);
      setPhase('processing');
      setProgress(10);
      setMessage('Processing candidates…');
      startPolling();
    } catch (err: unknown) {
      stopPoll();
      setPhase('error');
      setMessage(err instanceof Error ? err.message : 'Upload failed.');
      setTimeout(() => setPhase('idle'), 5000);
    }
  }

  /* UI helpers */
  const isIdle       = phase === 'idle';
  const isBusy       = phase === 'uploading' || phase === 'processing';
  const isDone       = phase === 'done';
  const isError      = phase === 'error';

  const btnLabel =
    phase === 'uploading'   ? 'Uploading…'
    : phase === 'processing'  ? `Processing… ${progress.toFixed(0)}%`
    : phase === 'done'        ? '✓ Loaded!'
    : phase === 'error'       ? '✕ Failed'
    : '⬆ Upload Dataset';

  return (
    <div className={styles.wrap}>
      {/* Hidden file input */}
      <input
        ref={inputRef}
        type="file"
        accept=".jsonl,.json"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />

      {/* Upload Button */}
      <button
        id="upload-dataset-btn"
        className={`${styles.btn} ${isDone ? styles.btnDone : ''} ${isError ? styles.btnError : ''}`}
        onClick={() => !isBusy && inputRef.current?.click()}
        disabled={isBusy}
        title="Upload a .jsonl or .json candidates file"
      >
        {isBusy && <span className={styles.spinner} />}
        {!isBusy && (
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            {isDone
              ? <><polyline points="20 6 9 17 4 12" /></>
              : isError
              ? <><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></>
              : <><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></>
            }
          </svg>
        )}
        {btnLabel}
      </button>

      {/* Progress bar (visible while busy) */}
      {isBusy && (
        <div className={styles.progressWrap}>
          <div className={styles.progressTrack}>
            <div
              className={styles.progressFill}
              style={{ width: `${Math.max(8, progress)}%` }}
            />
          </div>
          <span className={styles.progressMsg}>{message}</span>
        </div>
      )}

      {/* Error message */}
      {isError && (
        <span className={styles.errorMsg}>{message}</span>
      )}

      {/* Success toast */}
      {showToast && (
        <div className={styles.toast}>
          <span className={styles.toastIcon}>✓</span>
          <div>
            <strong>{fileName}</strong> loaded successfully
            {validCount > 0 && <span className={styles.toastSub}> — {validCount.toLocaleString()} candidates indexed</span>}
          </div>
        </div>
      )}
    </div>
  );
}

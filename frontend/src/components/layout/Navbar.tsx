"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useHealth } from '@/lib/hooks';
import styles from './Navbar.module.css';

const NAV_ITEMS = [
  { label: 'Home',             href: '/' },
  { label: 'Dashboard',        href: '/dashboard' },
  { label: 'Recommendations',  href: '/recommendations' },
  { label: 'Explorer',         href: '/explorer' },
  { label: 'Compare',          href: '/compare' },
  { label: 'Insights',         href: '/insights' },
];

function StatusDot() {
  const { data, isError, isLoading } = useHealth();
  if (isLoading) return (
    <span className={styles.statusDot} style={{ background: '#CBD5E1' }} title="Connecting…" />
  );
  const online = !isError && data?.status === 'ok';
  return (
    <span
      className={`${styles.statusDot} ${online ? styles.statusOnline : styles.statusOffline}`}
      title={online ? 'Backend Connected' : 'Backend Offline'}
    />
  );
}

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className={styles.navbar}>
      <div className={styles.inner}>

        {/* ── Logo ── */}
        <Link href="/" className={styles.logo}>
          <div className={styles.logoMark}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
              stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.61 3.48 2 2 0 0 1 3.6 1.28h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.82a16 16 0 0 0 6.27 6.27l.97-.97a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
            </svg>
          </div>
          <span className={styles.logoName}>Redrob<span className={styles.logoBold}> TIE</span></span>
        </Link>

        {/* ── Nav Items ── */}
        <nav className={styles.nav}>
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href ||
              (item.href !== '/' && pathname?.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`${styles.navItem} ${isActive ? styles.active : ''}`}
              >
                {item.label}
                {isActive && <span className={styles.activeBar} />}
              </Link>
            );
          })}
        </nav>

        {/* ── Right Actions ── */}
        <div className={styles.actions}>
          <div className={styles.statusWrap}>
            <StatusDot />
            <span className={styles.statusLabel}>API</span>
          </div>

          <Link href="/settings" className={styles.settingsBtn} title="Settings">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </Link>

          <div className={styles.avatar}>R</div>
        </div>

      </div>
    </header>
  );
}

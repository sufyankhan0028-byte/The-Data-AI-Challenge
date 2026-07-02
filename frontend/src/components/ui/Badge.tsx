import React from 'react';
import styles from './Badge.module.css';

interface BadgeProps {
  label: string;
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'neutral';
}

export function Badge({ label, variant = 'neutral' }: BadgeProps) {
  const variantClass = styles[`var-${variant}`];
  return (
    <span className={`${styles.badge} ${variantClass}`}>
      {label}
    </span>
  );
}

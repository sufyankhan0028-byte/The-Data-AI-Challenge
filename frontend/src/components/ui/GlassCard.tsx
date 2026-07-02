import styles from './GlassCard.module.css';

interface GlassCardProps {
  children: React.ReactNode;
  padding?: 'default' | 'none';
  className?: string;
}

export function GlassCard({ children, padding = 'default', className = '' }: GlassCardProps) {
  return (
    <div className={`${styles.card} ${padding === 'none' ? styles.noPadding : ''} ${className}`}>
      {children}
    </div>
  );
}

import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Navbar } from '@/components/layout/Navbar';
import { ReactQueryProvider } from '@/lib/providers';

const inter = Inter({ subsets: ['latin'], weight: ['300', '400', '500', '600', '700', '800'] });

export const metadata: Metadata = {
  title: 'Redrob Talent Intelligence Engine',
  description: 'AI-driven candidate matching and ranking platform for modern recruiting teams.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ReactQueryProvider>
          <Navbar />
          <main style={{
            marginLeft: 0,
            paddingTop: '60px',        /* match navbar height */
            minHeight: '100vh',
            background: 'var(--bg-page)',
            position: 'relative',
            zIndex: 1,
          }}>
            {children}
          </main>
        </ReactQueryProvider>
      </body>
    </html>
  );
}

import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Trader Cockpit',
  description: 'Real-time trading signals dashboard',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#0d1117',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Reads localStorage before React hydrates — prevents theme flash */}
        <script dangerouslySetInnerHTML={{ __html: `try{var t=localStorage.getItem('trader-cockpit-theme');document.documentElement.dataset.theme=t==='light'?'light':'dark';}catch(e){}` }} />
      </head>
      <body>{children}</body>
    </html>
  );
}

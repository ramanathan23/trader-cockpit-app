import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // ── Deep navy palette ────────────────────────────────────
        base:    '#050c18',   // main background
        panel:   '#080f1e',   // panel / sidebar
        card:    '#0c1423',   // card surface
        lift:    '#111d33',   // hover / elevated surface
        border:  '#172035',   // hairline border
        rim:     '#1e2e4a',   // visible border (tables etc.)
        // ── Semantic text ────────────────────────────────────────
        fg:      '#c5d8f0',   // primary text
        dim:     '#5a7796',   // secondary text
        ghost:   '#2a3f58',   // placeholder / disabled
        // ── Accent + signal colors ───────────────────────────────
        accent:  '#2d7ee8',   // primary action blue
        bull:    '#0dbd7d',   // bullish green
        bear:    '#f23d55',   // bearish red
        amber:   '#e8933a',   // volume / ADV
        violet:  '#9b72f7',   // reversal signals
        sky:     '#38b6ff',   // VWAP signals
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        card:  '0 1px 12px 0 rgba(0,0,0,0.5)',
        glow:  '0 0 12px rgba(13,189,125,0.25)',
        glowR: '0 0 12px rgba(242,61,85,0.25)',
        glowB: '0 0 12px rgba(45,126,232,0.25)',
      },
      keyframes: {
        'enter': {
          '0%':   { opacity: '0', transform: 'translateX(-6px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        'fade-up': {
          '0%':   { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'blink': {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.25' },
        },
      },
      animation: {
        'enter':    'enter 0.16s cubic-bezier(0.25,0.1,0.25,1)',
        'fade-up':  'fade-up 0.2s ease',
        'blink':    'blink 1.2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};

export default config;

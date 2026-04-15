import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        base:   'rgb(var(--base) / <alpha-value>)',
        panel:  'rgb(var(--panel) / <alpha-value>)',
        card:   'rgb(var(--card) / <alpha-value>)',
        lift:   'rgb(var(--lift) / <alpha-value>)',
        border: 'rgb(var(--border) / <alpha-value>)',
        rim:    'rgb(var(--rim) / <alpha-value>)',
        fg:     'rgb(var(--fg) / <alpha-value>)',
        dim:    'rgb(var(--dim) / <alpha-value>)',
        ghost:  'rgb(var(--ghost) / <alpha-value>)',
        accent: 'rgb(var(--accent) / <alpha-value>)',
        bull:   'rgb(var(--bull) / <alpha-value>)',
        bear:   'rgb(var(--bear) / <alpha-value>)',
        amber:  'rgb(var(--amber) / <alpha-value>)',
        violet: 'rgb(var(--violet) / <alpha-value>)',
        sky:    'rgb(var(--sky) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        card:  'var(--shadow-card)',
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

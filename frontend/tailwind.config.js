/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      colors: {
        bg: {
          DEFAULT: '#0b0d12',
          raised: '#12151c',
          card:   '#161a23',
          hover:  '#1c2130',
        },
        border: {
          DEFAULT: '#242938',
          strong:  '#303648',
        },
        text: {
          DEFAULT: '#e8eaf1',
          muted:   '#9ca4b5',
          subtle:  '#6f7a91',
        },
        accent: {
          DEFAULT: '#7c5cff',
          hover:   '#8f74ff',
        },
        tier: {
          high:   '#22c55e',
          midhi:  '#4ade80',
          mid:    '#eab308',
          midlo:  '#f97316',
          low:    '#ef4444',
        },
      },
      boxShadow: {
        card:  '0 1px 0 0 rgba(255,255,255,0.02) inset, 0 4px 24px rgba(0,0,0,0.35)',
        glow:  '0 0 0 1px rgba(124,92,255,0.25), 0 8px 24px rgba(124,92,255,0.15)',
      },
    },
  },
  plugins: [],
};

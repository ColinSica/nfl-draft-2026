/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        // Editorial serif for display — avoids generic AI sans defaults.
        display: ['"Fraunces"', 'ui-serif', 'Georgia', 'serif'],
        // Distinctive sans body — Instrument Sans has character vs Inter.
        sans: ['"Instrument Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        'display-xl': ['clamp(3rem, 8vw, 6rem)', { lineHeight: '0.95', letterSpacing: '-0.03em' }],
        'display-lg': ['clamp(2.25rem, 5vw, 3.75rem)', { lineHeight: '1', letterSpacing: '-0.025em' }],
        'display-md': ['clamp(1.75rem, 3.5vw, 2.5rem)', { lineHeight: '1.05', letterSpacing: '-0.02em' }],
      },
      colors: {
        // Warm-ink-on-paper aesthetic — avoids cold-slate cliche.
        ink: {
          DEFAULT: '#0C0D0E',
          raised: '#141618',
          card:   '#1A1D20',
          hover:  '#22262B',
          edge:   '#2D3137',
          rule:   '#3A3F47',
        },
        paper: {
          DEFAULT: '#EDE7D8',
          muted:   '#A29987',
          subtle:  '#716A5C',
          faint:   '#48443B',
        },
        // LEGACY aliases so existing pages don't break during transition
        bg: {
          DEFAULT: '#0C0D0E',
          raised:  '#141618',
          card:    '#1A1D20',
          hover:   '#22262B',
        },
        border: {
          DEFAULT: '#2D3137',
          strong:  '#3A3F47',
        },
        text: {
          DEFAULT: '#EDE7D8',
          muted:   '#A29987',
          subtle:  '#716A5C',
        },
        // MODE COLORS — visually distinct for product trust
        mode: {
          indie:      '#C8F169',
          indieDim:   '#6F8334',
          bench:      '#E6AF5A',
          benchDim:   '#82633A',
          compare:    '#6AA4D9',
          compareDim: '#3F6388',
        },
        state: {
          fresh:   '#7CC77C',
          stale:   '#E6AF5A',
          broken:  '#D66C5A',
          pending: '#A29987',
        },
        tier: {
          high:   '#C8F169',
          midhi:  '#A3D14A',
          mid:    '#E6AF5A',
          midlo:  '#D66C5A',
          low:    '#A29987',
          r1:   '#C8F169',
          r2:   '#E6AF5A',
          r3:   '#D66C5A',
          r4:   '#A29987',
          udfa: '#716A5C',
        },
        accent: {
          DEFAULT: '#C8F169',
          hover:   '#D4FF7A',
        },
      },
      boxShadow: {
        card:   '0 1px 0 rgba(237,231,216,0.04) inset, 0 8px 32px rgba(0,0,0,0.55)',
        chip:   '0 0 0 1px rgba(237,231,216,0.08), 0 2px 8px rgba(0,0,0,0.25)',
        rise:   '0 12px 40px -8px rgba(0,0,0,0.6)',
        glow:   '0 0 0 1px rgba(200,241,105,0.3), 0 8px 24px rgba(200,241,105,0.12)',
      },
      backgroundImage: {
        'paper-grain':
          "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 0.93 0 0 0 0 0.91 0 0 0 0 0.85 0 0 0 0.035 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
      },
      letterSpacing: {
        'caps': '0.18em',
        'caps-tight': '0.12em',
      },
      transitionTimingFunction: {
        'editorial': 'cubic-bezier(0.2, 0, 0, 1)',
      },
    },
  },
  plugins: [],
};

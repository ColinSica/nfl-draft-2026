/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  // Light-first theme — the product is a LIGHT sports-media product now.
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        display: ['"Barlow Condensed"', 'Oswald', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        sans: ['"Barlow"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        'display-xl': ['clamp(3.5rem, 11vw, 9rem)', { lineHeight: '0.85', letterSpacing: '-0.02em' }],
        'display-lg': ['clamp(2.5rem, 7vw, 5.5rem)', { lineHeight: '0.9', letterSpacing: '-0.015em' }],
        'display-md': ['clamp(1.875rem, 4vw, 3rem)', { lineHeight: '0.95', letterSpacing: '-0.01em' }],
      },
      colors: {
        // LIGHT THEME — warm newsprint base, crisp white cards, ink text.
        // Reverse of the prior dark: paper is now the surface, ink is text.
        paper: {
          DEFAULT: '#F5F2EA',   // warm newsprint
          surface: '#FFFFFF',   // card surface
          raised:  '#FBFAF5',   // very subtle raise
          hover:   '#EBE7DB',   // hover
          muted:   '#5B6370',   // muted text
          subtle:  '#848B98',   // subtle text
          faint:   '#B4B9C2',   // placeholders
        },
        ink: {
          DEFAULT: '#12151B',   // near-black text
          soft:    '#2A2E37',   // softer text
          edge:    '#D9D4C7',   // borders on light bg
          rule:    '#C3BDAE',   // stronger rules
          // dark-ink surfaces for select hero/contrast sections
          deep:    '#0F1218',
          raised:  '#1B1F27',
          card:    '#232832',
          hover:   '#2E3440',
        },
        // MODE ACCENTS — saturated for light-bg contrast
        mode: {
          indie:      '#D9A400',  // darkened broadcast yellow for readability on white
          indieDim:   '#7A5D00',
          indiePop:   '#FFD23F',  // bright variant for dark contexts
          bench:      '#1F6FEB',  // bright broadcast blue
          benchDim:   '#104399',
          compare:    '#17A870',  // deeper field green on light
          compareDim: '#0E6945',
        },
        // Urgent / LIVE
        live:      '#DC2F3D',
        liveDim:   '#7A1820',
        state: {
          fresh:   '#17A870',
          stale:   '#D9A400',
          broken:  '#DC2F3D',
          pending: '#848B98',
        },
        tier: {
          r1:   '#D9A400',
          r2:   '#1F6FEB',
          r3:   '#17A870',
          r4:   '#848B98',
          udfa: '#B4B9C2',
          high:  '#17A870',
          midhi: '#1F6FEB',
          mid:   '#D9A400',
          midlo: '#E68A6A',
          low:   '#DC2F3D',
        },
        // LEGACY aliases (light defaults)
        bg: {
          DEFAULT: '#F5F2EA',
          raised:  '#FBFAF5',
          card:    '#FFFFFF',
          hover:   '#EBE7DB',
        },
        border: {
          DEFAULT: '#D9D4C7',
          strong:  '#C3BDAE',
        },
        text: {
          DEFAULT: '#12151B',
          muted:   '#5B6370',
          subtle:  '#848B98',
        },
        accent: {
          DEFAULT: '#D9A400',
          hover:   '#B88A00',
        },
      },
      boxShadow: {
        card:   '0 1px 2px rgba(18,21,27,0.04), 0 4px 14px -2px rgba(18,21,27,0.05)',
        'card-raised': '0 1px 2px rgba(18,21,27,0.05), 0 10px 28px -6px rgba(18,21,27,0.10)',
        chip:   '0 1px 3px rgba(18,21,27,0.08)',
        rise:   '0 20px 50px -12px rgba(18,21,27,0.18)',
        glow:   '0 0 0 3px rgba(217,164,0,0.18), 0 6px 20px rgba(217,164,0,0.15)',
      },
      backgroundImage: {
        // Subtle paper-texture atmosphere on light bg
        'stadium':
          'radial-gradient(at 10% -8%, rgba(31,111,235,0.05) 0, transparent 48%), ' +
          'radial-gradient(at 90% 105%, rgba(217,164,0,0.05) 0, transparent 42%)',
      },
      letterSpacing: {
        'caps': '0.14em',
        'caps-tight': '0.08em',
      },
      transitionTimingFunction: {
        'broadcast': 'cubic-bezier(0.2, 0.9, 0.1, 1)',
        'editorial': 'cubic-bezier(0.2, 0, 0, 1)',
      },
    },
  },
  plugins: [],
};

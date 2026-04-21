/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        // Broadcast-authority condensed sans for pick numbers & headlines.
        display: ['"Barlow Condensed"', 'Oswald', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        // Body — the non-condensed sibling, clean and athletic.
        sans: ['"Barlow"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        'display-xl': ['clamp(3.5rem, 11vw, 9rem)', { lineHeight: '0.85', letterSpacing: '-0.02em' }],
        'display-lg': ['clamp(2.5rem, 7vw, 5.5rem)', { lineHeight: '0.9', letterSpacing: '-0.015em' }],
        'display-md': ['clamp(1.875rem, 4vw, 3rem)', { lineHeight: '0.95', letterSpacing: '-0.01em' }],
      },
      colors: {
        // Broadcast-authority palette: cool navy ink + stark white + saturated accents.
        ink: {
          DEFAULT: '#06080F',   // deep navy-black base
          raised:  '#0E131D',   // raised surface
          card:    '#141A25',   // card surface
          hover:   '#1A2230',   // hover state
          edge:    '#252D3D',   // edge/divider
          rule:    '#36405A',   // stronger rule
        },
        // "Paper" now reads as stark white (broadcast)
        paper: {
          DEFAULT: '#F3F6FA',
          muted:   '#9FACC2',
          subtle:  '#6B7A94',
          faint:   '#3B4558',
        },
        // MODE COLORS — broadcast saturated (yellow/blue/green)
        mode: {
          indie:      '#FFD23F',  // Independent = broadcast yellow
          indieDim:   '#8A6E1F',
          bench:      '#4A9EFF',  // Benchmark = broadcast blue
          benchDim:   '#26578F',
          compare:    '#2EE09A',  // Compare = bright field green
          compareDim: '#1A7D55',
        },
        // Urgent / live state
        live:      '#E63946',     // broadcast red for LIVE / urgent
        liveDim:   '#7D1F26',
        // State palette
        state: {
          fresh:   '#2EE09A',
          stale:   '#FFD23F',
          broken:  '#E63946',
          pending: '#9FACC2',
        },
        // Tier palette
        tier: {
          r1:   '#FFD23F',
          r2:   '#4A9EFF',
          r3:   '#2EE09A',
          r4:   '#9FACC2',
          udfa: '#6B7A94',
          // legacy aliases for older components
          high:  '#2EE09A',
          midhi: '#4A9EFF',
          mid:   '#FFD23F',
          midlo: '#E6826A',
          low:   '#E63946',
        },
        // LEGACY aliases so existing pages don't break during transition
        bg: {
          DEFAULT: '#06080F',
          raised:  '#0E131D',
          card:    '#141A25',
          hover:   '#1A2230',
        },
        border: {
          DEFAULT: '#252D3D',
          strong:  '#36405A',
        },
        text: {
          DEFAULT: '#F3F6FA',
          muted:   '#9FACC2',
          subtle:  '#6B7A94',
        },
        accent: {
          DEFAULT: '#FFD23F',
          hover:   '#FFDD6B',
        },
      },
      boxShadow: {
        card:   '0 1px 0 rgba(243,246,250,0.04) inset, 0 12px 40px rgba(0,0,0,0.55)',
        chip:   '0 0 0 1px rgba(243,246,250,0.08), 0 2px 10px rgba(0,0,0,0.35)',
        rise:   '0 14px 48px -10px rgba(0,0,0,0.65)',
        glow:   '0 0 0 1px rgba(255,210,63,0.35), 0 12px 32px rgba(255,210,63,0.18)',
      },
      backgroundImage: {
        // Stadium-style radial atmosphere — cool, energetic, not academic
        'stadium':
          'radial-gradient(at 10% -10%, rgba(74,158,255,0.12) 0, transparent 50%), ' +
          'radial-gradient(at 90% 110%, rgba(255,210,63,0.08) 0, transparent 40%), ' +
          'radial-gradient(at 50% 50%, rgba(230,57,70,0.04) 0, transparent 70%)',
        // Thin yard-line stripes for field texture
        'field-lines':
          'repeating-linear-gradient(90deg, transparent 0px, transparent 79px, rgba(243,246,250,0.025) 79px, rgba(243,246,250,0.025) 80px)',
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

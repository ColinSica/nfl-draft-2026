/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        // Fraunces for display (variable, optical-size aware — editorial serif with
        // real character). Source Serif 4 for body reading type. IBM Plex Mono
        // for ALL data — the canonical research/terminal mono. Plex Sans for
        // navigation and incidental labels where mono would read too sterile.
        display: ['Fraunces', 'GT Sectra', 'Times New Roman', 'serif'],
        serif:   ['"Source Serif 4"', 'Fraunces', 'Georgia', 'serif'],
        body:    ['"Source Serif 4"', 'Georgia', 'serif'],
        mono:    ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
        sans:    ['"IBM Plex Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'dateline': ['0.68rem', { lineHeight: '1', letterSpacing: '0.18em' }],
        'caption':  ['0.78rem', { lineHeight: '1.35' }],
      },
      colors: {
        // FT / WSJ / research-note palette. Warm cream paper, deep near-black ink,
        // FT salmon as the editorial accent. Secondary colors are desaturated —
        // muted sage for buy/long, deep burgundy for sell/flag, amber for warn.
        paper: {
          DEFAULT: '#F7EFDF',   // FT salmon-cream page base
          surface: '#FBF5E8',   // slightly brighter for raised cards
          raised:  '#FDF9ED',   // lightest — side columns
          hover:   '#EEE3CA',   // subtle hover
          muted:   '#7A6E58',
          subtle:  '#9C8E76',
          faint:   '#BDB09A',
          edge:    '#E4D7B7',   // subtle border on paper
        },
        ink: {
          DEFAULT: '#1A1612',   // near-black, warm undertone (not pure black)
          soft:    '#3B342C',
          muted:   '#6B6154',
          edge:    '#C9B995',   // visible rule on paper
          rule:    '#AA9872',   // stronger rule
          // Dark surfaces for contrast sections (Bloomberg-style reversal)
          deep:    '#15110D',
          raised:  '#211C16',
          card:    '#2B251D',
          hover:   '#3A3226',
        },
        accent: {
          // Salmon — FT pink on serious paper. Used sparingly: headers, kickers,
          // active rules. NOT buttons or large blocks.
          salmon:      '#C65A3E',
          salmonSoft:  '#E08B6C',
          salmonDeep:  '#8F3A20',
          // Sell-side slate — for headers, data marks, institutional feel
          slate:       '#1E3A5F',
          slateDeep:   '#122B47',
          // Parchment highlight — used as pale wash behind active rows
          highlight:   'rgba(198, 90, 62, 0.10)',
        },
        // Signal colors — all muted, research-grade
        signal: {
          pos:     '#4A6B3F',   // muted sage — positive signal
          neg:     '#8C2E2A',   // deep burgundy — negative
          warn:    '#B57328',   // warm amber — warning/flag
          neutral: '#6B6154',
        },
        // LEGACY aliases so existing pages keep compiling
        bg: {
          DEFAULT: '#F7EFDF',
          raised:  '#FDF9ED',
          card:    '#FBF5E8',
          hover:   '#EEE3CA',
        },
        border: {
          DEFAULT: '#C9B995',
          strong:  '#AA9872',
        },
        text: {
          DEFAULT: '#1A1612',
          muted:   '#6B6154',
          subtle:  '#9C8E76',
        },
        // Back-compat for old class names still referenced across pages.
        // These forward to the new research palette without breaking builds.
        mode: {
          indie:      '#C65A3E',    // formerly goldenrod — now salmon
          indieDim:   '#8F3A20',
          indiePop:   '#E08B6C',
          bench:      '#1E3A5F',    // slate
          benchDim:   '#122B47',
          compare:    '#4A6B3F',    // sage
          compareDim: '#2F4428',
        },
        live:      '#8C2E2A',
        liveDim:   '#5E1E1C',
        state: {
          fresh:   '#4A6B3F',
          stale:   '#B57328',
          broken:  '#8C2E2A',
          pending: '#9C8E76',
        },
        tier: {
          r1:   '#C65A3E',
          r2:   '#1E3A5F',
          r3:   '#4A6B3F',
          r4:   '#6B6154',
          udfa: '#9C8E76',
          high:  '#4A6B3F',
          midhi: '#1E3A5F',
          mid:   '#B57328',
          midlo: '#C65A3E',
          low:   '#8C2E2A',
        },
      },
      boxShadow: {
        // Subtle paper-lift — research reports don't do drop shadows; use rules.
        card:          'none',
        'card-raised': '0 1px 0 rgba(26, 22, 18, 0.04)',
        chip:          'none',
        rise:          '0 1px 0 rgba(26, 22, 18, 0.06)',
        glow:          'inset 0 0 0 1px #C65A3E',
      },
      backgroundImage: {
        // Very faint paper-grain atmosphere; no radial gradients
        'stadium':  'none',
      },
      letterSpacing: {
        'caps':       '0.16em',
        'caps-tight': '0.08em',
        'editorial': '0.02em',
      },
      transitionTimingFunction: {
        'broadcast': 'cubic-bezier(0.2, 0.9, 0.1, 1)',
        'editorial': 'cubic-bezier(0.2, 0, 0, 1)',
      },
    },
  },
  plugins: [],
};

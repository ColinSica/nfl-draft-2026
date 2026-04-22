/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        // Fraunces for editorial display (variable, optical-size). Source Serif 4
        // for reading body. IBM Plex Mono for all data. IBM Plex Sans for nav.
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
        /* ───────────────────────────────────────────────────────────
         * NAVY-FORWARD INSTITUTIONAL — cream paper, deep navy ink.
         * Palette inspired by Morgan Stanley research, The Economist
         * masthead, and the NFL shield navy. Brass/gold is the single
         * refined accent. Nothing bright, nothing saturated.
         * ─────────────────────────────────────────────────────────── */
        paper: {
          DEFAULT: '#F3ECD6',   // warm parchment — slightly cooler/cleaner
          surface: '#F8F2DF',   // raised card surface
          raised:  '#FAF6E6',   // side rails / lightest
          hover:   '#E7DEC2',   // subtle hover
          muted:   '#6E6650',
          subtle:  '#8A8169',
          faint:   '#AEA68D',
          edge:    '#D9CDA9',   // soft border on paper
        },
        ink: {
          // Ink is now DEEP NAVY — the institutional voice. Used for body,
          // headlines, rules. Warm near-black is gone.
          DEFAULT: '#0B1F3A',   // institutional navy (NFL-shield-adjacent)
          soft:    '#1F385F',
          muted:   '#4D6893',
          edge:    '#B6A57F',   // brass-tinted rule on paper
          rule:    '#7F6D46',   // deeper rule
          // Navy-deep surfaces for rare contrast blocks (footer, headers)
          deep:    '#0A1A32',
          raised:  '#122745',
          card:    '#1C3359',
          hover:   '#243F6C',
        },
        accent: {
          // Brass / old-gold — single warm accent for emphasis. Used for
          // kickers, section markers, active rules. NOT for fills.
          brass:       '#B68A2F',
          brassSoft:   '#D6A945',
          brassDeep:   '#8A6620',
          // Salmon-ish keys kept as aliases so existing components compile
          salmon:      '#B68A2F',
          salmonSoft:  '#D6A945',
          salmonDeep:  '#8A6620',
          // Deep navy slate for heavy emphasis (masthead, buttons)
          slate:       '#0B1F3A',
          slateDeep:   '#071528',
          // Pale wash behind active rows
          highlight:   'rgba(11, 31, 58, 0.07)',
        },
        // Signal colors — all muted, research-grade
        signal: {
          pos:     '#3A6B46',   // field green — positive / long
          neg:     '#8C2E2A',   // deep burgundy — negative / sell
          warn:    '#B68A2F',   // brass — flag
          neutral: '#4D6893',
        },
        // LEGACY aliases so existing pages keep compiling
        bg: {
          DEFAULT: '#F3ECD6',
          raised:  '#FAF6E6',
          card:    '#F8F2DF',
          hover:   '#E7DEC2',
        },
        border: {
          DEFAULT: '#B6A57F',
          strong:  '#7F6D46',
        },
        text: {
          DEFAULT: '#0B1F3A',
          muted:   '#4D6893',
          subtle:  '#6E6650',
        },
        mode: {
          indie:      '#0B1F3A',   // formerly salmon — now institutional navy
          indieDim:   '#071528',
          indiePop:   '#1F385F',
          bench:      '#B68A2F',   // brass
          benchDim:   '#8A6620',
          compare:    '#3A6B46',   // field green
          compareDim: '#234029',
        },
        live:      '#8C2E2A',
        liveDim:   '#5E1E1C',
        state: {
          fresh:   '#3A6B46',
          stale:   '#B68A2F',
          broken:  '#8C2E2A',
          pending: '#8A8169',
        },
        tier: {
          r1:   '#B68A2F',        // brass — R1 is the premium tier
          r2:   '#0B1F3A',        // navy
          r3:   '#3A6B46',        // field green
          r4:   '#6E6650',
          udfa: '#AEA68D',
          high:  '#3A6B46',
          midhi: '#0B1F3A',
          mid:   '#B68A2F',
          midlo: '#B6763F',
          low:   '#8C2E2A',
        },
      },
      boxShadow: {
        card:          'none',
        'card-raised': '0 1px 0 rgba(11, 31, 58, 0.06)',
        chip:          'none',
        rise:          '0 1px 0 rgba(11, 31, 58, 0.08)',
        glow:          'inset 0 0 0 1px #B68A2F',
      },
      backgroundImage: {
        'stadium':  'none',
      },
      letterSpacing: {
        'caps':       '0.16em',
        'caps-tight': '0.08em',
        'editorial':  '0.02em',
      },
      transitionTimingFunction: {
        'broadcast': 'cubic-bezier(0.2, 0.9, 0.1, 1)',
        'editorial': 'cubic-bezier(0.2, 0, 0, 1)',
      },
    },
  },
  plugins: [],
};

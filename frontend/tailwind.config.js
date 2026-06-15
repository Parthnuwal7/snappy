/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      // Editorial palette. Cream paper, deep warm ink, oxblood accent
      // (the colour of legal seals and antique bookbinding).
      colors: {
        // Surfaces
        paper: {
          DEFAULT: '#F8F4EC',  // cream page background
          deep: '#F1EBDC',      // sunken / well
          edge: '#E8E0CC',      // banded sections
        },
        surface: {
          DEFAULT: '#FFFFFF',  // raised cards / inputs lift off the cream
          muted: '#FBF8F1',
        },

        // Text — warm near-black, not pure #000
        ink: {
          DEFAULT: '#1C1814',  // primary text
          soft: '#3A332B',     // secondary
          muted: '#6B6358',    // tertiary, meta
          faint: '#9A9082',    // disabled, captions
        },

        // Borders. Hairlines for editorial separation, no shadows.
        rule: {
          DEFAULT: '#D8D2C5',  // standard hairline
          soft: '#E8E2D2',     // subtle separation
          strong: '#A8A091',   // emphatic divider
        },

        // Single accent: oxblood. Used sparingly. Conveys gravity.
        oxblood: {
          DEFAULT: '#7A2E2E',
          deep: '#5D1F1F',
          soft: '#9B4848',
          wash: '#F2E5E5',     // tint for backgrounds
        },

        // Status colours — muted, document-like, never neon
        status: {
          paid:    { DEFAULT: '#3A6B47', wash: '#E8F0E9' },  // ledger green
          pending: { DEFAULT: '#9A6E1F', wash: '#F4ECDB' },  // ochre / aged paper
          overdue: { DEFAULT: '#7A2E2E', wash: '#F2E5E5' },  // oxblood
          draft:   { DEFAULT: '#6B6358', wash: '#EFEBE0' },  // ink muted
        },
      },

      fontFamily: {
        // Editorial serif for display, brand, and large numerals
        display: ['Fraunces', 'ui-serif', 'Georgia', 'serif'],
        // Refined neutral sans for UI text
        sans: ['"Public Sans"', 'system-ui', 'sans-serif'],
        // Tabular monospace for invoice numbers, IDs, amounts in tight layouts
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },

      fontSize: {
        // Small caps / eyebrow labels
        '2xs': ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.08em' }],
        // Body
        xs:  ['0.75rem',   { lineHeight: '1.1rem' }],
        sm:  ['0.875rem',  { lineHeight: '1.35rem' }],
        base:['0.9375rem', { lineHeight: '1.5rem' }],
        lg:  ['1.0625rem', { lineHeight: '1.65rem' }],
        // Display sizes — meant for Fraunces with tight tracking
        xl:  ['1.25rem',   { lineHeight: '1.7rem',  letterSpacing: '-0.01em' }],
        '2xl':['1.5rem',   { lineHeight: '1.85rem', letterSpacing: '-0.015em' }],
        '3xl':['1.875rem', { lineHeight: '2.15rem', letterSpacing: '-0.02em' }],
        '4xl':['2.5rem',   { lineHeight: '2.7rem',  letterSpacing: '-0.025em' }],
        '5xl':['3.5rem',   { lineHeight: '3.6rem',  letterSpacing: '-0.03em' }],
        '6xl':['4.75rem',  { lineHeight: '4.8rem',  letterSpacing: '-0.035em' }],
      },

      letterSpacing: {
        // Small caps labels need open tracking; display heads sit tight.
        eyebrow: '0.12em',
        legal:   '0.06em',
      },

      borderRadius: {
        none: '0',
        sm: '2px',
        DEFAULT: '3px',  // restrained, document-like
        md: '4px',
        lg: '6px',
        full: '9999px',
      },

      boxShadow: {
        // No drop shadows — editorial layout uses hairlines instead.
        // Reserved for rare emphasis (modal, overlays).
        hair: 'inset 0 -1px 0 #D8D2C5',
        seal: '0 0 0 1px #7A2E2E, 0 1px 0 #5D1F1F',
        soft: '0 1px 0 rgba(28, 24, 20, 0.04), 0 2px 4px -2px rgba(28, 24, 20, 0.06)',
        modal: '0 10px 40px -10px rgba(28, 24, 20, 0.25), 0 0 0 1px #D8D2C5',
      },

      maxWidth: {
        prose: '68ch',
        page: '1400px',
      },

      keyframes: {
        fadeUp: {
          '0%':   { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        'fade-up': 'fadeUp 500ms cubic-bezier(0.16, 1, 0.3, 1) both',
        'fade-in': 'fadeIn 400ms ease-out both',
      },
    },
  },
  plugins: [],
};

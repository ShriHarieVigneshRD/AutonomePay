/** @type {import('tailwindcss').Config} */
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Geist', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"Geist Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      // Type scale: ratio 1.25 from a 14px body.
      fontSize: {
        xs: ['12px', '16px'],
        sm: ['14px', '20px'],
        base: ['16px', '24px'],
        lg: ['18px', '26px'],
        xl: ['22px', '28px'],
        '2xl': ['28px', '34px'],
        '3xl': ['36px', '40px'],
        hero: ['52px', '56px'],
      },
      colors: {
        paper: token('paper'),
        sheet: { DEFAULT: token('sheet'), raised: token('sheet-raised') },
        well: token('well'),
        rule: token('rule'),
        ink: {
          DEFAULT: token('ink'),
          2: token('ink-2'),
          3: token('ink-3'),
          4: token('ink-4'),
        },
        accent: { DEFAULT: token('accent'), on: token('on-accent') },
        settled: token('settled'),
        caution: { DEFAULT: token('caution'), ink: token('caution-ink') },
        void: token('void'),
      },
      borderRadius: {
        control: '6px',
        panel: '10px',
        dialog: '14px',
      },
      transitionTimingFunction: {
        out: 'cubic-bezier(0.23, 1, 0.32, 1)',
      },
      keyframes: {
        stamp: {
          from: { opacity: '0', transform: 'scale(0.96)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        shimmer: {
          from: { backgroundPosition: '200% 0' },
          to: { backgroundPosition: '-200% 0' },
        },
      },
      animation: {
        stamp: 'stamp 180ms cubic-bezier(0.23, 1, 0.32, 1) both',
        shimmer: 'shimmer 1.6s linear infinite',
      },
    },
  },
  plugins: [],
};

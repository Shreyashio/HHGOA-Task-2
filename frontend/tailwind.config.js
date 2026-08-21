/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        marathi: ['"Tiro Devanagari Marathi"', 'serif'],
        mono: ['"JetBrains Mono"', 'Consolas', 'monospace', 'sans-serif'],
      },
      colors: {
        hhg: {
          bg: '#0B0E11',
          card: '#12161B',
          cardHover: '#181E24',
          surface: '#181E24',
          border: '#222933',
          borderLight: '#2F3946',
          coral: {
            DEFAULT: '#FF6B35',
            hover: '#FF8254',
            light: '#FFA07A',
            deep: '#CC4E1F',
            glow: 'rgba(255, 107, 53, 0.35)',
          },
          teal: {
            DEFAULT: '#1DBFA3',
            hover: '#25D9B9',
            light: '#5CEAD1',
            deep: '#148C77',
            glow: 'rgba(29, 191, 163, 0.3)',
          },
          gold: {
            DEFAULT: '#FFB347',
            light: '#FFC87A',
            dim: '#B37D32',
            glow: 'rgba(255, 179, 71, 0.3)',
          },
          sand: {
            DEFAULT: '#F5F0E6',
            muted: '#8A8F94',
            dim: '#585F68',
            dark: '#353B44',
          },
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 18s linear infinite',
        'spin-reverse': 'spin-reverse 22s linear infinite',
        'ping-slow': 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
        'ripple': 'ripple 1.8s ease-out infinite',
        'shimmer': 'shimmer 2.5s infinite',
        'fadeIn': 'fadeIn 0.3s ease-out both',
      },
      keyframes: {
        'spin-reverse': {
          '0%': { transform: 'rotate(360deg)' },
          '100%': { transform: 'rotate(0deg)' },
        },
        'ripple': {
          '0%': { transform: 'scale(0.95)', opacity: '0.8' },
          '50%': { transform: 'scale(1.25)', opacity: '0.3' },
          '100%': { transform: 'scale(1.55)', opacity: '0' },
        },
        'shimmer': {
          '100%': { transform: 'translateX(100%)' },
        },
        'fadeIn': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}

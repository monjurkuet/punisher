/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#09090b', // Zinc-950
        surface: '#18181b',    // Zinc-900
        border: '#27272a',     // Zinc-800
        primary: '#22c55e',    // Green-500 (Neon-ish)
        secondary: '#a1a1aa',  // Zinc-400
        highlight: '#e4e4e7',  // Zinc-200
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '6px',
        md: '8px',
        lg: '12px',
      },
      boxShadow: {
        'glow': '0 0 20px rgba(34, 197, 94, 0.15)',
      }
    },
  },
  plugins: [],
}

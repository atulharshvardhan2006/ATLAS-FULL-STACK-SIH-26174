/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"JetBrains Mono"', 'monospace'],
        display: ['"JetBrains Mono"', 'monospace'],
        mono: ['"JetBrains Mono"', 'monospace'],
        logo: ['"Orbitron"', 'sans-serif'],
      },
      colors: {
        brand: {
          bg: '#080808',
          panel: '#111111',
          border: '#222222',
          borderDark: '#333333',
          text: '#F8F8F8',
          textMuted: '#999999',
          textLight: '#666666',
          accent: '#A09653', // Pale gold
        },
        status: {
          green: '#548749',
          amber: '#A09653',
          red: '#873B3B'
        }
      }
    },
  },
  plugins: [],
}

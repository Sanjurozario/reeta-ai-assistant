/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        obsidian: {
          950: '#06080C',
          900: '#0B0E14',
          800: '#111722',
          700: '#1A2234',
        },
        navy: {
          950: '#0A0F1D',
          900: '#0F172A',
          800: '#1E293B',
          700: '#334155',
        },
        reeta: {
          cyan: '#06B6D4',
          cyanDim: '#0891B2',
          blue: '#3B82F6',
          electric: '#60A5FA',
          accent: '#0EA5E9',
          danger: '#EF4444',
          warning: '#F59E0B',
          success: '#10B981',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      }
    },
  },
  plugins: [],
}

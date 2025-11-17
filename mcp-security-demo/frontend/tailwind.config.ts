import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        breach: '#dc2626',
        blocked: '#f97316'
      }
    }
  },
  plugins: []
} satisfies Config

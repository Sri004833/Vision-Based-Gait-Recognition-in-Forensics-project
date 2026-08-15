/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: '#080C14',
          card: '#0F1626',
          panel: '#151F32',
          border: '#1E293B',
          accent: '#10B981', // green accent
          blue: '#3B82F6',
          text: '#F8FAFC',
          muted: '#64748B'
        }
      }
    },
  },
  plugins: [],
}

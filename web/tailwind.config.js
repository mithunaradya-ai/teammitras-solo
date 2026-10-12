/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        darkbg: '#0B0F19',
        darkcard: '#111827',
        darkborder: '#1F2937',
        accentblue: '#3B82F6',
        accentgreen: '#10B981',
        accentamber: '#F59E0B',
      }
    },
  },
  plugins: [],
}

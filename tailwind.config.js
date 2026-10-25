/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './frontend/src/**/*.{js,ts,jsx,tsx}'],
  theme: { extend: { colors: { ink: '#071018', panel: '#0d1822', line: '#1e303d', pulse: '#5eead4' } } },
  plugins: [],
}

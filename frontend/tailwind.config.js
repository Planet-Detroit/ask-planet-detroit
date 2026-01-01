/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'pd-blue': '#2f80c3',
        'pd-orange': '#ea5a39',
        'pd-text': '#111111',
        'pd-text-light': '#515151',
        'pd-bg': '#f5f5f5',
      },
      fontFamily: {
        'heading': ['Asap', 'sans-serif'],
        'body': ['Gelasio', 'Georgia', 'serif'],
      },
    },
  },
  plugins: [],
}

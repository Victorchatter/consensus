/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0B0B0F',
        surface: '#141419',
        elevated: '#1E1E26',
        accent: '#00D4AA',
        'accent-light': '#5FFFD4',
        danger: '#FF4757',
        warning: '#FFA502',
        info: '#1E90FF',
        text: '#E8E8EC',
        muted: '#8A8A98',
        dim: '#5A5A68',
        border: '#2A2A35',
        'border-hover': '#3A3A48',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
}

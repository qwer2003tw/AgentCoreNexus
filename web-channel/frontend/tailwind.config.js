/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark theme colors (default)
        'dark-bg': '#1a1a1a',
        'dark-surface': '#2d2d2d',
        'dark-surface-hover': '#3a3a3a',
        'dark-border': '#404040',
        'dark-text': '#ffffff',
        'dark-text-secondary': '#a0a0a0',
        
        // Light theme colors
        'light-bg': '#ffffff',
        'light-surface': '#f5f5f5',
        'light-surface-hover': '#e8e8e8',
        'light-border': '#e0e0e0',
        'light-text': '#1a1a1a',
        'light-text-secondary': '#666666',
        
        // Accent colors
        'primary': '#3b82f6',
        'primary-hover': '#2563eb',
        'success': '#10b981',
        'error': '#ef4444',
        'warning': '#f59e0b'
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif']
      }
    },
  },
  plugins: [],
}
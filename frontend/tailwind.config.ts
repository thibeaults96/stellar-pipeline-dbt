import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        void: '#080b14',
        deep: '#0d1220',
        panel: '#111827',
        'panel-border': '#1e2d45',
        accent: '#00d4ff',
        'accent-dim': 'rgba(0,212,255,0.08)',
        stellar: {
          green: '#00ff9d',
          amber: '#ffb800',
          red: '#ff3d5a',
          purple: '#a855f7',
          text: '#c8d8e8',
          'text-dim': '#4a6070',
          'text-bright': '#e8f4ff',
        },
      },
      fontFamily: {
        orbitron: ['Orbitron', 'sans-serif'],
        'mono-tech': ['"Share Tech Mono"', 'monospace'],
        exo: ['"Exo 2"', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
export default config;

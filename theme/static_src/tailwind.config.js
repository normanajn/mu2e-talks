/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    '../../apps/**/templates/**/*.html',
    '../../templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        'mu2e-primary':      '#0f766e',
        'mu2e-primary-hover':'#115e59',
        'mu2e-accent':       '#2563eb',
        'mu2e-accent-soft':  '#dbeafe',
        'scd-primary':       '#0f766e',
        'scd-primary-hover': '#115e59',
        'scd-accent':        '#2563eb',
        'scd-accent-soft':   '#dbeafe',
      },
    },
  },
  plugins: [],
}

/** Privé external design system — palette mirrored from assets/theme.css. */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#0E3C5C', dark: '#0A2E47' },
        secondary: '#1F6FA8',
        tertiary: '#64748B',
        neutral: '#F7F8FA',
        ink: '#0F2433',
        border: '#E2E8F0',
        success: '#16A34A',
        danger: '#DC2626',
        inverted: '#1E293B',
        // Brand green used only within the logo mark.
        brandgreen: '#5FC08D',
      },
      fontFamily: {
        sans: ['proxima-nova', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

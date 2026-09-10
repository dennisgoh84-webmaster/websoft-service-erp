import { useTheme } from '../lib/ThemeContext'

/** Bright/Dark theme switch -- rendered once in Layout's top bar so it
 * appears on every module screen without each page wiring it up itself. */
export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggleTheme}
      aria-label={`Switch to ${isDark ? 'bright' : 'dark'} theme`}
      title={`Switch to ${isDark ? 'bright' : 'dark'} theme`}
    >
      <span className="theme-toggle-icon">{isDark ? '\u{1F319}' : '\u{2600}\u{FE0F}'}</span>
      {isDark ? 'Dark' : 'Bright'}
    </button>
  )
}

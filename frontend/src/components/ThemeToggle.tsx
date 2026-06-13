import { useTheme } from "../lib/theme";

// Light/dark toggle button shown in the header corner.
export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      className="toggle"
      onClick={toggle}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
    >
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}

import { useState } from 'react';

const isDark = () => document.documentElement.classList.contains('dark');

/** Light/dark toggle. The initial theme is applied by the inline script in index.html. */
export function useTheme() {
  const [dark, setDark] = useState(isDark);
  const toggle = () => {
    const next = !dark;
    document.documentElement.classList.toggle('dark', next);
    try {
      localStorage.setItem('theme', next ? 'dark' : 'light');
    } catch {
      /* storage unavailable: the choice lasts for this page only */
    }
    setDark(next);
  };
  return { dark, toggle };
}

import { createContext, useContext, useEffect, useState } from 'react';import { jsx as _jsx } from "react/jsx-runtime";














const initialState = {
  theme: 'system',
  setTheme: () => null
};

const ThemeProviderContext = /*#__PURE__*/createContext(initialState);

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = 'vite-ui-theme',
  ...props
}) {
  const [theme, setTheme] = useState(
    () => localStorage.getItem(storageKey) || defaultTheme
  );

  useEffect(() => {
    const root = window.document.documentElement;

    root.classList.remove('light', 'dark');

    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').
      matches ?
      'dark' :
      'light';

      root.classList.add(systemTheme);
      return;
    }

    root.classList.add(theme);
  }, [theme]);

  const value = {
    theme,
    setTheme: (theme) => {
      localStorage.setItem(storageKey, theme);
      setTheme(theme);
    }
  };

  return (/*#__PURE__*/
    _jsx(ThemeProviderContext.Provider, { ...props, value: value, children:
      children }
    ));

}

export const useTheme = () => {
  const context = useContext(ThemeProviderContext);

  if (context === undefined)
  throw new Error('useTheme must be used within a ThemeProvider');

  return context;
};

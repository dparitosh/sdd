import { Moon, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTheme } from '@/components/theme-provider';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger } from
'@/components/ui/dropdown-menu';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

export function ThemeToggle() {
  const { setTheme, theme } = useTheme();

  return (/*#__PURE__*/
    _jsxs(DropdownMenu, { children: [/*#__PURE__*/
      _jsx(DropdownMenuTrigger, { asChild: true, children: /*#__PURE__*/
        _jsxs(Button, {
          variant: "ghost",
          size: "icon",
          "aria-label": "Toggle theme",
          "aria-expanded": "false",
          "aria-haspopup": "true", children: [/*#__PURE__*/

          _jsx(Sun, { className: "h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" }), /*#__PURE__*/
          _jsx(Moon, { className: "absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" }), /*#__PURE__*/
          _jsx("span", { className: "sr-only", children: "Toggle theme" })] }
        ) }
      ), /*#__PURE__*/
      _jsxs(DropdownMenuContent, { align: "end", "aria-label": "Theme options", children: [/*#__PURE__*/
        _jsxs(DropdownMenuItem, {
          onClick: () => setTheme('light'),
          "aria-label": "Light theme",
          "aria-current": theme === 'light' ? 'true' : 'false', children: [/*#__PURE__*/

          _jsx(Sun, { className: "mr-2 h-4 w-4" }), /*#__PURE__*/
          _jsx("span", { children: "Light" })] }
        ), /*#__PURE__*/
        _jsxs(DropdownMenuItem, {
          onClick: () => setTheme('dark'),
          "aria-label": "Dark theme",
          "aria-current": theme === 'dark' ? 'true' : 'false', children: [/*#__PURE__*/

          _jsx(Moon, { className: "mr-2 h-4 w-4" }), /*#__PURE__*/
          _jsx("span", { children: "Dark" })] }
        ), /*#__PURE__*/
        _jsxs(DropdownMenuItem, {
          onClick: () => setTheme('system'),
          "aria-label": "System theme",
          "aria-current": theme === 'system' ? 'true' : 'false', children: [/*#__PURE__*/

          _jsx("span", { className: "mr-2", children: "\uD83D\uDCBB" }), /*#__PURE__*/
          _jsx("span", { children: "System" })] }
        )] }
      )] }
    ));

}

export default ThemeToggle;

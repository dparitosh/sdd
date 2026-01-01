import { Moon, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTheme } from '@/components/theme-provider';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
export function ThemeToggle() {
  const {
    setTheme,
    theme
  } = useTheme();
  return <DropdownMenu><DropdownMenuTrigger asChild><Button variant="ghost" size="icon" aria-label="Toggle theme" aria-expanded="false" aria-haspopup="true"><Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" /><Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" /><span className="sr-only">Toggle theme</span></Button></DropdownMenuTrigger><DropdownMenuContent align="end" aria-label="Theme options"><DropdownMenuItem onClick={() => setTheme('light')} aria-label="Light theme" aria-current={theme === 'light' ? 'true' : 'false'}><Sun className="mr-2 h-4 w-4" /><span>Light</span></DropdownMenuItem><DropdownMenuItem onClick={() => setTheme('dark')} aria-label="Dark theme" aria-current={theme === 'dark' ? 'true' : 'false'}><Moon className="mr-2 h-4 w-4" /><span>Dark</span></DropdownMenuItem><DropdownMenuItem onClick={() => setTheme('system')} aria-label="System theme" aria-current={theme === 'system' ? 'true' : 'false'}><span className="mr-2">💻</span><span>System</span></DropdownMenuItem></DropdownMenuContent></DropdownMenu>;
}
export default ThemeToggle;

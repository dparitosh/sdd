import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Shield, Wrench, ClipboardCheck } from 'lucide-react';
import { useRole } from '../hooks/useRole';

const ROLE_META = {
  engineer: { label: 'Engineer', icon: Wrench, color: 'bg-blue-500/10 text-blue-700 dark:text-blue-400' },
  quality:  { label: 'Quality Head', icon: ClipboardCheck, color: 'bg-amber-500/10 text-amber-700 dark:text-amber-400' },
  admin:    { label: 'Admin', icon: Shield, color: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400' },
} as const;

/**
 * Dropdown allowing the user to switch between Engineer, Quality Head, Admin personas.
 * Persists choice to localStorage and triggers a route reload.
 */
export default function RoleSelector() {
  const { role, setRole } = useRole();
  const meta = ROLE_META[role];

  return (
    <div className="flex items-center gap-2">
      <Badge variant="outline" className={`${meta.color} px-2 py-1 text-xs font-medium`}>
        <meta.icon className="h-3 w-3 mr-1" />
        {meta.label}
      </Badge>
      <Select value={role} onValueChange={(v) => setRole(v)}>
        <SelectTrigger className="w-[140px] h-8 text-xs">
          <SelectValue placeholder="Switch role" />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(ROLE_META).map(([key, m]) => (
            <SelectItem key={key} value={key}>
              <span className="flex items-center gap-2">
                <m.icon className="h-3.5 w-3.5" />
                {m.label}
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

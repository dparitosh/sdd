import { useState } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { useNavigate } from 'react-router-dom';
import { Button } from '@ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@ui/avatar';
import { Badge } from '@ui/badge';
import { User, LogOut, Settings, Shield } from 'lucide-react';
import { apiClient } from '@/services/api';
import { toast } from 'sonner';
export default function UserMenu() {
  const {
    user,
    logout
  } = useAuthStore();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const handleLogout = async () => {
    setIsLoading(true);
    try {
      await apiClient.post('/auth/logout');
      logout();
      toast.success('Logged out successfully');
      navigate('/login');
    } catch (error) {
      logout();
      navigate('/login');
    } finally {
      setIsLoading(false);
    }
  };
  if (!user) return null;
  const initials = user.name?.split(' ').map(n => n[0]).join('').toUpperCase() || user.username?.substring(0, 2).toUpperCase() || 'U';
  const displayName = user.name || user.username;
  const displayEmail = user.email || `${user.username}@mbse.local`;
  return <DropdownMenu><DropdownMenuTrigger asChild><Button variant="ghost" className="relative h-10 w-10 rounded-full"><Avatar className="h-10 w-10"><AvatarImage src={user.avatar} alt={displayName} /><AvatarFallback>{initials}</AvatarFallback></Avatar></Button></DropdownMenuTrigger><DropdownMenuContent className="w-64" align="end"><DropdownMenuLabel><div className="flex flex-col space-y-1"><p className="text-sm font-medium leading-none">{displayName}</p><p className="text-xs leading-none text-muted-foreground">{displayEmail}</p><div className="flex gap-1 mt-2">{user.role && <Badge variant="secondary" className="text-xs">{user.role}</Badge>}{user.roles?.map(role => <Badge variant="secondary" className="text-xs">{role}</Badge>)}</div></div></DropdownMenuLabel><DropdownMenuSeparator /><DropdownMenuItem onClick={() => navigate('/profile')}><User className="mr-2 h-4 w-4" />Profile</DropdownMenuItem><DropdownMenuItem onClick={() => navigate('/settings')}><Settings className="mr-2 h-4 w-4" />Settings</DropdownMenuItem>{(user.role === 'admin' || user.roles?.includes('admin')) && <DropdownMenuItem onClick={() => navigate('/admin')}><Shield className="mr-2 h-4 w-4" />Admin Panel</DropdownMenuItem>}<DropdownMenuSeparator /><DropdownMenuItem onClick={handleLogout} disabled={isLoading}><LogOut className="mr-2 h-4 w-4" />{isLoading ? 'Logging out...' : 'Logout'}</DropdownMenuItem></DropdownMenuContent></DropdownMenu>;
}

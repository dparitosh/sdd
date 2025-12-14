import { useState } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { useNavigate } from 'react-router-dom';
import { Button } from '@ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger } from
'@ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@ui/avatar';
import { Badge } from '@ui/badge';
import { User, LogOut, Settings, Shield } from 'lucide-react';
import { apiClient } from '@/services/api';
import { toast } from 'sonner';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

export default function UserMenu() {
  const { user, logout } = useAuthStore();
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

  // Get initials from username (first 2 chars) or name if available
  const initials = user.name?.
  split(' ').
  map((n) => n[0]).
  join('').
  toUpperCase() || user.username?.substring(0, 2).toUpperCase() || 'U';

  // Display name: use name if available, otherwise username
  const displayName = user.name || user.username;
  const displayEmail = user.email || `${user.username}@mbse.local`;

  return (/*#__PURE__*/
    _jsxs(DropdownMenu, { children: [/*#__PURE__*/
      _jsx(DropdownMenuTrigger, { asChild: true, children: /*#__PURE__*/
        _jsx(Button, { variant: "ghost", className: "relative h-10 w-10 rounded-full", children: /*#__PURE__*/
          _jsxs(Avatar, { className: "h-10 w-10", children: [/*#__PURE__*/
            _jsx(AvatarImage, { src: user.avatar, alt: displayName }), /*#__PURE__*/
            _jsx(AvatarFallback, { children: initials })] }
          ) }
        ) }
      ), /*#__PURE__*/
      _jsxs(DropdownMenuContent, { className: "w-64", align: "end", children: [/*#__PURE__*/
        _jsx(DropdownMenuLabel, { children: /*#__PURE__*/
          _jsxs("div", { className: "flex flex-col space-y-1", children: [/*#__PURE__*/
            _jsx("p", { className: "text-sm font-medium leading-none", children: displayName }), /*#__PURE__*/
            _jsx("p", { className: "text-xs leading-none text-muted-foreground", children: displayEmail }), /*#__PURE__*/
            _jsxs("div", { className: "flex gap-1 mt-2", children: [
              user.role && /*#__PURE__*/
              _jsx(Badge, { variant: "secondary", className: "text-xs", children:
                user.role }
              ),

              user.roles?.map((role) => /*#__PURE__*/
              _jsx(Badge, { variant: "secondary", className: "text-xs", children:
                role }, role
              )
              )] }
            )] }
          ) }
        ), /*#__PURE__*/
        _jsx(DropdownMenuSeparator, {}), /*#__PURE__*/
        _jsxs(DropdownMenuItem, { onClick: () => navigate('/profile'), children: [/*#__PURE__*/
          _jsx(User, { className: "mr-2 h-4 w-4" }), "Profile"] }

        ), /*#__PURE__*/
        _jsxs(DropdownMenuItem, { onClick: () => navigate('/settings'), children: [/*#__PURE__*/
          _jsx(Settings, { className: "mr-2 h-4 w-4" }), "Settings"] }

        ),
        (user.role === 'admin' || user.roles?.includes('admin')) && /*#__PURE__*/
        _jsxs(DropdownMenuItem, { onClick: () => navigate('/admin'), children: [/*#__PURE__*/
          _jsx(Shield, { className: "mr-2 h-4 w-4" }), "Admin Panel"] }

        ), /*#__PURE__*/

        _jsx(DropdownMenuSeparator, {}), /*#__PURE__*/
        _jsxs(DropdownMenuItem, { onClick: handleLogout, disabled: isLoading, children: [/*#__PURE__*/
          _jsx(LogOut, { className: "mr-2 h-4 w-4" }),
          isLoading ? 'Logging out...' : 'Logout'] }
        )] }
      )] }
    ));

}

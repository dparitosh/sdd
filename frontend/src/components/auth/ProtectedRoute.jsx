import { Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { Alert, AlertDescription } from '@ui/alert';
import { ShieldAlert } from 'lucide-react';
export default function ProtectedRoute({
  children,
  requiredRoles = [],
  requireAny = true
}) {
  const {
    isAuthenticated,
    user
  } = useAuthStore();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  if (requiredRoles.length > 0) {
    const hasRequiredAccess = requireAny ? requiredRoles.some(role => user?.roles?.includes(role)) : requiredRoles.every(role => user?.roles?.includes(role));
    if (!hasRequiredAccess) {
      return <div className="flex h-screen items-center justify-center p-4"><Alert variant="destructive" className="max-w-md"><ShieldAlert className="h-4 w-4" /><AlertDescription>You don't have permission to access this page. Required roles: {requiredRoles.join(', ')}</AlertDescription></Alert></div>;
    }
  }
  return <>{children}</>;
}

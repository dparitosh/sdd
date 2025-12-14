
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { Alert, AlertDescription } from '@ui/alert';
import { ShieldAlert } from 'lucide-react';import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";







export default function ProtectedRoute({
  children,
  requiredRoles = [],
  requireAny = true
}) {
  const { isAuthenticated, user } = useAuthStore();

  if (!isAuthenticated) {
    return /*#__PURE__*/_jsx(Navigate, { to: "/login", replace: true });
  }

  // Check role requirements
  if (requiredRoles.length > 0) {
    const hasRequiredAccess = requireAny ?
    requiredRoles.some((role) => user?.roles?.includes(role)) :
    requiredRoles.every((role) => user?.roles?.includes(role));

    if (!hasRequiredAccess) {
      return (/*#__PURE__*/
        _jsx("div", { className: "flex h-screen items-center justify-center p-4", children: /*#__PURE__*/
          _jsxs(Alert, { variant: "destructive", className: "max-w-md", children: [/*#__PURE__*/
            _jsx(ShieldAlert, { className: "h-4 w-4" }), /*#__PURE__*/
            _jsxs(AlertDescription, { children: ["You don't have permission to access this page. Required roles:",
              ' ',
              requiredRoles.join(', ')] }
            )] }
          ) }
        ));

    }
  }

  return /*#__PURE__*/_jsx(_Fragment, { children: children });
}

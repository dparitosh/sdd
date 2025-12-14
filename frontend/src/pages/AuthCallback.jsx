import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { apiClient } from '@/services/api';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

export default function AuthCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const setAuth = useAuthStore((state) => state.setAuth);

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');

      if (error) {
        toast.error('Authentication failed', {
          description: searchParams.get('error_description') || error
        });
        navigate('/login');
        return;
      }

      if (!code) {
        toast.error('Invalid callback', {
          description: 'No authorization code received'
        });
        navigate('/login');
        return;
      }

      try {
        // Exchange code for token
        const response = await apiClient.post(







          '/auth/oauth/callback', {
            code,
            state
          });

        setAuth(response.token, response.user);
        toast.success('Login successful!');
        navigate('/dashboard');
      } catch (error) {
        toast.error('Authentication failed', {
          description: error.response?.data?.error || 'Failed to process OAuth callback'
        });
        navigate('/login');
      }
    };

    handleCallback();
  }, [searchParams, setAuth, navigate]);

  return (/*#__PURE__*/
    _jsx("div", { className: "flex min-h-screen items-center justify-center", children: /*#__PURE__*/
      _jsxs("div", { className: "text-center space-y-4", children: [/*#__PURE__*/
        _jsx(Loader2, { className: "h-12 w-12 animate-spin mx-auto text-primary" }), /*#__PURE__*/
        _jsx("p", { className: "text-muted-foreground", children: "Processing authentication..." })] }
      ) }
    ));

}

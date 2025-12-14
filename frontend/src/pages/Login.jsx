import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { useAuthStore } from '@/stores/authStore';
import { apiClient } from '@/services/api';
import { Button } from '@ui/button';
import { Input } from '@ui/input';
import { Label } from '@ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@ui/tabs';
import { Separator } from '@ui/separator';
import { Badge } from '@ui/badge';
import { Database, Loader2 } from 'lucide-react';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

const loginSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  password: z.string().min(6, 'Password must be at least 6 characters')
});

const oauthProviders = [
{ id: 'azure', name: 'Microsoft Azure AD', color: 'bg-blue-600 hover:bg-blue-700' },
{ id: 'google', name: 'Google Workspace', color: 'bg-red-600 hover:bg-red-700' },
{ id: 'okta', name: 'Okta', color: 'bg-gray-800 hover:bg-gray-900' },
{ id: 'generic', name: 'Generic OIDC', color: 'bg-purple-600 hover:bg-purple-700' }];




export default function Login() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm({
    resolver: zodResolver(loginSchema)
  });

  const onSubmit = async (data) => {
    setIsLoading(true);
    try {
      const response = await apiClient.post(





        '/auth/login', data);

      setAuth(response.access_token, response.user);
      toast.success('Login successful!');
      navigate('/dashboard');
    } catch (error) {
      const errorMessage = error.response?.data?.message || error.response?.data?.error || 'Invalid credentials';
      toast.error('Login failed', {
        description: errorMessage
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleOAuthLogin = (provider) => {
    // Redirect to OAuth provider
    const redirectUri = `${window.location.origin}/auth/callback`;
    window.location.href = `/api/auth/oauth/${provider}?redirect_uri=${encodeURIComponent(
      redirectUri
    )}`;
  };

  return (/*#__PURE__*/
    _jsx("div", { className: "flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 p-4", children: /*#__PURE__*/
      _jsxs(Card, { className: "w-full max-w-md", children: [/*#__PURE__*/
        _jsxs(CardHeader, { className: "space-y-1", children: [/*#__PURE__*/
          _jsx("div", { className: "flex items-center justify-center mb-4", children: /*#__PURE__*/
            _jsx(Database, { className: "h-12 w-12 text-primary" }) }
          ), /*#__PURE__*/
          _jsx(CardTitle, { className: "text-2xl text-center", children: "MBSE-Led Platform" }), /*#__PURE__*/
          _jsx(CardDescription, { className: "text-center", children: "Simulation engineering collaboration for distributed teams" }

          ), /*#__PURE__*/
          _jsxs("div", { className: "flex justify-center gap-2 mt-2", children: [/*#__PURE__*/
            _jsx(Badge, { variant: "secondary", className: "text-xs", children: "Multi-Location" }), /*#__PURE__*/
            _jsx(Badge, { variant: "secondary", className: "text-xs", children: "Multi-Tool" })] }
          )] }
        ), /*#__PURE__*/
        _jsx(CardContent, { children: /*#__PURE__*/
          _jsxs(Tabs, { defaultValue: "credentials", className: "w-full", children: [/*#__PURE__*/
            _jsxs(TabsList, { className: "grid w-full grid-cols-2", children: [/*#__PURE__*/
              _jsx(TabsTrigger, { value: "credentials", children: "Credentials" }), /*#__PURE__*/
              _jsx(TabsTrigger, { value: "oauth", children: "OAuth2/SSO" })] }
            ), /*#__PURE__*/

            _jsxs(TabsContent, { value: "credentials", className: "space-y-4", children: [/*#__PURE__*/
              _jsxs("form", { onSubmit: handleSubmit(onSubmit), className: "space-y-4", children: [/*#__PURE__*/
                _jsxs("div", { className: "space-y-2", children: [/*#__PURE__*/
                  _jsx(Label, { htmlFor: "username", children: "Username" }), /*#__PURE__*/
                  _jsx(Input, {
                    id: "username",
                    type: "text",
                    placeholder: "admin", ...
                    register('username'),
                    disabled: isLoading }
                  ),
                  errors.username && /*#__PURE__*/
                  _jsx("p", { className: "text-sm text-destructive", children: errors.username.message })] }

                ), /*#__PURE__*/

                _jsxs("div", { className: "space-y-2", children: [/*#__PURE__*/
                  _jsx(Label, { htmlFor: "password", children: "Password" }), /*#__PURE__*/
                  _jsx(Input, {
                    id: "password",
                    type: "password",
                    placeholder: "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022", ...
                    register('password'),
                    disabled: isLoading }
                  ),
                  errors.password && /*#__PURE__*/
                  _jsx("p", { className: "text-sm text-destructive", children: errors.password.message })] }

                ), /*#__PURE__*/

                _jsxs(Button, { type: "submit", className: "w-full", disabled: isLoading, children: [
                  isLoading && /*#__PURE__*/_jsx(Loader2, { className: "mr-2 h-4 w-4 animate-spin" }), "Sign In"] }

                )] }
              ), /*#__PURE__*/

              _jsx("div", { className: "text-center text-sm text-muted-foreground", children: /*#__PURE__*/
                _jsx("a", { href: "#", className: "hover:text-primary", children: "Forgot password?" }

                ) }
              )] }
            ), /*#__PURE__*/

            _jsxs(TabsContent, { value: "oauth", className: "space-y-4", children: [/*#__PURE__*/
              _jsx("div", { className: "space-y-2", children:
                oauthProviders.map((provider) => /*#__PURE__*/
                _jsxs(Button, {

                  variant: "outline",
                  className: `w-full ${provider.color} text-white`,
                  onClick: () => handleOAuthLogin(provider.id), children: [
                  "Sign in with ",
                  provider.name] }, provider.id
                )
                ) }
              ), /*#__PURE__*/

              _jsx(Separator, {}), /*#__PURE__*/

              _jsx("div", { className: "text-center text-xs text-muted-foreground", children: "Enterprise SSO powered by OAuth2/OIDC" }

              )] }
            )] }
          ) }
        )] }
      ) }
    ));

}

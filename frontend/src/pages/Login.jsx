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
import { Database, Loader2 } from 'lucide-react';
const loginSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  password: z.string().min(6, 'Password must be at least 6 characters')
});
const oauthProviders = [{
  id: 'azure',
  name: 'Microsoft Azure AD',
  color: 'bg-blue-600 hover:bg-blue-700'
}, {
  id: 'google',
  name: 'Google Workspace',
  color: 'bg-red-600 hover:bg-red-700'
}, {
  id: 'okta',
  name: 'Okta',
  color: 'bg-gray-800 hover:bg-gray-900'
}, {
  id: 'generic',
  name: 'Generic OIDC',
  color: 'bg-purple-600 hover:bg-purple-700'
}];
export default function Login() {
  const navigate = useNavigate();
  const setAuth = useAuthStore(state => state.setAuth);
  const [isLoading, setIsLoading] = useState(false);
  const {
    register,
    handleSubmit,
    formState: {
      errors
    }
  } = useForm({
    resolver: zodResolver(loginSchema)
  });
  const onSubmit = async data => {
    setIsLoading(true);
    try {
      const response = await apiClient.post('/auth/login', data);
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
  const handleOAuthLogin = provider => {
    const redirectUri = `${window.location.origin}/auth/callback`;
    window.location.href = `/api/auth/oauth/${provider}?redirect_uri=${encodeURIComponent(redirectUri)}`;
  };
  return <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 p-4"><Card className="w-full max-w-md"><CardHeader className="space-y-1"><div className="flex items-center justify-center mb-4"><Database className="h-12 w-12 text-primary" /></div><CardTitle className="text-2xl text-center">MBSE-Led Platform</CardTitle><CardDescription className="text-center">Simulation engineering collaboration for distributed teams</CardDescription><div className="flex justify-center gap-2 mt-2"><Badge variant="secondary" className="text-xs">Multi-Location</Badge><Badge variant="secondary" className="text-xs">Multi-Tool</Badge></div></CardHeader><CardContent><Tabs defaultValue="credentials" className="w-full"><TabsList className="grid w-full grid-cols-2"><TabsTrigger value="credentials">Credentials</TabsTrigger><TabsTrigger value="oauth">OAuth2/SSO</TabsTrigger></TabsList><TabsContent value="credentials" className="space-y-4"><form onSubmit={handleSubmit(onSubmit)} className="space-y-4"><div className="space-y-2"><Label htmlFor="username">Username</Label><Input id="username" type="text" placeholder="admin" {...register('username')} disabled={isLoading} />{errors.username && <p className="text-sm text-destructive">{errors.username.message}</p>}</div><div className="space-y-2"><Label htmlFor="password">Password</Label><Input id="password" type="password" placeholder="\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022" {...register('password')} disabled={isLoading} />{errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}</div><Button type="submit" className="w-full" disabled={isLoading}>{isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Sign In</Button></form><div className="text-center text-sm text-muted-foreground"><a href="#" className="hover:text-primary">Forgot password?</a></div></TabsContent><TabsContent value="oauth" className="space-y-4"><div className="space-y-2">{oauthProviders.map(provider => <Button variant="outline" className={`w-full ${provider.color} text-white`} onClick={() => handleOAuthLogin(provider.id)}>Sign in with {provider.name}</Button>)}</div><Separator /><div className="text-center text-xs text-muted-foreground">Enterprise SSO powered by OAuth2/OIDC</div></TabsContent></Tabs></CardContent></Card></div>;
}

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { useAuthStore } from '@/stores/authStore';
import { apiClient } from '@/services/api';
import { Loader2, ChevronDown, UserCircle2, Lock } from 'lucide-react';

const loginSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  password: z.string().min(6, 'Password must be at least 6 characters')
});

const oauthProviders = [
  { id: 'azure', name: 'Microsoft Azure AD', icon: '🔷' },
  { id: 'google', name: 'Google Workspace', icon: '🔴' },
  { id: 'okta', name: 'Okta', icon: '⚫' },
  { id: 'generic', name: 'Generic OIDC', icon: '🟣' }
];
export default function Login() {
  const navigate = useNavigate();
  const setAuth = useAuthStore(state => state.setAuth);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('credentials'); // 'credentials' or 'oauth'

  const {
    register,
    handleSubmit,
    formState: { errors }
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

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6 bg-[url('https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=2070&auto=format&fit=crop')] bg-cover bg-center">
      <div className="absolute inset-0 bg-slate-900/80 backdrop-blur-md"></div>
      
      <div className="max-w-md w-full bg-white rounded-3xl shadow-2xl p-10 relative z-10 border border-white/20 overflow-hidden">
        {/* Top Accent Bar */}
        <div className="absolute top-0 left-0 w-full h-2 bg-[#004A99]"></div>
        
        {/* Header */}
        <div className="flex flex-col items-center mb-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 bg-[#004A99] rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
              <span className="text-white font-black text-xl tracking-tighter">TCS</span>
            </div>
            <div className="h-8 w-px bg-slate-200"></div>
            <span className="text-slate-800 font-black text-sm uppercase tracking-widest">Simulation Digital Thread</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-800 text-center leading-tight">Simulation Data Dossier</h1>
          <p className="text-slate-500 text-xs mt-3 text-center uppercase font-black tracking-widest opacity-60">Enterprise Platform</p>
        </div>

        {/* Tab Selector */}
        <div className="flex gap-2 mb-6 bg-slate-100 rounded-xl p-1">
          <button
            onClick={() => setActiveTab('credentials')}
            className={`flex-1 px-4 py-2.5 rounded-lg text-sm font-bold transition-all ${
              activeTab === 'credentials'
                ? 'bg-white text-[#004A99] shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Credentials
          </button>
          <button
            onClick={() => setActiveTab('oauth')}
            className={`flex-1 px-4 py-2.5 rounded-lg text-sm font-bold transition-all ${
              activeTab === 'oauth'
                ? 'bg-white text-[#004A99] shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            OAuth2/SSO
          </button>
        </div>

        {/* Credentials Tab */}
        {activeTab === 'credentials' && (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div className="space-y-2">
              <label htmlFor="username" className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Username
              </label>
              <div className="relative">
                <UserCircle2 className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                <input
                  id="username"
                  type="text"
                  placeholder="Enter username"
                  {...register('username')}
                  disabled={isLoading}
                  className="w-full pl-10 pr-4 py-3 rounded-xl border-2 border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#004A99] focus:border-transparent disabled:bg-slate-50 disabled:cursor-not-allowed transition-all"
                />
              </div>
              {errors.username && (
                <p className="text-xs text-red-600 mt-1">{errors.username.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <label htmlFor="password" className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                <input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  {...register('password')}
                  disabled={isLoading}
                  className="w-full pl-10 pr-4 py-3 rounded-xl border-2 border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#004A99] focus:border-transparent disabled:bg-slate-50 disabled:cursor-not-allowed transition-all"
                />
              </div>
              {errors.password && (
                <p className="text-xs text-red-600 mt-1">{errors.password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-[#004A99] text-white py-3 rounded-xl font-bold text-sm hover:bg-[#003d7a] disabled:bg-slate-300 disabled:cursor-not-allowed transition-all shadow-lg shadow-blue-900/20 flex items-center justify-center gap-2"
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              {isLoading ? 'Signing In...' : 'Sign In'}
            </button>

            <div className="text-center">
              <a href="#" className="text-xs text-slate-500 hover:text-[#004A99] font-medium transition-colors">
                Forgot password?
              </a>
            </div>
          </form>
        )}

        {/* OAuth Tab */}
        {activeTab === 'oauth' && (
          <div className="space-y-4">
            <div className="space-y-3">
              {oauthProviders.map(provider => (
                <button
                  key={provider.id}
                  onClick={() => handleOAuthLogin(provider.id)}
                  className="w-full flex items-center justify-between p-4 border-2 border-slate-200 rounded-xl hover:border-[#004A99] hover:bg-blue-50/50 transition-all group"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{provider.icon}</span>
                    <div className="text-left">
                      <div className="font-bold text-slate-800 text-sm group-hover:text-[#004A99] transition-colors">
                        {provider.name}
                      </div>
                      <div className="text-xs text-slate-500">Enterprise SSO</div>
                    </div>
                  </div>
                  <div className="w-6 h-6 rounded-full bg-slate-50 flex items-center justify-center group-hover:bg-[#004A99] group-hover:text-white transition-colors">
                    <ChevronDown className="-rotate-90" size={14} />
                  </div>
                </button>
              ))}
            </div>

            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200"></div>
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-white px-2 text-slate-500 font-medium">OAuth2/OIDC Powered</span>
              </div>
            </div>

            <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
              <p className="text-xs text-slate-600 text-center leading-relaxed">
                Enterprise Single Sign-On enables secure access across distributed engineering teams
              </p>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="mt-8 pt-6 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
          <span>© 2025 TCS</span>
          <div className="flex gap-2">
            <span className="px-2 py-1 bg-slate-100 rounded text-slate-600 font-medium">ISO 17025</span>
            <span className="px-2 py-1 bg-slate-100 rounded text-slate-600 font-medium">MOSSEC</span>
          </div>
        </div>
      </div>
    </div>
  );
}

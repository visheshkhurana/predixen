import { useState, useEffect } from 'react';
import { useLocation } from 'wouter';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import { api, ApiError } from '@/api/client';
import { useFounderStore } from '@/store/founderStore';
import { Eye, EyeOff, Mail, Lock, AlertCircle, Sparkles, TrendingUp, Shield, Zap, Loader2, ArrowRight, BarChart3, Brain, Target, ChevronRight } from 'lucide-react';
import { SiGoogle } from 'react-icons/si';


const identifyUser = (userId: number, email: string) => {
  if (typeof window !== 'undefined' && (window as any).gtag) {
    (window as any).gtag('config', 'G-NJKW0TGC4C', { user_id: String(userId) });
    (window as any).gtag('set', 'user_properties', { user_email: email });
    (window as any).gtag('event', 'login', { method: 'email' });
  }
  if (typeof window !== 'undefined' && (window as any).fbq) {
    (window as any).fbq('init', '872167299140812', { em: email });
    (window as any).fbq('track', 'Lead');
  }
};

function AnimatedMetric({ label, value, delay }: { label: string; value: string; delay: number }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), delay);
    return () => clearTimeout(t);
  }, [delay]);
  return (
    <div className={`transition-all duration-700 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}`}>
      <div className="text-2xl font-bold tracking-tight text-white">{value}</div>
      <div className="text-xs text-white/50 uppercase tracking-wider mt-0.5">{label}</div>
    </div>
  );
}

export default function AuthPage() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const { setToken, setUser, setCurrentCompany, setCompanies } = useFounderStore();
  const [isLoading, setIsLoading] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [socialLoadingProvider, setSocialLoadingProvider] = useState<'google' | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [activeTab, setActiveTab] = useState('login');
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotPasswordEmail, setForgotPasswordEmail] = useState('');
  const [forgotPasswordSent, setForgotPasswordSent] = useState(false);
  const [isForgotLoading, setIsForgotLoading] = useState(false);
  
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState({ email: '', password: '', confirmPassword: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const oauthError = params.get('error');
    if (oauthError) {
      const messages: Record<string, string> = {
        google_denied: 'Google sign-in was cancelled.',
        google_token_failed: 'Could not complete Google sign-in. Please try again.',
        google_no_email: 'No email found on your Google account.',
      };
      toast({
        title: 'Sign-in issue',
        description: messages[oauthError] || 'Something went wrong. Please try again.',
        variant: 'destructive',
      });
      window.history.replaceState({}, '', '/auth');
    }
  }, []);

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const validatePassword = (password: string): string | null => {
    if (password.length < 8) return 'Password must be at least 8 characters';
    if (!/\d/.test(password)) return 'Password must contain at least one number';
    return null;
  };

  const handleForgotPassword = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!validateEmail(forgotPasswordEmail)) {
      toast({ title: 'Invalid email', description: 'Please enter a valid email address.', variant: 'destructive' });
      return;
    }
    setIsForgotLoading(true);
    try {
      await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: forgotPasswordEmail })
      });
      setForgotPasswordSent(true);
    } catch {
      setForgotPasswordSent(true);
    } finally {
      setIsForgotLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrors({});
    
    if (!validateEmail(loginForm.email)) {
      setErrors({ email: 'Please enter a valid email address' });
      return;
    }
    
    setIsLoading(true);
    try {
      const result = await api.auth.login(loginForm.email, loginForm.password);
      localStorage.setItem('founderconsole-token', result.access_token);
      setToken(result.access_token);
      setUser({ id: result.user_id, email: result.email, role: result.role, is_platform_admin: result.is_platform_admin, is_email_verified: result.is_email_verified });
      identifyUser(result.user_id, result.email);

      let userCompanies: any[] = [];
      try {
        userCompanies = await api.companies.list();
        if (userCompanies && userCompanies.length > 0) {
          setCompanies(userCompanies);
          setCurrentCompany(userCompanies[0]);
        }
      } catch {
      }

      toast({ title: 'Welcome back!' });
      if (!result.is_platform_admin && (!userCompanies || userCompanies.length === 0)) {
        setLocation('/onboarding');
        return;
      }
      setLocation('/');
    } catch (err) {
      let description = 'An unexpected error occurred. Please try again.';
      if (err instanceof ApiError) {
        description = err.message;
      } else if (err instanceof TypeError && err.message === 'Failed to fetch') {
        description = 'Unable to reach the server. Please check your connection and try again.';
      } else if (err instanceof Error) {
        description = err.message;
      }
      toast({ title: 'Login failed', description, variant: 'destructive' });
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleRegister = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrors({});
    
    const newErrors: Record<string, string> = {};
    
    if (!validateEmail(registerForm.email)) {
      newErrors.email = 'Please enter a valid email address';
    }
    
    const passwordError = validatePassword(registerForm.password);
    if (passwordError) {
      newErrors.password = passwordError;
    }
    
    if (registerForm.password !== registerForm.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }
    
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    
    setIsLoading(true);
    try {
      const result = await api.auth.register(registerForm.email, registerForm.password);
      localStorage.setItem('founderconsole-token', result.access_token);
      setToken(result.access_token);
      setUser({ id: result.user_id, email: result.email, role: result.role, is_platform_admin: result.is_platform_admin, is_email_verified: result.is_email_verified });
      identifyUser(result.user_id, result.email);
      toast({ title: 'Account created!' });
      setLocation('/onboarding');
    } catch (err) {
      let description = 'An unexpected error occurred. Please try again.';
      if (err instanceof ApiError) {
        description = err.message;
      } else if (err instanceof TypeError && err.message === 'Failed to fetch') {
        description = 'Unable to reach the server. Please check your connection and try again.';
      } else if (err instanceof Error) {
        description = err.message;
      }
      toast({ title: 'Registration failed', description, variant: 'destructive' });
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleDemoLogin = async () => {
    setIsDemoLoading(true);
    try {
      const result = await api.auth.login('demo@founderconsole.ai', 'demo123');
      localStorage.setItem('founderconsole-token', result.access_token);
      setToken(result.access_token);
      setUser({ id: result.user_id, email: result.email, role: result.role, is_platform_admin: result.is_platform_admin, is_email_verified: result.is_email_verified });
      identifyUser(result.user_id, result.email);
      
      try {
        const companies = await api.companies.list();
        if (companies && companies.length > 0) {
          const demoCompany = companies.find((c: any) => c.name === 'TechFlow Analytics') || companies[0];
          setCompanies(companies);
          setCurrentCompany(demoCompany);
        }
      } catch (e) {
        console.warn('Failed to auto-select demo company');
      }
      
      toast({ title: 'Welcome to the demo!' });
      setLocation('/');
    } catch (err) {
      let description = 'An unexpected error occurred. Please try again.';
      if (err instanceof ApiError) {
        description = err.message;
      } else if (err instanceof TypeError && err.message === 'Failed to fetch') {
        description = 'Unable to reach the server. Please check your connection and try again.';
      } else if (err instanceof Error) {
        description = err.message;
      }
      toast({ title: 'Demo login failed', description, variant: 'destructive' });
    } finally {
      setIsDemoLoading(false);
    }
  };

  const handleSocialLogin = (provider: 'google') => {
    setSocialLoadingProvider(provider);
    window.location.assign(`/api/auth/${provider}/start`);
  };

  const capabilities = [
    { icon: BarChart3, title: 'Monte Carlo Simulations', desc: 'Run thousands of probabilistic scenarios on real company data' },
    { icon: Brain, title: 'AI Decision Copilot', desc: 'Ask strategic questions and get data-backed recommendations' },
    { icon: Target, title: 'Scenario Modeling', desc: 'Compare hiring plans, pricing changes, and fundraising strategies' },
    { icon: Shield, title: 'Investor-Grade Diligence', desc: 'Truth-scanned metrics with full audit trail and provenance' },
  ];

  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      <div className="hidden md:flex md:w-[55%] relative overflow-hidden" style={{ background: 'linear-gradient(135deg, #0a0e1a 0%, #111827 40%, #0f172a 100%)' }}>
        <div className="absolute inset-0" style={{
          backgroundImage: `radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99, 102, 241, 0.15), transparent),
                            radial-gradient(ellipse 60% 40% at 80% 80%, rgba(59, 130, 246, 0.08), transparent)`,
        }} />

        <div className="absolute inset-0 opacity-[0.03]" style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
          backgroundSize: '64px 64px',
        }} />

        <div className="relative z-10 flex flex-col justify-between w-full px-8 lg:px-12 xl:px-16 py-10 lg:py-12">
          <div>
            <div className="flex items-center gap-3 mb-16">
              <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
                <Sparkles className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-semibold text-white tracking-tight">FounderConsole</span>
            </div>

            <div className="max-w-xl">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 mb-6">
                <div className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-xs font-medium text-blue-300 tracking-wide uppercase">Now in Public Beta</span>
              </div>
              
              <h1 className="text-4xl xl:text-5xl font-bold text-white leading-[1.1] tracking-tight mb-5">
                Financial Intelligence
                <br />
                <span className="bg-gradient-to-r from-blue-400 via-indigo-400 to-violet-400 bg-clip-text text-transparent">
                  for Founders
                </span>
              </h1>
              <p className="text-base xl:text-lg text-white/50 leading-relaxed max-w-md">
                Simulate decisions before you execute them. Monte Carlo-powered scenario analysis with AI-driven recommendations.
              </p>
            </div>
          </div>

          <div className="mt-12 space-y-3">
            {capabilities.map((cap, i) => (
              <div
                key={cap.title}
                className="group flex items-start gap-4 p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.06] hover:border-white/[0.1] transition-all duration-300"
                style={{ animationDelay: `${i * 100}ms` }}
              >
                <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-white/[0.08] to-white/[0.02] border border-white/[0.08] flex items-center justify-center flex-shrink-0 group-hover:border-blue-500/30 transition-colors">
                  <cap.icon className="h-4 w-4 text-blue-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-medium text-white/90">{cap.title}</h3>
                  <p className="text-xs text-white/40 mt-0.5 leading-relaxed">{cap.desc}</p>
                </div>
                <ChevronRight className="h-4 w-4 text-white/20 group-hover:text-white/40 transition-colors mt-0.5 flex-shrink-0" />
              </div>
            ))}
          </div>

          <div className="mt-12 pt-8 border-t border-white/[0.06]">
            <div className="grid grid-cols-4 gap-6">
              <AnimatedMetric label="Scenarios Run" value="2.4M+" delay={200} />
              <AnimatedMetric label="Companies" value="1,200+" delay={400} />
              <AnimatedMetric label="Accuracy" value="94%" delay={600} />
              <AnimatedMetric label="Time Saved" value="40hrs" delay={800} />
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center bg-background px-5 py-8 sm:p-8 md:p-12">
        <div className="w-full max-w-[420px]">
          <div className="md:hidden flex items-center justify-center gap-2.5 mb-8">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <span className="text-lg font-semibold tracking-tight">FounderConsole</span>
          </div>

          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold tracking-tight mb-2">
              {activeTab === 'login' ? 'Welcome back' : 'Get started'}
            </h2>
            <p className="text-sm text-muted-foreground">
              {activeTab === 'login' 
                ? 'Sign in to your account to continue'
                : 'Create your account to get started'
              }
            </p>
          </div>

          <div className="mb-6">
            <Button
              variant="outline"
              type="button"
              className="w-full h-11 gap-2.5 text-sm font-medium"
              onClick={() => handleSocialLogin('google')}
              disabled={isLoading || socialLoadingProvider !== null}
              data-testid="button-google-login"
            >
              {socialLoadingProvider === 'google' ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <SiGoogle className="h-3.5 w-3.5" />
              )}
              Continue with Google
            </Button>
          </div>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-background px-3 text-xs text-muted-foreground uppercase tracking-wider">or</span>
            </div>
          </div>
          
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-6 h-10 p-1 bg-muted/50" role="tablist">
              <TabsTrigger 
                value="login" 
                className="h-8 text-sm font-medium rounded-md data-[state=active]:bg-background data-[state=active]:shadow-sm"
                data-testid="tab-login"
                role="tab"
                aria-selected={activeTab === 'login'}
              >
                Sign In
              </TabsTrigger>
              <TabsTrigger 
                value="register" 
                className="h-8 text-sm font-medium rounded-md data-[state=active]:bg-background data-[state=active]:shadow-sm"
                data-testid="tab-register"
                role="tab"
                aria-selected={activeTab === 'register'}
              >
                Create Account
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="login" className="mt-0">
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="login-email" className="text-sm font-medium">
                    Email
                  </Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
                    <Input
                      id="login-email"
                      type="email"
                      required
                      placeholder="you@company.com"
                      className={`pl-10 h-11 bg-muted/30 border-border/60 focus:bg-background transition-colors ${errors.email ? 'border-destructive focus-visible:ring-destructive' : ''}`}
                      value={loginForm.email}
                      onChange={(e) => {
                        setLoginForm({ ...loginForm, email: e.target.value });
                        if (errors.email) setErrors({ ...errors, email: '' });
                      }}
                      data-testid="input-login-email"
                      aria-invalid={!!errors.email}
                      aria-describedby={errors.email ? 'login-email-error' : undefined}
                    />
                  </div>
                  {errors.email && (
                    <p id="login-email-error" className="text-xs text-destructive flex items-center gap-1 mt-1">
                      <AlertCircle className="h-3 w-3" />
                      {errors.email}
                    </p>
                  )}
                </div>
                
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="login-password" className="text-sm font-medium">
                      Password
                    </Label>
                    <button 
                      type="button"
                      className="text-xs text-muted-foreground hover:text-foreground transition-colors focus:outline-none"
                      onClick={() => { setShowForgotPassword(true); setForgotPasswordSent(false); setForgotPasswordEmail(loginForm.email); }}
                      data-testid="link-forgot-password"
                    >
                      Forgot password?
                    </button>
                  </div>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
                    <Input
                      id="login-password"
                      type={showPassword ? 'text' : 'password'}
                      required
                      placeholder="Enter your password"
                      className="pl-10 pr-10 h-11 bg-muted/30 border-border/60 focus:bg-background transition-colors"
                      value={loginForm.password}
                      onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                      data-testid="input-login-password"
                    />
                    <button
                      type="button"
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/60 hover:text-foreground transition-colors focus:outline-none"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      data-testid="button-toggle-password"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
                
                <Button 
                  type="submit" 
                  className="w-full h-11 text-sm font-medium mt-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 transition-all" 
                  disabled={isLoading} 
                  data-testid="button-login"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Signing in...
                    </>
                  ) : (
                    <>
                      Sign In
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </>
                  )}
                </Button>
              </form>
            </TabsContent>
            
            <TabsContent value="register" className="mt-0">
              <form onSubmit={handleRegister} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="register-email" className="text-sm font-medium">
                    Work email
                  </Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
                    <Input
                      id="register-email"
                      type="email"
                      required
                      placeholder="you@company.com"
                      className={`pl-10 h-11 bg-muted/30 border-border/60 focus:bg-background transition-colors ${errors.email ? 'border-destructive focus-visible:ring-destructive' : ''}`}
                      value={registerForm.email}
                      onChange={(e) => {
                        setRegisterForm({ ...registerForm, email: e.target.value });
                        if (errors.email) setErrors({ ...errors, email: '' });
                      }}
                      data-testid="input-register-email"
                      aria-invalid={!!errors.email}
                      aria-describedby={errors.email ? 'register-email-error' : undefined}
                    />
                  </div>
                  {errors.email && (
                    <p id="register-email-error" className="text-xs text-destructive flex items-center gap-1 mt-1">
                      <AlertCircle className="h-3 w-3" />
                      {errors.email}
                    </p>
                  )}
                </div>
                
                <div className="space-y-1.5">
                  <Label htmlFor="register-password" className="text-sm font-medium">
                    Password
                  </Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
                    <Input
                      id="register-password"
                      type={showPassword ? 'text' : 'password'}
                      required
                      placeholder="Min. 8 characters"
                      className={`pl-10 pr-10 h-11 bg-muted/30 border-border/60 focus:bg-background transition-colors ${errors.password ? 'border-destructive focus-visible:ring-destructive' : ''}`}
                      value={registerForm.password}
                      onChange={(e) => {
                        setRegisterForm({ ...registerForm, password: e.target.value });
                        if (errors.password) setErrors({ ...errors, password: '' });
                      }}
                      data-testid="input-register-password"
                      aria-invalid={!!errors.password}
                      aria-describedby="password-requirements"
                    />
                    <button
                      type="button"
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/60 hover:text-foreground transition-colors focus:outline-none"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {errors.password ? (
                    <p className="text-xs text-destructive flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      {errors.password}
                    </p>
                  ) : (
                    <p id="password-requirements" className="text-[11px] text-muted-foreground">
                      8+ characters with at least one number
                    </p>
                  )}
                </div>
                
                <div className="space-y-1.5">
                  <Label htmlFor="register-confirm-password" className="text-sm font-medium">
                    Confirm password
                  </Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
                    <Input
                      id="register-confirm-password"
                      type={showConfirmPassword ? 'text' : 'password'}
                      required
                      placeholder="Confirm your password"
                      className={`pl-10 pr-10 h-11 bg-muted/30 border-border/60 focus:bg-background transition-colors ${errors.confirmPassword ? 'border-destructive focus-visible:ring-destructive' : ''}`}
                      value={registerForm.confirmPassword}
                      onChange={(e) => {
                        setRegisterForm({ ...registerForm, confirmPassword: e.target.value });
                        if (errors.confirmPassword) setErrors({ ...errors, confirmPassword: '' });
                      }}
                      data-testid="input-register-confirm-password"
                      aria-invalid={!!errors.confirmPassword}
                      aria-describedby={errors.confirmPassword ? 'confirm-password-error' : undefined}
                    />
                    <button
                      type="button"
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/60 hover:text-foreground transition-colors focus:outline-none"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                    >
                      {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {errors.confirmPassword && (
                    <p id="confirm-password-error" className="text-xs text-destructive flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      {errors.confirmPassword}
                    </p>
                  )}
                </div>
                
                <Button 
                  type="submit" 
                  className="w-full h-11 text-sm font-medium mt-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 transition-all" 
                  disabled={isLoading} 
                  data-testid="button-register"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Creating account...
                    </>
                  ) : (
                    <>
                      Create Account
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </>
                  )}
                </Button>
                
                <p className="text-[11px] text-center text-muted-foreground leading-relaxed">
                  By creating an account, you agree to our{' '}
                  <a href="/terms" className="text-foreground hover:underline" data-testid="link-auth-terms">Terms</a>
                  {' '}and{' '}
                  <a href="/privacy" className="text-foreground hover:underline" data-testid="link-auth-privacy">Privacy Policy</a>
                </p>
              </form>
            </TabsContent>
          </Tabs>
          
          <div className="mt-6 pt-5 border-t border-border/50">
            <button
              type="button"
              className="w-full group flex items-center justify-between p-3.5 rounded-xl bg-muted/30 hover:bg-muted/50 border border-border/50 hover:border-border transition-all"
              onClick={handleDemoLogin}
              disabled={isDemoLoading || isLoading}
              data-testid="button-demo-login"
            >
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-500/20 flex items-center justify-center border border-amber-500/20">
                  {isDemoLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin text-amber-500" />
                  ) : (
                    <Sparkles className="h-4 w-4 text-amber-500" />
                  )}
                </div>
                <div className="text-left">
                  <div className="text-sm font-medium">{isDemoLoading ? 'Loading demo...' : 'Try the live demo'}</div>
                  <div className="text-[11px] text-muted-foreground">Pre-loaded SaaS company data</div>
                </div>
              </div>
              {!isDemoLoading && (
                <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground group-hover:translate-x-0.5 transition-all" />
              )}
            </button>
          </div>

          <p className="text-center text-[11px] text-muted-foreground/60 mt-6">
            TLS encryption &middot; Secure cloud infrastructure &middot; Role-based access control
          </p>
        </div>
      </div>

      {showForgotPassword && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <Card className="w-full max-w-md mx-4">
            <CardContent className="p-6">
              {forgotPasswordSent ? (
                <div className="text-center space-y-4">
                  <div className="w-12 h-12 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto">
                    <Mail className="h-6 w-6 text-emerald-500" />
                  </div>
                  <h2 className="text-xl font-semibold" data-testid="text-reset-sent">Check your email</h2>
                  <p className="text-sm text-muted-foreground">
                    If an account exists for <strong>{forgotPasswordEmail}</strong>, we've sent a password reset link. The link expires in 1 hour.
                  </p>
                  <Button
                    className="w-full"
                    onClick={() => setShowForgotPassword(false)}
                    data-testid="button-back-to-login"
                  >
                    Back to Sign In
                  </Button>
                </div>
              ) : (
                <form onSubmit={handleForgotPassword} className="space-y-4">
                  <div className="text-center space-y-2">
                    <h2 className="text-xl font-semibold">Reset your password</h2>
                    <p className="text-sm text-muted-foreground">
                      Enter your email address and we'll send you a link to reset your password.
                    </p>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="forgot-email">Email address</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
                      <Input
                        id="forgot-email"
                        type="email"
                        required
                        placeholder="you@company.com"
                        className="pl-10 h-11"
                        value={forgotPasswordEmail}
                        onChange={(e) => setForgotPasswordEmail(e.target.value)}
                        data-testid="input-forgot-email"
                      />
                    </div>
                  </div>
                  <Button type="submit" className="w-full" disabled={isForgotLoading} data-testid="button-send-reset">
                    {isForgotLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                    Send Reset Link
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    className="w-full text-sm"
                    onClick={() => setShowForgotPassword(false)}
                    data-testid="button-cancel-forgot"
                  >
                    Back to Sign In
                  </Button>
                </form>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

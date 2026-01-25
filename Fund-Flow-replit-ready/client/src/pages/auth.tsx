import { useState } from 'react';
import { useLocation } from 'wouter';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import { api, ApiError } from '@/api/client';
import { useFounderStore } from '@/store/founderStore';
import { Eye, EyeOff, Mail, Lock, AlertCircle, Sparkles, TrendingUp, Shield, Zap } from 'lucide-react';
import { SiGoogle, SiGithub } from 'react-icons/si';

export default function AuthPage() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const { setToken, setUser } = useFounderStore();
  const [isLoading, setIsLoading] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [activeTab, setActiveTab] = useState('login');
  
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState({ email: '', password: '', confirmPassword: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const validatePassword = (password: string): string | null => {
    if (password.length < 8) return 'Password must be at least 8 characters';
    if (!/\d/.test(password)) return 'Password must contain at least one number';
    return null;
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
      localStorage.setItem('predixen-token', result.access_token);
      setToken(result.access_token);
      setUser({ id: result.user_id, email: result.email, role: result.role, is_platform_admin: result.is_platform_admin });
      toast({ title: 'Welcome back!' });
      setLocation('/');
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Login failed';
      toast({ title: 'Login failed', description: message, variant: 'destructive' });
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
      localStorage.setItem('predixen-token', result.access_token);
      setToken(result.access_token);
      setUser({ id: result.user_id, email: result.email, role: result.role, is_platform_admin: result.is_platform_admin });
      toast({ title: 'Account created!' });
      setLocation('/onboarding');
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Registration failed';
      toast({ title: 'Registration failed', description: message, variant: 'destructive' });
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleDemoLogin = async () => {
    setIsDemoLoading(true);
    try {
      const result = await api.auth.login('demo@predixen.ai', 'demo123');
      localStorage.setItem('predixen-token', result.access_token);
      setToken(result.access_token);
      setUser({ id: result.user_id, email: result.email, role: result.role, is_platform_admin: result.is_platform_admin });
      toast({ title: 'Welcome to the demo!' });
      setLocation('/');
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Demo login failed';
      toast({ title: 'Demo login failed', description: message, variant: 'destructive' });
    } finally {
      setIsDemoLoading(false);
    }
  };

  const handleSocialLogin = (provider: string) => {
    toast({ 
      title: 'Coming Soon', 
      description: `${provider} login will be available soon.`,
    });
  };

  const features = [
    { icon: TrendingUp, title: 'Decision Simulation Engine', description: 'Run Monte Carlo simulations on real company data to model outcomes, risks, and trade-offs' },
    { icon: Sparkles, title: 'Scenario Builder', description: 'Compare multiple futures — aggressive growth, conservative burn, fundraising delays — side by side' },
    { icon: Shield, title: 'Outcome Probability Mapping', description: 'See survival likelihood, runway distribution, dilution risk, and downside exposure' },
    { icon: Zap, title: 'AI Decision Copilot', description: 'Ask "What happens if we hire 10 engineers?" and simulate the answer' },
  ];
  
  return (
    <div className="min-h-screen flex bg-background">
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/20 via-primary/10 to-background" />
        <div 
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }}
        />
        
        <div className="relative z-10 flex flex-col justify-center px-12 py-16">
          <div className="mb-12">
            <div className="flex items-center gap-3 mb-6">
              <div className="h-12 w-12 rounded-xl bg-primary/20 flex items-center justify-center">
                <Sparkles className="h-6 w-6 text-primary" />
              </div>
              <span className="text-2xl font-bold">Predixen</span>
            </div>
            <h1 className="text-4xl font-bold mb-4 leading-tight">
              AI Decision Simulator<br />
              <span className="text-primary">for Founders & CXOs</span>
            </h1>
            <p className="text-lg text-muted-foreground max-w-md">
              Simulate strategic decisions <em>before</em> you execute them. Test hiring plans, 
              pricing changes, fundraising strategies across thousands of probabilistic scenarios.
            </p>
          </div>
          
          <div className="space-y-4">
            {features.map((feature) => (
              <div key={feature.title} className="flex items-start gap-4 p-4 rounded-lg bg-card/50 backdrop-blur-sm border border-border/50">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <feature.icon className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground">{feature.description}</p>
                </div>
              </div>
            ))}
          </div>
          
          <div className="mt-8 pt-6 border-t border-border/30">
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">Built for High-Stakes Decisions</span>
              <br />
              Predixen is not accounting software. It's a decision laboratory for venture-backed startups and growth-stage companies.
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
        <Card className="w-full max-w-md shadow-xl border-border/50">
          <CardContent className="p-6 sm:p-8">
            <div className="text-center mb-6">
              <div className="lg:hidden flex items-center justify-center gap-2 mb-4">
                <div className="h-10 w-10 rounded-xl bg-primary/20 flex items-center justify-center">
                  <Sparkles className="h-5 w-5 text-primary" />
                </div>
                <span className="text-xl font-bold">Predixen</span>
              </div>
              <h2 className="text-2xl font-bold mb-2">
                {activeTab === 'login' ? 'Welcome back' : 'Create your account'}
              </h2>
              <p className="text-muted-foreground">
                {activeTab === 'login' 
                  ? 'Sign in to continue simulating decisions and outcomes'
                  : 'Start simulating strategic decisions today'
                }
              </p>
            </div>

            <div className="space-y-3 mb-6">
              <Button
                variant="outline"
                className="w-full h-11 gap-3"
                onClick={() => handleSocialLogin('Google')}
                disabled={isLoading}
                data-testid="button-google-login"
              >
                <SiGoogle className="h-4 w-4" />
                Continue with Google
              </Button>
              <Button
                variant="outline"
                className="w-full h-11 gap-3"
                onClick={() => handleSocialLogin('GitHub')}
                disabled={isLoading}
                data-testid="button-github-login"
              >
                <SiGithub className="h-4 w-4" />
                Continue with GitHub
              </Button>
            </div>

            <div className="relative mb-6">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-card px-2 text-muted-foreground">Or continue with email</span>
              </div>
            </div>
            
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6 h-11" role="tablist">
                <TabsTrigger 
                  value="login" 
                  className="h-9 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                  data-testid="tab-login"
                  role="tab"
                  aria-selected={activeTab === 'login'}
                >
                  Sign In
                </TabsTrigger>
                <TabsTrigger 
                  value="register" 
                  className="h-9 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                  data-testid="tab-register"
                  role="tab"
                  aria-selected={activeTab === 'register'}
                >
                  Create Account
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="login" className="mt-0">
                <form onSubmit={handleLogin} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="login-email" className="text-sm font-medium">
                      Email address
                    </Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="login-email"
                        type="email"
                        required
                        placeholder="you@company.com"
                        className={`pl-10 h-11 ${errors.email ? 'border-destructive focus-visible:ring-destructive' : ''}`}
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
                      <p id="login-email-error" className="text-sm text-destructive flex items-center gap-1">
                        <AlertCircle className="h-3 w-3" />
                        {errors.email}
                      </p>
                    )}
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="login-password" className="text-sm font-medium">
                        Password
                      </Label>
                      <button 
                        type="button"
                        className="text-xs text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded"
                        onClick={() => toast({ title: 'Password reset', description: 'Feature coming soon' })}
                      >
                        Forgot password?
                      </button>
                    </div>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="login-password"
                        type={showPassword ? 'text' : 'password'}
                        required
                        placeholder="Enter your password"
                        className="pl-10 pr-10 h-11"
                        value={loginForm.password}
                        onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                        data-testid="input-login-password"
                      />
                      <button
                        type="button"
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary rounded"
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
                    className="w-full h-11 text-base font-medium" 
                    disabled={isLoading} 
                    data-testid="button-login"
                  >
                    {isLoading ? 'Signing in...' : 'Sign In'}
                  </Button>
                </form>
              </TabsContent>
              
              <TabsContent value="register" className="mt-0">
                <form onSubmit={handleRegister} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="register-email" className="text-sm font-medium">
                      Email address
                    </Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="register-email"
                        type="email"
                        required
                        placeholder="you@company.com"
                        className={`pl-10 h-11 ${errors.email ? 'border-destructive focus-visible:ring-destructive' : ''}`}
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
                      <p id="register-email-error" className="text-sm text-destructive flex items-center gap-1">
                        <AlertCircle className="h-3 w-3" />
                        {errors.email}
                      </p>
                    )}
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="register-password" className="text-sm font-medium">
                      Password
                    </Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="register-password"
                        type={showPassword ? 'text' : 'password'}
                        required
                        placeholder="Create a strong password"
                        className={`pl-10 pr-10 h-11 ${errors.password ? 'border-destructive focus-visible:ring-destructive' : ''}`}
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
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary rounded"
                        onClick={() => setShowPassword(!showPassword)}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                    {errors.password ? (
                      <p className="text-sm text-destructive flex items-center gap-1">
                        <AlertCircle className="h-3 w-3" />
                        {errors.password}
                      </p>
                    ) : (
                      <p id="password-requirements" className="text-xs text-muted-foreground">
                        Minimum 8 characters with at least one number
                      </p>
                    )}
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="register-confirm-password" className="text-sm font-medium">
                      Confirm password
                    </Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="register-confirm-password"
                        type={showConfirmPassword ? 'text' : 'password'}
                        required
                        placeholder="Confirm your password"
                        className={`pl-10 pr-10 h-11 ${errors.confirmPassword ? 'border-destructive focus-visible:ring-destructive' : ''}`}
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
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary rounded"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                      >
                        {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                    {errors.confirmPassword && (
                      <p id="confirm-password-error" className="text-sm text-destructive flex items-center gap-1">
                        <AlertCircle className="h-3 w-3" />
                        {errors.confirmPassword}
                      </p>
                    )}
                  </div>
                  
                  <Button 
                    type="submit" 
                    className="w-full h-11 text-base font-medium" 
                    disabled={isLoading} 
                    data-testid="button-register"
                  >
                    {isLoading ? 'Creating account...' : 'Create Account'}
                  </Button>
                  
                  <p className="text-xs text-center text-muted-foreground">
                    By creating an account, you agree to our{' '}
                    <button type="button" className="text-primary hover:underline">Terms of Service</button>
                    {' '}and{' '}
                    <button type="button" className="text-primary hover:underline">Privacy Policy</button>
                  </p>
                </form>
              </TabsContent>
            </Tabs>
            
            <div className="mt-6 pt-4 border-t text-center">
              <button
                type="button"
                className="text-sm text-muted-foreground hover:text-foreground transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded px-2 py-1"
                onClick={handleDemoLogin}
                disabled={isDemoLoading}
                data-testid="button-demo-login"
              >
                <span className="flex items-center justify-center gap-2">
                  <Sparkles className="h-4 w-4" />
                  {isDemoLoading ? 'Loading simulation...' : 'Try Demo Simulation'}
                </span>
                {!isDemoLoading && (
                  <span className="block text-xs opacity-70 mt-1">
                    Explore with a pre-loaded startup with realistic data and scenarios
                  </span>
                )}
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

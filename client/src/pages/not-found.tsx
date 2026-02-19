import { Button } from "@/components/ui/button";
import { Link } from "wouter";
import { Home, LogIn, Sparkles } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-center bg-background px-4" data-testid="page-not-found">
      <div className="flex flex-col items-center gap-6 max-w-md text-center">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-md bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-base">FC</span>
          </div>
          <span className="text-xl font-semibold text-foreground tracking-tight">FounderConsole</span>
        </div>

        <div className="space-y-2">
          <h1 className="text-5xl font-bold text-foreground" data-testid="text-404-heading">404</h1>
          <p className="text-lg text-muted-foreground">Page not found</p>
          <p className="text-sm text-muted-foreground">
            The page you're looking for doesn't exist or has been moved.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
          <Link href="/">
            <Button data-testid="button-go-dashboard">
              <Home className="h-4 w-4 mr-2" />
              Go to Dashboard
            </Button>
          </Link>
          <Link href="/auth">
            <Button variant="outline" data-testid="button-go-login">
              <LogIn className="h-4 w-4 mr-2" />
              Go to Login
            </Button>
          </Link>
          <Link href="/demo">
            <Button variant="ghost" data-testid="button-see-demo">
              <Sparkles className="h-4 w-4 mr-2" />
              See Demo
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

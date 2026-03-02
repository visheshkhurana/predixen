import { useState, useEffect } from "react";
import { Link, useLocation } from "wouter";
import { Menu, Twitter, Linkedin, Github } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import logo from "@assets/generated_images/predixen_fintech_logo_icon.png";

const navLinks = [
  { label: "Features", href: "/features" },
  { label: "Pricing", href: "/pricing" },
  { label: "About", href: "/about" },
  { label: "Blog", href: "/blog" },
  { label: "FAQ", href: "/faq" },
];

const footerProduct = [
  { label: "Features", href: "/features" },
  { label: "Pricing", href: "/pricing" },
  { label: "FAQ", href: "/faq" },
  { label: "Demo", href: "/demo" },
];

const footerCompany = [
  { label: "About", href: "/about" },
  { label: "Blog", href: "/blog" },
  { label: "Contact", href: "/contact" },
];

const footerLegal = [
  { label: "Privacy", href: "/privacy" },
  { label: "Terms", href: "/terms" },
];

function NavLink({ href, label, onClick }: { href: string; label: string; onClick?: () => void }) {
  const [location] = useLocation();
  const isActive = location === href;
  return (
    <Link
      href={href}
      onClick={onClick}
      data-testid={`nav-link-${label.toLowerCase()}`}
      className={`text-sm font-medium transition-colors hover:text-foreground ${
        isActive ? "text-foreground" : "text-muted-foreground"
      }`}
    >
      {label}
    </Link>
  );
}

function Header() {
  const [open, setOpen] = useState(false);
  const [location] = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location]);

  return (
    <header className="sticky top-0 z-[9999] border-b bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" data-testid="link-logo" className="flex items-center gap-2">
          <img src={logo} alt="FounderConsole" className="h-8 w-8 rounded-md" />
          <span className="text-lg font-semibold tracking-tight text-foreground">FounderConsole</span>
        </Link>

        <nav className="hidden items-center gap-6 md:flex" data-testid="nav-desktop">
          {navLinks.map((link) => (
            <NavLink key={link.href} href={link.href} label={link.label} />
          ))}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          <Button variant="outline" size="sm" asChild data-testid="button-watch-demo">
            <Link href="/demo">Watch Demo</Link>
          </Button>
          <Button size="sm" asChild data-testid="button-get-started">
            <Link href="/auth">Get Started Free</Link>
          </Button>
        </div>

        <div className="md:hidden">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button size="icon" variant="ghost" aria-label="Open menu" data-testid="button-mobile-menu">
                <Menu />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-72">
              <SheetHeader>
                <SheetTitle>
                  <Link
                    href="/"
                    onClick={() => setOpen(false)}
                    className="flex items-center gap-2"
                    data-testid="link-mobile-logo"
                  >
                    <img src={logo} alt="FounderConsole" className="h-7 w-7 rounded-md" />
                    <span className="text-base font-semibold">FounderConsole</span>
                  </Link>
                </SheetTitle>
              </SheetHeader>
              <nav className="mt-6 flex flex-col gap-4" data-testid="nav-mobile">
                {navLinks.map((link) => (
                  <NavLink
                    key={link.href}
                    href={link.href}
                    label={link.label}
                    onClick={() => setOpen(false)}
                  />
                ))}
              </nav>
              <div className="mt-8 flex flex-col gap-2">
                <Button variant="outline" asChild data-testid="button-mobile-watch-demo">
                  <Link href="/demo" onClick={() => setOpen(false)}>Watch Demo</Link>
                </Button>
                <Button asChild data-testid="button-mobile-get-started">
                  <Link href="/auth" onClick={() => setOpen(false)}>Get Started Free</Link>
                </Button>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}

function FooterLinkGroup({ title, links }: { title: string; links: { label: string; href: string }[] }) {
  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold text-foreground">{title}</h3>
      <ul className="flex flex-col gap-2">
        {links.map((link) => (
          <li key={link.href + link.label}>
            <Link
              href={link.href}
              data-testid={`footer-link-${link.label.toLowerCase().replace(/\s+/g, "-")}`}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Footer() {
  return (
    <footer className="border-t bg-background">
      <div className="mx-auto max-w-6xl px-4 py-12">
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
          <FooterLinkGroup title="Product" links={footerProduct} />
          <FooterLinkGroup title="Company" links={footerCompany} />
          <FooterLinkGroup title="Legal" links={footerLegal} />
          <div>
            <h3 className="mb-3 text-sm font-semibold text-foreground">Connect</h3>
            <div className="flex items-center gap-3 flex-wrap">
              <a href="https://twitter.com" target="_blank" rel="noopener noreferrer" aria-label="Twitter" data-testid="footer-link-twitter" className="text-muted-foreground transition-colors hover:text-foreground">
                <Twitter className="h-5 w-5" />
              </a>
              <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn" data-testid="footer-link-linkedin" className="text-muted-foreground transition-colors hover:text-foreground">
                <Linkedin className="h-5 w-5" />
              </a>
              <a href="https://github.com" target="_blank" rel="noopener noreferrer" aria-label="GitHub" data-testid="footer-link-github" className="text-muted-foreground transition-colors hover:text-foreground">
                <Github className="h-5 w-5" />
              </a>
            </div>
          </div>
        </div>

        <div className="mt-10 border-t pt-6">
          <div className="flex flex-col items-center gap-2 text-center sm:flex-row sm:justify-between">
            <p className="text-sm text-muted-foreground">
              Financial clarity for founders through real-time forecasting, Monte Carlo simulation, and explainability.
            </p>
          </div>
          <div className="mt-4 flex flex-col items-center gap-2 text-center sm:flex-row sm:justify-between">
            <p className="text-xs text-muted-foreground" data-testid="text-copyright">
              &copy; {new Date().getFullYear()} FounderConsole. All rights reserved.
            </p>
            <p className="text-xs text-muted-foreground italic" data-testid="text-tagline">
              Built for founders, by founders.
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}

export function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <Header />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  );
}

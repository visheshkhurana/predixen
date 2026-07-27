import { useState, useEffect, useRef } from "react";
import { Link, useLocation } from "wouter";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { FCLogo } from "@/components/FCLogo";
import { MarketingBackground } from "@/components/marketing/MarketingBackground";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";

const navLinks = [
  { label: "Features", href: "/features" },
  { label: "Pricing", href: "/pricing" },
  { label: "About", href: "/about" },
  { label: "Blog", href: "/blog" },
  { label: "FAQ", href: "/faq" },
  { label: "Survival Simulator", href: "/survival-simulator" },
];

const footerProduct = [
  { label: "Features", href: "/features" },
  { label: "Pricing", href: "/pricing" },
  { label: "FAQ", href: "/faq" },
  { label: "Demo", href: "/demo" },
  { label: "Runway Calculator", href: "/tools/runway-calculator" },
  { label: "Survival Simulator", href: "/survival-simulator" },
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
      aria-current={isActive ? "page" : undefined}
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
    <header className="sticky top-0 z-[9999] border-b border-border/50 bg-background/60 backdrop-blur-2xl backdrop-saturate-150">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" data-testid="link-logo" className="flex items-center gap-2">
          <FCLogo size="md" />
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
                    <FCLogo size="sm" />
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
            <p className="text-sm text-muted-foreground">
              Questions or feedback?{" "}
              <Link href="/contact" data-testid="footer-link-contact" className="text-foreground transition-colors hover:underline">
                Get in touch
              </Link>
            </p>
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

function MobileStickyCTA() {
  return (
    <div className="fixed bottom-0 left-0 right-0 z-[9998] border-t bg-background/95 backdrop-blur-md p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] md:hidden" data-testid="mobile-sticky-cta">
      <Button className="w-full" size="lg" asChild>
        <Link href="/auth">Get Started Free</Link>
      </Button>
    </div>
  );
}

function useMetaPixel() {
  const pixelLoaded = useRef(false);
  const [location] = useLocation();

  useEffect(() => {
    if (pixelLoaded.current) {
      if ((window as any).fbq) {
        (window as any).fbq('track', 'PageView');
      }
      return;
    }
    pixelLoaded.current = true;
    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://connect.facebook.net/en_US/fbevents.js';
    (window as any).fbq = function () {
      (window as any).fbq.callMethod
        ? (window as any).fbq.callMethod.apply((window as any).fbq, arguments)
        : (window as any).fbq.queue.push(arguments);
    };
    (window as any).fbq.push = (window as any).fbq;
    (window as any).fbq.loaded = true;
    (window as any).fbq.version = '2.0';
    (window as any).fbq.queue = [];
    document.head.appendChild(script);
    (window as any).fbq('init', '872167299140812');
    (window as any).fbq('track', 'PageView');
  }, [location]);
}

export function MarketingLayout({ children }: { children: React.ReactNode }) {
  useMetaPixel();
  const [location] = useLocation();
  const prefersReducedMotion = useReducedMotion();

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <MarketingBackground />
      <Header />
      {prefersReducedMotion ? (
        <main className="relative z-[1] flex-1 pb-16 md:pb-0">{children}</main>
      ) : (
        <AnimatePresence mode="wait" initial={false}>
          <motion.main
            key={location}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="relative z-[1] flex-1 pb-16 md:pb-0"
          >
            {children}
          </motion.main>
        </AnimatePresence>
      )}
      <Footer />
      <MobileStickyCTA />
    </div>
  );
}

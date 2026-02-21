import { useLocation } from "wouter";
import { ChevronRight } from "lucide-react";

const ROUTE_LABELS: Record<string, string> = {
  "/": "Home",
  "/overview": "Overview",
  "/dashboard": "Dashboard",
  "/truth-scan": "Truth Scan",
  "/truth": "Truth Scan",
  "/data": "Data Input",
  "/scenarios": "Scenarios",
  "/decisions": "Decisions",
  "/copilot": "AI Copilot",
  "/integrations": "Integrations",
  "/marketplace": "Connector Marketplace",
  "/add-data-source": "Add Data Source",
  "/alerts": "Alerts",
  "/templates": "Templates",
  "/docs": "Documentation",
  "/fundraising": "Fundraising",
  "/investor-room": "Investor Room",
  "/dashboards": "Dashboards",
  "/metrics": "Metrics",
  "/suggested-metrics": "Suggested Metrics",
  "/journal": "Journal",
  "/goals": "Goals",
  "/kpi-board": "KPI Board",
};

export function Breadcrumbs() {
  const [location] = useLocation();

  // Hide on auth, onboarding, and other standalone pages
  const shouldHide =
    location === "/auth" ||
    location === "/onboarding" ||
    location.startsWith("/admin") ||
    location === "/pricing" ||
    location === "/demo" ||
    location === "/owner-console" ||
    location.startsWith("/scenarios/shared/");

  if (shouldHide) {
    return null;
  }

  // Parse the current path
  const pathSegments = location.split("/").filter(Boolean);
  const breadcrumbs: Array<{ label: string; path: string; isCurrent: boolean }> = [
    { label: "Home", path: "/", isCurrent: location === "/" },
  ];

  // Build breadcrumb trail
  let currentPath = "";
  for (const segment of pathSegments) {
    currentPath += `/${segment}`;
    const label = ROUTE_LABELS[currentPath] || segment.replace(/-/g, " ");
    breadcrumbs.push({
      label: label.charAt(0).toUpperCase() + label.slice(1),
      path: currentPath,
      isCurrent: location === currentPath,
    });
  }

  if (breadcrumbs.length <= 1) {
    return null;
  }

  return (
    <nav
      className="flex items-center gap-2 px-6 py-2 text-xs text-muted-foreground bg-background border-b"
      data-testid="breadcrumbs"
    >
      {breadcrumbs.map((crumb, index) => (
        <div key={crumb.path} className="flex items-center gap-2">
          {crumb.isCurrent ? (
            <span className="text-foreground font-medium">{crumb.label}</span>
          ) : (
            <a
              href={crumb.path}
              className="hover:text-foreground transition-colors"
              data-testid={`breadcrumb-link-${crumb.label.toLowerCase().replace(/\s/g, '-')}`}
            >
              {crumb.label}
            </a>
          )}
          {index < breadcrumbs.length - 1 && (
            <ChevronRight className="h-3 w-3 text-muted-foreground/50" />
          )}
        </div>
      ))}
    </nav>
  );
}

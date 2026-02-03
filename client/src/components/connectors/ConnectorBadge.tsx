import { Badge } from "@/components/ui/badge";
import { Zap, FlaskConical, Shield, Webhook, RefreshCw } from "lucide-react";

interface ConnectorBadgeProps {
  type: "native" | "beta" | "realtime" | "webhook" | "verified";
  size?: "sm" | "default";
}

export function ConnectorBadge({ type, size = "default" }: ConnectorBadgeProps) {
  const sizeClasses = size === "sm" ? "text-xs px-1.5 py-0" : "";
  
  switch (type) {
    case "native":
      return (
        <Badge variant="default" className={`bg-emerald-500/10 text-emerald-600 border-emerald-500/20 ${sizeClasses}`}>
          <Shield className="h-3 w-3 mr-1" />
          Native
        </Badge>
      );
    case "beta":
      return (
        <Badge variant="outline" className={`border-amber-500/30 text-amber-600 ${sizeClasses}`}>
          <FlaskConical className="h-3 w-3 mr-1" />
          Beta
        </Badge>
      );
    case "realtime":
      return (
        <Badge variant="outline" className={`border-blue-500/30 text-blue-600 ${sizeClasses}`}>
          <Zap className="h-3 w-3 mr-1" />
          Real-time
        </Badge>
      );
    case "webhook":
      return (
        <Badge variant="outline" className={`border-purple-500/30 text-purple-600 ${sizeClasses}`}>
          <Webhook className="h-3 w-3 mr-1" />
          Webhook
        </Badge>
      );
    case "verified":
      return (
        <Badge variant="outline" className={`border-emerald-500/30 text-emerald-600 ${sizeClasses}`}>
          <Shield className="h-3 w-3 mr-1" />
          Verified
        </Badge>
      );
    default:
      return null;
  }
}

interface RefreshBadgeProps {
  cadence: string;
  size?: "sm" | "default";
}

export function RefreshBadge({ cadence, size = "default" }: RefreshBadgeProps) {
  const sizeClasses = size === "sm" ? "text-xs px-1.5 py-0" : "";
  
  const getColor = () => {
    switch (cadence) {
      case "real-time": return "text-emerald-600 border-emerald-500/30";
      case "hourly": return "text-blue-600 border-blue-500/30";
      case "daily": return "text-amber-600 border-amber-500/30";
      default: return "text-muted-foreground";
    }
  };
  
  return (
    <Badge variant="outline" className={`${getColor()} ${sizeClasses}`}>
      <RefreshCw className="h-3 w-3 mr-1" />
      {cadence}
    </Badge>
  );
}

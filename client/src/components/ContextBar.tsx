import { useFounderStore } from "@/store/founderStore";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Building2, GitBranch, Play, Clock, Database } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

interface ContextBarProps {
  scenarioName?: string;
  scenarioId?: number | null;
  runId?: string | null;
  runTimestamp?: string | null;
}

export function ContextBar({ scenarioName, scenarioId, runId, runTimestamp }: ContextBarProps) {
  const { currentCompany, truthScan } = useFounderStore();
  
  if (!currentCompany) return null;
  
  const truthTimestamp = truthScan?.computed_at;
  const dataFreshness = truthTimestamp 
    ? formatDistanceToNow(new Date(truthTimestamp), { addSuffix: true })
    : null;
  
  const runFreshness = runTimestamp
    ? formatDistanceToNow(new Date(runTimestamp), { addSuffix: true })
    : null;

  const getDataFreshnessColor = () => {
    if (!truthTimestamp) return "text-muted-foreground";
    const hoursSince = (Date.now() - new Date(truthTimestamp).getTime()) / (1000 * 60 * 60);
    if (hoursSince < 24) return "text-emerald-400";
    if (hoursSince < 72) return "text-amber-400";
    return "text-red-400";
  };

  return (
    <div 
      className="flex items-center gap-1 text-xs bg-muted/50 rounded-md px-2 py-1 overflow-hidden whitespace-nowrap"
      data-testid="context-bar"
    >
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-1 px-1.5 py-0.5 rounded hover-elevate cursor-default">
            <Building2 className="h-3 w-3 text-primary" />
            <span className="font-medium truncate max-w-[120px]" data-testid="context-company">
              {currentCompany.name}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          <div className="text-xs">
            <p className="font-medium">{currentCompany.name}</p>
            {currentCompany.industry && <p className="text-muted-foreground">{currentCompany.industry}</p>}
            {currentCompany.stage && <p className="text-muted-foreground">Stage: {currentCompany.stage}</p>}
          </div>
        </TooltipContent>
      </Tooltip>

      <span className="text-muted-foreground">•</span>

      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-1 px-1.5 py-0.5 rounded hover-elevate cursor-default">
            <GitBranch className="h-3 w-3 text-blue-400" />
            <span className="truncate max-w-[100px]" data-testid="context-scenario">
              {scenarioName || "No Scenario"}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          <div className="text-xs">
            <p className="font-medium">Active Scenario</p>
            <p>{scenarioName || "No scenario selected"}</p>
            {scenarioId && <p className="text-muted-foreground">ID: {scenarioId}</p>}
          </div>
        </TooltipContent>
      </Tooltip>

      {runId && (
        <>
          <span className="text-muted-foreground">•</span>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1 px-1.5 py-0.5 rounded hover-elevate cursor-default">
                <Play className="h-3 w-3 text-green-400" />
                <span className="font-mono text-[10px]" data-testid="context-run-id">
                  {runId.slice(0, 8)}
                </span>
              </div>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              <div className="text-xs">
                <p className="font-medium">Simulation Run</p>
                <p className="font-mono">{runId}</p>
                {runFreshness && <p className="text-muted-foreground">Ran {runFreshness}</p>}
              </div>
            </TooltipContent>
          </Tooltip>
        </>
      )}

      <span className="text-muted-foreground">•</span>

      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-1 px-1.5 py-0.5 rounded hover-elevate cursor-default">
            <Database className={`h-3 w-3 ${getDataFreshnessColor()}`} />
            <span className={`${getDataFreshnessColor()} truncate max-w-[120px]`} data-testid="context-data-freshness">
              {dataFreshness ? `Data ${dataFreshness}` : "No Data"}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          <div className="text-xs">
            <p className="font-medium">Data Freshness</p>
            {truthTimestamp ? (
              <>
                <p>Last validated: {new Date(truthTimestamp).toLocaleString()}</p>
                <p className="text-muted-foreground">
                  Confidence: {truthScan?.data_confidence_score || 0}%
                </p>
              </>
            ) : (
              <p className="text-muted-foreground">No validated data available</p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>

      {(runTimestamp || truthTimestamp) && (
        <>
          <span className="text-muted-foreground">•</span>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1 px-1.5 py-0.5 rounded hover-elevate cursor-default">
                <Clock className={`h-3 w-3 ${runTimestamp ? 'text-amber-400' : 'text-emerald-400'}`} />
                <span className="text-[10px] font-mono truncate" data-testid="context-timestamp">
                  {new Date(runTimestamp || truthTimestamp!).toLocaleString(undefined, { 
                    month: 'short', 
                    day: 'numeric', 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </span>
              </div>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              <div className="text-xs">
                <p className="font-medium">{runTimestamp ? 'Last Simulation Run' : 'Last Truth Scan'}</p>
                <p>{new Date(runTimestamp || truthTimestamp!).toLocaleString()}</p>
                {runTimestamp && runFreshness && <p className="text-muted-foreground">{runFreshness}</p>}
                {!runTimestamp && dataFreshness && <p className="text-muted-foreground">Data {dataFreshness}</p>}
              </div>
            </TooltipContent>
          </Tooltip>
        </>
      )}
      
      {truthScan && (
        <>
          <span className="text-muted-foreground">•</span>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1 px-1.5 py-0.5 rounded hover-elevate cursor-default">
                <Badge 
                  variant="outline" 
                  className="text-[10px] px-1 py-0 h-4"
                  data-testid="context-confidence"
                >
                  {truthScan.data_confidence_score}% conf
                </Badge>
              </div>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              <div className="text-xs">
                <p className="font-medium">Data Confidence Score</p>
                <p>Based on validation checks and data completeness</p>
                <p className="text-muted-foreground mt-1">
                  Quality of Growth: {truthScan.quality_of_growth_index?.toFixed(2) || "N/A"}
                </p>
              </div>
            </TooltipContent>
          </Tooltip>
        </>
      )}
    </div>
  );
}

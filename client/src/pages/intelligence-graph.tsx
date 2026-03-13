import { useState, useCallback, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useFounderStore } from "@/store/founderStore";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { queryClient, apiRequest } from "@/lib/queryClient";
import {
  Network,
  Users,
  Target,
  TrendingUp,
  BarChart3,
  Lightbulb,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Brain,
  Activity,
  Award,
  GitBranch,
  Loader2,
  RefreshCw,
  ChevronRight,
  Sparkles,
  Building2,
  Zap,
  AlertTriangle,
  CheckCircle2,
  Info,
  Shield,
  Link2,
  Circle,
  Share2,
} from "lucide-react";


function SimilarCompanies({ companyId }: { companyId: number }) {
  const { data, isLoading } = useQuery<any>({
    queryKey: ["/api/companies", companyId, "intelligence", "similar"],
    enabled: !!companyId,
  });

  if (isLoading) return <Skeleton className="h-64" />;

  const similar = data?.similar_companies || [];
  const profile = data?.your_profile || {};

  return (
    <Card data-testid="similar-companies">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Users className="h-4 w-4 text-primary" />
          Similar Companies
        </CardTitle>
        <CardDescription>
          Companies matching your profile: {profile.stage} stage, {profile.industry} industry, {profile.mrr_range} MRR
        </CardDescription>
      </CardHeader>
      <CardContent>
        {similar.length === 0 ? (
          <div className="text-center py-6 text-muted-foreground text-sm">
            <Building2 className="h-8 w-8 mx-auto mb-2 opacity-40" />
            <p>No similar companies found yet</p>
            <p className="text-xs mt-1">As more companies join the platform, peer matching improves</p>
          </div>
        ) : (
          <div className="space-y-3">
            {similar.map((c: any, i: number) => (
              <div
                key={i}
                className="flex items-center gap-3 p-3 rounded-lg bg-muted/20 border border-border/30"
                data-testid={`similar-company-${i}`}
              >
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <span className="text-sm font-bold text-primary">{Math.round(c.similarity_score * 100)}%</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{c.industry}</span>
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4">
                      {c.stage}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {c.shared_traits?.slice(0, 3).map((trait: string, j: number) => (
                      <span key={j} className="text-[10px] text-muted-foreground bg-muted/40 px-1.5 py-0.5 rounded">
                        {trait}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-xs text-muted-foreground">{c.mrr_range}</div>
                  <div className="text-xs text-muted-foreground">{c.growth_tier}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}


function StrategyLeaderboard({ companyId }: { companyId: number }) {
  const { data, isLoading } = useQuery<any>({
    queryKey: ["/api/companies", companyId, "intelligence", "strategies"],
    enabled: !!companyId,
  });

  if (isLoading) return <Skeleton className="h-64" />;

  const strategies = data?.strategies || [];
  const peerInsights = data?.peer_insights || [];

  return (
    <div className="space-y-4">
      <Card data-testid="strategy-leaderboard">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Award className="h-4 w-4 text-amber-500" />
            Strategy Leaderboard
          </CardTitle>
          <CardDescription>Most adopted strategies across the platform</CardDescription>
        </CardHeader>
        <CardContent>
          {strategies.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">No strategy data available yet</p>
          ) : (
            <div className="space-y-3">
              {strategies.map((s: any, i: number) => (
                <div key={i} className="space-y-1.5" data-testid={`strategy-${s.strategy}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium capitalize">{s.strategy.replace("_", " ")}</span>
                      <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4">
                        {s.company_count} {s.company_count === 1 ? "company" : "companies"}
                      </Badge>
                    </div>
                    <span className="text-xs text-muted-foreground font-mono">
                      {s.high_confidence_rate}% confidence
                    </span>
                  </div>
                  <Progress value={Math.min(s.adoption_count * 10, 100)} className="h-1.5" />
                  <p className="text-xs text-muted-foreground leading-relaxed">{s.recommendation}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card data-testid="peer-insights">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            Peer Insights
          </CardTitle>
        </CardHeader>
        <CardContent>
          {peerInsights.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">No peer insights available</p>
          ) : (
            <div className="space-y-3">
              {peerInsights.map((insight: any, i: number) => {
                const Icon = insight.position === "above" ? ArrowUpRight :
                             insight.position === "below" ? ArrowDownRight : Minus;
                const color = insight.position === "above" ? "text-emerald-500" :
                              insight.position === "below" ? "text-amber-500" : "text-muted-foreground";
                return (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-muted/20 border border-border/30">
                    <Icon className={`h-4 w-4 mt-0.5 flex-shrink-0 ${color}`} />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium">{insight.title}</div>
                      <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{insight.description}</p>
                      {insight.your_value && insight.metric && (
                        <div className="flex gap-3 mt-2">
                          <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded">
                            You: {insight.your_value}
                          </span>
                          <span className="text-xs bg-muted/40 px-2 py-0.5 rounded">
                            Peers: {insight.metric}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


function DecisionPatterns({ companyId }: { companyId: number }) {
  const { data, isLoading } = useQuery<any>({
    queryKey: ["/api/companies", companyId, "intelligence", "patterns"],
    enabled: !!companyId,
  });

  if (isLoading) return <Skeleton className="h-64" />;

  const patterns = data?.patterns || [];
  const recentDecisions = data?.your_recent_decisions || [];
  const totalDecisions = data?.total_decisions || 0;

  return (
    <div className="space-y-4">
      <Card data-testid="decision-patterns">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-violet-500" />
            Decision Patterns
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
              {totalDecisions} total
            </Badge>
          </CardTitle>
          <CardDescription>How decisions are distributed and their acceptance rates</CardDescription>
        </CardHeader>
        <CardContent>
          {patterns.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">No decision data available</p>
          ) : (
            <div className="space-y-3">
              {patterns.map((p: any, i: number) => (
                <div key={i} className="flex items-center gap-3" data-testid={`pattern-${p.decision_type}`}>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium capitalize">{p.decision_type.replace("_", " ")}</span>
                      <span className="text-xs text-muted-foreground">{p.total_count} decisions</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Progress value={p.acceptance_rate} className="h-1.5 flex-1" />
                      <span className="text-xs font-mono w-10 text-right">{p.acceptance_rate}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card data-testid="your-recent-decisions">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Target className="h-4 w-4 text-primary" />
            Your Recent Decisions
          </CardTitle>
        </CardHeader>
        <CardContent>
          {recentDecisions.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">No decisions logged yet</p>
          ) : (
            <div className="space-y-2">
              {recentDecisions.map((d: any, i: number) => (
                <div key={i} className="flex items-center gap-3 p-2 rounded-lg bg-muted/10">
                  <div className={`h-2 w-2 rounded-full flex-shrink-0 ${
                    d.status === "accepted" || d.status === "implemented" || d.status === "completed" ? "bg-emerald-500" :
                    d.status === "rejected" ? "bg-red-500" : "bg-amber-500"
                  }`} />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm truncate block">{d.title}</span>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 capitalize">
                        {d.type}
                      </Badge>
                      <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4">
                        {d.status}
                      </Badge>
                    </div>
                  </div>
                  {d.created_at && (
                    <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                      {new Date(d.created_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


function GrowthBenchmarks({ companyId }: { companyId: number }) {
  const { data, isLoading } = useQuery<any>({
    queryKey: ["/api/companies", companyId, "intelligence", "benchmarks"],
    enabled: !!companyId,
  });

  if (isLoading) return <Skeleton className="h-64" />;

  const profile = data?.your_profile || {};
  const benchmarks = data?.stage_benchmarks || {};
  const totalCompanies = data?.total_companies_analyzed || 0;
  const totalPoints = data?.total_data_points || 0;

  const yourStage = profile.stage || "unknown";
  const stageData = benchmarks[yourStage];

  return (
    <Card data-testid="growth-benchmarks">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-emerald-500" />
          Growth Benchmarks
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
            {totalCompanies} companies, {totalPoints} data points
          </Badge>
        </CardTitle>
        <CardDescription>How you compare to companies at your stage</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricBox label="Your MRR" value={`$${(profile.mrr || 0).toLocaleString()}`} />
            <MetricBox label="Growth" value={`${profile.growth_pct || 0}%`} />
            <MetricBox label="Runway" value={`${Math.round(profile.runway_months || 0)}mo`} />
            <MetricBox label="Stage" value={profile.stage || "—"} />
          </div>

          {stageData ? (
            <div className="mt-4">
              <h4 className="text-sm font-medium mb-3">Revenue Distribution — {yourStage} Stage</h4>
              <div className="flex items-end gap-2 h-24">
                <BenchmarkBar label="P25" value={stageData.p25} max={stageData.p75 * 1.2} yourValue={profile.mrr} />
                <BenchmarkBar label="Median" value={stageData.median} max={stageData.p75 * 1.2} yourValue={profile.mrr} />
                <BenchmarkBar label="P75" value={stageData.p75} max={stageData.p75 * 1.2} yourValue={profile.mrr} />
                <BenchmarkBar label="You" value={profile.mrr || 0} max={stageData.p75 * 1.2} isYou />
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Based on {stageData.sample_size} data points from {yourStage}-stage companies
              </p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              No benchmark data available for {yourStage} stage yet
            </p>
          )}

          {Object.keys(benchmarks).length > 1 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium mb-2">All Stage Benchmarks</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {Object.entries(benchmarks).map(([stage, data]: [string, any]) => (
                  <div key={stage} className="flex items-center justify-between p-2 rounded bg-muted/20 border border-border/30">
                    <span className="text-sm capitalize">{stage}</span>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground font-mono">
                      <span>P25: ${data.p25?.toLocaleString()}</span>
                      <span>Med: ${data.median?.toLocaleString()}</span>
                      <span>P75: ${data.p75?.toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}


const NODE_COLORS: Record<string, string> = {
  Company: "bg-primary text-primary-foreground",
  Metric: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  Decision: "bg-violet-500/20 text-violet-400 border-violet-500/30",
  Strategy: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  Outcome: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  Simulation: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
};

const NODE_ICONS: Record<string, any> = {
  Company: Building2,
  Metric: Activity,
  Decision: GitBranch,
  Strategy: Lightbulb,
  Outcome: CheckCircle2,
  Simulation: TrendingUp,
};

function NetworkGraph({ companyId }: { companyId: number }) {
  const { data, isLoading } = useQuery<any>({
    queryKey: ["/api/companies", companyId, "intelligence", "network"],
    enabled: !!companyId,
  });

  const nodes = data?.nodes || [];
  const edges = data?.edges || [];
  const nodeTypes = data?.node_types || [];

  const nodesByType = useMemo(() => {
    const grouped: Record<string, any[]> = {};
    nodes.forEach((n: any) => {
      if (!grouped[n.type]) grouped[n.type] = [];
      grouped[n.type].push(n);
    });
    return grouped;
  }, [nodes]);

  const typeOrder = ["Company", "Metric", "Decision", "Strategy", "Outcome", "Simulation"];
  const layoutPositions = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {};
    const centerX = 400;
    const centerY = 300;

    const selfNode = nodes.find((n: any) => n.is_self);
    if (selfNode) {
      positions[selfNode.id] = { x: centerX, y: centerY };
    }

    const rings: Record<string, { radius: number; startAngle: number }> = {
      Metric: { radius: 140, startAngle: -Math.PI / 2 },
      Decision: { radius: 200, startAngle: Math.PI / 6 },
      Strategy: { radius: 160, startAngle: Math.PI },
      Outcome: { radius: 240, startAngle: Math.PI / 3 },
      Company: { radius: 220, startAngle: -Math.PI / 4 },
      Simulation: { radius: 180, startAngle: -Math.PI / 6 },
    };

    typeOrder.forEach((type) => {
      const typeNodes = (nodesByType[type] || []).filter((n: any) => !n.is_self);
      const ring = rings[type] || { radius: 200, startAngle: 0 };
      const angleStep = typeNodes.length > 1 ? (Math.PI * 0.8) / (typeNodes.length - 1) : 0;

      typeNodes.forEach((n: any, i: number) => {
        const angle = ring.startAngle + i * angleStep;
        positions[n.id] = {
          x: centerX + ring.radius * Math.cos(angle),
          y: centerY + ring.radius * Math.sin(angle),
        };
      });
    });

    return positions;
  }, [nodes, nodesByType]);

  if (isLoading) return <Skeleton className="h-96" />;

  return (
    <div className="space-y-4">
      <Card data-testid="network-graph">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Share2 className="h-4 w-4 text-primary" />
            Intelligence Network
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
              {nodes.length} nodes, {edges.length} edges
            </Badge>
          </CardTitle>
          <CardDescription>
            Relationships between your company, metrics, decisions, strategies, and peers
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative bg-muted/10 border border-border/30 rounded-lg overflow-hidden" style={{ height: "500px" }}>
            <svg width="100%" height="100%" viewBox="0 0 800 600" data-testid="network-svg">
              {edges.map((edge: any, i: number) => {
                const from = layoutPositions[edge.from];
                const to = layoutPositions[edge.to];
                if (!from || !to) return null;
                return (
                  <line
                    key={i}
                    x1={from.x}
                    y1={from.y}
                    x2={to.x}
                    y2={to.y}
                    stroke="currentColor"
                    strokeOpacity={0.15}
                    strokeWidth={1}
                  />
                );
              })}
            </svg>

            {nodes.map((node: any) => {
              const pos = layoutPositions[node.id];
              if (!pos) return null;
              const colorClass = NODE_COLORS[node.type] || "bg-muted text-muted-foreground";
              const IconComp = NODE_ICONS[node.type] || Circle;
              const isCompanySelf = node.is_self;
              const size = isCompanySelf ? "w-16 h-16" : "w-10 h-10";
              const iconSize = isCompanySelf ? "h-5 w-5" : "h-3.5 w-3.5";

              return (
                <div
                  key={node.id}
                  className="absolute transform -translate-x-1/2 -translate-y-1/2 group"
                  style={{
                    left: `${(pos.x / 800) * 100}%`,
                    top: `${(pos.y / 600) * 100}%`,
                  }}
                  data-testid={`node-${node.id}`}
                >
                  <div className={`${size} rounded-full ${colorClass} border flex items-center justify-center cursor-pointer transition-transform hover:scale-110`}>
                    <IconComp className={iconSize} />
                  </div>
                  <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 whitespace-nowrap">
                    <span className="text-[9px] text-muted-foreground font-medium">
                      {node.label?.length > 20 ? node.label.substring(0, 20) + "..." : node.label}
                    </span>
                  </div>
                  <div className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50">
                    <div className="bg-popover border border-border rounded-md shadow-lg p-2 text-xs min-w-[140px]">
                      <div className="font-medium">{node.label}</div>
                      <div className="text-muted-foreground">{node.type}</div>
                      {node.properties && Object.entries(node.properties).slice(0, 3).map(([key, val]: [string, any]) => (
                        <div key={key} className="text-muted-foreground">
                          {key}: {typeof val === "number" ? val.toLocaleString() : String(val)}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="flex flex-wrap gap-3 mt-3">
            {nodeTypes.map((type: string) => {
              const colorClass = NODE_COLORS[type] || "bg-muted";
              const Icon = NODE_ICONS[type] || Circle;
              return (
                <div key={type} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <div className={`w-3 h-3 rounded-full ${colorClass} border flex items-center justify-center`}>
                    <Icon className="h-1.5 w-1.5" />
                  </div>
                  {type}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Card className="p-3">
          <div className="text-xs text-muted-foreground mb-1">Node Types</div>
          <div className="flex flex-wrap gap-1">
            {nodeTypes.map((t: string) => (
              <Badge key={t} variant="outline" className="text-[10px]">{t}</Badge>
            ))}
          </div>
        </Card>
        <Card className="p-3">
          <div className="text-xs text-muted-foreground mb-1">Relationships</div>
          <div className="flex flex-wrap gap-1">
            {(data?.relationship_types || []).map((r: string) => (
              <Badge key={r} variant="outline" className="text-[10px]">{r}</Badge>
            ))}
          </div>
        </Card>
        <Card className="p-3">
          <div className="text-xs text-muted-foreground mb-1">Graph Size</div>
          <div className="text-lg font-bold font-mono">{nodes.length} <span className="text-xs font-normal text-muted-foreground">nodes</span> / {edges.length} <span className="text-xs font-normal text-muted-foreground">edges</span></div>
        </Card>
      </div>
    </div>
  );
}


function AIInsights({ companyId }: { companyId: number }) {
  const { data, isLoading } = useQuery<any>({
    queryKey: ["/api/companies", companyId, "intelligence", "ai-insights"],
    enabled: !!companyId,
  });

  if (isLoading) return <Skeleton className="h-64" />;

  const insights = data?.insights || [];
  const profile = data?.profile || {};
  const peerCount = data?.peer_count || 0;

  const severityConfig: Record<string, { icon: any; color: string; bg: string }> = {
    critical: { icon: AlertTriangle, color: "text-red-500", bg: "bg-red-500/10 border-red-500/20" },
    high: { icon: AlertTriangle, color: "text-amber-500", bg: "bg-amber-500/10 border-amber-500/20" },
    medium: { icon: Lightbulb, color: "text-blue-500", bg: "bg-blue-500/10 border-blue-500/20" },
    low: { icon: CheckCircle2, color: "text-emerald-500", bg: "bg-emerald-500/10 border-emerald-500/20" },
    info: { icon: Info, color: "text-muted-foreground", bg: "bg-muted/20 border-border/30" },
  };

  return (
    <div className="space-y-4">
      <Card data-testid="ai-insights">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Brain className="h-4 w-4 text-primary" />
            AI Strategy Insights
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
              {insights.length} insights
            </Badge>
          </CardTitle>
          <CardDescription>
            AI-powered analysis based on {peerCount} peer companies and cross-platform intelligence
          </CardDescription>
        </CardHeader>
        <CardContent>
          {insights.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">
              <Brain className="h-8 w-8 mx-auto mb-2 opacity-40" />
              <p>No AI insights available yet</p>
              <p className="text-xs mt-1">Insights are generated as more platform data becomes available</p>
            </div>
          ) : (
            <div className="space-y-3">
              {insights.map((insight: any, i: number) => {
                const config = severityConfig[insight.severity] || severityConfig.info;
                const Icon = config.icon;
                return (
                  <div
                    key={i}
                    className={`p-4 rounded-lg border ${config.bg}`}
                    data-testid={`insight-${insight.type}`}
                  >
                    <div className="flex items-start gap-3">
                      <Icon className={`h-4 w-4 mt-0.5 flex-shrink-0 ${config.color}`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-medium">{insight.title}</span>
                          <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 capitalize">
                            {insight.severity}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed">{insight.description}</p>
                        {insight.recommended_strategies && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {insight.recommended_strategies.map((s: string) => (
                              <Badge key={s} variant="outline" className="text-[10px] capitalize">
                                {s.replace("_", " ")}
                              </Badge>
                            ))}
                          </div>
                        )}
                        {insight.peer_evidence && (
                          <div className="mt-2 text-[10px] text-muted-foreground bg-muted/30 px-2 py-1 rounded">
                            Peer evidence: {insight.peer_evidence.adoption_count} adoptions across {insight.peer_evidence.company_count} companies ({insight.peer_evidence.confidence_rate}% confidence)
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <GraphRecommendations companyId={companyId} />
    </div>
  );
}


function GraphRecommendations({ companyId }: { companyId: number }) {
  const { data, isLoading, refetch } = useQuery<any>({
    queryKey: ["/api/companies", companyId, "intelligence", "recommendations"],
    enabled: false,
  });

  const recommendMutation = useMutation({
    mutationFn: () => apiRequest("POST", `/api/companies/${companyId}/intelligence/recommendations`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/companies", companyId, "intelligence", "recommendations"] });
      refetch();
    },
  });

  const recommendations = data?.recommendations || [];

  return (
    <Card data-testid="graph-recommendations">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Zap className="h-4 w-4 text-amber-500" />
              Graph-Powered Recommendations
            </CardTitle>
            <CardDescription>Simulation + peer intelligence combined recommendations</CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => recommendMutation.mutate()}
            disabled={recommendMutation.isPending}
            data-testid="button-generate-recommendations"
          >
            {recommendMutation.isPending ? (
              <Loader2 className="h-3 w-3 mr-2 animate-spin" />
            ) : (
              <Sparkles className="h-3 w-3 mr-2" />
            )}
            Generate
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {recommendations.length === 0 && !recommendMutation.isPending ? (
          <div className="text-center py-6 text-muted-foreground text-sm">
            <Zap className="h-8 w-8 mx-auto mb-2 opacity-40" />
            <p>Click Generate to get recommendations powered by peer intelligence and simulation data</p>
          </div>
        ) : recommendMutation.isPending ? (
          <div className="text-center py-6">
            <Loader2 className="h-6 w-6 mx-auto mb-2 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Analyzing peer data and simulations...</p>
          </div>
        ) : (
          <div className="space-y-3">
            {recommendations.map((rec: any, i: number) => {
              const priorityColors: Record<string, string> = {
                critical: "border-red-500/30 bg-red-500/5",
                high: "border-amber-500/30 bg-amber-500/5",
                medium: "border-blue-500/30 bg-blue-500/5",
                low: "border-border/30 bg-muted/10",
              };
              return (
                <div
                  key={i}
                  className={`p-3 rounded-lg border ${priorityColors[rec.priority] || priorityColors.low}`}
                  data-testid={`recommendation-${i}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 capitalize">
                      {rec.priority}
                    </Badge>
                    <span className="text-sm font-medium">{rec.title}</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">{rec.description}</p>
                  {rec.suggested_actions && (
                    <div className="mt-2 space-y-1">
                      {rec.suggested_actions.map((action: string, j: number) => (
                        <div key={j} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <ChevronRight className="h-3 w-3" />
                          {action}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}


function TwinSyncPanel({ companyId }: { companyId: number }) {
  const syncMutation = useMutation({
    mutationFn: () => apiRequest("POST", `/api/companies/${companyId}/intelligence/sync`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/companies", companyId, "intelligence"] });
    },
  });

  const syncData = syncMutation.data as any;

  return (
    <Card data-testid="twin-sync-panel">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Link2 className="h-4 w-4 text-cyan-500" />
              Digital Twin Sync
            </CardTitle>
            <CardDescription>Synchronize your Digital Twin state to the Intelligence Graph</CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            data-testid="button-sync-twin"
          >
            {syncMutation.isPending ? (
              <Loader2 className="h-3 w-3 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-3 w-3 mr-2" />
            )}
            Sync Now
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {syncMutation.isPending ? (
          <div className="text-center py-4">
            <Loader2 className="h-5 w-5 mx-auto mb-2 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Syncing Digital Twin to graph...</p>
          </div>
        ) : syncData?.synced ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm text-emerald-500">
              <CheckCircle2 className="h-4 w-4" />
              Sync complete
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-2 rounded bg-muted/20 border border-border/30 text-center">
                <div className="text-lg font-bold font-mono">{syncData.nodes_count}</div>
                <div className="text-[10px] text-muted-foreground uppercase">Nodes</div>
              </div>
              <div className="p-2 rounded bg-muted/20 border border-border/30 text-center">
                <div className="text-lg font-bold font-mono">{syncData.relationships_count}</div>
                <div className="text-[10px] text-muted-foreground uppercase">Relationships</div>
              </div>
            </div>
            {syncData.last_updated && (
              <p className="text-xs text-muted-foreground">
                Last twin update: {new Date(syncData.last_updated).toLocaleString()}
              </p>
            )}
          </div>
        ) : (
          <div className="text-center py-4 text-muted-foreground text-sm">
            <Link2 className="h-8 w-8 mx-auto mb-2 opacity-40" />
            <p>Click Sync to update the Intelligence Graph with your latest Digital Twin state</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}


function MetricBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-3 rounded-lg bg-muted/20 border border-border/30 text-center">
      <div className="text-lg font-semibold font-mono">{value}</div>
      <div className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</div>
    </div>
  );
}


function BenchmarkBar({
  label,
  value,
  max,
  yourValue,
  isYou,
}: {
  label: string;
  value: number;
  max: number;
  yourValue?: number;
  isYou?: boolean;
}) {
  const heightPct = max > 0 ? Math.min((value / max) * 100, 100) : 10;

  return (
    <div className="flex-1 flex flex-col items-center gap-1">
      <div className="text-[10px] font-mono text-muted-foreground">${value >= 1000 ? `${(value / 1000).toFixed(0)}K` : value.toFixed(0)}</div>
      <div className="w-full relative" style={{ height: "60px" }}>
        <div
          className={`absolute bottom-0 w-full rounded-t ${isYou ? "bg-primary" : "bg-muted-foreground/20"}`}
          style={{ height: `${heightPct}%`, minHeight: "4px" }}
        />
      </div>
      <span className={`text-[10px] ${isYou ? "text-primary font-medium" : "text-muted-foreground"}`}>{label}</span>
    </div>
  );
}


export default function IntelligenceGraphPage() {
  const { currentCompany } = useFounderStore();
  const companyId = currentCompany?.id;
  const [activeTab, setActiveTab] = useState("overview");

  const { data: summary, isLoading, isError, refetch } = useQuery<any>({
    queryKey: ["/api/companies", companyId, "intelligence", "summary"],
    enabled: !!companyId,
    staleTime: 60000,
  });

  if (!companyId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <Network className="h-12 w-12 mx-auto mb-3 text-muted-foreground/40" />
          <p className="text-muted-foreground" data-testid="text-no-company">Select a company to view intelligence</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-6 space-y-4 max-w-7xl mx-auto">
        <Skeleton className="h-10 w-72" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <Network className="h-12 w-12 mx-auto mb-3 text-red-500/40" />
          <p className="text-muted-foreground mb-3" data-testid="text-error">Failed to load Intelligence Graph</p>
          <Button variant="outline" size="sm" onClick={() => refetch()} data-testid="button-retry">
            <RefreshCw className="h-3 w-3 mr-2" /> Retry
          </Button>
        </div>
      </div>
    );
  }

  const stats = summary?.graph_stats || {};
  const profile = summary?.company_profile || {};

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto" data-testid="intelligence-graph-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2" data-testid="text-page-title">
            <Network className="h-5 w-5 text-primary" />
            Intelligence Graph
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Cross-company intelligence for {currentCompany?.name || "your company"}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} data-testid="button-refresh">
          <RefreshCw className="h-3 w-3 mr-2" /> Refresh
        </Button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <Card className="p-4" data-testid="stat-companies">
          <div className="flex items-center gap-2 text-muted-foreground mb-1">
            <Building2 className="h-3.5 w-3.5" />
            <span className="text-xs">Companies</span>
          </div>
          <div className="text-2xl font-bold font-mono">{stats.total_companies || 0}</div>
        </Card>
        <Card className="p-4" data-testid="stat-decisions">
          <div className="flex items-center gap-2 text-muted-foreground mb-1">
            <GitBranch className="h-3.5 w-3.5" />
            <span className="text-xs">Decisions</span>
          </div>
          <div className="text-2xl font-bold font-mono">{stats.total_decisions || 0}</div>
        </Card>
        <Card className="p-4" data-testid="stat-records">
          <div className="flex items-center gap-2 text-muted-foreground mb-1">
            <Activity className="h-3.5 w-3.5" />
            <span className="text-xs">Data Points</span>
          </div>
          <div className="text-2xl font-bold font-mono">{stats.total_financial_records || 0}</div>
        </Card>
        <Card className="p-4" data-testid="stat-events">
          <div className="flex items-center gap-2 text-muted-foreground mb-1">
            <Zap className="h-3.5 w-3.5" />
            <span className="text-xs">Events</span>
          </div>
          <div className="text-2xl font-bold font-mono">{stats.total_events || 0}</div>
        </Card>
        <Card className="p-4" data-testid="stat-similar">
          <div className="flex items-center gap-2 text-muted-foreground mb-1">
            <Users className="h-3.5 w-3.5" />
            <span className="text-xs">Similar Peers</span>
          </div>
          <div className="text-2xl font-bold font-mono">{stats.similar_companies_found || 0}</div>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview" data-testid="tab-overview">
            <Brain className="h-3.5 w-3.5 mr-1.5" /> Overview
          </TabsTrigger>
          <TabsTrigger value="network" data-testid="tab-network">
            <Share2 className="h-3.5 w-3.5 mr-1.5" /> Network
          </TabsTrigger>
          <TabsTrigger value="ai-insights" data-testid="tab-ai-insights">
            <Sparkles className="h-3.5 w-3.5 mr-1.5" /> AI Insights
          </TabsTrigger>
          <TabsTrigger value="strategies" data-testid="tab-strategies">
            <Lightbulb className="h-3.5 w-3.5 mr-1.5" /> Strategies
          </TabsTrigger>
          <TabsTrigger value="decisions" data-testid="tab-decisions">
            <GitBranch className="h-3.5 w-3.5 mr-1.5" /> Decisions
          </TabsTrigger>
          <TabsTrigger value="benchmarks" data-testid="tab-benchmarks">
            <BarChart3 className="h-3.5 w-3.5 mr-1.5" /> Benchmarks
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <SimilarCompanies companyId={companyId} />
            <div className="space-y-4">
              <TwinSyncPanel companyId={companyId} />
              <StrategyLeaderboard companyId={companyId} />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="network" className="mt-4">
          <NetworkGraph companyId={companyId} />
        </TabsContent>

        <TabsContent value="ai-insights" className="mt-4">
          <AIInsights companyId={companyId} />
        </TabsContent>

        <TabsContent value="strategies" className="mt-4">
          <StrategyLeaderboard companyId={companyId} />
        </TabsContent>

        <TabsContent value="decisions" className="mt-4">
          <DecisionPatterns companyId={companyId} />
        </TabsContent>

        <TabsContent value="benchmarks" className="mt-4">
          <GrowthBenchmarks companyId={companyId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

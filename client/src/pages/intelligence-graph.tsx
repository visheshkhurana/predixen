import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useFounderStore } from "@/store/founderStore";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
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
                    d.status === "accepted" || d.status === "implemented" ? "bg-emerald-500" :
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

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
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
            <StrategyLeaderboard companyId={companyId} />
          </div>
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

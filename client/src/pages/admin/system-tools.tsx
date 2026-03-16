import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Activity, Bot, Flag, Shield, AlertTriangle, Clock, RefreshCw, Zap, Brain, TrendingUp, Users, Database, ThumbsUp, BarChart3, Sparkles } from "lucide-react";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

export default function SystemToolsPage() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("events");

  const { data: eventsData, isLoading: eventsLoading } = useQuery({
    queryKey: ["/api/system/events"],
  });

  const { data: eventStats } = useQuery({
    queryKey: ["/api/system/events/stats"],
  });

  const { data: flagsData, isLoading: flagsLoading } = useQuery({
    queryKey: ["/api/system/flags"],
  });

  const { data: agentsData, isLoading: agentsLoading } = useQuery({
    queryKey: ["/api/system/agents"],
  });

  const { data: agentStats } = useQuery({
    queryKey: ["/api/system/agents/stats"],
  });

  const { data: briefingData } = useQuery({
    queryKey: ["/api/system/autopilot/briefing"],
  });

  const { data: risksData } = useQuery({
    queryKey: ["/api/system/autopilot/risks"],
  });

  const { data: platformIntelData, isLoading: platformIntelLoading } = useQuery({
    queryKey: ["/api/system/platform-intelligence"],
  });

  const { data: feedbackStats, isLoading: feedbackStatsLoading } = useQuery({
    queryKey: ["/api/ai/feedback/stats"],
  });

  const runAggregation = useMutation({
    mutationFn: async () => {
      return apiRequest("POST", "/api/system/platform-intelligence/aggregate");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/system/platform-intelligence"] });
      toast({ title: "Aggregation complete", description: "Cross-company patterns have been recomputed." });
    },
    onError: () => {
      toast({ title: "Aggregation failed", variant: "destructive" });
    },
  });

  const toggleFlag = useMutation({
    mutationFn: async ({ key, enabled }: { key: string; enabled: boolean }) => {
      return apiRequest("POST", `/api/system/flags/${key}?enabled=${enabled}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/system/flags"] });
      toast({ title: "Flag updated" });
    },
  });

  const runAutopilot = useMutation({
    mutationFn: async () => {
      return apiRequest("POST", "/api/system/autopilot/run");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/system/autopilot/briefing"] });
      queryClient.invalidateQueries({ queryKey: ["/api/system/autopilot/risks"] });
      toast({ title: "Autopilot run completed" });
    },
  });

  return (
    <div className="space-y-6" data-testid="system-tools-page">
      <div>
        <h1 className="text-2xl font-bold" data-testid="text-system-tools-title">System Tools</h1>
        <p className="text-muted-foreground">Internal tooling for events, agents, flags, and autopilot</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-6" data-testid="system-tools-tabs">
          <TabsTrigger value="events" data-testid="tab-events">
            <Activity className="w-4 h-4 mr-2" /> Events
          </TabsTrigger>
          <TabsTrigger value="agents" data-testid="tab-agents">
            <Bot className="w-4 h-4 mr-2" /> Agents
          </TabsTrigger>
          <TabsTrigger value="flags" data-testid="tab-flags">
            <Flag className="w-4 h-4 mr-2" /> Flags
          </TabsTrigger>
          <TabsTrigger value="autopilot" data-testid="tab-autopilot">
            <Zap className="w-4 h-4 mr-2" /> Autopilot
          </TabsTrigger>
          <TabsTrigger value="intelligence" data-testid="tab-intelligence">
            <Brain className="w-4 h-4 mr-2" /> Intelligence
          </TabsTrigger>
          <TabsTrigger value="learning" data-testid="tab-learning">
            <Sparkles className="w-4 h-4 mr-2" /> AI Learning
          </TabsTrigger>
        </TabsList>

        <TabsContent value="events" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Total Events</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold" data-testid="text-total-events">
                  {eventStats?.total_events ?? 0}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Event Types</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold" data-testid="text-event-types">
                  {eventStats?.by_type ? Object.keys(eventStats.by_type).length : 0}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Recent Events</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold" data-testid="text-recent-events">
                  {eventsData?.events?.length ?? 0}
                </div>
              </CardContent>
            </Card>
          </div>

          {eventStats?.by_type && Object.keys(eventStats.by_type).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Events by Type</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(eventStats.by_type).map(([type, count]: [string, any]) => (
                    <Badge key={type} variant="outline" data-testid={`badge-event-type-${type}`}>
                      {type}: {count}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Event Stream</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                {eventsLoading ? (
                  <p className="text-muted-foreground">Loading events...</p>
                ) : eventsData?.events?.length > 0 ? (
                  <div className="space-y-2">
                    {eventsData.events.map((event: any) => (
                      <div key={event.id} className="flex items-center justify-between p-3 rounded-lg border border-border" data-testid={`event-row-${event.id}`}>
                        <div className="flex items-center gap-3">
                          <Badge variant="secondary">{event.event_type}</Badge>
                          <span className="text-sm text-muted-foreground">{event.aggregate_type}</span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Clock className="w-3 h-3" />
                          {event.timestamp ? new Date(event.timestamp).toLocaleString() : "—"}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground">No events recorded yet. Events will appear as the system processes actions.</p>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="agents" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Total Requests (7d)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold" data-testid="text-agent-total-requests">
                  {agentStats?.total_requests ?? 0}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold" data-testid="text-active-agents">
                  {agentStats?.agents?.length ?? 0}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Agent Permissions</CardTitle>
            </CardHeader>
            <CardContent>
              {agentsLoading ? (
                <p className="text-muted-foreground">Loading agents...</p>
              ) : (
                <div className="space-y-3">
                  {(agentsData?.agents ?? []).map((agent: any) => (
                    <div key={agent.agent_name} className="flex items-center justify-between p-3 rounded-lg border border-border" data-testid={`agent-row-${agent.agent_name}`}>
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          <Bot className="w-4 h-4" />
                          {agent.agent_name}
                          {agent.requires_human_approval && (
                            <Badge variant="destructive" className="text-xs">
                              <Shield className="w-3 h-3 mr-1" /> Approval Required
                            </Badge>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          Max: {agent.max_daily_requests}/day · Actions: {(agent.allowed_actions || []).join(", ")}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {agentStats?.agents?.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Agent Usage (Last 7 Days)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {agentStats.agents.map((agent: any) => (
                    <div key={agent.agent_name} className="flex items-center justify-between p-2 border-b border-border" data-testid={`agent-usage-${agent.agent_name}`}>
                      <span className="font-medium">{agent.agent_name}</span>
                      <div className="flex items-center gap-4 text-sm">
                        <span>{agent.requests} requests</span>
                        <span className="text-muted-foreground">${agent.total_cost?.toFixed(4) ?? "0.00"}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="flags" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Feature Flags</CardTitle>
            </CardHeader>
            <CardContent>
              {flagsLoading ? (
                <p className="text-muted-foreground">Loading flags...</p>
              ) : (
                <div className="space-y-3">
                  {(flagsData?.flags ?? []).map((flag: any) => (
                    <div key={flag.key} className="flex items-center justify-between p-3 rounded-lg border border-border" data-testid={`flag-row-${flag.key}`}>
                      <div>
                        <div className="font-medium">{flag.key}</div>
                        <div className="text-xs text-muted-foreground">{flag.description}</div>
                      </div>
                      <Switch
                        checked={flag.enabled}
                        onCheckedChange={(checked) => toggleFlag.mutate({ key: flag.key, enabled: checked })}
                        data-testid={`switch-flag-${flag.key}`}
                      />
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="autopilot" className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold">Founder Autopilot</h3>
              <p className="text-sm text-muted-foreground">Automated risk detection and CEO briefing generation</p>
            </div>
            <Button
              onClick={() => runAutopilot.mutate()}
              disabled={runAutopilot.isPending}
              data-testid="button-run-autopilot"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${runAutopilot.isPending ? "animate-spin" : ""}`} />
              {runAutopilot.isPending ? "Running..." : "Run Autopilot"}
            </Button>
          </div>

          {risksData?.risks?.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-500" />
                  Detected Risks ({risksData.risks.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {risksData.risks.map((risk: any, i: number) => (
                    <div key={i} className="p-3 rounded-lg border border-border" data-testid={`risk-row-${risk.rule_id}`}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium">{risk.name}</span>
                        <Badge variant={risk.severity === "critical" ? "destructive" : risk.severity === "high" ? "default" : "secondary"}>
                          {risk.severity}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{risk.description}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {briefingData && !briefingData.message && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Latest Briefing</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm" data-testid="text-briefing-summary">{briefingData.summary}</p>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {briefingData.state_snapshot?.mrr != null && (
                    <div className="text-center p-2 rounded bg-muted">
                      <div className="text-xs text-muted-foreground">MRR</div>
                      <div className="text-lg font-bold" data-testid="text-briefing-mrr">${(briefingData.state_snapshot.mrr / 1000).toFixed(0)}K</div>
                    </div>
                  )}
                  {briefingData.state_snapshot?.monthly_burn != null && (
                    <div className="text-center p-2 rounded bg-muted">
                      <div className="text-xs text-muted-foreground">Burn</div>
                      <div className="text-lg font-bold" data-testid="text-briefing-burn">${(briefingData.state_snapshot.monthly_burn / 1000).toFixed(0)}K</div>
                    </div>
                  )}
                  {briefingData.state_snapshot?.cash_balance != null && (
                    <div className="text-center p-2 rounded bg-muted">
                      <div className="text-xs text-muted-foreground">Cash</div>
                      <div className="text-lg font-bold" data-testid="text-briefing-cash">${(briefingData.state_snapshot.cash_balance / 1000).toFixed(0)}K</div>
                    </div>
                  )}
                  {briefingData.state_snapshot?.runway_months != null && (
                    <div className="text-center p-2 rounded bg-muted">
                      <div className="text-xs text-muted-foreground">Runway</div>
                      <div className="text-lg font-bold" data-testid="text-briefing-runway">{briefingData.state_snapshot.runway_months}mo</div>
                    </div>
                  )}
                </div>

                {briefingData.suggestions?.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold">Suggestions</h4>
                    {briefingData.suggestions.map((s: any, i: number) => (
                      <div key={i} className="p-3 rounded border border-border" data-testid={`suggestion-row-${i}`}>
                        <div className="font-medium text-sm">{s.title}</div>
                        <p className="text-xs text-muted-foreground mt-1">{s.description}</p>
                        {s.impact && <p className="text-xs text-green-500 mt-1">{s.impact}</p>}
                      </div>
                    ))}
                  </div>
                )}

                <div className="text-xs text-muted-foreground">
                  Generated: {briefingData.generated_at ? new Date(briefingData.generated_at).toLocaleString() : "—"}
                </div>
              </CardContent>
            </Card>
          )}

          {briefingData?.message && (
            <Card>
              <CardContent className="p-6 text-center text-muted-foreground">
                <Zap className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>{briefingData.message}</p>
                <p className="text-sm mt-2">Click "Run Autopilot" to generate your first briefing.</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="intelligence" className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold">Platform Intelligence</h3>
              <p className="text-sm text-muted-foreground">Cross-company learning metrics and pattern aggregation</p>
            </div>
            <Button
              onClick={() => runAggregation.mutate()}
              disabled={runAggregation.isPending}
              data-testid="button-run-aggregation"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${runAggregation.isPending ? "animate-spin" : ""}`} />
              {runAggregation.isPending ? "Aggregating..." : "Run Aggregation"}
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-1">
                  <Users className="w-4 h-4" /> Contributors
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold" data-testid="text-contributing-companies">
                  {platformIntelData?.contributing_companies ?? 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  of {platformIntelData?.total_companies ?? 0} total ({platformIntelData?.participation_rate ?? 0}%)
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-1">
                  <Brain className="w-4 h-4" /> Patterns
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold" data-testid="text-patterns-discovered">
                  {platformIntelData?.patterns_discovered ?? 0}
                </div>
                <p className="text-xs text-muted-foreground">patterns discovered</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-1">
                  <TrendingUp className="w-4 h-4" /> Decisions
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold" data-testid="text-decisions-analyzed">
                  {platformIntelData?.total_decisions_analyzed ?? 0}
                </div>
                <p className="text-xs text-muted-foreground">decisions analyzed</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-1">
                  <Database className="w-4 h-4" /> Data Points
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold" data-testid="text-financial-records">
                  {platformIntelData?.total_financial_records ?? 0}
                </div>
                <p className="text-xs text-muted-foreground">financial records</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Aggregation Status</CardTitle>
            </CardHeader>
            <CardContent>
              {platformIntelLoading ? (
                <p className="text-muted-foreground">Loading platform intelligence data...</p>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 rounded-lg border border-border">
                    <div>
                      <div className="font-medium">Last Computed</div>
                      <div className="text-sm text-muted-foreground">
                        {platformIntelData?.last_computed
                          ? new Date(platformIntelData.last_computed).toLocaleString()
                          : "Never — click 'Run Aggregation' to compute patterns"}
                      </div>
                    </div>
                    <Badge variant={platformIntelData?.last_computed ? "default" : "secondary"} data-testid="badge-aggregation-status">
                      {platformIntelData?.last_computed ? "Active" : "Pending"}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg border border-border">
                    <div>
                      <div className="font-medium">Privacy</div>
                      <div className="text-sm text-muted-foreground">
                        Only statistical aggregates (medians, percentiles, success rates) are stored. Individual company data is never exposed.
                      </div>
                    </div>
                    <Badge variant="outline" className="text-green-500 border-green-500/30" data-testid="badge-privacy-status">
                      <Shield className="w-3 h-3 mr-1" /> Protected
                    </Badge>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="learning" className="space-y-4">
          <div>
            <h3 className="text-lg font-semibold">AI Learning Metrics</h3>
            <p className="text-sm text-muted-foreground">Response quality trends, recommendation effectiveness, and feedback volume</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-1">
                  <ThumbsUp className="w-4 h-4" /> Feedback Volume
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold" data-testid="text-feedback-volume">
                  {feedbackStats?.patterns?.total_feedback ?? 0}
                </div>
                <p className="text-xs text-muted-foreground">total ratings received</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-1">
                  <TrendingUp className="w-4 h-4" /> Positive Rate
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold" data-testid="text-positive-rate">
                  {feedbackStats?.patterns?.overall_quality_score ?? 0}%
                </div>
                <p className="text-xs text-muted-foreground">
                  {feedbackStats?.patterns?.total_helpful ?? 0} helpful of {feedbackStats?.patterns?.total_feedback ?? 0}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-1">
                  <BarChart3 className="w-4 h-4" /> Categories Tracked
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold" data-testid="text-categories-tracked">
                  {feedbackStats?.quality_scores ? Object.keys(feedbackStats.quality_scores).length : 0}
                </div>
                <p className="text-xs text-muted-foreground">advice categories scored</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-1">
                  <Sparkles className="w-4 h-4" /> Outcome Correlations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold" data-testid="text-outcome-correlations">
                  {feedbackStats?.outcome_correlations?.length ?? 0}
                </div>
                <p className="text-xs text-muted-foreground">advice-outcome links</p>
              </CardContent>
            </Card>
          </div>

          {feedbackStats?.patterns?.by_response_type && Object.keys(feedbackStats.patterns.by_response_type).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Effectiveness by Response Type</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(feedbackStats.patterns.by_response_type).map(([type, data]: [string, any]) => (
                    <div key={type} className="flex items-center justify-between p-3 rounded-lg border border-border" data-testid={`row-response-type-${type}`}>
                      <div>
                        <div className="font-medium text-sm">{type.replace(/_/g, ' ')}</div>
                        <div className="text-xs text-muted-foreground">
                          {data.total} ratings · {data.helpful} helpful · {data.not_helpful} not helpful
                        </div>
                      </div>
                      <Badge 
                        variant={data.quality_score >= 70 ? "default" : data.quality_score >= 40 ? "secondary" : "destructive"}
                        data-testid={`badge-quality-${type}`}
                      >
                        {data.quality_score}% quality
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {feedbackStats?.outcome_correlations && feedbackStats.outcome_correlations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Advice-Outcome Correlations</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {feedbackStats.outcome_correlations.map((corr: any, idx: number) => (
                    <div key={idx} className="flex items-center justify-between p-3 rounded-lg border border-border" data-testid={`row-correlation-${idx}`}>
                      <div>
                        <div className="font-medium text-sm">{corr.advice_category?.replace(/_/g, ' ')}</div>
                        <div className="text-xs text-muted-foreground">
                          {corr.total_decisions} decisions tracked · {corr.positive_rate}% positive · {corr.negative_rate}% negative
                        </div>
                      </div>
                      <Badge 
                        variant={corr.effectiveness_score >= 50 ? "default" : "secondary"}
                        data-testid={`badge-effectiveness-${idx}`}
                      >
                        {corr.effectiveness_score} effectiveness
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {feedbackStats?.daily_trend && feedbackStats.daily_trend.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Daily Feedback Trend (Last 30 Days)</CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-48">
                  <div className="space-y-1">
                    {feedbackStats.daily_trend.map((day: any, idx: number) => (
                      <div key={idx} className="flex items-center justify-between text-sm py-1 border-b border-border/30" data-testid={`row-daily-trend-${idx}`}>
                        <span className="text-muted-foreground">{day.date}</span>
                        <div className="flex items-center gap-3">
                          <span>{day.total} ratings</span>
                          <Badge variant="outline" className="text-xs">
                            {day.total > 0 ? Math.round((day.helpful / day.total) * 100) : 0}% positive
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          )}

          {feedbackStatsLoading && (
            <Card>
              <CardContent className="p-6 text-center text-muted-foreground">
                <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-50 animate-pulse" />
                <p>Loading AI learning metrics...</p>
              </CardContent>
            </Card>
          )}

          {!feedbackStatsLoading && (!feedbackStats?.patterns?.total_feedback) && (
            <Card>
              <CardContent className="p-6 text-center text-muted-foreground">
                <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No feedback data collected yet.</p>
                <p className="text-sm mt-2">AI learning metrics will appear here once users start rating Copilot responses.</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

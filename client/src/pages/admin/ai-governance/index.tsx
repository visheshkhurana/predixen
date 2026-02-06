import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useFinancialMetrics } from '@/hooks/useFinancialMetrics';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import {
  Brain, Users, Activity, Code2, AlertTriangle, Database, Shield,
  CheckCircle, XCircle, RefreshCw, Pause, Play, Lock, Unlock, Send,
  TrendingUp, TrendingDown, AlertOctagon, Zap, Eye, GitBranch, FileCode,
  Clock, ChevronRight, Loader2, ThumbsUp, ThumbsDown, Filter, Search,
  BarChart3, Timer, AlertCircle
} from 'lucide-react';

interface AgentStatus {
  status: 'idle' | 'thinking' | 'responded' | 'flagged';
  summary: string | null;
  confidence: number | null;
  lastUpdate: string | null;
}

interface SystemState {
  id: number;
  mode: string;
  aiPaused: boolean;
  codeChangesFrozen: boolean;
  manualOnly: boolean;
  lastChangedBy: string;
}

interface AiRequest {
  id: number;
  requestId: string;
  question: string;
  status: string;
  type: string;
  createdAt: string;
}

interface AiDecision {
  id: number;
  requestId: string;
  label: string;
  confidence: number;
  rationale: any;
  actions: any;
  requiresApproval: boolean;
  agentPositions: Record<string, string>;
  status: string;
  createdAt: string;
}

interface AiCodeChange {
  id: number;
  requestId: string;
  branch: string;
  filesChanged: any;
  testsPassed: boolean;
  riskLevel: string;
  summary: string;
  status: string;
  createdAt: string;
}

interface GovernanceState {
  systemState: SystemState;
  agents: Record<string, AgentStatus>;
  activeRequest: AiRequest | null;
  requests: AiRequest[];
  decisions: AiDecision[];
  codeChanges: AiCodeChange[];
  events: any[];
  approvals: any[];
}

const AGENTS = ['CEO', 'CFO', 'CRO', 'CPO', 'CTO', 'RISK', 'CHIEF_OF_STAFF'] as const;

function getRationaleItems(rationale: any): string[] {
  if (!rationale) return [];
  if (Array.isArray(rationale)) return rationale.filter((r): r is string => typeof r === 'string');
  if (typeof rationale === 'object') {
    const items: string[] = [];
    Object.entries(rationale).forEach(([key, val]) => {
      if (typeof val === 'string') items.push(`${key}: ${val}`);
      else if (val != null) items.push(`${key}: ${String(val)}`);
    });
    return items;
  }
  if (typeof rationale === 'string') return [rationale];
  return [];
}

const AGENT_COLORS: Record<string, string> = {
  CEO: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  CFO: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  CRO: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  CPO: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  CTO: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  RISK: 'bg-red-500/20 text-red-400 border-red-500/30',
  CHIEF_OF_STAFF: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
};

const STATUS_ICONS: Record<string, any> = {
  idle: Clock,
  thinking: Loader2,
  responded: CheckCircle,
  flagged: AlertTriangle,
};

function getStatusColor(status: string) {
  switch (status) {
    case 'idle': return 'text-muted-foreground';
    case 'thinking': return 'text-yellow-400 animate-pulse';
    case 'responded': return 'text-emerald-400';
    case 'flagged': return 'text-red-400';
    default: return 'text-muted-foreground';
  }
}

function getTimeAgo(dateStr: string): string {
  const now = Date.now();
  const created = new Date(dateStr).getTime();
  const diffMs = now - created;
  if (diffMs < 0) return 'just now';
  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function ConfidenceBar({ value }: { value: number | null | undefined }) {
  if (value == null) return null;
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 bg-muted rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-muted-foreground">{pct}%</span>
    </div>
  );
}

// ============ BOARDROOM VIEW ============
function BoardroomView({ data }: { data: GovernanceState }) {
  const queryClient = useQueryClient();
  const [question, setQuestion] = useState('');
  const [expandedAgents, setExpandedAgents] = useState<Record<string, boolean>>({});
  const [confirmApproval, setConfirmApproval] = useState<{id: number; requestId: string; label: string; action: 'approve' | 'reject'} | null>(null);

  const toggleAgent = (agent: string) => {
    setExpandedAgents(prev => ({ ...prev, [agent]: !prev[agent] }));
  };

  const askMutation = useMutation({
    mutationFn: async (q: string) => {
      const res = await fetch('/admin/ai-governance/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      });
      return res.json();
    },
    onSuccess: () => {
      setQuestion('');
      queryClient.invalidateQueries({ queryKey: ['ai-governance-state'] });
    },
  });

  const boardroomApproveMutation = useMutation({
    mutationFn: async ({ requestId, decisionId }: { requestId: string; decisionId: number }) => {
      const res = await fetch('/admin/ai-governance/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requestId, decisionId }),
      });
      return res.json();
    },
    onSuccess: () => {
      setConfirmApproval(null);
      queryClient.invalidateQueries({ queryKey: ['ai-governance-state'] });
    },
  });

  const boardroomRejectMutation = useMutation({
    mutationFn: async ({ requestId, decisionId }: { requestId: string; decisionId: number }) => {
      const res = await fetch('/admin/ai-governance/reject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requestId, decisionId }),
      });
      return res.json();
    },
    onSuccess: () => {
      setConfirmApproval(null);
      queryClient.invalidateQueries({ queryKey: ['ai-governance-state'] });
    },
  });

  const pendingDecisions = data.decisions.filter(d => d.requiresApproval && d.status !== 'approved' && d.status !== 'rejected');

  return (
    <div className="space-y-6">
      {/* Pending Approvals Banner */}
      {pendingDecisions.length > 0 && (
        <div className="flex items-center justify-between gap-3 px-4 py-3 rounded-md bg-amber-500/10 border border-amber-500/30">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-amber-400 shrink-0" />
            <p className="text-sm text-amber-300 font-medium">
              {pendingDecisions.length} decision{pendingDecisions.length > 1 ? 's' : ''} pending your approval
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            className="border-amber-500/40 text-amber-300 shrink-0"
            onClick={() => document.getElementById('boardroom-floor')?.scrollIntoView({ behavior: 'smooth' })}
            data-testid="button-review-now"
          >
            Review Now
          </Button>
        </div>
      )}

      {/* Agent Ring */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
        {AGENTS.map((agent) => {
          const agentData = data.agents[agent] || { status: 'idle', summary: null, confidence: null, lastUpdate: null };
          const StatusIcon = STATUS_ICONS[agentData.status] || Clock;
          const isExpanded = expandedAgents[agent] || false;
          return (
            <Card
              key={agent}
              className={`border ${AGENT_COLORS[agent]} bg-card/50 ${agentData.summary ? 'cursor-pointer hover-elevate' : ''}`}
              onClick={() => agentData.summary && toggleAgent(agent)}
              data-testid={`card-agent-${agent}`}
            >
              <CardContent className="p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold tracking-wide">{agent.replace('_', ' ')}</span>
                  <StatusIcon className={`h-3.5 w-3.5 ${getStatusColor(agentData.status)}`} />
                </div>
                {agentData.summary && (
                  <p className={`text-xs text-muted-foreground mb-1 ${isExpanded ? '' : 'line-clamp-2'}`}>{agentData.summary}</p>
                )}
                <ConfidenceBar value={agentData.confidence} />
                {agentData.lastUpdate && (
                  <p className="text-[10px] text-muted-foreground/40 mt-0.5 flex items-center gap-0.5">
                    <Timer className="h-2.5 w-2.5" />
                    {getTimeAgo(agentData.lastUpdate)}
                  </p>
                )}
                {agentData.summary && (
                  <p className="text-[10px] text-muted-foreground/60 mt-1">{isExpanded ? 'click to collapse' : 'click to expand'}</p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Confirmation Modal Overlay */}
      {confirmApproval && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setConfirmApproval(null)}>
          <Card className="w-full max-w-sm mx-4" onClick={(e) => e.stopPropagation()}>
            <CardContent className="p-6">
              <div className="flex items-center gap-2 mb-4">
                {confirmApproval.action === 'approve' ? (
                  <ThumbsUp className="h-5 w-5 text-emerald-400" />
                ) : (
                  <ThumbsDown className="h-5 w-5 text-red-400" />
                )}
                <h3 className="font-semibold text-base">
                  {confirmApproval.action === 'approve' ? 'Approve' : 'Reject'} Decision?
                </h3>
              </div>
              <p className="text-sm text-muted-foreground mb-6">
                {confirmApproval.action === 'approve'
                  ? `Are you sure you want to approve "${confirmApproval.label}"?`
                  : `Are you sure you want to reject "${confirmApproval.label}"? This cannot be undone.`}
              </p>
              <div className="flex gap-2 justify-end">
                <Button size="sm" variant="outline" onClick={() => setConfirmApproval(null)}>
                  Cancel
                </Button>
                <Button
                  size="sm"
                  variant={confirmApproval.action === 'approve' ? 'default' : 'destructive'}
                  className={confirmApproval.action === 'approve' ? 'bg-emerald-600' : ''}
                  onClick={() => {
                    const mut = confirmApproval.action === 'approve' ? boardroomApproveMutation : boardroomRejectMutation;
                    mut.mutate({ requestId: confirmApproval.requestId, decisionId: confirmApproval.id });
                  }}
                  disabled={boardroomApproveMutation.isPending || boardroomRejectMutation.isPending}
                >
                  {(boardroomApproveMutation.isPending || boardroomRejectMutation.isPending) && (
                    <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />
                  )}
                  Confirm {confirmApproval.action === 'approve' ? 'Approval' : 'Rejection'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Boardroom Floor */}
      <Card id="boardroom-floor">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Brain className="h-4 w-4" />
            Pending Decisions
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!data.activeRequest && data.decisions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Brain className="h-10 w-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">No active discussions. Ask a question to convene the boardroom.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {data.decisions.filter(d => d.status === 'pending').slice(0, 3).map((decision) => (
                <div key={decision.id} className="border rounded-lg p-4 bg-muted/20">
                  <div className="flex items-start justify-between mb-2 gap-2">
                    <div>
                      <h4 className="font-medium text-sm">{decision.label}</h4>
                      <ConfidenceBar value={decision.confidence} />
                    </div>
                    {decision.requiresApproval ? (
                      decision.status === 'approved' ? (
                        <Badge variant="default" className="text-xs shrink-0">Approved</Badge>
                      ) : decision.status === 'rejected' ? (
                        <Badge variant="destructive" className="text-xs shrink-0">Rejected</Badge>
                      ) : (
                        <div className="flex items-center gap-1 shrink-0">
                          <Button
                            size="icon"
                            variant="ghost"
                            className="text-emerald-400"
                            onClick={(e) => { e.stopPropagation(); setConfirmApproval({ id: decision.id, requestId: decision.requestId, label: decision.label, action: 'approve' }); }}
                            data-testid={`button-approve-${decision.id}`}
                          >
                            <ThumbsUp className="h-4 w-4" />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            className="text-red-400"
                            onClick={(e) => { e.stopPropagation(); setConfirmApproval({ id: decision.id, requestId: decision.requestId, label: decision.label, action: 'reject' }); }}
                            data-testid={`button-reject-${decision.id}`}
                          >
                            <ThumbsDown className="h-4 w-4" />
                          </Button>
                        </div>
                      )
                    ) : null}
                  </div>
                  {decision.agentPositions && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {Object.entries(decision.agentPositions as Record<string, string>).map(([agent, position]) => (
                        <Badge key={agent} variant="outline" className="text-xs">
                          {agent}: {typeof position === "string" ? position : (position as any)?.sentiment || "N/A"}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Founder Console */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Send className="h-4 w-4" />
            Founder Console
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask the boardroom a question..."
              className="flex-1 px-3 py-2 text-sm bg-muted/50 border rounded-md focus:outline-none focus:ring-1 focus:ring-ring"
              onKeyDown={(e) => { if (e.key === 'Enter' && question.trim()) askMutation.mutate(question); }}
              disabled={data.systemState.aiPaused || data.systemState.manualOnly}
            />
            <Button
              size="sm"
              onClick={() => question.trim() && askMutation.mutate(question)}
              disabled={!question.trim() || askMutation.isPending || data.systemState.aiPaused}
            >
              {askMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Ask'}
            </Button>
          </div>
          {data.systemState.aiPaused && (
            <p className="text-xs text-red-400 mt-2">AI is currently paused. Resume from Emergency tab.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ============ DECISIONS VIEW ============
function DecisionsView({ data }: { data: GovernanceState }) {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const approveMutation = useMutation({
    mutationFn: async ({ requestId, decisionId }: { requestId: string; decisionId: number }) => {
      const res = await fetch('/admin/ai-governance/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requestId, decisionId }),
      });
      return res.json();
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ai-governance-state'] }),
  });

  const rejectMutation = useMutation({
    mutationFn: async ({ requestId, decisionId }: { requestId: string; decisionId: number }) => {
      const res = await fetch('/admin/ai-governance/reject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requestId, decisionId }),
      });
      return res.json();
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ai-governance-state'] }),
  });

  const filteredDecisions = useMemo(() => {
    return data.decisions.filter(d => {
      if (statusFilter !== 'all' && d.status !== statusFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return d.label.toLowerCase().includes(q) || d.requestId.toLowerCase().includes(q);
      }
      return true;
    });
  }, [data.decisions, statusFilter, searchQuery]);

  if (data.decisions.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <Activity className="h-10 w-10 mx-auto mb-3 opacity-30" />
        <p className="text-sm">No decisions yet. Ask the boardroom a question to generate decisions.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[180px] max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search decisions..."
            className="pl-8 text-sm"
            data-testid="input-search-decisions"
          />
        </div>
        <div className="flex items-center gap-1">
          {(['all', 'pending', 'approved', 'rejected'] as const).map((s) => (
            <Button
              key={s}
              size="sm"
              variant={statusFilter === s ? 'default' : 'outline'}
              onClick={() => setStatusFilter(s)}
              data-testid={`button-filter-${s}`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </Button>
          ))}
        </div>
      </div>

      {filteredDecisions.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <Filter className="h-8 w-8 mx-auto mb-3 opacity-30" />
          <p className="text-sm">No decisions match your filters.</p>
        </div>
      ) : (
        filteredDecisions.map((decision) => (
          <Card key={decision.id}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center flex-wrap gap-2 mb-1">
                    <h4 className="font-medium">{decision.label}</h4>
                    <Badge variant={decision.status === 'approved' ? 'default' : decision.status === 'rejected' ? 'destructive' : 'outline'}>
                      {decision.status}
                    </Badge>
                    {decision.requiresApproval && decision.status === 'pending' && (
                      <Badge variant="destructive" className="text-xs">Needs Approval</Badge>
                    )}
                  </div>
                  <ConfidenceBar value={decision.confidence} />
                </div>
              </div>

              {decision.rationale && getRationaleItems(decision.rationale).length > 0 && (
                <div className="mb-3">
                  <p className="text-xs font-medium text-muted-foreground mb-1">Rationale</p>
                  <ul className="text-xs text-muted-foreground space-y-0.5">
                    {getRationaleItems(decision.rationale).slice(0, 3).map((r, i) => (
                      <li key={i} className="flex items-start gap-1">
                        <ChevronRight className="h-3 w-3 mt-0.5 shrink-0" />{r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {decision.agentPositions && (
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {Object.entries(decision.agentPositions as Record<string, string>).map(([agent, position]) => (
                    <Badge key={agent} variant="outline" className="text-xs">
                      {agent}: {typeof position === "string" ? position : (position as any)?.sentiment || "N/A"}
                    </Badge>
                  ))}
                </div>
              )}

              {decision.status === 'pending' && (
                <div className="flex flex-wrap gap-2 pt-2 border-t">
                  <Button
                    size="sm"
                    onClick={() => approveMutation.mutate({ requestId: decision.requestId, decisionId: decision.id })}
                    disabled={approveMutation.isPending}
                    className="bg-emerald-600"
                  >
                    <CheckCircle className="h-3.5 w-3.5 mr-1" /> Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => rejectMutation.mutate({ requestId: decision.requestId, decisionId: decision.id })}
                    disabled={rejectMutation.isPending}
                  >
                    <XCircle className="h-3.5 w-3.5 mr-1" /> Reject
                  </Button>
                  <Button size="sm" variant="outline">
                    <RefreshCw className="h-3.5 w-3.5 mr-1" /> Rerun
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
}

// ============ CODE CHANGES VIEW ============
function CodeChangesView({ data }: { data: GovernanceState }) {
  const queryClient = useQueryClient();

  const approveMergeMutation = useMutation({
    mutationFn: async ({ requestId }: { requestId: string }) => {
      const res = await fetch('/admin/ai-governance/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requestId, reason: 'Code change approved for merge' }),
      });
      return res.json();
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ai-governance-state'] }),
  });

  if (data.codeChanges.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <Code2 className="h-10 w-10 mx-auto mb-3 opacity-30" />
        <p className="text-sm">No AI-proposed code changes pending.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {data.codeChanges.map((change) => (
        <Card key={change.id}>
          <CardContent className="p-4">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center flex-wrap gap-2 mb-1">
                  <GitBranch className="h-4 w-4 text-muted-foreground" />
                  <span className="font-mono text-sm">{change.branch || 'unknown-branch'}</span>
                  <Badge variant={change.status === 'approved' ? 'default' : change.status === 'rejected' ? 'destructive' : 'outline'}>
                    {change.status}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">{change.summary || 'No summary available'}</p>
              </div>
              <Badge
                variant="outline"
                className={
                  change.riskLevel === 'high' ? 'border-red-500 text-red-400' :
                  change.riskLevel === 'medium' ? 'border-amber-500 text-amber-400' :
                  'border-emerald-500 text-emerald-400'
                }
              >
                {change.riskLevel} risk
              </Badge>
            </div>

            <div className="flex items-center flex-wrap gap-4 text-xs text-muted-foreground mb-3">
              <span className="flex items-center gap-1">
                <FileCode className="h-3.5 w-3.5" />
                {Array.isArray(change.filesChanged) ? change.filesChanged.length : 0} files
              </span>
              <span className="flex items-center gap-1">
                {change.testsPassed ? (
                  <><CheckCircle className="h-3.5 w-3.5 text-emerald-400" /> Tests pass</>
                ) : (
                  <><XCircle className="h-3.5 w-3.5 text-red-400" /> Tests failing</>
                )}
              </span>
            </div>

            {change.status === 'pending' && (
              <div className="flex flex-wrap gap-2 pt-2 border-t">
                <Button
                  size="sm"
                  className="bg-emerald-600"
                  onClick={() => approveMergeMutation.mutate({ requestId: change.requestId })}
                  disabled={approveMergeMutation.isPending || data.systemState.codeChangesFrozen}
                >
                  <CheckCircle className="h-3.5 w-3.5 mr-1" /> Approve Merge
                </Button>
                <Button size="sm" variant="destructive">
                  <XCircle className="h-3.5 w-3.5 mr-1" /> Reject
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ============ COMPANY HEALTH VIEW ============
function extractBurnRate(summary: string | null | undefined): string {
  if (!summary) return '';
  const dollarMatch = summary.match(/\$\s*([\d,]+(?:\.\d+)?)\s*[Kk]/);
  if (dollarMatch) return `$${dollarMatch[1]}K/mo`;
  const fullDollarMatch = summary.match(/\$\s*([\d,]+(?:\.\d+)?)/);
  if (fullDollarMatch) {
    const num = parseFloat(fullDollarMatch[1].replace(/,/g, ''));
    if (num >= 1000) return `$${Math.round(num / 1000)}K/mo`;
    return `$${fullDollarMatch[1]}/mo`;
  }
  const numKMatch = summary.match(/([\d,]+(?:\.\d+)?)\s*[Kk]\s*(?:\/\s*mo|per\s*month|monthly|burn)/i);
  if (numKMatch) return `$${numKMatch[1]}K/mo`;
  const burnMatch = summary.match(/burn\s*(?:rate)?\s*(?:of|is|:)?\s*\$?\s*([\d,]+(?:\.\d+)?)/i);
  if (burnMatch) {
    const num = parseFloat(burnMatch[1].replace(/,/g, ''));
    if (num >= 1000) return `$${Math.round(num / 1000)}K/mo`;
    return `$${burnMatch[1]}/mo`;
  }
  return '';
}

function formatDollarShort(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M/mo`;
  if (value >= 1_000) return `$${Math.round(value / 1_000)}K/mo`;
  return `$${Math.round(value)}/mo`;
}

function CompanyHealthView({ data }: { data: GovernanceState }) {
  const { metrics: financialMetrics } = useFinancialMetrics();
  const cfoEvent = data.events.find((e: any) => e.agent === 'CFO');
  const riskEvent = data.events.find((e: any) => e.agent === 'RISK');
  const cfoSummary = cfoEvent?.summary || data.agents?.CFO?.summary || null;

  const burnFromSummary = useMemo(() => extractBurnRate(cfoSummary), [cfoSummary]);
  const burnTrendValue = burnFromSummary || (financialMetrics.burnRate > 0 ? formatDollarShort(financialMetrics.burnRate) : '');

  const runwayFromSummary = cfoSummary?.match(/(\d+\.?\d*)\s*months/)?.[1];
  const runwayValue = runwayFromSummary
    ? `${runwayFromSummary} mo`
    : (financialMetrics.runway > 0 && financialMetrics.runway < 999 ? `${financialMetrics.runway.toFixed(1)} mo` : '');

  const metrics = [
    {
      label: 'Runway P50',
      value: runwayValue,
      icon: TrendingUp,
      color: 'text-emerald-400',
    },
    {
      label: 'Burn Trend',
      value: burnTrendValue,
      icon: TrendingDown,
      color: 'text-amber-400',
    },
    {
      label: 'Risk Index',
      value: riskEvent?.confidence ? `${Math.round(riskEvent.confidence * 100)}%` : '',
      icon: Shield,
      color: 'text-red-400',
    },
    {
      label: 'Decision Accuracy',
      value: Array.isArray(data.approvals) && data.approvals.length > 0
        ? `${Math.round((data.approvals.filter((a: any) => a.approved).length / data.approvals.length) * 100)}%`
        : '',
      icon: Activity,
      color: 'text-blue-400',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <metric.icon className={`h-4 w-4 ${metric.color}`} />
                <span className="text-xs text-muted-foreground">{metric.label}</span>
              </div>
              <p className="text-2xl font-bold">{metric.value || <span className="text-sm text-muted-foreground">No data</span>}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Recent Agent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {data.events.length === 0 ? (
            <p className="text-sm text-muted-foreground">No agent activity recorded yet.</p>
          ) : (
            <div className="space-y-2">
              {data.events.slice(0, 10).map((event: any, i: number) => (
                <div key={i} className="flex items-center gap-3 text-sm py-1.5 border-b border-border/50 last:border-0">
                  <Badge variant="outline" className="text-xs min-w-[60px] justify-center">{event.agent}</Badge>
                  <span className="text-muted-foreground flex-1">{event.summary || event.eventType}</span>
                  <ConfidenceBar value={event.confidence} />
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ============ AI TASKS VIEW ============
function resolveExecutionStatus(req: AiRequest): { label: string; variant: 'default' | 'destructive' | 'secondary' | 'outline'; className?: string } {
  if (req.status === 'approved') return { label: 'approved', variant: 'default' as const };
  if (req.status === 'rejected') return { label: 'rejected', variant: 'destructive' as const };
  if (req.status === 'decision_ready') return { label: 'decision_ready', variant: 'default' as const, className: 'bg-blue-600 text-white' };
  if (req.status === 'pending') return { label: 'pending', variant: 'default' as const, className: 'bg-amber-500 text-white' };
  if (req.status === 'in_progress' || req.status === 'executing') {
    const elapsed = Date.now() - new Date(req.createdAt).getTime();
    if (elapsed > 60_000) return { label: 'completed', variant: 'default' as const };
    return { label: 'executing', variant: 'secondary' as const };
  }
  return { label: req.status, variant: 'outline' as const };
}

function AiTasksView({ data }: { data: GovernanceState }) {
  return (
    <div className="space-y-4">
      {data.requests.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Zap className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">No AI tasks in the queue.</p>
        </div>
      ) : (
        data.requests.map((req) => {
          const resolved = resolveExecutionStatus(req);
          return (
            <Card key={req.id} data-testid={`card-task-${req.id}`}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="font-medium text-sm">{req.question}</p>
                    <div className="flex items-center flex-wrap gap-2 mt-1">
                      <Badge variant="outline" className="text-xs bg-muted">{req.type}</Badge>
                      <Badge variant={resolved.variant} className={`text-xs ${resolved.className || ''}`}>
                        {resolved.label === 'executing' && <Loader2 className="h-3 w-3 animate-spin mr-1" />}
                        {resolved.label === 'completed' && <CheckCircle className="h-3 w-3 mr-1" />}
                        {resolved.label}
                      </Badge>
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {getTimeAgo(req.createdAt)}
                      </span>
                    </div>
                  </div>
                  <code className="text-xs text-muted-foreground font-mono">{req.requestId.slice(0, 12)}...</code>
                </div>
              </CardContent>
            </Card>
          );
        })
      )}
    </div>
  );
}

// ============ EXECUTIONS VIEW ============
function ExecutionsView({ data }: { data: GovernanceState }) {
  const executions = useMemo(() => {
    const starts = data.events.filter((e: any) => e.eventType === 'execution_started');
    const results = data.events.filter((e: any) => e.eventType === 'execution_result');
    const resultMap = new Map<string, any>();
    results.forEach((r: any) => {
      const rid = r.requestId || r.metadata?.requestId;
      if (rid) resultMap.set(rid, r);
    });

    return starts.map((s: any) => {
      const rid = s.requestId || s.metadata?.requestId || s.id;
      const result = resultMap.get(rid);
      const elapsed = Date.now() - new Date(s.createdAt).getTime();
      let status: 'completed' | 'executing' | 'failed' = 'executing';
      if (result) {
        status = result.metadata?.success === false ? 'failed' : 'completed';
      } else if (elapsed > 60_000) {
        status = 'completed';
      }
      return {
        id: s.id,
        requestId: rid,
        agentId: s.agentId || 'system',
        summary: s.metadata?.summary || s.metadata?.question || s.eventType,
        status,
        createdAt: s.createdAt,
        elapsed,
        resultSummary: result?.metadata?.summary || result?.metadata?.result || null,
      };
    }).sort((a: any, b: any) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  }, [data.events]);

  return (
    <div className="space-y-4">
      {executions.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Play className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">No executions recorded yet.</p>
        </div>
      ) : (
        executions.map((exec) => (
          <Card key={exec.id} data-testid={`card-execution-${exec.id}`}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{exec.summary}</p>
                  <div className="flex items-center flex-wrap gap-2 mt-1">
                    <Badge variant="outline" className="text-xs">{exec.agentId}</Badge>
                    <Badge
                      variant={exec.status === 'completed' ? 'default' : exec.status === 'failed' ? 'destructive' : 'secondary'}
                      className="text-xs"
                    >
                      {exec.status === 'executing' && <Loader2 className="h-3 w-3 animate-spin mr-1" />}
                      {exec.status === 'completed' && <CheckCircle className="h-3 w-3 mr-1" />}
                      {exec.status === 'failed' && <XCircle className="h-3 w-3 mr-1" />}
                      {exec.status}
                    </Badge>
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {getTimeAgo(exec.createdAt)}
                    </span>
                  </div>
                  {exec.resultSummary && (
                    <p className="text-xs text-muted-foreground mt-2 line-clamp-2">{exec.resultSummary}</p>
                  )}
                </div>
                <code className="text-xs text-muted-foreground font-mono shrink-0">
                  {String(exec.requestId).slice(0, 12)}...
                </code>
              </div>
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
}

// ============ MEMORY VIEW ============
function MemoryView({ data }: { data: GovernanceState }) {
  const intelligence = useMemo(() => {
    const decisions = Array.isArray(data.decisions) ? data.decisions : [];
    const decided = decisions.filter(d => d.status === 'approved' || d.status === 'rejected');
    const approvedCount = decisions.filter(d => d.status === 'approved').length;
    const approvalRate = decided.length > 0 ? Math.round((approvedCount / decided.length) * 100) : null;

    const confidences = decisions.filter(d => d.confidence != null).map(d => d.confidence);
    const avgConfidence = confidences.length > 0 ? Math.round((confidences.reduce((a, b) => a + b, 0) / confidences.length) * 100) : null;

    const pendingCount = decisions.filter(d => d.requiresApproval && d.status !== 'approved' && d.status !== 'rejected').length;

    let mostCautious: string | null = null;
    const agentConfMap: Record<string, number[]> = {};
    decisions.forEach(d => {
      if (d.agentPositions) {
        Object.entries(d.agentPositions).forEach(([agent, pos]) => {
          const sentiment = typeof pos === 'string' ? pos : (pos as any)?.sentiment || '';
          if (/caution|concern|risk|oppose|reject|against/i.test(sentiment)) {
            if (!agentConfMap[agent]) agentConfMap[agent] = [];
            agentConfMap[agent].push(1);
          }
        });
      }
    });
    let maxCautions = 0;
    Object.entries(agentConfMap).forEach(([agent, arr]) => {
      if (arr.length > maxCautions) {
        maxCautions = arr.length;
        mostCautious = agent;
      }
    });

    return { approvalRate, avgConfidence, pendingCount, mostCautious };
  }, [data.decisions]);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Database className="h-4 w-4" /> Governance Memory
          </CardTitle>
          <CardDescription>Persistent state of all AI governance records</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="text-center p-3 bg-muted/30 rounded-lg">
              <p className="text-2xl font-bold">{data.requests.length}</p>
              <p className="text-xs text-muted-foreground">Total Requests</p>
            </div>
            <div className="text-center p-3 bg-muted/30 rounded-lg">
              <p className="text-2xl font-bold">{data.decisions.length}</p>
              <p className="text-xs text-muted-foreground">Total Decisions</p>
            </div>
            <div className="text-center p-3 bg-muted/30 rounded-lg">
              <p className="text-2xl font-bold">{data.events.length}</p>
              <p className="text-xs text-muted-foreground">Agent Events</p>
            </div>
            <div className="text-center p-3 bg-muted/30 rounded-lg">
              <p className="text-2xl font-bold">{data.approvals.length}</p>
              <p className="text-xs text-muted-foreground">Approvals</p>
            </div>
            <div className="text-center p-3 bg-muted/30 rounded-lg">
              <p className="text-2xl font-bold">{data.codeChanges.length}</p>
              <p className="text-xs text-muted-foreground">Code Changes</p>
            </div>
            <div className="text-center p-3 bg-muted/30 rounded-lg">
              <p className="text-2xl font-bold">{data.systemState.mode}</p>
              <p className="text-xs text-muted-foreground">System Mode</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Governance Intelligence */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="h-4 w-4" /> Governance Intelligence
          </CardTitle>
          <CardDescription>Derived metrics from decision history</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 bg-emerald-500/5 border border-emerald-500/20 rounded-lg">
              <p className="text-2xl font-bold text-emerald-400">{intelligence.approvalRate !== null ? `${intelligence.approvalRate}%` : '—'}</p>
              <p className="text-xs text-muted-foreground">Approval Rate</p>
            </div>
            <div className="text-center p-3 bg-blue-500/5 border border-blue-500/20 rounded-lg">
              <p className="text-2xl font-bold text-blue-400">{intelligence.avgConfidence !== null ? `${intelligence.avgConfidence}%` : '—'}</p>
              <p className="text-xs text-muted-foreground">Avg Confidence</p>
            </div>
            <div className="text-center p-3 bg-amber-500/5 border border-amber-500/20 rounded-lg">
              <p className="text-2xl font-bold text-amber-400">{intelligence.pendingCount}</p>
              <p className="text-xs text-muted-foreground">Pending Decisions</p>
            </div>
            <div className="text-center p-3 bg-red-500/5 border border-red-500/20 rounded-lg">
              <p className="text-2xl font-bold text-red-400">{intelligence.mostCautious || 'None'}</p>
              <p className="text-xs text-muted-foreground">Most Cautious Agent</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ============ EMERGENCY VIEW ============
function EmergencyView({ data }: { data: GovernanceState }) {
  const queryClient = useQueryClient();
  const [confirmAction, setConfirmAction] = useState<string | null>(null);

  const emergencyMutation = useMutation({
    mutationFn: async (action: string) => {
      const res = await fetch('/admin/ai-governance/emergency', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      return res.json();
    },
    onSuccess: () => {
      setConfirmAction(null);
      queryClient.invalidateQueries({ queryKey: ['ai-governance-state'] });
    },
  });

  const controls = [
    {
      action: 'pause_all',
      label: 'Pause All AI',
      description: 'Immediately halt all AI agent processing and decision-making.',
      icon: Pause,
      variant: 'destructive' as const,
      active: data.systemState.aiPaused,
      activeLabel: 'AI Paused',
    },
    {
      action: 'freeze_code',
      label: 'Freeze Code Changes',
      description: 'Prevent any AI-proposed code changes from being merged.',
      icon: Lock,
      variant: 'destructive' as const,
      active: data.systemState.codeChangesFrozen,
      activeLabel: 'Code Frozen',
    },
    {
      action: 'manual_only',
      label: 'Manual-Only Mode',
      description: 'Require manual founder approval for every action.',
      icon: Eye,
      variant: 'destructive' as const,
      active: data.systemState.manualOnly,
      activeLabel: 'Manual Only Active',
    },
    {
      action: 'resume_all',
      label: 'Resume All Systems',
      description: 'Restore normal AI operations. Unfreeze code, unpause agents.',
      icon: Play,
      variant: 'default' as const,
      active: false,
      activeLabel: '',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Status Banner */}
      <Card className={data.systemState.aiPaused ? 'border-red-500/50 bg-red-500/5' : 'border-emerald-500/30 bg-emerald-500/5'}>
        <CardContent className="p-4 flex items-center gap-3">
          {data.systemState.aiPaused ? (
            <AlertOctagon className="h-6 w-6 text-red-400" />
          ) : (
            <CheckCircle className="h-6 w-6 text-emerald-400" />
          )}
          <div>
            <p className="font-medium">
              System Mode: <span className="uppercase">{data.systemState.mode}</span>
            </p>
            <p className="text-sm text-muted-foreground">
              {data.systemState.aiPaused ? 'All AI operations are halted.' : 'AI systems operating normally.'}
              {data.systemState.codeChangesFrozen ? ' Code changes frozen.' : ''}
              {data.systemState.manualOnly ? ' Manual-only mode active.' : ''}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Emergency Controls */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {controls.map((control) => (
          <Card key={control.action} className={control.active ? 'border-red-500/30' : ''}>
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <control.icon className={`h-5 w-5 mt-0.5 ${control.active ? 'text-red-400' : 'text-muted-foreground'}`} />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <h4 className="font-medium text-sm">{control.label}</h4>
                    {control.active && (
                      <Badge variant="destructive" className="text-xs">{control.activeLabel}</Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mb-3">{control.description}</p>
                  {confirmAction === control.action ? (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-amber-400 font-medium">Are you sure?</span>
                      <Button
                        size="sm"
                        variant={control.variant}
                        onClick={() => emergencyMutation.mutate(control.action)}
                        disabled={emergencyMutation.isPending}
                      >
                        {emergencyMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : null}
                        Confirm
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setConfirmAction(null)}
                      >
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <Button
                      size="sm"
                      variant={control.variant}
                      onClick={() => setConfirmAction(control.action)}
                      disabled={control.active}
                    >
                      {control.active ? control.activeLabel : control.label}
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ============ MAIN PAGE ============
export default function AiGovernancePage() {
  const [activeTab, setActiveTab] = useState('boardroom');

  const { data: rawData, isLoading, error } = useQuery<GovernanceState>({
    queryKey: ['ai-governance-state'],
    queryFn: async () => {
      const res = await fetch('/admin/ai-governance/state');
      if (!res.ok) throw new Error('Failed to fetch state');
      return res.json();
    },
    refetchInterval: 30000,
    refetchIntervalInBackground: false,
  });

  const data = useMemo(() => {
    if (!rawData) return rawData;
    return {
      ...rawData,
      events: Array.isArray(rawData.events) ? rawData.events : [],
      requests: Array.isArray(rawData.requests) ? rawData.requests : [],
      decisions: Array.isArray(rawData.decisions) ? rawData.decisions : [],
      codeChanges: Array.isArray(rawData.codeChanges) ? rawData.codeChanges : [],
      approvals: Array.isArray(rawData.approvals) ? rawData.approvals : [],
      agents: rawData.agents || {},
    };
  }, [rawData]);

  if (isLoading) {
    return (
      <>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </>
    );
  }

  if (error || !data) {
    return (
      <>
        <div className="text-center py-12">
          <AlertTriangle className="h-8 w-8 mx-auto mb-3 text-red-400" />
          <p className="text-sm text-muted-foreground">Failed to load AI Governance state. DB tables may need initialization.</p>
          <p className="text-xs text-muted-foreground mt-1">Run the migration script or check server logs.</p>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Brain className="h-5 w-5" />
              AI Governance
            </h2>
            <p className="text-sm text-muted-foreground">Virtual Boardroom & Founder Control Panel</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={data.systemState.aiPaused ? 'destructive' : 'default'} className="text-xs">
              {data.systemState.mode.toUpperCase()}
            </Badge>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="w-full justify-start overflow-x-auto">
            <TabsTrigger value="boardroom" className="gap-1.5"><Brain className="h-3.5 w-3.5" />Boardroom</TabsTrigger>
            <TabsTrigger value="decisions" className="gap-1.5"><Activity className="h-3.5 w-3.5" />Decisions</TabsTrigger>
            <TabsTrigger value="health" className="gap-1.5"><TrendingUp className="h-3.5 w-3.5" />Health</TabsTrigger>
            <TabsTrigger value="tasks" className="gap-1.5"><Zap className="h-3.5 w-3.5" />Tasks</TabsTrigger>
            <TabsTrigger value="executions" className="gap-1.5"><Play className="h-3.5 w-3.5" />Executions</TabsTrigger>
            <TabsTrigger value="code" className="gap-1.5"><Code2 className="h-3.5 w-3.5" />Code</TabsTrigger>
            <TabsTrigger value="memory" className="gap-1.5"><Database className="h-3.5 w-3.5" />Memory</TabsTrigger>
            <TabsTrigger value="emergency" className="gap-1.5"><AlertTriangle className="h-3.5 w-3.5" />Emergency</TabsTrigger>
          </TabsList>
          <TabsContent value="boardroom"><BoardroomView data={data} /></TabsContent>
          <TabsContent value="decisions"><DecisionsView data={data} /></TabsContent>
          <TabsContent value="health"><CompanyHealthView data={data} /></TabsContent>
          <TabsContent value="tasks"><AiTasksView data={data} /></TabsContent>
          <TabsContent value="executions"><ExecutionsView data={data} /></TabsContent>
          <TabsContent value="code"><CodeChangesView data={data} /></TabsContent>
          <TabsContent value="memory"><MemoryView data={data} /></TabsContent>
          <TabsContent value="emergency"><EmergencyView data={data} /></TabsContent>
        </Tabs>
      </div>
    </>
  );
}

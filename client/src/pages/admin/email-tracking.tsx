import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Mail, Send, Eye, MousePointerClick, AlertTriangle, Bot,
  RefreshCw, TrendingUp, ExternalLink, User, Clock
} from 'lucide-react';
import { apiRequest } from '@/lib/queryClient';

interface EmailRecipient {
  email_id: string;
  to: string;
  recipient_id: string | null;
  campaign: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  opened_at: string | null;
  clicked_at: string | null;
  bounced_at: string | null;
  is_bot_open: boolean;
  classification: string | null;
  open_count: number;
  click_count: number;
  clicked_urls: Array<{ url: string; at: string }> | null;
}

interface TrackedLink {
  label: string;
  url: string;
  clicks: number;
  unique_clickers: number;
}

interface AnalyticsData {
  period_days: number;
  campaign_filter: string | null;
  summary: {
    total_sent: number;
    delivered: number;
    opened_human: number;
    opened_bot: number;
    clicked: number;
    bounced: number;
    complained: number;
    open_rate_pct: number;
    click_rate_pct: number;
    bounce_rate_pct: number;
  };
  per_recipient: EmailRecipient[];
  top_links: TrackedLink[];
  feedback: {
    total: number;
    avg_rating: number | null;
    helpful: number;
    somewhat: number;
    not_helpful: number;
  };
}

function formatDate(iso: string | null): string {
  if (!iso) return '--';
  const d = new Date(iso + 'Z');
  return d.toLocaleString('en-IN', {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true
  });
}

function StatCard({ icon: Icon, label, value, color = 'text-foreground' }: {
  icon: React.ElementType; label: string; value: string | number; color?: string;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-md bg-muted">
            <Icon className="h-4 w-4 text-muted-foreground" />
          </div>
          <div>
            <p className={`text-2xl font-bold ${color}`}>{value}</p>
            <p className="text-xs text-muted-foreground uppercase tracking-wide">{label}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AdminEmailTracking() {
  const [campaign, setCampaign] = useState<string>('all');
  const [days, setDays] = useState<number>(90);

  const { data, isLoading, refetch, isFetching } = useQuery<AnalyticsData>({
    queryKey: ['/email-tracking/analytics', campaign, days],
    queryFn: async () => {
      const params = new URLSearchParams({ days: String(days) });
      if (campaign && campaign !== 'all') params.set('campaign', campaign);
      const res = await apiRequest('GET', `/email-tracking/analytics?${params}`);
      return res.json();
    },
    refetchInterval: 30000,
  });

  const allCampaignsQuery = useQuery<AnalyticsData>({
    queryKey: ['/email-tracking/analytics', 'all-campaigns', 365],
    queryFn: async () => {
      const res = await apiRequest('GET', '/email-tracking/analytics?days=365');
      return res.json();
    },
  });

  const campaigns = Array.from(
    new Set(allCampaignsQuery.data?.per_recipient?.map(r => r.campaign).filter(Boolean) || [])
  ).sort().reverse();

  const s = data?.summary;

  return (
    <div className="space-y-6" data-testid="admin-email-tracking">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold" data-testid="text-page-title">Email Tracking</h2>
          <p className="text-sm text-muted-foreground">Monitor email delivery, opens, clicks, and bounces</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Select value={campaign} onValueChange={setCampaign}>
            <SelectTrigger className="w-[240px]" data-testid="select-campaign">
              <SelectValue placeholder="All Campaigns" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Campaigns</SelectItem>
              {campaigns.map(c => (
                <SelectItem key={c!} value={c!}>{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={String(days)} onValueChange={(v) => setDays(Number(v))}>
            <SelectTrigger className="w-[120px]" data-testid="select-days">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">7 days</SelectItem>
              <SelectItem value="30">30 days</SelectItem>
              <SelectItem value="90">90 days</SelectItem>
              <SelectItem value="365">1 year</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="icon"
            onClick={() => refetch()}
            disabled={isFetching}
            data-testid="button-refresh"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={i}><CardContent className="p-4"><Skeleton className="h-12 w-full" /></CardContent></Card>
          ))}
        </div>
      ) : s ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard icon={Send} label="Sent" value={s.total_sent} color="text-blue-500" />
          <StatCard icon={Mail} label="Delivered" value={s.delivered} color="text-green-500" />
          <StatCard icon={Eye} label="Human Opens" value={s.opened_human} color="text-purple-500" />
          <StatCard icon={Bot} label="Bot Opens" value={s.opened_bot} color="text-yellow-500" />
          <StatCard icon={MousePointerClick} label="Clicked" value={s.clicked} color="text-green-500" />
          <StatCard icon={AlertTriangle} label="Bounced" value={s.bounced} color="text-red-500" />
          <StatCard icon={TrendingUp} label="Open Rate" value={`${s.open_rate_pct.toFixed(1)}%`} />
          <StatCard icon={TrendingUp} label="Click Rate" value={`${s.click_rate_pct.toFixed(1)}%`} />
        </div>
      ) : null}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
          <CardTitle className="text-base">Per Recipient</CardTitle>
          <Badge variant="secondary">{data?.per_recipient?.length || 0} recipients</Badge>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-4 space-y-3">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-3 text-xs text-muted-foreground uppercase tracking-wide font-medium">Recipient</th>
                    <th className="text-left p-3 text-xs text-muted-foreground uppercase tracking-wide font-medium">ID</th>
                    <th className="text-left p-3 text-xs text-muted-foreground uppercase tracking-wide font-medium">Sent</th>
                    <th className="text-left p-3 text-xs text-muted-foreground uppercase tracking-wide font-medium">Delivered</th>
                    <th className="text-left p-3 text-xs text-muted-foreground uppercase tracking-wide font-medium">Opened</th>
                    <th className="text-left p-3 text-xs text-muted-foreground uppercase tracking-wide font-medium">Clicked</th>
                    <th className="text-left p-3 text-xs text-muted-foreground uppercase tracking-wide font-medium">Bounced</th>
                    <th className="text-left p-3 text-xs text-muted-foreground uppercase tracking-wide font-medium">Opens</th>
                    <th className="text-left p-3 text-xs text-muted-foreground uppercase tracking-wide font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.per_recipient?.length === 0 && (
                    <tr>
                      <td colSpan={9} className="p-6 text-center text-muted-foreground">No email data yet</td>
                    </tr>
                  )}
                  {data?.per_recipient?.map((r, i) => (
                    <tr key={r.email_id || i} className="border-b last:border-0" data-testid={`row-recipient-${i}`}>
                      <td className="p-3 font-medium">{r.to}</td>
                      <td className="p-3 text-muted-foreground text-xs">{r.recipient_id || '--'}</td>
                      <td className="p-3 text-xs">
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3 text-muted-foreground" />
                          {formatDate(r.sent_at)}
                        </div>
                      </td>
                      <td className="p-3 text-xs">{formatDate(r.delivered_at)}</td>
                      <td className="p-3 text-xs">{formatDate(r.opened_at)}</td>
                      <td className="p-3 text-xs">{formatDate(r.clicked_at)}</td>
                      <td className="p-3 text-xs">{formatDate(r.bounced_at)}</td>
                      <td className="p-3 text-center">{r.open_count || 0}</td>
                      <td className="p-3">
                        {r.bounced_at ? (
                          <Badge variant="destructive" className="text-xs">bounced</Badge>
                        ) : r.classification === 'human' ? (
                          <Badge className="bg-green-500/20 text-green-600 dark:text-green-400 text-xs no-default-hover-elevate">human</Badge>
                        ) : r.classification === 'machine' ? (
                          <Badge className="bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 text-xs no-default-hover-elevate">bot</Badge>
                        ) : (
                          <Badge variant="secondary" className="text-xs">pending</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Top Links</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="p-4 space-y-2">
                {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-3 text-xs text-muted-foreground uppercase tracking-wide font-medium">Label</th>
                      <th className="text-left p-3 text-xs text-muted-foreground uppercase tracking-wide font-medium">Clicks</th>
                      <th className="text-left p-3 text-xs text-muted-foreground uppercase tracking-wide font-medium">Recipients</th>
                      <th className="text-left p-3 text-xs text-muted-foreground uppercase tracking-wide font-medium">URL</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.top_links?.length === 0 && (
                      <tr><td colSpan={4} className="p-4 text-center text-muted-foreground">No links tracked yet</td></tr>
                    )}
                    {data?.top_links?.map((link, i) => (
                      <tr key={i} className="border-b last:border-0" data-testid={`row-link-${i}`}>
                        <td className="p-3">
                          <Badge variant="outline" className="text-xs">{link.label}</Badge>
                        </td>
                        <td className="p-3 font-medium">{link.clicks}</td>
                        <td className="p-3 text-muted-foreground">{link.unique_clickers}</td>
                        <td className="p-3 text-xs text-muted-foreground max-w-[200px] truncate">
                          <a href={link.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 hover:text-foreground">
                            <ExternalLink className="h-3 w-3 flex-shrink-0" />
                            <span className="truncate">{link.url}</span>
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Feedback</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-16 w-full" />
            ) : data?.feedback ? (
              <div className="space-y-3">
                <div className="flex items-center gap-4 flex-wrap">
                  <div>
                    <p className="text-2xl font-bold">{data.feedback.total}</p>
                    <p className="text-xs text-muted-foreground">Total Responses</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{data.feedback.avg_rating ?? 'N/A'}</p>
                    <p className="text-xs text-muted-foreground">Avg Rating</p>
                  </div>
                </div>
                {data.feedback.total > 0 && (
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge className="bg-green-500/20 text-green-600 dark:text-green-400 text-xs no-default-hover-elevate">
                      <User className="h-3 w-3 mr-1" /> Helpful: {data.feedback.helpful}
                    </Badge>
                    <Badge className="bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 text-xs no-default-hover-elevate">
                      Somewhat: {data.feedback.somewhat}
                    </Badge>
                    <Badge className="bg-red-500/20 text-red-600 dark:text-red-400 text-xs no-default-hover-elevate">
                      Not helpful: {data.feedback.not_helpful}
                    </Badge>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">No feedback data</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

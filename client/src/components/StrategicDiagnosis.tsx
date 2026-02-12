import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  Brain, ChevronDown, ChevronUp, Activity, 
  AlertTriangle, Eye, Crosshair
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface Priority {
  priority: string;
  why_now: string;
  expected_impact: string;
}

interface StrategicDiagnosisData {
  diagnosis_narrative: string;
  company_stage_label: string;
  health_score: number;
  health_label: string;
  top_3_priorities: Priority[];
  blind_spots: string[];
  company_name?: string;
  generated_at?: string;
  model_used?: string;
}

interface StrategicDiagnosisProps {
  data: StrategicDiagnosisData | null;
  isLoading: boolean;
  onRefresh?: () => void;
}

function HealthGauge({ score, label }: { score: number; label: string }) {
  const getColor = () => {
    if (score >= 80) return 'text-emerald-500';
    if (score >= 60) return 'text-primary';
    if (score >= 40) return 'text-amber-500';
    return 'text-red-500';
  };

  const getBgColor = () => {
    if (score >= 80) return 'bg-emerald-500';
    if (score >= 60) return 'bg-primary';
    if (score >= 40) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <div className="flex items-center gap-3">
      <div className="relative w-16 h-16">
        <svg className="w-16 h-16 -rotate-90" viewBox="0 0 36 36">
          <path
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke="currentColor"
            className="text-secondary"
            strokeWidth="3"
          />
          <path
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke="currentColor"
            className={getColor()}
            strokeWidth="3"
            strokeDasharray={`${score}, 100`}
            strokeLinecap="round"
          />
        </svg>
        <span className={cn("absolute inset-0 flex items-center justify-center text-lg font-bold", getColor())}>
          {score}
        </span>
      </div>
      <div>
        <Badge className={cn("text-xs font-semibold text-white", getBgColor())}>
          {label}
        </Badge>
        <p className="text-xs text-muted-foreground mt-1">Health Score</p>
      </div>
    </div>
  );
}

export function StrategicDiagnosis({ data, isLoading, onRefresh }: StrategicDiagnosisProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (isLoading) {
    return (
      <Card data-testid="card-strategic-diagnosis-loading">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            <Skeleton className="h-6 w-48" />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-4/6" />
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  return (
    <Card 
      className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent"
      data-testid="card-strategic-diagnosis"
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center">
              <Brain className="h-5 w-5 text-white" />
            </div>
            <div>
              <CardTitle className="text-lg">Strategic Diagnosis</CardTitle>
              <p className="text-xs text-muted-foreground mt-0.5">
                AI-powered analysis for {data.company_name || 'your company'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <HealthGauge score={data.health_score} label={data.health_label} />
            <Badge variant="outline" className="text-xs">
              {data.company_stage_label}
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              data-testid="button-toggle-diagnosis"
            >
              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-6 pt-0">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            {data.diagnosis_narrative.split('\n\n').map((paragraph, i) => (
              <p key={i} className="text-sm leading-relaxed text-muted-foreground">
                {i === 0 ? (
                  <span className="text-foreground font-medium">{paragraph}</span>
                ) : paragraph}
              </p>
            ))}
          </div>

          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Crosshair className="h-4 w-4 text-primary" />
              <span>Top Priorities</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {data.top_3_priorities.map((priority, idx) => (
                <div 
                  key={idx} 
                  className="p-3 rounded-lg bg-secondary/50 space-y-1.5"
                  data-testid={`priority-${idx}`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-primary">#{idx + 1}</span>
                    <span className="text-sm font-medium">{priority.priority}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{priority.why_now}</p>
                  <p className="text-xs text-emerald-500 font-medium">{priority.expected_impact}</p>
                </div>
              ))}
            </div>
          </div>

          {data.blind_spots && data.blind_spots.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Eye className="h-4 w-4 text-amber-500" />
                <span>Blind Spots</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {data.blind_spots.map((spot, idx) => (
                  <Badge 
                    key={idx} 
                    variant="outline" 
                    className="text-xs bg-amber-500/10 border-amber-500/20 text-amber-400"
                    data-testid={`blind-spot-${idx}`}
                  >
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    {spot}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {data.generated_at && (
            <p className="text-xs text-muted-foreground/60 flex items-center gap-1">
              <Activity className="h-3 w-3" />
              Generated {new Date(data.generated_at).toLocaleString()}
              {data.model_used && data.model_used !== 'fallback' && ` via ${data.model_used}`}
            </p>
          )}
        </CardContent>
      )}
    </Card>
  );
}

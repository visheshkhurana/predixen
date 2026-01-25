import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { MessageSquareText, Lightbulb, TrendingUp, Users } from 'lucide-react';

interface ExplanationData {
  summary?: string;
  drivers?: string;
  recommendation?: string;
  cohorts?: string;
}

interface SimulationExplanationProps {
  data?: ExplanationData;
  isLoading?: boolean;
}

function renderMarkdown(text: string): JSX.Element[] {
  const lines = text.split('\n');
  return lines.map((line, idx) => {
    if (line.startsWith('**') && line.endsWith('**')) {
      return <h4 key={idx} className="font-semibold text-foreground mb-2">{line.replace(/\*\*/g, '')}</h4>;
    }
    if (line.includes('**')) {
      const parts = line.split(/\*\*/).map((part, i) => 
        i % 2 === 1 ? <strong key={i}>{part}</strong> : part
      );
      return <p key={idx} className="text-sm text-muted-foreground mb-1">{parts}</p>;
    }
    if (line.startsWith('- ')) {
      return <li key={idx} className="text-sm text-muted-foreground ml-4">{line.slice(2)}</li>;
    }
    if (line.match(/^\d+\./)) {
      return <li key={idx} className="text-sm text-muted-foreground ml-4">{line}</li>;
    }
    if (line.trim() === '') {
      return <div key={idx} className="h-2" />;
    }
    return <p key={idx} className="text-sm text-muted-foreground">{line}</p>;
  });
}

export function SimulationExplanation({ data, isLoading }: SimulationExplanationProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <MessageSquareText className="h-5 w-5" />
            Analysis Summary
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-12 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <MessageSquareText className="h-5 w-5" />
            Analysis Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Run a simulation to see AI-generated insights about your financial projections.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <MessageSquareText className="h-5 w-5" />
            Analysis Summary
          </CardTitle>
          <Badge variant="secondary">AI Generated</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {data.summary && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <TrendingUp className="h-4 w-4 text-primary" />
              Runway Assessment
            </div>
            <div className="pl-6 border-l-2 border-primary/20">
              {renderMarkdown(data.summary)}
            </div>
          </div>
        )}

        {data.drivers && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Lightbulb className="h-4 w-4 text-yellow-500" />
              Key Drivers
            </div>
            <div className="pl-6 border-l-2 border-yellow-500/20">
              {renderMarkdown(data.drivers)}
            </div>
          </div>
        )}

        {data.recommendation && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Lightbulb className="h-4 w-4 text-green-500" />
              Recommendation
            </div>
            <div className="pl-6 border-l-2 border-green-500/20">
              {renderMarkdown(data.recommendation)}
            </div>
          </div>
        )}

        {data.cohorts && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Users className="h-4 w-4 text-blue-500" />
              Customer Insights
            </div>
            <div className="pl-6 border-l-2 border-blue-500/20">
              {renderMarkdown(data.cohorts)}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

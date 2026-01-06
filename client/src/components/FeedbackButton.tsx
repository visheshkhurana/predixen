import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { ThumbsUp, ThumbsDown, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FeedbackButtonProps {
  onFeedback?: (feedback: 'positive' | 'negative') => void;
  testId?: string;
}

export function FeedbackButton({ onFeedback, testId }: FeedbackButtonProps) {
  const [feedback, setFeedback] = useState<'positive' | 'negative' | null>(null);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleFeedback = (type: 'positive' | 'negative') => {
    setFeedback(type);
    setIsSubmitted(true);
    onFeedback?.(type);
    
    setTimeout(() => {
      setIsSubmitted(false);
    }, 2000);
  };

  if (isSubmitted) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground" data-testid={`${testId}-submitted`}>
        <Check className="h-3 w-3 text-emerald-500" />
        <span>Thanks for the feedback!</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1" data-testid={testId}>
      <Button
        variant="ghost"
        size="sm"
        className={cn(
          'h-7 px-2',
          feedback === 'positive' && 'bg-emerald-500/20 text-emerald-500'
        )}
        onClick={() => handleFeedback('positive')}
        data-testid={`${testId}-up`}
      >
        <ThumbsUp className="h-3.5 w-3.5" />
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className={cn(
          'h-7 px-2',
          feedback === 'negative' && 'bg-red-500/20 text-red-500'
        )}
        onClick={() => handleFeedback('negative')}
        data-testid={`${testId}-down`}
      >
        <ThumbsDown className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

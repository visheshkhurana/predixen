import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { ThumbsUp, ThumbsDown, Check } from 'lucide-react';

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
        variant={feedback === 'positive' ? 'default' : 'ghost'}
        size="icon"
        onClick={() => handleFeedback('positive')}
        data-testid={`${testId}-up`}
        aria-label="Helpful"
      >
        <ThumbsUp className="h-4 w-4" />
      </Button>
      <Button
        variant={feedback === 'negative' ? 'default' : 'ghost'}
        size="icon"
        onClick={() => handleFeedback('negative')}
        data-testid={`${testId}-down`}
        aria-label="Not helpful"
      >
        <ThumbsDown className="h-4 w-4" />
      </Button>
    </div>
  );
}

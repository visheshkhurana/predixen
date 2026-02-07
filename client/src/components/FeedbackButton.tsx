import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { ThumbsUp, ThumbsDown, Check, Send, X } from 'lucide-react';
import { Input } from '@/components/ui/input';

interface FeedbackButtonProps {
  onFeedback?: (feedback: 'positive' | 'negative', comment?: string) => void;
  testId?: string;
}

export function FeedbackButton({ onFeedback, testId }: FeedbackButtonProps) {
  const [feedback, setFeedback] = useState<'positive' | 'negative' | null>(null);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [showCommentInput, setShowCommentInput] = useState(false);
  const [comment, setComment] = useState('');
  const commentInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (showCommentInput && commentInputRef.current) {
      commentInputRef.current.focus();
    }
  }, [showCommentInput]);

  const handlePositive = () => {
    setFeedback('positive');
    setIsSubmitted(true);
    onFeedback?.('positive');
    setTimeout(() => setIsSubmitted(false), 2000);
  };

  const handleNegativeClick = () => {
    setFeedback('negative');
    setShowCommentInput(true);
  };

  const cancelFeedback = () => {
    setShowCommentInput(false);
    setFeedback(null);
    setComment('');
  };

  const submitNegativeFeedback = () => {
    setIsSubmitted(true);
    setShowCommentInput(false);
    onFeedback?.('negative', comment.trim() || undefined);
    setComment('');
    setTimeout(() => setIsSubmitted(false), 2000);
  };

  const handleCommentKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      submitNegativeFeedback();
    } else if (e.key === 'Escape') {
      cancelFeedback();
    }
  };

  if (isSubmitted) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground" data-testid={`${testId}-submitted`}>
        <Check className="h-3 w-3 text-emerald-500" />
        <span>Thanks for the feedback!</span>
      </div>
    );
  }

  if (showCommentInput) {
    return (
      <div className="flex items-center gap-1" data-testid={`${testId}-comment`}>
        <Input
          ref={commentInputRef}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          onKeyDown={handleCommentKeyDown}
          placeholder="What went wrong? (optional)"
          className="text-xs max-w-40"
          data-testid={`${testId}-comment-input`}
          aria-label="Feedback comment"
        />
        <Button
          variant="ghost"
          size="icon"
          onClick={submitNegativeFeedback}
          data-testid={`${testId}-comment-submit`}
          aria-label="Submit feedback"
        >
          <Send className="h-3 w-3" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={cancelFeedback}
          data-testid={`${testId}-comment-cancel`}
          aria-label="Cancel feedback"
        >
          <X className="h-3 w-3" />
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1" data-testid={testId}>
      <Button
        variant={feedback === 'positive' ? 'default' : 'ghost'}
        size="icon"
        onClick={handlePositive}
        data-testid={`${testId}-up`}
        aria-label="Helpful"
      >
        <ThumbsUp className="h-4 w-4" />
      </Button>
      <Button
        variant={feedback === 'negative' ? 'default' : 'ghost'}
        size="icon"
        onClick={handleNegativeClick}
        data-testid={`${testId}-down`}
        aria-label="Not helpful"
      >
        <ThumbsDown className="h-4 w-4" />
      </Button>
    </div>
  );
}

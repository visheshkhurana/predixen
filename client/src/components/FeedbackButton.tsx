import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { ThumbsUp, ThumbsDown, Check, Send, X, Sparkles } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { apiRequest } from '@/lib/queryClient';

interface FeedbackButtonProps {
  onFeedback?: (feedback: 'positive' | 'negative', comment?: string) => void;
  testId?: string;
  companyId?: number;
  conversationId?: string;
  messageIndex?: number;
  messageId?: string;
  responseType?: string;
  tags?: string[];
  showEffectivenessHint?: boolean;
}

export function FeedbackButton({ 
  onFeedback, 
  testId, 
  companyId, 
  conversationId, 
  messageIndex,
  messageId,
  responseType,
  tags,
  showEffectivenessHint 
}: FeedbackButtonProps) {
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

  const submitToApi = async (rating: 'helpful' | 'not_helpful', feedbackText?: string) => {
    if (!companyId) return;
    try {
      await apiRequest('POST', '/api/ai/feedback', {
        company_id: companyId,
        conversation_id: conversationId,
        message_index: messageIndex,
        message_id: messageId,
        rating,
        feedback_text: feedbackText,
        response_type: responseType,
        tags: tags || [],
      });
    } catch {
    }
  };

  const handlePositive = () => {
    setFeedback('positive');
    setIsSubmitted(true);
    onFeedback?.('positive');
    submitToApi('helpful');
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
    const feedbackText = comment.trim() || undefined;
    onFeedback?.('negative', feedbackText);
    submitToApi('not_helpful', feedbackText);
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
      {showEffectivenessHint && (
        <span className="text-[10px] text-emerald-500/80 flex items-center gap-1 ml-1" data-testid={`${testId}-effectiveness-hint`}>
          <Sparkles className="h-3 w-3" />
          Worked well for similar companies
        </span>
      )}
    </div>
  );
}

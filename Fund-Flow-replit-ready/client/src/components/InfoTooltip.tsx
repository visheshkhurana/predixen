import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Info } from 'lucide-react';
import { cn } from '@/lib/utils';

interface InfoTooltipProps {
  title?: string;
  content: string;
  className?: string;
  iconClassName?: string;
}

export function InfoTooltip({ title, content, className, iconClassName }: InfoTooltipProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className={cn(
            'inline-flex items-center justify-center rounded-full p-0.5 hover-elevate',
            className
          )}
          data-testid="button-info-tooltip"
        >
          <Info className={cn('h-3.5 w-3.5 text-muted-foreground', iconClassName)} />
        </button>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs" side="top">
        {title && <p className="font-medium mb-1">{title}</p>}
        <p className="text-sm text-muted-foreground">{content}</p>
      </TooltipContent>
    </Tooltip>
  );
}

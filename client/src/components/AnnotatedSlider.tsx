import { useState } from 'react';
import { Slider } from '@/components/ui/slider';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Info } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SliderMarker {
  value: number;
  label: string;
}

interface AnnotatedSliderProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  markers?: SliderMarker[];
  tooltip?: string;
  unit?: string;
  testId?: string;
  showTextInput?: boolean;
  example?: string;
  icon?: React.ReactNode;
}

export function AnnotatedSlider({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  markers = [],
  tooltip,
  unit = '%',
  testId,
  showTextInput = true,
  example,
  icon,
}: AnnotatedSliderProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [textValue, setTextValue] = useState(value.toString());

  const getMarkerPosition = (markerValue: number) => {
    return ((markerValue - min) / (max - min)) * 100;
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setTextValue(e.target.value);
  };

  const handleTextBlur = () => {
    setIsEditing(false);
    const parsed = parseFloat(textValue);
    if (!isNaN(parsed)) {
      const clamped = Math.min(max, Math.max(min, parsed));
      onChange(clamped);
      setTextValue(clamped.toString());
    } else {
      setTextValue(value.toString());
    }
  };

  const handleTextKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleTextBlur();
    } else if (e.key === 'Escape') {
      setIsEditing(false);
      setTextValue(value.toString());
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 flex-1">
          {icon && <span className="shrink-0">{icon}</span>}
          <Label className="text-sm">{label}</Label>
          {tooltip && (
            <Tooltip>
              <TooltipTrigger asChild>
                <button type="button" className="inline-flex" data-testid={`${testId}-tooltip`}>
                  <Info className="h-3.5 w-3.5 text-muted-foreground" />
                </button>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <p className="text-sm">{tooltip}</p>
                {example && (
                  <p className="text-xs text-muted-foreground mt-1 italic">
                    Example: {example}
                  </p>
                )}
              </TooltipContent>
            </Tooltip>
          )}
        </div>
        {showTextInput ? (
          isEditing ? (
            <Input
              type="number"
              value={textValue}
              onChange={handleTextChange}
              onBlur={handleTextBlur}
              onKeyDown={handleTextKeyDown}
              min={min}
              max={max}
              step={step}
              className="w-20 h-7 text-sm font-mono text-right"
              autoFocus
              data-testid={`${testId}-input`}
            />
          ) : (
            <button
              onClick={() => {
                setIsEditing(true);
                setTextValue(value.toString());
              }}
              className="text-sm font-mono font-medium px-2 py-0.5 rounded hover:bg-muted transition-colors"
              data-testid={`${testId}-value`}
              aria-label={`${label} value: ${value}${unit}. Click to edit.`}
            >
              {value > 0 ? '+' : ''}{value}{unit}
            </button>
          )
        ) : (
          <span className="text-sm font-mono font-medium">
            {value > 0 ? '+' : ''}{value}{unit}
          </span>
        )}
      </div>
      
      <div className="relative pt-2">
        <Slider
          value={[value]}
          onValueChange={([v]) => {
            onChange(v);
            setTextValue(v.toString());
          }}
          min={min}
          max={max}
          step={step}
          data-testid={testId}
          aria-label={label}
        />
        
        {markers.length > 0 && (
          <div className="relative h-6 mt-1">
            {markers.map((marker, i) => (
              <div
                key={i}
                className="absolute transform -translate-x-1/2"
                style={{ left: `${getMarkerPosition(marker.value)}%` }}
              >
                <div className={cn(
                  'w-1 h-2 bg-muted-foreground/40 mx-auto',
                  value === marker.value && 'bg-primary'
                )} />
                <span className={cn(
                  'text-xs text-muted-foreground whitespace-nowrap',
                  value === marker.value && 'text-foreground font-medium'
                )}>
                  {marker.label}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

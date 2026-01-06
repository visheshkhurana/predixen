import { Slider } from '@/components/ui/slider';
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
}: AnnotatedSliderProps) {
  const getMarkerPosition = (markerValue: number) => {
    return ((markerValue - min) / (max - min)) * 100;
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
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
              </TooltipContent>
            </Tooltip>
          )}
        </div>
        <span className="text-sm font-mono font-medium">
          {value > 0 ? '+' : ''}{value}{unit}
        </span>
      </div>
      
      <div className="relative pt-2">
        <Slider
          value={[value]}
          onValueChange={([v]) => onChange(v)}
          min={min}
          max={max}
          step={step}
          data-testid={testId}
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

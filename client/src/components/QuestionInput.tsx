import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface QuestionOption {
  label: string;
  value: string;
}

interface QuestionInputProps {
  id: string;
  question: string;
  helpText?: string;
  type: 'number' | 'select' | 'percentage';
  value: number | string;
  onChange: (value: number | string) => void;
  options?: QuestionOption[];
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  className?: string;
}

export function QuestionInput({
  id,
  question,
  helpText,
  type,
  value,
  onChange,
  options,
  min,
  max,
  step = 1,
  unit,
  className,
}: QuestionInputProps) {
  const handleNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    if (!isNaN(val)) {
      onChange(val);
    } else if (e.target.value === '' || e.target.value === '-') {
      onChange(e.target.value);
    }
  };

  return (
    <div className={cn("space-y-2", className)} data-testid={`question-input-${id}`}>
      <div className="flex items-center gap-2">
        <Label htmlFor={id} className="text-sm font-medium">
          {question}
        </Label>
        {helpText && (
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" className="text-muted-foreground hover:text-foreground">
                <HelpCircle className="w-4 h-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-xs">
              <p className="text-sm">{helpText}</p>
            </TooltipContent>
          </Tooltip>
        )}
      </div>
      
      {type === 'select' && options ? (
        <Select 
          value={String(value)} 
          onValueChange={(val) => onChange(val)}
        >
          <SelectTrigger id={id} data-testid={`select-${id}`}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {options.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ) : (
        <div className="relative">
          <Input
            id={id}
            type="number"
            value={value}
            onChange={handleNumberChange}
            min={min}
            max={max}
            step={step}
            className={cn(unit && "pr-12")}
            data-testid={`input-${id}`}
          />
          {unit && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
              {unit}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export const PRICING_OPTIONS: QuestionOption[] = [
  { label: '-10% (Price reduction)', value: '-10' },
  { label: 'No change', value: '0' },
  { label: '+5%', value: '5' },
  { label: '+10%', value: '10' },
  { label: '+15%', value: '15' },
  { label: '+20%', value: '20' },
];

export const EXPENSE_REDUCTION_OPTIONS: QuestionOption[] = [
  { label: 'No reduction', value: '0' },
  { label: '-10%', value: '10' },
  { label: '-20%', value: '20' },
  { label: '-30%', value: '30' },
  { label: '-40%', value: '40' },
];

export const HIRING_OPTIONS: QuestionOption[] = [
  { label: 'Hiring freeze', value: '0' },
  { label: '1-2 hires', value: '2' },
  { label: '3-5 hires', value: '5' },
  { label: '5-10 hires', value: '10' },
  { label: '10+ hires', value: '15' },
];

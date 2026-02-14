import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Plus, Trash2, HelpCircle, Calendar, Percent, DollarSign, TrendingUp, TrendingDown, Users, Scissors, Megaphone, RefreshCw } from 'lucide-react';
import { formatCurrencyAbbrev } from '@/lib/utils';

export interface ScenarioEvent {
  id: string;
  event_type: string;
  start_month: number;
  duration_months?: number;
  probability: number;
  params: Record<string, number | string>;
}

const EVENT_TYPES = [
  { 
    value: 'pricing_change', 
    label: 'Pricing Change', 
    icon: DollarSign,
    description: 'Adjust product pricing',
    params: [{ key: 'change_pct', label: 'Price Change %', type: 'percent', default: 10, min: -50, max: 50 }]
  },
  { 
    value: 'cost_cut', 
    label: 'Cost Reduction', 
    icon: Scissors,
    description: 'Reduce operating expenses',
    params: [
      { key: 'opex_reduction_pct', label: 'OpEx Reduction %', type: 'percent', default: 15, min: 0, max: 50 },
      { key: 'payroll_reduction_pct', label: 'Payroll Reduction %', type: 'percent', default: 10, min: 0, max: 40 }
    ]
  },
  { 
    value: 'hiring_freeze', 
    label: 'Hiring Freeze', 
    icon: Users,
    description: 'Pause all new hiring',
    params: [{ key: 'duration_months', label: 'Duration (months)', type: 'number', default: 6, min: 1, max: 24 }]
  },
  { 
    value: 'hiring_plan', 
    label: 'Hiring Plan', 
    icon: Users,
    description: 'Plan new hires',
    params: [
      { key: 'new_hires', label: 'New Hires', type: 'number', default: 5, min: 1, max: 50 },
      { key: 'avg_salary', label: 'Avg Salary ($)', type: 'currency', default: 80000, min: 30000, max: 300000 }
    ]
  },
  { 
    value: 'fundraise', 
    label: 'Fundraising', 
    icon: TrendingUp,
    description: 'Model funding round',
    params: [
      { key: 'amount', label: 'Amount ($)', type: 'currency', default: 1000000, min: 100000, max: 50000000 },
      { key: 'dilution_pct', label: 'Dilution %', type: 'percent', default: 15, min: 5, max: 40 }
    ]
  },
  { 
    value: 'marketing_spend_change', 
    label: 'Marketing Spend', 
    icon: Megaphone,
    description: 'Adjust marketing budget',
    params: [{ key: 'change_pct', label: 'Budget Change %', type: 'percent', default: 25, min: -50, max: 100 }]
  },
  { 
    value: 'churn_initiative', 
    label: 'Churn Initiative', 
    icon: RefreshCw,
    description: 'Customer retention program',
    params: [
      { key: 'churn_reduction_pct', label: 'Churn Reduction %', type: 'percent', default: 20, min: 5, max: 50 },
      { key: 'investment', label: 'Investment ($)', type: 'currency', default: 50000, min: 10000, max: 500000 }
    ]
  },
  { 
    value: 'expansion_revenue', 
    label: 'Expansion Revenue', 
    icon: TrendingUp,
    description: 'Upsell/cross-sell initiative',
    params: [{ key: 'uplift_pct', label: 'Revenue Uplift %', type: 'percent', default: 15, min: 5, max: 50 }]
  },
];

interface CustomEventBuilderProps {
  events: ScenarioEvent[];
  onChange: (events: ScenarioEvent[]) => void;
  horizonMonths?: number;
}

export function CustomEventBuilder({ events, onChange, horizonMonths = 24 }: CustomEventBuilderProps) {
  const [selectedEventType, setSelectedEventType] = useState<string>('');

  const generateId = () => `event_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

  const addEvent = () => {
    if (!selectedEventType) return;
    
    const eventDef = EVENT_TYPES.find(e => e.value === selectedEventType);
    if (!eventDef) return;

    const defaultParams: Record<string, number | string> = {};
    eventDef.params.forEach(p => {
      defaultParams[p.key] = p.default;
    });

    const newEvent: ScenarioEvent = {
      id: generateId(),
      event_type: selectedEventType,
      start_month: 1,
      probability: 100,
      params: defaultParams,
    };

    onChange([...events, newEvent]);
    setSelectedEventType('');
  };

  const updateEvent = (id: string, updates: Partial<ScenarioEvent>) => {
    onChange(events.map(e => e.id === id ? { ...e, ...updates } : e));
  };

  const updateEventParam = (id: string, key: string, value: number | string) => {
    onChange(events.map(e => 
      e.id === id ? { ...e, params: { ...e.params, [key]: value } } : e
    ));
  };

  const removeEvent = (id: string) => {
    onChange(events.filter(e => e.id !== id));
  };

  const formatParamValue = (type: string, value: number) => {
    if (type === 'currency') {
      return formatCurrencyAbbrev(value);
    }
    if (type === 'percent') {
      return `${value}%`;
    }
    return value.toString();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <h3 className="font-medium">Custom Events</h3>
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" className="p-0.5">
                <HelpCircle className="h-4 w-4 text-muted-foreground" />
              </button>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="text-sm">
                Add custom events with timing and probability. Events can have different likelihoods of occurring, allowing you to model uncertainty.
              </p>
            </TooltipContent>
          </Tooltip>
        </div>
        <Badge variant="outline">{events.length} events</Badge>
      </div>

      <div className="flex gap-2">
        <Select value={selectedEventType} onValueChange={setSelectedEventType}>
          <SelectTrigger className="flex-1" data-testid="select-event-type">
            <SelectValue placeholder="Select event type to add..." />
          </SelectTrigger>
          <SelectContent>
            {EVENT_TYPES.map(type => {
              const Icon = type.icon;
              return (
                <SelectItem key={type.value} value={type.value}>
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4" />
                    <span>{type.label}</span>
                  </div>
                </SelectItem>
              );
            })}
          </SelectContent>
        </Select>
        <Button onClick={addEvent} disabled={!selectedEventType} data-testid="button-add-event">
          <Plus className="h-4 w-4 mr-1" />
          Add
        </Button>
      </div>

      {events.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground text-sm">
              No custom events added. Select an event type above to model specific scenarios.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {events.map((event, index) => {
            const eventDef = EVENT_TYPES.find(e => e.value === event.event_type);
            if (!eventDef) return null;
            const Icon = eventDef.icon;

            return (
              <Card key={event.id} data-testid={`event-card-${index}`}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded bg-primary/10">
                        <Icon className="h-4 w-4 text-primary" />
                      </div>
                      <CardTitle className="text-base">{eventDef.label}</CardTitle>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => removeEvent(event.id)}
                      data-testid={`button-remove-event-${index}`}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="flex items-center gap-1">
                        <Calendar className="h-3.5 w-3.5" />
                        Start Month
                      </Label>
                      <Select
                        value={event.start_month.toString()}
                        onValueChange={(v) => updateEvent(event.id, { start_month: parseInt(v) })}
                      >
                        <SelectTrigger data-testid={`select-start-month-${index}`}>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {Array.from({ length: horizonMonths }, (_, i) => i + 1).map(month => (
                            <SelectItem key={month} value={month.toString()}>
                              Month {month}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label className="flex items-center gap-1">
                        <Percent className="h-3.5 w-3.5" />
                        Probability
                      </Label>
                      <div className="flex items-center gap-2">
                        <Slider
                          value={[event.probability]}
                          onValueChange={([v]) => updateEvent(event.id, { probability: v })}
                          min={10}
                          max={100}
                          step={5}
                          className="flex-1"
                        />
                        <span className="text-sm font-mono w-12 text-right">{event.probability}%</span>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {eventDef.params.map(param => (
                      <div key={param.key} className="space-y-2">
                        <Label>{param.label}</Label>
                        {param.type === 'currency' ? (
                          <div className="space-y-1">
                            <Slider
                              value={[Number(event.params[param.key]) || param.default]}
                              onValueChange={([v]) => updateEventParam(event.id, param.key, v)}
                              min={param.min}
                              max={param.max}
                              step={param.max > 1000000 ? 100000 : 10000}
                            />
                            <p className="text-sm font-mono text-right">
                              {formatParamValue('currency', Number(event.params[param.key]) || param.default)}
                            </p>
                          </div>
                        ) : param.type === 'percent' ? (
                          <div className="space-y-1">
                            <Slider
                              value={[Number(event.params[param.key]) || param.default]}
                              onValueChange={([v]) => updateEventParam(event.id, param.key, v)}
                              min={param.min}
                              max={param.max}
                              step={1}
                            />
                            <p className="text-sm font-mono text-right">
                              {Number(event.params[param.key]) || param.default}%
                            </p>
                          </div>
                        ) : (
                          <Input
                            type="number"
                            value={event.params[param.key] || param.default}
                            onChange={(e) => updateEventParam(event.id, param.key, parseInt(e.target.value) || param.default)}
                            min={param.min}
                            max={param.max}
                          />
                        )}
                      </div>
                    ))}
                  </div>

                  {event.probability < 100 && (
                    <div className="text-xs text-muted-foreground bg-muted/50 rounded p-2">
                      This event has a {event.probability}% chance of occurring in simulations.
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

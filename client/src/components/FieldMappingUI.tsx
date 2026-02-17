import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  ArrowRight,
  Check,
  AlertCircle,
  Sparkles,
  RefreshCw,
  Link2,
  Unlink2,
  HelpCircle,
} from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

export interface SourceField {
  name: string;
  sample_values: string[];
  data_type: 'string' | 'number' | 'date' | 'boolean' | 'unknown';
}

export interface TargetField {
  id: string;
  name: string;
  description: string;
  required: boolean;
  data_type: 'string' | 'number' | 'date' | 'boolean';
  category: string;
}

export interface FieldMapping {
  source_field: string;
  target_field: string;
  transform?: string;
  confidence?: number;
}

interface FieldMappingUIProps {
  sourceFields: SourceField[];
  targetFields: TargetField[];
  initialMappings?: FieldMapping[];
  onMappingsChange: (mappings: FieldMapping[]) => void;
  onConfirm: (mappings: FieldMapping[]) => void;
  onCancel: () => void;
  isLoading?: boolean;
  showAutoMap?: boolean;
}

const TARGET_FIELDS: TargetField[] = [
  { id: 'monthly_revenue', name: 'Monthly Revenue', description: 'Total revenue for the month', required: true, data_type: 'number', category: 'Revenue' },
  { id: 'mrr', name: 'MRR', description: 'Monthly Recurring Revenue', required: false, data_type: 'number', category: 'Revenue' },
  { id: 'arr', name: 'ARR', description: 'Annual Recurring Revenue', required: false, data_type: 'number', category: 'Revenue' },
  { id: 'cash_balance', name: 'Cash Balance', description: 'Total cash on hand', required: true, data_type: 'number', category: 'Cash' },
  { id: 'net_burn', name: 'Net Burn', description: 'Monthly net burn rate', required: false, data_type: 'number', category: 'Expenses' },
  { id: 'gross_burn', name: 'Gross Burn', description: 'Total monthly expenses', required: false, data_type: 'number', category: 'Expenses' },
  { id: 'payroll', name: 'Payroll Expenses', description: 'Employee compensation costs', required: false, data_type: 'number', category: 'Expenses' },
  { id: 'marketing', name: 'Marketing Expenses', description: 'Marketing and advertising spend', required: false, data_type: 'number', category: 'Expenses' },
  { id: 'cogs', name: 'Cost of Goods Sold', description: 'Direct costs of revenue', required: false, data_type: 'number', category: 'Expenses' },
  { id: 'headcount', name: 'Headcount', description: 'Total employee count', required: false, data_type: 'number', category: 'Team' },
  { id: 'customers', name: 'Customer Count', description: 'Number of paying customers', required: false, data_type: 'number', category: 'Customers' },
  { id: 'churn_rate', name: 'Churn Rate', description: 'Monthly customer churn percentage', required: false, data_type: 'number', category: 'Customers' },
  { id: 'cac', name: 'CAC', description: 'Customer Acquisition Cost', required: false, data_type: 'number', category: 'Unit Economics' },
  { id: 'ltv', name: 'LTV', description: 'Customer Lifetime Value', required: false, data_type: 'number', category: 'Unit Economics' },
  { id: 'gross_margin', name: 'Gross Margin', description: 'Gross margin percentage', required: false, data_type: 'number', category: 'Margins' },
  { id: 'date', name: 'Date', description: 'Date of the data record', required: false, data_type: 'date', category: 'Metadata' },
];

function autoMapFields(sourceFields: SourceField[], targetFields: TargetField[]): FieldMapping[] {
  const mappings: FieldMapping[] = [];
  
  const keywordMap: Record<string, string[]> = {
    'monthly_revenue': ['revenue', 'sales', 'income', 'total_revenue'],
    'mrr': ['mrr', 'monthly_recurring', 'recurring_revenue'],
    'arr': ['arr', 'annual_recurring', 'yearly_revenue'],
    'cash_balance': ['cash', 'balance', 'bank', 'cash_on_hand'],
    'net_burn': ['net_burn', 'burn_rate', 'net_expenses'],
    'gross_burn': ['gross_burn', 'total_expenses', 'expenses'],
    'payroll': ['payroll', 'salaries', 'wages', 'compensation'],
    'marketing': ['marketing', 'advertising', 'ads', 'ad_spend'],
    'cogs': ['cogs', 'cost_of_goods', 'direct_costs'],
    'headcount': ['headcount', 'employees', 'team_size', 'staff'],
    'customers': ['customers', 'users', 'clients', 'customer_count'],
    'churn_rate': ['churn', 'churn_rate', 'attrition'],
    'cac': ['cac', 'acquisition_cost', 'customer_acquisition'],
    'ltv': ['ltv', 'lifetime_value', 'clv'],
    'gross_margin': ['margin', 'gross_margin', 'gm'],
    'date': ['date', 'period', 'month', 'timestamp'],
  };
  
  for (const source of sourceFields) {
    const normalizedName = source.name.toLowerCase().replace(/[^a-z0-9]/g, '_');
    
    for (const [targetId, keywords] of Object.entries(keywordMap)) {
      if (keywords.some(kw => normalizedName.includes(kw))) {
        if (!mappings.find(m => m.target_field === targetId)) {
          mappings.push({
            source_field: source.name,
            target_field: targetId,
            confidence: 0.8,
          });
          break;
        }
      }
    }
  }
  
  return mappings;
}

export function FieldMappingUI({
  sourceFields,
  targetFields = TARGET_FIELDS,
  initialMappings = [],
  onMappingsChange,
  onConfirm,
  onCancel,
  isLoading = false,
  showAutoMap = true,
}: FieldMappingUIProps) {
  const [mappings, setMappings] = useState<FieldMapping[]>(initialMappings);
  const [showUnmapped, setShowUnmapped] = useState(true);
  
  useEffect(() => {
    if (initialMappings.length === 0 && sourceFields.length > 0 && showAutoMap) {
      const autoMappings = autoMapFields(sourceFields, targetFields);
      setMappings(autoMappings);
      onMappingsChange(autoMappings);
    }
  }, [sourceFields]);
  
  const updateMapping = (targetId: string, sourceField: string | null) => {
    const newMappings = mappings.filter(m => m.target_field !== targetId);
    
    if (sourceField) {
      newMappings.push({
        source_field: sourceField,
        target_field: targetId,
      });
    }
    
    setMappings(newMappings);
    onMappingsChange(newMappings);
  };
  
  const getMappingForTarget = (targetId: string): string | undefined => {
    return mappings.find(m => m.target_field === targetId)?.source_field;
  };
  
  const handleAutoMap = () => {
    const autoMappings = autoMapFields(sourceFields, targetFields);
    setMappings(autoMappings);
    onMappingsChange(autoMappings);
  };
  
  const handleClearAll = () => {
    setMappings([]);
    onMappingsChange([]);
  };
  
  const requiredFieldsMapped = targetFields
    .filter(f => f.required)
    .every(f => mappings.some(m => m.target_field === f.id));
  
  const mappedCount = mappings.length;
  const totalFields = targetFields.length;
  
  const groupedFields = targetFields.reduce((acc, field) => {
    if (!acc[field.category]) {
      acc[field.category] = [];
    }
    acc[field.category].push(field);
    return acc;
  }, {} as Record<string, TargetField[]>);
  
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <div>
            <CardTitle className="text-lg">Field Mapping</CardTitle>
            <CardDescription>
              Map your imported fields to FounderConsole metrics
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">
              {mappedCount}/{totalFields} mapped
            </Badge>
            {showAutoMap && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleAutoMap}
                data-testid="button-auto-map"
              >
                <Sparkles className="h-4 w-4 mr-1" />
                Auto-Map
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearAll}
              data-testid="button-clear-mappings"
            >
              <Unlink2 className="h-4 w-4 mr-1" />
              Clear
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[500px] pr-4">
          {Object.entries(groupedFields).map(([category, fields]) => (
            <div key={category} className="mb-6">
              <h4 className="text-sm font-medium text-muted-foreground mb-3">
                {category}
              </h4>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[200px]">FounderConsole Field</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                    <TableHead>Your Data Field</TableHead>
                    <TableHead className="w-[100px]">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {fields.map((field) => {
                    const mappedSource = getMappingForTarget(field.id);
                    const sourceField = sourceFields.find(s => s.name === mappedSource);
                    
                    return (
                      <TableRow key={field.id} data-testid={`mapping-row-${field.id}`}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{field.name}</span>
                            {field.required && (
                              <Badge variant="destructive" className="text-[10px] px-1 py-0">
                                Required
                              </Badge>
                            )}
                            <Tooltip>
                              <TooltipTrigger>
                                <HelpCircle className="h-3 w-3 text-muted-foreground" />
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>{field.description}</p>
                              </TooltipContent>
                            </Tooltip>
                          </div>
                        </TableCell>
                        <TableCell>
                          <ArrowRight className="h-4 w-4 text-muted-foreground" />
                        </TableCell>
                        <TableCell>
                          <Select
                            value={mappedSource || ""}
                            onValueChange={(val) => updateMapping(field.id, val || null)}
                          >
                            <SelectTrigger 
                              className="w-full"
                              data-testid={`select-mapping-${field.id}`}
                            >
                              <SelectValue placeholder="Select a field..." />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="">
                                <span className="text-muted-foreground">-- Not mapped --</span>
                              </SelectItem>
                              {sourceFields.map((source) => (
                                <SelectItem key={source.name} value={source.name}>
                                  <div className="flex items-center gap-2">
                                    <span>{source.name}</span>
                                    {source.sample_values.length > 0 && (
                                      <span className="text-xs text-muted-foreground">
                                        ({source.sample_values[0]?.substring(0, 20)})
                                      </span>
                                    )}
                                  </div>
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </TableCell>
                        <TableCell>
                          {mappedSource ? (
                            <Badge variant="default" className="gap-1">
                              <Link2 className="h-3 w-3" />
                              Mapped
                            </Badge>
                          ) : field.required ? (
                            <Badge variant="destructive" className="gap-1">
                              <AlertCircle className="h-3 w-3" />
                              Missing
                            </Badge>
                          ) : (
                            <Badge variant="secondary">
                              Optional
                            </Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          ))}
        </ScrollArea>
        
        <div className="flex items-center justify-between mt-6 pt-4 border-t">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {!requiredFieldsMapped && (
              <span className="flex items-center gap-1 text-destructive">
                <AlertCircle className="h-4 w-4" />
                Please map all required fields
              </span>
            )}
            {requiredFieldsMapped && mappedCount > 0 && (
              <span className="flex items-center gap-1 text-green-600">
                <Check className="h-4 w-4" />
                Ready to import
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={onCancel} data-testid="button-cancel-mapping">
              Cancel
            </Button>
            <Button 
              onClick={() => onConfirm(mappings)}
              disabled={!requiredFieldsMapped || isLoading}
              data-testid="button-confirm-mapping"
            >
              {isLoading && <RefreshCw className="h-4 w-4 mr-2 animate-spin" />}
              Confirm Mapping
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

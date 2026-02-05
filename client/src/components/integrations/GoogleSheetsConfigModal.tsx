import { useState, useEffect } from 'react';
import { SheetMapping, ColumnMapping, SpreadsheetInfo, SheetInfo, SyncInterval } from '@/lib/integrations/types';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { FileSpreadsheet, RefreshCw, Plus, Trash2, ChevronRight, Loader2, Check, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface GoogleSheetsConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (mappings: SheetMapping[]) => void;
  existingMappings?: SheetMapping[];
}

const mockSpreadsheets: SpreadsheetInfo[] = [
  {
    id: 'sheet1',
    name: 'Company Financials 2024',
    sheets: [
      { id: 0, name: 'Monthly Revenue', rowCount: 36, columnCount: 8 },
      { id: 1, name: 'Expenses', rowCount: 100, columnCount: 12 },
      { id: 2, name: 'KPIs', rowCount: 24, columnCount: 6 },
    ],
    lastModified: '2024-02-01T10:30:00Z',
  },
  {
    id: 'sheet2',
    name: 'Sales Pipeline',
    sheets: [
      { id: 0, name: 'Deals', rowCount: 150, columnCount: 10 },
      { id: 1, name: 'Forecast', rowCount: 12, columnCount: 5 },
    ],
    lastModified: '2024-02-03T14:22:00Z',
  },
  {
    id: 'sheet3',
    name: 'Budget Tracker',
    sheets: [
      { id: 0, name: 'Budget vs Actual', rowCount: 48, columnCount: 8 },
      { id: 1, name: 'Department Breakdown', rowCount: 24, columnCount: 6 },
    ],
    lastModified: '2024-02-04T09:15:00Z',
  },
];

const mockColumns = [
  { letter: 'A', header: 'Month', sample: 'January 2024' },
  { letter: 'B', header: 'Revenue', sample: '$125,000' },
  { letter: 'C', header: 'Expenses', sample: '$95,000' },
  { letter: 'D', header: 'Net Income', sample: '$30,000' },
  { letter: 'E', header: 'MRR', sample: '$45,000' },
  { letter: 'F', header: 'Customers', sample: '156' },
];

type Step = 'select-spreadsheet' | 'select-sheet' | 'map-columns' | 'configure-sync';

const syncIntervalOptions: { value: SyncInterval; label: string }[] = [
  { value: '15min', label: 'Every 15 minutes' },
  { value: '30min', label: 'Every 30 minutes' },
  { value: 'hourly', label: 'Every hour' },
  { value: 'daily', label: 'Daily' },
];

const dataTypeOptions = [
  { value: 'number', label: 'Number' },
  { value: 'currency', label: 'Currency' },
  { value: 'percentage', label: 'Percentage' },
  { value: 'string', label: 'Text' },
  { value: 'date', label: 'Date' },
];

const aggregationOptions = [
  { value: 'latest', label: 'Latest Value' },
  { value: 'sum', label: 'Sum' },
  { value: 'average', label: 'Average' },
  { value: 'min', label: 'Minimum' },
  { value: 'max', label: 'Maximum' },
];

export function GoogleSheetsConfigModal({
  isOpen,
  onClose,
  onSave,
  existingMappings = [],
}: GoogleSheetsConfigModalProps) {
  const [step, setStep] = useState<Step>('select-spreadsheet');
  const [isLoading, setIsLoading] = useState(false);
  const [spreadsheets, setSpreadsheets] = useState<SpreadsheetInfo[]>([]);
  const [selectedSpreadsheet, setSelectedSpreadsheet] = useState<SpreadsheetInfo | null>(null);
  const [selectedSheet, setSelectedSheet] = useState<SheetInfo | null>(null);
  const [columnMappings, setColumnMappings] = useState<ColumnMapping[]>([]);
  const [hasHeaderRow, setHasHeaderRow] = useState(true);
  const [syncInterval, setSyncInterval] = useState<SyncInterval>('hourly');

  useEffect(() => {
    if (isOpen) {
      loadSpreadsheets();
    }
  }, [isOpen]);

  const loadSpreadsheets = async () => {
    setIsLoading(true);
    await new Promise(resolve => setTimeout(resolve, 800));
    setSpreadsheets(mockSpreadsheets);
    setIsLoading(false);
  };

  const handleSelectSpreadsheet = (spreadsheet: SpreadsheetInfo) => {
    setSelectedSpreadsheet(spreadsheet);
    setStep('select-sheet');
  };

  const handleSelectSheet = (sheet: SheetInfo) => {
    setSelectedSheet(sheet);
    setColumnMappings([]);
    setStep('map-columns');
  };

  const handleAddColumnMapping = (columnIndex: number) => {
    const column = mockColumns[columnIndex];
    if (!column) return;
    
    const exists = columnMappings.some(m => m.columnIndex === columnIndex);
    if (exists) return;

    const newMapping: ColumnMapping = {
      columnIndex,
      columnLetter: column.letter,
      columnHeader: column.header,
      metricName: column.header.toLowerCase().replace(/\s+/g, '_'),
      dataType: 'number',
      aggregation: 'latest',
    };
    setColumnMappings([...columnMappings, newMapping]);
  };

  const handleRemoveColumnMapping = (columnIndex: number) => {
    setColumnMappings(columnMappings.filter(m => m.columnIndex !== columnIndex));
  };

  const handleUpdateMapping = (columnIndex: number, field: keyof ColumnMapping, value: any) => {
    setColumnMappings(columnMappings.map(m => 
      m.columnIndex === columnIndex ? { ...m, [field]: value } : m
    ));
  };

  const handleSave = () => {
    if (!selectedSpreadsheet || !selectedSheet) return;

    const mapping: SheetMapping = {
      spreadsheetId: selectedSpreadsheet.id,
      spreadsheetName: selectedSpreadsheet.name,
      sheetId: selectedSheet.id.toString(),
      sheetName: selectedSheet.name,
      dataRange: `${selectedSheet.name}!A1:${String.fromCharCode(65 + selectedSheet.columnCount - 1)}${selectedSheet.rowCount}`,
      columnMappings,
      hasHeaderRow,
      syncInterval,
    };

    onSave([...existingMappings, mapping]);
    handleClose();
  };

  const handleClose = () => {
    setStep('select-spreadsheet');
    setSelectedSpreadsheet(null);
    setSelectedSheet(null);
    setColumnMappings([]);
    setHasHeaderRow(true);
    setSyncInterval('hourly');
    onClose();
  };

  const renderBreadcrumb = () => (
    <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
      <span className={cn(step === 'select-spreadsheet' ? 'text-foreground font-medium' : '')}>
        Select Spreadsheet
      </span>
      {(step === 'select-sheet' || step === 'map-columns' || step === 'configure-sync') && (
        <>
          <ChevronRight className="w-4 h-4" />
          <span className={cn(step === 'select-sheet' ? 'text-foreground font-medium' : '')}>
            Select Sheet
          </span>
        </>
      )}
      {(step === 'map-columns' || step === 'configure-sync') && (
        <>
          <ChevronRight className="w-4 h-4" />
          <span className={cn(step === 'map-columns' ? 'text-foreground font-medium' : '')}>
            Map Columns
          </span>
        </>
      )}
      {step === 'configure-sync' && (
        <>
          <ChevronRight className="w-4 h-4" />
          <span className="text-foreground font-medium">Configure Sync</span>
        </>
      )}
    </div>
  );

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col" data-testid="modal-sheets-config">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-green-500" />
            Configure Google Sheets
          </DialogTitle>
          <DialogDescription>
            Select a spreadsheet and map columns to metrics.
          </DialogDescription>
        </DialogHeader>

        {renderBreadcrumb()}

        <div className="flex-1 overflow-y-auto">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          )}

          {!isLoading && step === 'select-spreadsheet' && (
            <div className="space-y-2">
              {spreadsheets.map((spreadsheet) => (
                <Card 
                  key={spreadsheet.id}
                  className="cursor-pointer hover-elevate"
                  onClick={() => handleSelectSpreadsheet(spreadsheet)}
                  data-testid={`card-spreadsheet-${spreadsheet.id}`}
                >
                  <CardContent className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <FileSpreadsheet className="w-8 h-8 text-green-500" />
                      <div>
                        <h4 className="font-medium">{spreadsheet.name}</h4>
                        <p className="text-xs text-muted-foreground">
                          {spreadsheet.sheets.length} sheets - Last modified {new Date(spreadsheet.lastModified).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-muted-foreground" />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {!isLoading && step === 'select-sheet' && selectedSpreadsheet && (
            <div className="space-y-2">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-medium">{selectedSpreadsheet.name}</h4>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => setStep('select-spreadsheet')}
                  data-testid="button-change-spreadsheet"
                >
                  Change
                </Button>
              </div>
              {selectedSpreadsheet.sheets.map((sheet) => (
                <Card 
                  key={sheet.id}
                  className="cursor-pointer hover-elevate"
                  onClick={() => handleSelectSheet(sheet)}
                  data-testid={`card-sheet-${sheet.id}`}
                >
                  <CardContent className="p-4 flex items-center justify-between">
                    <div>
                      <h4 className="font-medium">{sheet.name}</h4>
                      <p className="text-xs text-muted-foreground">
                        {sheet.rowCount} rows × {sheet.columnCount} columns
                      </p>
                    </div>
                    <ChevronRight className="w-5 h-5 text-muted-foreground" />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {!isLoading && step === 'map-columns' && selectedSheet && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <Checkbox
                  id="has-header"
                  checked={hasHeaderRow}
                  onCheckedChange={(checked) => setHasHeaderRow(checked as boolean)}
                />
                <Label htmlFor="has-header" className="text-sm">First row contains headers</Label>
              </div>

              <div className="space-y-2">
                <Label className="text-sm font-medium">Available Columns</Label>
                <div className="flex flex-wrap gap-2">
                  {mockColumns.map((col, idx) => {
                    const isMapped = columnMappings.some(m => m.columnIndex === idx);
                    return (
                      <Badge
                        key={col.letter}
                        variant={isMapped ? "default" : "outline"}
                        className={cn("cursor-pointer", isMapped && "bg-green-600")}
                        onClick={() => isMapped ? handleRemoveColumnMapping(idx) : handleAddColumnMapping(idx)}
                        data-testid={`badge-column-${col.letter}`}
                      >
                        {isMapped && <Check className="w-3 h-3 mr-1" />}
                        {col.letter}: {col.header}
                      </Badge>
                    );
                  })}
                </div>
              </div>

              {columnMappings.length > 0 && (
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Column Mappings</Label>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Column</TableHead>
                        <TableHead>Metric Name</TableHead>
                        <TableHead>Data Type</TableHead>
                        <TableHead>Aggregation</TableHead>
                        <TableHead></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {columnMappings.map((mapping) => (
                        <TableRow key={mapping.columnIndex}>
                          <TableCell className="font-medium">
                            {mapping.columnLetter}: {mapping.columnHeader}
                          </TableCell>
                          <TableCell>
                            <Input
                              value={mapping.metricName}
                              onChange={(e) => handleUpdateMapping(mapping.columnIndex, 'metricName', e.target.value)}
                              className="h-8"
                              data-testid={`input-metric-${mapping.columnLetter}`}
                            />
                          </TableCell>
                          <TableCell>
                            <Select
                              value={mapping.dataType}
                              onValueChange={(v) => handleUpdateMapping(mapping.columnIndex, 'dataType', v)}
                            >
                              <SelectTrigger className="h-8" data-testid={`select-type-${mapping.columnLetter}`}>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {dataTypeOptions.map(opt => (
                                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </TableCell>
                          <TableCell>
                            <Select
                              value={mapping.aggregation || 'latest'}
                              onValueChange={(v) => handleUpdateMapping(mapping.columnIndex, 'aggregation', v)}
                            >
                              <SelectTrigger className="h-8" data-testid={`select-agg-${mapping.columnLetter}`}>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {aggregationOptions.map(opt => (
                                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => handleRemoveColumnMapping(mapping.columnIndex)}
                              data-testid={`button-remove-${mapping.columnLetter}`}
                            >
                              <Trash2 className="w-4 h-4 text-destructive" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              {columnMappings.length === 0 && (
                <div className="flex items-center gap-2 p-4 bg-muted/50 rounded-lg">
                  <AlertCircle className="w-5 h-5 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    Click on columns above to add them as metrics.
                  </p>
                </div>
              )}
            </div>
          )}

          {!isLoading && step === 'configure-sync' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Sync Frequency</Label>
                <Select value={syncInterval} onValueChange={(v) => setSyncInterval(v as SyncInterval)}>
                  <SelectTrigger data-testid="select-sync-interval">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {syncIntervalOptions.map(opt => (
                      <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Card>
                <CardContent className="p-4 space-y-2">
                  <h4 className="font-medium">Summary</h4>
                  <div className="text-sm text-muted-foreground space-y-1">
                    <p>Spreadsheet: <span className="text-foreground">{selectedSpreadsheet?.name}</span></p>
                    <p>Sheet: <span className="text-foreground">{selectedSheet?.name}</span></p>
                    <p>Metrics: <span className="text-foreground">{columnMappings.length} columns mapped</span></p>
                    <p>Sync: <span className="text-foreground">{syncIntervalOptions.find(o => o.value === syncInterval)?.label}</span></p>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>

        <DialogFooter className="mt-4">
          {step === 'select-spreadsheet' && (
            <Button variant="outline" onClick={handleClose} data-testid="button-cancel">
              Cancel
            </Button>
          )}
          {step === 'select-sheet' && (
            <Button variant="outline" onClick={() => setStep('select-spreadsheet')} data-testid="button-back">
              Back
            </Button>
          )}
          {step === 'map-columns' && (
            <>
              <Button variant="outline" onClick={() => setStep('select-sheet')} data-testid="button-back">
                Back
              </Button>
              <Button 
                onClick={() => setStep('configure-sync')} 
                disabled={columnMappings.length === 0}
                data-testid="button-continue"
              >
                Continue
              </Button>
            </>
          )}
          {step === 'configure-sync' && (
            <>
              <Button variant="outline" onClick={() => setStep('map-columns')} data-testid="button-back">
                Back
              </Button>
              <Button onClick={handleSave} data-testid="button-save">
                <Check className="w-4 h-4 mr-2" />
                Save Configuration
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default GoogleSheetsConfigModal;

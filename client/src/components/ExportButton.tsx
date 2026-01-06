import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Download, FileSpreadsheet, FileJson } from 'lucide-react';
import { downloadCSV, downloadJSON } from '@/lib/exportUtils';
import { useToast } from '@/hooks/use-toast';

interface ExportButtonProps {
  data: any;
  filename: string;
  formatForCSV?: (data: any) => Record<string, any>[];
  testId?: string;
}

export function ExportButton({
  data,
  filename,
  formatForCSV,
  testId = 'export-button',
}: ExportButtonProps) {
  const { toast } = useToast();

  const handleExportCSV = () => {
    try {
      const formattedData = formatForCSV ? formatForCSV(data) : [data];
      if (formattedData.length === 0) {
        toast({
          title: 'No data to export',
          description: 'There is no data available for export.',
          variant: 'destructive',
        });
        return;
      }
      downloadCSV(formattedData, filename);
      toast({
        title: 'Export successful',
        description: `${filename}.csv has been downloaded.`,
      });
    } catch (error) {
      toast({
        title: 'Export failed',
        description: 'There was an error exporting the data.',
        variant: 'destructive',
      });
    }
  };

  const handleExportJSON = () => {
    try {
      downloadJSON(data, filename);
      toast({
        title: 'Export successful',
        description: `${filename}.json has been downloaded.`,
      });
    } catch (error) {
      toast({
        title: 'Export failed',
        description: 'There was an error exporting the data.',
        variant: 'destructive',
      });
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" data-testid={testId}>
          <Download className="h-4 w-4 mr-2" />
          Export
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={handleExportCSV} data-testid={`${testId}-csv`}>
          <FileSpreadsheet className="h-4 w-4 mr-2" />
          Export as CSV
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleExportJSON} data-testid={`${testId}-json`}>
          <FileJson className="h-4 w-4 mr-2" />
          Export as JSON
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

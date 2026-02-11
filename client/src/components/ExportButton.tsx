import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Download, FileSpreadsheet, FileJson, FileText } from 'lucide-react';
import { downloadCSV, downloadJSON, downloadPDF } from '@/lib/exportUtils';
import { useToast } from '@/hooks/use-toast';

interface ExportButtonProps {
  data: any;
  filename: string;
  formatForCSV?: (data: any) => Record<string, any>[];
  pdfTitle?: string;
  showPDF?: boolean;
  onGeneratePDF?: () => Promise<void>;
  testId?: string;
}

export function ExportButton({
  data,
  filename,
  formatForCSV,
  pdfTitle,
  showPDF = false,
  onGeneratePDF,
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

  const handleExportPDF = async () => {
    try {
      if (onGeneratePDF) {
        await onGeneratePDF();
        toast({
          title: 'PDF downloaded',
          description: 'Your investor report has been saved.',
        });
      } else {
        downloadPDF(data, filename, pdfTitle || 'Truth Scan Report');
        toast({
          title: 'PDF opened',
          description: 'Use your browser print dialog to save as PDF.',
        });
      }
    } catch (error) {
      toast({
        title: 'Export failed',
        description: 'There was an error generating the PDF.',
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
        {(showPDF || onGeneratePDF) && (
          <DropdownMenuItem onClick={handleExportPDF} data-testid={`${testId}-pdf`}>
            <FileText className="h-4 w-4 mr-2" />
            {onGeneratePDF ? 'Download PDF Report' : 'Export as PDF'}
          </DropdownMenuItem>
        )}
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

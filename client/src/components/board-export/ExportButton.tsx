import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Download, Presentation, FileText, BarChart3 } from 'lucide-react';
import { BOARD_TEMPLATES } from './templates';
import { PreviewModal } from './PreviewModal';

interface ExportButtonProps {
  companyId: number;
}

export function BoardExportButton({ companyId }: ExportButtonProps) {
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);

  const templateIcons: Record<string, typeof Presentation> = {
    'monthly-update': FileText,
    'fundraising-prep': Presentation,
    'scenario-analysis': BarChart3,
  };

  const handleSelect = (templateId: string) => {
    setSelectedTemplateId(templateId);
    setPreviewOpen(true);
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" data-testid="button-board-export">
            <Download className="h-4 w-4 mr-1" />
            Board Deck
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" data-testid="menu-board-export">
          {BOARD_TEMPLATES.map((template) => {
            const Icon = templateIcons[template.id] || FileText;
            return (
              <DropdownMenuItem
                key={template.id}
                onClick={() => handleSelect(template.id)}
                data-testid={`menu-item-export-${template.id}`}
              >
                <Icon className="h-4 w-4 mr-2" />
                <div>
                  <div className="font-medium">{template.name}</div>
                  <div className="text-xs text-muted-foreground">{template.description}</div>
                </div>
              </DropdownMenuItem>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>

      {selectedTemplateId && (
        <PreviewModal
          open={previewOpen}
          onOpenChange={setPreviewOpen}
          companyId={companyId}
          templateId={selectedTemplateId}
        />
      )}
    </>
  );
}

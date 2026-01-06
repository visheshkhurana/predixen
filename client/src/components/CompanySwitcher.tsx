import { useState } from 'react';
import { useLocation } from 'wouter';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Building2, ChevronDown, Plus, Check } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useCompanies } from '@/api/hooks';
import { Skeleton } from '@/components/ui/skeleton';

export function CompanySwitcher() {
  const { currentCompany, setCurrentCompany } = useFounderStore();
  const { data: companies, isLoading } = useCompanies();
  const [open, setOpen] = useState(false);
  const [, navigate] = useLocation();

  if (isLoading) {
    return <Skeleton className="h-9 w-40" />;
  }

  const companyList = companies || [];

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="justify-between gap-2"
          data-testid="button-company-switcher"
          aria-label="Switch company"
        >
          <Building2 className="h-4 w-4" />
          <span className="truncate max-w-[120px]">
            {currentCompany?.name || 'Select Company'}
          </span>
          <ChevronDown className="h-4 w-4 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuLabel>Your Companies</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {companyList.length === 0 ? (
          <DropdownMenuItem disabled>
            <span className="text-muted-foreground">No companies yet</span>
          </DropdownMenuItem>
        ) : (
          companyList.map((company: any) => (
            <DropdownMenuItem
              key={company.id}
              onClick={() => {
                setCurrentCompany(company);
                setOpen(false);
              }}
              className="justify-between"
              data-testid={`company-option-${company.id}`}
            >
              <div className="flex items-center gap-2">
                <Building2 className="h-4 w-4 text-muted-foreground" />
                <span className="truncate">{company.name}</span>
              </div>
              {currentCompany?.id === company.id && (
                <Check className="h-4 w-4 text-primary" />
              )}
            </DropdownMenuItem>
          ))
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => {
            setOpen(false);
            navigate('/onboarding');
          }}
          data-testid="button-add-company"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add New Company
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

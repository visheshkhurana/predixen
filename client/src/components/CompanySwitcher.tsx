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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Building2, ChevronDown, Plus, Check, Pencil, Trash2 } from 'lucide-react';
import { useFounderStore } from '@/store/founderStore';
import { useCompanies, useUpdateCompany, useDeleteCompany } from '@/api/hooks';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';

interface Company {
  id: number;
  name: string;
  website?: string;
  industry?: string;
  stage?: string;
  currency: string;
  description?: string;
}

const INDUSTRIES = [
  'SaaS',
  'E-commerce',
  'Fintech',
  'Healthcare',
  'EdTech',
  'Marketplace',
  'Enterprise',
  'Consumer',
  'Other'
];

const STAGES = [
  'Pre-seed',
  'Seed',
  'Series A',
  'Series B',
  'Series C+',
  'Growth',
  'Profitable'
];

const CURRENCIES = [
  'USD', 'EUR', 'GBP', 'INR', 'CAD', 'AUD', 'SGD', 'JPY',
  'AED', 'CHF', 'CNY', 'HKD', 'NZD', 'SEK', 'NOK', 'DKK',
  'BRL', 'MXN', 'ZAR', 'KRW', 'THB', 'IDR', 'MYR', 'PHP',
  'TWD', 'ILS', 'PLN', 'CZK', 'HUF', 'TRY', 'RON', 'BGN', 'ISK',
];

const CURRENCY_LABELS: Record<string, string> = {
  USD: '$ USD', EUR: '\u20ac EUR', GBP: '\u00a3 GBP', INR: '\u20b9 INR',
  CAD: 'C$ CAD', AUD: 'A$ AUD', SGD: 'S$ SGD', JPY: '\u00a5 JPY',
  AED: 'AED', CHF: 'CHF', CNY: '\u00a5 CNY', HKD: 'HK$ HKD',
  NZD: 'NZ$ NZD', SEK: 'kr SEK', NOK: 'kr NOK', DKK: 'kr DKK',
  BRL: 'R$ BRL', MXN: 'MX$ MXN', ZAR: 'R ZAR', KRW: '\u20a9 KRW',
  THB: '\u0e3f THB', IDR: 'Rp IDR', MYR: 'RM MYR', PHP: '\u20b1 PHP',
  TWD: 'NT$ TWD', ILS: '\u20aa ILS', PLN: 'z\u0142 PLN', CZK: 'K\u010d CZK',
  HUF: 'Ft HUF', TRY: '\u20ba TRY', RON: 'lei RON', BGN: '\u043b\u0432 BGN',
  ISK: 'kr ISK',
};

export function CompanySwitcher() {
  const { currentCompany, setCurrentCompany } = useFounderStore();
  const { data: companies, isLoading } = useCompanies();
  const updateCompany = useUpdateCompany();
  const deleteCompany = useDeleteCompany();
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [, navigate] = useLocation();
  
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  
  const [editForm, setEditForm] = useState({
    name: '',
    website: '',
    industry: '',
    stage: '',
    currency: 'USD',
  });

  if (isLoading) {
    return <Skeleton className="h-9 w-40" />;
  }

  const companyList = (companies || []) as Company[];

  const handleEditClick = (e: React.MouseEvent, company: Company) => {
    e.stopPropagation();
    setSelectedCompany(company);
    setEditForm({
      name: company.name,
      website: company.website || '',
      industry: company.industry || '',
      stage: company.stage || '',
      currency: company.currency || 'USD',
    });
    setEditDialogOpen(true);
    setOpen(false);
  };

  const handleDeleteClick = (e: React.MouseEvent, company: Company) => {
    e.stopPropagation();
    setSelectedCompany(company);
    setDeleteDialogOpen(true);
    setOpen(false);
  };

  const handleEditSubmit = async () => {
    if (!selectedCompany) return;
    
    if (!editForm.name.trim()) {
      toast({ title: 'Error', description: 'Company name is required', variant: 'destructive' });
      return;
    }
    
    try {
      await updateCompany.mutateAsync({
        id: selectedCompany.id,
        data: {
          name: editForm.name.trim(),
          website: editForm.website.trim() || undefined,
          industry: editForm.industry || undefined,
          stage: editForm.stage || undefined,
          currency: editForm.currency,
        },
      });
      toast({ title: 'Success', description: 'Company updated successfully' });
      setEditDialogOpen(false);
      setSelectedCompany(null);
    } catch (err) {
      toast({ title: 'Error', description: 'Failed to update company', variant: 'destructive' });
    }
  };

  const handleDeleteConfirm = async () => {
    if (!selectedCompany) return;
    
    try {
      await deleteCompany.mutateAsync(selectedCompany.id);
      toast({ title: 'Success', description: 'Company deleted successfully' });
      setDeleteDialogOpen(false);
      setSelectedCompany(null);
    } catch (err) {
      toast({ title: 'Error', description: 'Failed to delete company', variant: 'destructive' });
    }
  };

  return (
    <>
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
        <DropdownMenuContent align="start" className="w-64 max-h-80 overflow-y-auto">
          <DropdownMenuItem
            onClick={() => {
              setOpen(false);
              navigate('/onboarding');
            }}
            className="text-primary font-medium"
            data-testid="button-add-company"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add New Company
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuLabel>Your Companies</DropdownMenuLabel>
          {companyList.length === 0 ? (
            <DropdownMenuItem disabled>
              <span className="text-muted-foreground">No companies yet</span>
            </DropdownMenuItem>
          ) : (
            (() => {
              const seen = new Set<string>();
              return companyList.filter((company) => {
                const key = company.name?.toLowerCase() || '';
                if (seen.has(key) && company.id !== currentCompany?.id) return false;
                seen.add(key);
                return true;
              }).map((company) => (
              <DropdownMenuItem
                key={company.id}
                onClick={() => {
                  setCurrentCompany(company);
                  setOpen(false);
                }}
                className="justify-between group"
                data-testid={`company-option-${company.id}`}
              >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <Building2 className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <span className="truncate">{company.name}</span>
                  {currentCompany?.id === company.id && (
                    <Check className="h-4 w-4 text-primary flex-shrink-0" />
                  )}
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={(e) => handleEditClick(e, company)}
                    data-testid={`button-edit-company-${company.id}`}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                    onClick={(e) => handleDeleteClick(e, company)}
                    data-testid={`button-delete-company-${company.id}`}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </DropdownMenuItem>
            ));
            })()
          )}
        </DropdownMenuContent>

      </DropdownMenu>

      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Edit Company</DialogTitle>
            <DialogDescription>
              Update your company information below.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-name">Company Name *</Label>
              <Input
                id="edit-name"
                value={editForm.name}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                placeholder="Enter company name"
                data-testid="input-edit-company-name"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-website">Website</Label>
              <Input
                id="edit-website"
                value={editForm.website}
                onChange={(e) => setEditForm({ ...editForm, website: e.target.value })}
                placeholder="https://example.com"
                data-testid="input-edit-company-website"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-industry">Industry</Label>
              <Select
                value={editForm.industry}
                onValueChange={(value) => setEditForm({ ...editForm, industry: value })}
              >
                <SelectTrigger data-testid="select-edit-company-industry">
                  <SelectValue placeholder="Select industry" />
                </SelectTrigger>
                <SelectContent>
                  {INDUSTRIES.map((industry) => (
                    <SelectItem key={industry} value={industry}>
                      {industry}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-stage">Stage</Label>
              <Select
                value={editForm.stage}
                onValueChange={(value) => setEditForm({ ...editForm, stage: value })}
              >
                <SelectTrigger data-testid="select-edit-company-stage">
                  <SelectValue placeholder="Select stage" />
                </SelectTrigger>
                <SelectContent>
                  {STAGES.map((stage) => (
                    <SelectItem key={stage} value={stage}>
                      {stage}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-currency">Currency</Label>
              <Select
                value={editForm.currency}
                onValueChange={(value) => setEditForm({ ...editForm, currency: value })}
              >
                <SelectTrigger data-testid="select-edit-company-currency">
                  <SelectValue placeholder="Select currency" />
                </SelectTrigger>
                <SelectContent>
                  {CURRENCIES.map((currency) => (
                    <SelectItem key={currency} value={currency}>
                      {CURRENCY_LABELS[currency] || currency}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setEditDialogOpen(false)}
              data-testid="button-cancel-edit"
            >
              Cancel
            </Button>
            <Button
              onClick={handleEditSubmit}
              disabled={updateCompany.isPending}
              data-testid="button-save-company"
            >
              {updateCompany.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Company</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{selectedCompany?.name}</strong>? 
              This will permanently remove all associated data including financial records, 
              scenarios, simulations, and Truth Scans. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="button-cancel-delete">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteCompany.isPending}
              data-testid="button-confirm-delete"
            >
              {deleteCompany.isPending ? 'Deleting...' : 'Delete Company'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

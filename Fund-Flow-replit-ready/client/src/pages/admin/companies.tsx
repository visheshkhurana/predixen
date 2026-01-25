import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Building2, ExternalLink, Search, Filter, Eye } from 'lucide-react';
import { api } from '@/api/client';
import { 
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription 
} from '@/components/ui/dialog';
import { format } from 'date-fns';

function CompanyDetailModal({ company, open, onClose }: { company: any | null; open: boolean; onClose: () => void }) {
  if (!company) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-primary" />
            {company.name}
          </DialogTitle>
          <DialogDescription>Company details and information</DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Industry</p>
              <p className="font-medium">{company.industry || 'Not specified'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Stage</p>
              <p className="font-medium">{company.stage || 'Not specified'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Owner</p>
              <p className="font-medium">{company.user_email}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Created</p>
              <p className="font-medium">{format(new Date(company.created_at), 'MMM d, yyyy')}</p>
            </div>
          </div>
          
          {company.description && (
            <div>
              <p className="text-sm text-muted-foreground">Description</p>
              <p className="font-medium">{company.description}</p>
            </div>
          )}
        </div>
        
        <div className="flex justify-end">
          <Button variant="outline" onClick={onClose}>Close</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function AdminCompanies() {
  const [searchQuery, setSearchQuery] = useState('');
  const [stageFilter, setStageFilter] = useState<string>('all');
  const [industryFilter, setIndustryFilter] = useState<string>('all');
  const [selectedCompany, setSelectedCompany] = useState<any | null>(null);

  const { data: companies, isLoading } = useQuery({
    queryKey: ['/admin/companies'],
    queryFn: () => api.admin.companies.list(),
  });

  const getStageColor = (stage: string | null) => {
    switch (stage?.toLowerCase()) {
      case 'seed':
        return 'bg-green-500';
      case 'series a':
        return 'bg-blue-500';
      case 'series b':
        return 'bg-purple-500';
      case 'series c':
        return 'bg-orange-500';
      default:
        return 'bg-gray-500';
    }
  };

  const uniqueStages = Array.from(new Set(companies?.map(c => c.stage).filter(Boolean) || []));
  const uniqueIndustries = Array.from(new Set(companies?.map(c => c.industry).filter(Boolean) || []));

  const filteredCompanies = companies?.filter((company) => {
    const matchesSearch = company.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (company.user_email?.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesStage = stageFilter === 'all' || company.stage === stageFilter;
    const matchesIndustry = industryFilter === 'all' || company.industry === industryFilter;
    return matchesSearch && matchesStage && matchesIndustry;
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
          <Building2 className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Company Management</h1>
          <p className="text-muted-foreground text-sm">View and manage all registered companies</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Companies</p>
                <p className="text-2xl font-bold">{companies?.length ?? 0}</p>
              </div>
              <Building2 className="h-8 w-8 text-muted-foreground/50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Industries</p>
                <p className="text-2xl font-bold">{uniqueIndustries.length}</p>
              </div>
              <Filter className="h-8 w-8 text-muted-foreground/50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Stages</p>
                <p className="text-2xl font-bold">{uniqueStages.length}</p>
              </div>
              <Filter className="h-8 w-8 text-muted-foreground/50" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <CardTitle>All Companies ({filteredCompanies?.length ?? 0})</CardTitle>
              <CardDescription>Search and filter registered companies</CardDescription>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input 
                  placeholder="Search companies..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 w-56"
                  data-testid="input-search-companies"
                />
              </div>
              <Select value={stageFilter} onValueChange={setStageFilter}>
                <SelectTrigger className="w-32" data-testid="select-filter-stage">
                  <SelectValue placeholder="Stage" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Stages</SelectItem>
                  {uniqueStages.map((stage) => (
                    <SelectItem key={stage} value={stage!}>{stage}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={industryFilter} onValueChange={setIndustryFilter}>
                <SelectTrigger className="w-36" data-testid="select-filter-industry">
                  <SelectValue placeholder="Industry" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Industries</SelectItem>
                  {uniqueIndustries.map((industry) => (
                    <SelectItem key={industry} value={industry!}>{industry}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full" data-testid="table-companies">
                <thead>
                  <tr className="border-b text-left">
                    <th className="p-3 font-medium text-muted-foreground">Name</th>
                    <th className="p-3 font-medium text-muted-foreground">Industry</th>
                    <th className="p-3 font-medium text-muted-foreground">Stage</th>
                    <th className="p-3 font-medium text-muted-foreground">Owner</th>
                    <th className="p-3 font-medium text-muted-foreground">Created</th>
                    <th className="p-3 font-medium text-muted-foreground text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCompanies?.map((company) => (
                    <tr key={company.id} className="border-b hover:bg-muted/50 transition-colors" data-testid={`row-company-${company.id}`}>
                      <td className="p-3 font-medium">{company.name}</td>
                      <td className="p-3 text-muted-foreground">{company.industry || '-'}</td>
                      <td className="p-3">
                        {company.stage ? (
                          <Badge className={`${getStageColor(company.stage)} text-white`}>
                            {company.stage}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </td>
                      <td className="p-3 text-muted-foreground text-sm">{company.user_email}</td>
                      <td className="p-3 text-muted-foreground text-sm">
                        {format(new Date(company.created_at), 'MMM d, yyyy')}
                      </td>
                      <td className="p-3 text-right">
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => setSelectedCompany(company)}
                          data-testid={`button-view-${company.id}`}
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          View
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              
              {filteredCompanies?.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <Building2 className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No companies found</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <CompanyDetailModal 
        company={selectedCompany} 
        open={!!selectedCompany} 
        onClose={() => setSelectedCompany(null)} 
      />
    </div>
  );
}

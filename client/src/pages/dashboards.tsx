import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLocation } from 'wouter';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog';
import { useFounderStore } from '@/store/founderStore';
import { useToast } from '@/hooks/use-toast';
import { apiRequest } from '@/lib/queryClient';
import {
  Plus,
  LayoutDashboard,
  MoreVertical,
  Trash2,
  Edit,
  Eye,
  Grid3X3,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface Dashboard {
  id: number;
  company_id: number;
  name: string;
  description: string | null;
  layout_config: Record<string, unknown> | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export default function DashboardsPage() {
  const [, setLocation] = useLocation();
  const { currentCompany } = useFounderStore();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');

  const { data: dashboards = [], isLoading } = useQuery<Dashboard[]>({
    queryKey: [`/api/dashboards?company_id=${currentCompany?.id}`],
    enabled: !!currentCompany,
  });

  const createMutation = useMutation({
    mutationFn: async (data: { name: string; description: string }) => {
      const res = await apiRequest('POST', `/api/dashboards?company_id=${currentCompany?.id}`, data);
      return res.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: [`/api/dashboards?company_id=${currentCompany?.id}`] });
      setCreateOpen(false);
      setNewName('');
      setNewDescription('');
      toast({ title: 'Dashboard created', description: 'Your new dashboard is ready.' });
      setLocation(`/dashboard/${data.id}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await apiRequest('DELETE', `/api/dashboards/${id}`);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/dashboards?company_id=${currentCompany?.id}`] });
      toast({ title: 'Dashboard deleted' });
    },
  });

  const handleCreate = () => {
    if (!newName.trim()) {
      toast({ title: 'Enter a name', variant: 'destructive' });
      return;
    }
    createMutation.mutate({ name: newName, description: newDescription });
  };

  if (!currentCompany) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            Please select a company first
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">KPI Dashboards</h1>
          <p className="text-muted-foreground">Create custom dashboards to monitor your key metrics</p>
        </div>
        <Button onClick={() => setCreateOpen(true)} data-testid="button-create-dashboard">
          <Plus className="h-4 w-4 mr-2" />
          New Dashboard
        </Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      ) : dashboards.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <LayoutDashboard className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="font-semibold text-lg mb-2">No dashboards yet</h3>
            <p className="text-muted-foreground mb-4">Create your first dashboard to start tracking KPIs</p>
            <Button onClick={() => setCreateOpen(true)} data-testid="button-create-first-dashboard">
              <Plus className="h-4 w-4 mr-2" />
              Create Dashboard
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {dashboards.map(dashboard => (
            <Card 
              key={dashboard.id} 
              className="hover-elevate cursor-pointer"
              onClick={() => setLocation(`/dashboard/${dashboard.id}`)}
              data-testid={`dashboard-card-${dashboard.id}`}
            >
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Grid3X3 className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-base">{dashboard.name}</CardTitle>
                      {dashboard.is_default && (
                        <Badge variant="outline" className="text-xs mt-1">Default</Badge>
                      )}
                    </div>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                      <Button variant="ghost" size="icon" className="h-8 w-8" data-testid={`button-menu-${dashboard.id}`}>
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={(e) => { e.stopPropagation(); setLocation(`/dashboard/${dashboard.id}`); }}>
                        <Eye className="h-4 w-4 mr-2" />
                        View
                      </DropdownMenuItem>
                      <DropdownMenuItem 
                        className="text-destructive" 
                        onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(dashboard.id); }}
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {dashboard.description || 'No description'}
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  Updated {new Date(dashboard.updated_at).toLocaleDateString()}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Dashboard</DialogTitle>
            <DialogDescription>
              Create a new dashboard to track your key metrics
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Name</label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g., Executive Summary"
                data-testid="input-dashboard-name"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Description (optional)</label>
              <Input
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="What metrics will this dashboard track?"
                data-testid="input-dashboard-description"
              />
            </div>
          </div>

          <DialogFooter>
            <DialogClose asChild>
              <Button variant="ghost" data-testid="button-cancel-create">Cancel</Button>
            </DialogClose>
            <Button onClick={handleCreate} disabled={createMutation.isPending} data-testid="button-confirm-create">
              {createMutation.isPending ? 'Creating...' : 'Create Dashboard'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

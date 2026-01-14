import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Building2, ExternalLink } from 'lucide-react';
import { api } from '@/api/client';
import { Link } from 'wouter';

export default function AdminCompanies() {
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

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Building2 className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Company Management</h1>
          <p className="text-muted-foreground">View and manage all registered companies</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Companies ({companies?.length ?? 0})</CardTitle>
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
                    <th className="p-3 font-medium">Name</th>
                    <th className="p-3 font-medium">Industry</th>
                    <th className="p-3 font-medium">Stage</th>
                    <th className="p-3 font-medium">Owner</th>
                    <th className="p-3 font-medium">Created</th>
                    <th className="p-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {companies?.map((company) => (
                    <tr key={company.id} className="border-b" data-testid={`row-company-${company.id}`}>
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
                        {new Date(company.created_at).toLocaleDateString()}
                      </td>
                      <td className="p-3">
                        <Link href={`/dashboard`}>
                          <a className="text-primary hover:underline flex items-center gap-1" data-testid={`link-view-${company.id}`}>
                            <ExternalLink className="h-4 w-4" />
                            View
                          </a>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

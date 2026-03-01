import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ConnectorCard } from "@/components/connectors/ConnectorCard";
import { ConnectorFilters } from "@/components/connectors/ConnectorFilters";
import { ConnectorDetailDrawer } from "@/components/connectors/ConnectorDetailDrawer";
import { fetchConnectorCatalog, fetchCategories, CatalogConnector, Category } from "@/services/connectors.api";
import { useFounderStore } from "@/store/founderStore";
import { 
  Link2, 
  Sparkles, 
  Shield, 
  Zap, 
  ArrowRight,
  Database,
  TrendingUp
} from "lucide-react";

export default function ConnectorMarketplace() {
  const [, setLocation] = useLocation();
  const { currentCompany } = useFounderStore();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    nativeOnly: false,
    realtimeOnly: false,
    installedOnly: false,
  });
  const [selectedConnector, setSelectedConnector] = useState<CatalogConnector | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  
  const { data: connectors = [], isLoading: connectorsLoading } = useQuery({
    queryKey: ["/api/connectors/catalog", currentCompany?.id],
    queryFn: () => fetchConnectorCatalog({ companyId: currentCompany?.id }),
    staleTime: 5 * 60 * 1000,
  });
  
  const { data: categories = [] } = useQuery({
    queryKey: ["/api/connectors/categories"],
    queryFn: fetchCategories,
    staleTime: 5 * 60 * 1000,
  });
  
  const filteredConnectors = useMemo(() => {
    let result = [...connectors];
    
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(c => 
        c.name.toLowerCase().includes(query) ||
        c.description.toLowerCase().includes(query) ||
        c.category.toLowerCase().includes(query)
      );
    }
    
    if (selectedCategory) {
      result = result.filter(c => c.category === selectedCategory);
    }
    
    if (filters.nativeOnly) {
      result = result.filter(c => c.native);
    }
    
    if (filters.realtimeOnly) {
      result = result.filter(c => c.typicalRefresh === "real-time");
    }
    
    if (filters.installedOnly) {
      result = result.filter(c => c.installStatus?.status === "active" || c.installStatus?.status === "paused");
    }
    
    result.sort((a, b) => {
      const aInstalled = a.installStatus?.status === "active" || a.installStatus?.status === "paused";
      const bInstalled = b.installStatus?.status === "active" || b.installStatus?.status === "paused";
      if (aInstalled !== bInstalled) return bInstalled ? 1 : -1;
      if (a.native !== b.native) return b.native ? 1 : -1;
      return a.popularityRank - b.popularityRank;
    });
    
    return result;
  }, [connectors, searchQuery, selectedCategory, filters]);
  
  const installedCount = connectors.filter(c => 
    c.installStatus?.status === "active" || c.installStatus?.status === "paused"
  ).length;
  
  const handleConnect = (connectorId: string) => {
    setLocation(`/add-data-source?connector=${connectorId}`);
  };
  
  const handleManage = (connectorId: string) => {
    setLocation(`/data-source/${connectorId}`);
  };
  
  const handleCardClick = (connector: CatalogConnector) => {
    setSelectedConnector(connector);
    setDrawerOpen(true);
  };
  
  const handleFilterChange = (key: keyof typeof filters, value: boolean) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };
  
  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6" data-testid="connector-marketplace-page">
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Link2 className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" data-testid="text-page-title">Connect Your Data</h1>
            <p className="text-muted-foreground">
              Connect FounderConsole to the tools you already use
            </p>
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-full bg-primary/10">
                <Database className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{connectors.length}</p>
                <p className="text-sm text-muted-foreground">Available Connectors</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-emerald-500/5 to-emerald-500/10 border-emerald-500/20">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-full bg-emerald-500/10">
                <TrendingUp className="h-5 w-5 text-emerald-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{installedCount}</p>
                <p className="text-sm text-muted-foreground">Connected Sources</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-blue-500/5 to-blue-500/10 border-blue-500/20">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-full bg-blue-500/10">
                <Sparkles className="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{connectors.filter(c => c.native).length}</p>
                <p className="text-sm text-muted-foreground">Native Integrations</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-lg">Find Connectors</CardTitle>
          <CardDescription>
            Search and filter to find the right integrations for your business
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ConnectorFilters
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            selectedCategory={selectedCategory}
            onCategoryChange={setSelectedCategory}
            categories={categories}
            filters={filters}
            onFilterChange={handleFilterChange}
          />
        </CardContent>
      </Card>
      
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {filteredConnectors.length} of {connectors.length} connectors
          </p>
        </div>
        
        {connectorsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Card key={i} className="p-4">
                <div className="flex items-start gap-4">
                  <Skeleton className="h-12 w-12 rounded-lg" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-5 w-32" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-2/3" />
                  </div>
                  <Skeleton className="h-9 w-20" />
                </div>
              </Card>
            ))}
          </div>
        ) : filteredConnectors.length === 0 ? (
          <Card className="p-8 text-center">
            <Database className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="font-semibold mb-2">No connectors found</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Try adjusting your search or filters
            </p>
            <Button variant="outline" onClick={() => {
              setSearchQuery("");
              setSelectedCategory(null);
              setFilters({ nativeOnly: false, realtimeOnly: false, installedOnly: false });
            }}>
              Clear Filters
            </Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredConnectors.map((connector) => (
              <div 
                key={connector.id} 
                onClick={() => handleCardClick(connector)}
                className="cursor-pointer"
              >
                <ConnectorCard
                  connector={connector}
                  onConnect={handleConnect}
                  onManage={handleManage}
                />
              </div>
            ))}
          </div>
        )}
      </div>
      
      <Card className="bg-muted/30">
        <CardContent className="p-6">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-full bg-primary/10">
              <Shield className="h-6 w-6 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold mb-1">Secure by Design</h3>
              <p className="text-sm text-muted-foreground">
                All integrations use read-only access. Your data is encrypted at rest and in transit. 
                Raw data in your connected systems is never modified.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <ConnectorDetailDrawer
        connector={selectedConnector}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        onConnect={handleConnect}
      />
    </div>
  );
}

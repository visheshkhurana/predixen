import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Search, X, Filter, CheckCircle, Zap, Shield } from "lucide-react";

interface ConnectorFiltersProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  selectedCategory: string | null;
  onCategoryChange: (category: string | null) => void;
  categories: { name: string; count: number }[];
  filters: {
    nativeOnly: boolean;
    realtimeOnly: boolean;
    installedOnly: boolean;
  };
  onFilterChange: (key: keyof ConnectorFiltersProps["filters"], value: boolean) => void;
}

export function ConnectorFilters({
  searchQuery,
  onSearchChange,
  selectedCategory,
  onCategoryChange,
  categories,
  filters,
  onFilterChange,
}: ConnectorFiltersProps) {
  const hasActiveFilters = filters.nativeOnly || filters.realtimeOnly || filters.installedOnly || selectedCategory;
  
  const clearAllFilters = () => {
    onCategoryChange(null);
    onFilterChange("nativeOnly", false);
    onFilterChange("realtimeOnly", false);
    onFilterChange("installedOnly", false);
  };
  
  return (
    <div className="space-y-4">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search connectors..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-10 pr-10"
          data-testid="input-search-connectors"
        />
        {searchQuery && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
            onClick={() => onSearchChange("")}
            data-testid="button-clear-search"
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
      
      <div className="flex items-center gap-2 flex-wrap">
        <div className="flex items-center gap-1 text-sm text-muted-foreground mr-2">
          <Filter className="h-4 w-4" />
          Filters:
        </div>
        
        <Button
          variant={filters.installedOnly ? "default" : "outline"}
          size="sm"
          onClick={() => onFilterChange("installedOnly", !filters.installedOnly)}
          className="h-8"
          data-testid="filter-installed"
        >
          <CheckCircle className="h-3 w-3 mr-1" />
          Installed
        </Button>
        
        <Button
          variant={filters.nativeOnly ? "default" : "outline"}
          size="sm"
          onClick={() => onFilterChange("nativeOnly", !filters.nativeOnly)}
          className="h-8"
          data-testid="filter-native"
        >
          <Shield className="h-3 w-3 mr-1" />
          Native
        </Button>
        
        <Button
          variant={filters.realtimeOnly ? "default" : "outline"}
          size="sm"
          onClick={() => onFilterChange("realtimeOnly", !filters.realtimeOnly)}
          className="h-8"
          data-testid="filter-realtime"
        >
          <Zap className="h-3 w-3 mr-1" />
          Real-time
        </Button>
        
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearAllFilters}
            className="h-8 text-muted-foreground"
            data-testid="button-clear-filters"
          >
            <X className="h-3 w-3 mr-1" />
            Clear all
          </Button>
        )}
      </div>
      
      <div className="flex items-center gap-2 flex-wrap">
        <Badge
          variant={selectedCategory === null ? "default" : "outline"}
          className="cursor-pointer hover-elevate"
          onClick={() => onCategoryChange(null)}
          data-testid="category-all"
        >
          All ({categories.reduce((sum, c) => sum + c.count, 0)})
        </Badge>
        
        {categories.map((category) => (
          <Badge
            key={category.name}
            variant={selectedCategory === category.name ? "default" : "outline"}
            className="cursor-pointer hover-elevate"
            onClick={() => onCategoryChange(category.name)}
            data-testid={`category-${category.name.toLowerCase()}`}
          >
            {category.name} ({category.count})
          </Badge>
        ))}
      </div>
    </div>
  );
}

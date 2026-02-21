/**
 * UI Components Usage Examples
 *
 * This file demonstrates practical patterns for using the new UI improvement components
 * in real-world scenarios. Copy and adapt these patterns for your pages.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

// Skeleton Loaders
import {
  TableSkeleton,
  CardSkeleton,
  ChartSkeleton,
  MetricGridSkeleton,
  ListSkeleton,
} from '@/components/ui/skeleton-loaders';

// Empty States
import {
  EmptyTable,
  EmptyChart,
  EmptyList,
  EmptySearch,
} from '@/components/ui/empty-states';

// State Management
import { StateRenderer } from '@/components/StateRenderer';
import { useLoadingState } from '@/hooks/useLoadingState';

// Icons
import { Plus, Upload, TrendingUp, Database } from 'lucide-react';

// ============================================================================
// PATTERN 1: Simple Loading + Empty + Content (Direct Conditional)
// ============================================================================

/**
 * Basic pattern - useful for single data source pages
 * Shows skeleton while loading, empty state if no data, content otherwise
 */
export function ExamplePattern1_BasicPage() {
  // Simulated data fetch
  const { data: items = [], isLoading, error } = useQuery({
    queryKey: ['items'],
    queryFn: async () => {
      // Your API call here
      return [];
    },
  });

  const isEmpty = !isLoading && items.length === 0;

  return (
    <div className="p-6">
      {isLoading && <TableSkeleton rows={5} columns={4} />}

      {isEmpty && (
        <EmptyTable
          title="No Items Yet"
          description="Create your first item to get started"
          action={{
            label: 'Create New',
            onClick: () => console.log('Create clicked'),
            icon: Plus,
          }}
        />
      )}

      {!isLoading && !isEmpty && (
        <div>
          {items.map((item: any) => (
            <div key={item.id}>{item.name}</div>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// PATTERN 2: Using StateRenderer Component (Cleaner)
// ============================================================================

/**
 * StateRenderer reduces boilerplate - pass it states and renderers
 * Best for when you want clean, readable JSX
 */
export function ExamplePattern2_StateRenderer() {
  const { data: metrics = [], isLoading, error } = useQuery({
    queryKey: ['metrics'],
    queryFn: async () => {
      return [];
    },
  });

  return (
    <StateRenderer
      isLoading={isLoading}
      data={metrics}
      error={error}
      skeleton={<MetricGridSkeleton count={6} />}
      empty={
        <EmptyChart
          title="No Metrics Available"
          description="Add some metrics to your dashboard"
        />
      }
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {metrics.map((metric: any) => (
          <div key={metric.id} className="p-4 border rounded">
            {metric.name}
          </div>
        ))}
      </div>
    </StateRenderer>
  );
}

// ============================================================================
// PATTERN 3: Using useLoadingState Hook (Most Flexible)
// ============================================================================

/**
 * useLoadingState hook - gives you fine control over each state
 * Best when you need custom styling or complex conditional logic
 */
export function ExamplePattern3_useLoadingStateHook() {
  const { data: items = [], isLoading, error } = useQuery({
    queryKey: ['items'],
    queryFn: async () => {
      return [];
    },
  });

  const { shouldShowSkeleton, shouldShowEmpty, shouldShowContent } =
    useLoadingState({
      isLoading,
      data: items,
      error,
    });

  return (
    <div className="space-y-4">
      {shouldShowSkeleton && (
        <div>
          <p className="mb-2 text-sm font-medium">Loading data...</p>
          <ListSkeleton items={6} variant="detailed" />
        </div>
      )}

      {shouldShowEmpty && (
        <div className="p-8">
          <EmptyList
            title="No Results"
            description="Try adjusting your filters"
            action={{
              label: 'Reset Filters',
              onClick: () => console.log('Reset'),
            }}
            compact={true}
          />
        </div>
      )}

      {shouldShowContent && (
        <div className="space-y-2">
          {items.map((item: any) => (
            <div key={item.id} className="p-3 border rounded">
              {item.name}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// PATTERN 4: Multiple Data Sources (Dashboard with Multiple Sections)
// ============================================================================

/**
 * Pattern for pages with multiple independent data sources
 * Each section can load independently, good for dashboards
 */
export function ExamplePattern4_MultipleSections() {
  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['overview'],
    queryFn: async () => null,
  });

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: async () => [],
  });

  const { data: recentActivity, isLoading: activityLoading } = useQuery({
    queryKey: ['activity'],
    queryFn: async () => [],
  });

  return (
    <div className="space-y-6">
      {/* Overview Section */}
      <StateRenderer
        isLoading={overviewLoading}
        data={overview}
        skeleton={<CardSkeleton variant="large" />}
        empty={<EmptyChart title="Overview Not Available" height={200} />}
      >
        <div className="p-4 border rounded">Overview Content</div>
      </StateRenderer>

      {/* Metrics Section */}
      <div>
        <h2 className="mb-4 text-lg font-semibold">Key Metrics</h2>
        <StateRenderer
          isLoading={metricsLoading}
          data={metrics}
          skeleton={<MetricGridSkeleton count={4} />}
          empty={
            <EmptyTable
              title="No Metrics"
              description="Configure your metrics in settings"
            />
          }
        >
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {metrics.map((m: any) => (
              <div key={m.id} className="p-4 border rounded">
                {m.name}
              </div>
            ))}
          </div>
        </StateRenderer>
      </div>

      {/* Activity Section */}
      <div>
        <h2 className="mb-4 text-lg font-semibold">Recent Activity</h2>
        <StateRenderer
          isLoading={activityLoading}
          data={recentActivity}
          skeleton={<ListSkeleton items={5} variant="detailed" />}
          empty={
            <EmptyList
              title="No Activity Yet"
              description="Activity will appear here"
              compact={true}
            />
          }
        >
          <div className="space-y-2">
            {recentActivity.map((a: any) => (
              <div key={a.id} className="p-3 border rounded">
                {a.title}
              </div>
            ))}
          </div>
        </StateRenderer>
      </div>
    </div>
  );
}

// ============================================================================
// PATTERN 5: Search Results with Custom Empty State
// ============================================================================

/**
 * Pattern for search results - shows different empty state based on context
 */
export function ExamplePattern5_SearchResults() {
  const [searchQuery, setSearchQuery] = useState('');
  const { data: results = [], isLoading } = useQuery({
    queryKey: ['search', searchQuery],
    queryFn: async () => {
      // Search API call
      return [];
    },
    enabled: searchQuery.length > 0,
  });

  const isEmpty = !isLoading && searchQuery && results.length === 0;

  return (
    <div className="space-y-4">
      <input
        type="text"
        placeholder="Search..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="w-full p-2 border rounded"
      />

      {isLoading && <ListSkeleton items={4} />}

      {isEmpty && (
        <EmptySearch
          title="No Results Found"
          searchQuery={searchQuery}
          description="Try different search terms or filters"
          action={{
            label: 'Clear Search',
            onClick: () => setSearchQuery(''),
          }}
        />
      )}

      {!isLoading && !isEmpty && searchQuery && (
        <div className="space-y-2">
          {results.map((r: any) => (
            <div key={r.id} className="p-3 border rounded">
              {r.name}
            </div>
          ))}
        </div>
      )}

      {!searchQuery && (
        <EmptyList
          title="Enter a search term"
          description="Type above to search"
          compact={true}
        />
      )}
    </div>
  );
}

// ============================================================================
// PATTERN 6: Data Table with Loading and Empty States
// ============================================================================

/**
 * Pattern for data tables - mimics table structure in empty state
 */
export function ExamplePattern6_DataTable() {
  const { data: rows = [], isLoading } = useQuery({
    queryKey: ['table'],
    queryFn: async () => {
      return [];
    },
  });

  return (
    <StateRenderer
      isLoading={isLoading}
      data={rows}
      skeleton={<TableSkeleton rows={8} columns={5} />}
      empty={
        <EmptyTable
          title="No Data"
          description="Add your first record to get started"
          columnCount={5}
          action={{
            label: 'Add Record',
            onClick: () => console.log('Add clicked'),
            icon: Plus,
          }}
        />
      }
    >
      <div className="border rounded overflow-x-auto">
        <table className="w-full">
          <thead className="bg-muted/50 border-b">
            <tr>
              <th className="p-3 text-left text-sm font-medium">Name</th>
              <th className="p-3 text-left text-sm font-medium">Status</th>
              <th className="p-3 text-left text-sm font-medium">Date</th>
              <th className="p-3 text-left text-sm font-medium">Value</th>
              <th className="p-3 text-left text-sm font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row: any) => (
              <tr key={row.id} className="border-b hover:bg-muted/30">
                <td className="p-3">{row.name}</td>
                <td className="p-3">{row.status}</td>
                <td className="p-3">{row.date}</td>
                <td className="p-3">{row.value}</td>
                <td className="p-3">
                  <button className="text-sm text-primary hover:underline">
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </StateRenderer>
  );
}

// ============================================================================
// PATTERN 7: Chart with Dynamic Height and Empty State
// ============================================================================

/**
 * Pattern for charts - empty state respects chart height
 */
export function ExamplePattern7_Chart() {
  const { data: chartData = [], isLoading } = useQuery({
    queryKey: ['chart'],
    queryFn: async () => {
      return [];
    },
  });

  return (
    <StateRenderer
      isLoading={isLoading}
      data={chartData}
      skeleton={<ChartSkeleton height={400} />}
      empty={
        <EmptyChart
          title="No Data Available"
          description="Configure data sources to see the chart"
          height={400}
          action={{
            label: 'Configure Data',
            onClick: () => console.log('Configure'),
            icon: Upload,
          }}
        />
      }
    >
      <div className="h-96 border rounded p-4">
        {/* Your chart library here (Recharts, Chart.js, etc.) */}
        Chart placeholder
      </div>
    </StateRenderer>
  );
}

// ============================================================================
// PATTERN 8: Form with Async Validation and Loading
// ============================================================================

/**
 * Pattern for forms with loading states during submission
 */
export function ExamplePattern8_FormWithLoading() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({ name: '', email: '' });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    // Simulate form submission
    await new Promise((resolve) => setTimeout(resolve, 2000));
    setIsSubmitting(false);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
      {isSubmitting ? (
        <div>
          <p className="mb-4">Submitting...</p>
          <FormSkeleton fields={2} showButton={true} />
        </div>
      ) : (
        <>
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              className="w-full p-2 border rounded"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) =>
                setFormData({ ...formData, email: e.target.value })
              }
              className="w-full p-2 border rounded"
            />
          </div>
          <button
            type="submit"
            className="w-full p-2 bg-primary text-white rounded hover:bg-primary/90"
          >
            Submit
          </button>
        </>
      )}
    </form>
  );
}

// ============================================================================
// EXPORT FOR REFERENCE
// ============================================================================

export const EXAMPLES = [
  {
    name: 'Pattern 1: Basic Page',
    component: ExamplePattern1_BasicPage,
    description:
      'Simple conditional rendering with inline conditions - good for simple pages',
  },
  {
    name: 'Pattern 2: StateRenderer',
    component: ExamplePattern2_StateRenderer,
    description: 'Using StateRenderer component - cleaner JSX, recommended',
  },
  {
    name: 'Pattern 3: useLoadingState Hook',
    component: ExamplePattern3_useLoadingStateHook,
    description:
      'Using the hook directly - most flexible, best for custom logic',
  },
  {
    name: 'Pattern 4: Multiple Sections',
    component: ExamplePattern4_MultipleSections,
    description: 'Multiple independent data sources - typical dashboard layout',
  },
  {
    name: 'Pattern 5: Search Results',
    component: ExamplePattern5_SearchResults,
    description:
      'Search with context-aware empty states - shows different messages',
  },
  {
    name: 'Pattern 6: Data Table',
    component: ExamplePattern6_DataTable,
    description:
      'Table with matching empty state structure - maintains layout consistency',
  },
  {
    name: 'Pattern 7: Chart',
    component: ExamplePattern7_Chart,
    description: 'Chart with dynamic height empty state - respects chart space',
  },
  {
    name: 'Pattern 8: Form Loading',
    component: ExamplePattern8_FormWithLoading,
    description: 'Async form submission with loading state',
  },
];

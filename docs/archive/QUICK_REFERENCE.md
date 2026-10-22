# FounderConsole UI Improvements - Quick Reference Card

## Files Overview

| File | Purpose | Lines |
|------|---------|-------|
| `client/src/components/ui/skeleton-loaders.tsx` | 7 skeleton components | 514 |
| `client/src/components/ui/empty-states.tsx` | 6 empty state components | 428 |
| `client/src/components/GlobalLoadingBar.tsx` | Global progress bar | 46 |
| `client/src/hooks/useLoadingState.ts` | State management hooks | 97 |
| `client/src/components/StateRenderer.tsx` | State rendering helpers | 122 |
| `client/src/components/UI_USAGE_EXAMPLES.tsx` | 8 example patterns | 360 |
| `client/src/pages/overview.tsx` | Enhanced dashboard | Modified |
| `client/src/App.tsx` | Global bar integration | Modified |

## Components at a Glance

### Skeleton Loaders (Import from `@/components/ui/skeleton-loaders`)
```tsx
<TableSkeleton rows={5} columns={4} />
<CardSkeleton variant="standard" showChart={false} />
<ChartSkeleton height={300} />
<FormSkeleton fields={4} showButton={true} />
<MetricGridSkeleton count={6} />
<ListSkeleton items={5} variant="compact" />
<HeroSkeleton />
```

### Empty States (Import from `@/components/ui/empty-states`)
```tsx
<EmptyTable title="No data" columnCount={4} action={{...}} />
<EmptyChart title="No data" height={300} action={{...}} />
<EmptyList title="Nothing" description="text" action={{...}} />
<EmptySearch title="No results" searchQuery="term" />
<EmptyStateCard title="Title" variant="muted" compact={true} />
```

### State Hooks (Import from `@/hooks/useLoadingState`)
```tsx
const { shouldShowSkeleton, shouldShowEmpty, shouldShowContent } =
  useLoadingState({ isLoading, data, error });

const isAnyLoading = useAnyLoading(loading1, loading2);
const allLoaded = useAllLoaded(loading1, loading2);
const combined = useCombinedLoadingState([{...}, {...}]);
```

### Helper Components (Import from `@/components/StateRenderer`)
```tsx
<StateRenderer
  isLoading={loading}
  data={data}
  skeleton={<Skeleton />}
  empty={<Empty />}
>
  <Content />
</StateRenderer>

{renderState(state, {
  loading: <Skeleton />,
  empty: <Empty />,
  content: <Content />,
  error: <Error />,
})}

<RenderWhenReady states={[state1, state2]}>
  <Content />
</RenderWhenReady>
```

## Pattern 1: Simple (Direct Conditional)
```tsx
const { data, isLoading } = useQuery(...);
return (
  <>
    {isLoading && <Skeleton />}
    {!isLoading && !data?.length && <Empty />}
    {!isLoading && data?.length > 0 && <Content />}
  </>
);
```

## Pattern 2: StateRenderer (Recommended)
```tsx
return (
  <StateRenderer
    isLoading={isLoading}
    data={data}
    skeleton={<Skeleton />}
    empty={<Empty />}
  >
    <Content />
  </StateRenderer>
);
```

## Pattern 3: useLoadingState (Flexible)
```tsx
const state = useLoadingState({ isLoading, data, error });
return (
  <>
    {state.shouldShowSkeleton && <Skeleton />}
    {state.shouldShowEmpty && <Empty />}
    {state.shouldShowContent && <Content />}
  </>
);
```

## Common Props

### Skeleton Components
- `rows?: number` - Number of rows/items
- `columns?: number` - Number of columns
- `variant?: 'compact' | 'standard' | 'large'` - Size
- `showChart?: boolean` - Show chart-like content
- `height?: number` - Height in pixels
- `className?: string` - Additional CSS

### Empty States
- `title: string` - Title text (required)
- `description?: string` - Description text
- `icon?: LucideIcon` - Icon component
- `action?: { label, onClick, icon? }` - Primary button
- `secondaryAction?: { label, onClick }` - Secondary button
- `columnCount?: number` - Table columns
- `height?: number` - Chart height
- `variant?: 'default' | 'muted' | 'warning'` - Style variant
- `compact?: boolean` - Compact size
- `className?: string` - Additional CSS

## Global Features

### GlobalLoadingBar
- Already integrated in App.tsx
- Tracks React Query requests automatically
- Positioned at top of viewport
- Uses `useIsFetching()` from React Query
- **No setup needed**

### useLoadingState Hook Return
```tsx
{
  isLoading: boolean;
  isEmpty: boolean;
  hasError: boolean;
  hasData: boolean;
  shouldShowSkeleton: boolean;
  shouldShowEmpty: boolean;
  shouldShowContent: boolean;
}
```

## Integration Checklist

- [ ] Import skeleton/empty component
- [ ] Get `isLoading` and `data` from hook
- [ ] Choose pattern (1, 2, or 3)
- [ ] Implement conditional rendering
- [ ] Add action buttons to empty states
- [ ] Test loading state
- [ ] Test empty state
- [ ] Test with actual data

## Icon Examples (lucide-react)
```tsx
import {
  Plus,        // Add new item
  Upload,      // Upload data
  TrendingUp,  // Chart/analytics
  Database,    // Data/table
  List,        // Collections
  Search,      // Search results
  AlertCircle, // Search empty
  Zap,         // Loading/action
  ChevronRight,// Navigation
} from 'lucide-react';
```

## Quick Copy-Paste Templates

### Template 1: Table with Data
```tsx
import { useQuery } from '@tanstack/react-query';
import { StateRenderer } from '@/components/StateRenderer';
import { TableSkeleton } from '@/components/ui/skeleton-loaders';
import { EmptyTable } from '@/components/ui/empty-states';
import { Upload } from 'lucide-react';

export function MyTablePage() {
  const { data = [], isLoading } = useQuery(...);

  return (
    <StateRenderer
      isLoading={isLoading}
      data={data}
      skeleton={<TableSkeleton rows={8} columns={5} />}
      empty={
        <EmptyTable
          title="No records yet"
          description="Add your first record to get started"
          columnCount={5}
          action={{
            label: "Add Record",
            onClick: () => {},
            icon: Plus,
          }}
        />
      }
    >
      <table className="w-full">
        {/* Your table content */}
      </table>
    </StateRenderer>
  );
}
```

### Template 2: Chart with Data
```tsx
import { ChartSkeleton } from '@/components/ui/skeleton-loaders';
import { EmptyChart } from '@/components/ui/empty-states';
import { StateRenderer } from '@/components/StateRenderer';

export function MyChartPage() {
  const { data = [], isLoading } = useQuery(...);

  return (
    <StateRenderer
      isLoading={isLoading}
      data={data}
      skeleton={<ChartSkeleton height={400} />}
      empty={<EmptyChart title="No chart data" height={400} />}
    >
      <div className="h-96">{/* Your chart */}</div>
    </StateRenderer>
  );
}
```

### Template 3: Multiple Sections
```tsx
const section1 = useLoadingState({ isLoading: load1, data: data1 });
const section2 = useLoadingState({ isLoading: load2, data: data2 });

<>
  <StateRenderer {...}>
    <Section1 />
  </StateRenderer>
  <StateRenderer {...}>
    <Section2 />
  </StateRenderer>
</>
```

## Styling

- All components use Tailwind CSS
- Matches FounderConsole design system
- Dark mode compatible
- Responsive out of the box
- No hardcoded colors (uses theme variables)

## Performance Tips

1. Use `useMemo` for computed loading states
2. Lazy-load components with `lazy()` for initial page load
3. Use appropriate skeleton complexity (don't over-animate)
4. Cache queries with React Query's stale time settings
5. Test performance in dev tools

## Common Mistakes to Avoid

❌ Showing both skeleton and content
```tsx
// WRONG
{loading && <Skeleton />}
{!loading && <Content />}  // Could both be true momentarily
```

✅ Use conditional guards
```tsx
// RIGHT
{isLoading && <Skeleton />}
{!isLoading && hasData && <Content />}
```

---

❌ Empty state without CTA
```tsx
<EmptyTable title="No data" />  // User doesn't know what to do
```

✅ Provide actionable guidance
```tsx
<EmptyTable
  title="No data"
  description="Upload your data to get started"
  action={{
    label: "Upload Data",
    onClick: () => navigate('/upload'),
    icon: Upload,
  }}
/>
```

---

❌ Generic skeleton sizes
```tsx
<TableSkeleton />  // Uses defaults, might not match your layout
```

✅ Match your actual layout
```tsx
<TableSkeleton rows={10} columns={5} />  // Matches your 5-column table
```

## Documentation Links

- **Full Docs:** `/client/src/components/ui/UI_IMPROVEMENTS.md`
- **Examples:** `/client/src/components/UI_USAGE_EXAMPLES.tsx`
- **Summary:** `/UI_IMPROVEMENTS_SUMMARY.md`
- **This Reference:** `/QUICK_REFERENCE.md`

## Support

For issues or questions:
1. Check the examples in `UI_USAGE_EXAMPLES.tsx`
2. Review the full docs in `UI_IMPROVEMENTS.md`
3. Look at the Overview page implementation in `pages/overview.tsx`
4. Verify imports are correct (check file locations above)

---

**Version:** 1.0.0
**Date:** February 2025
**Status:** Production Ready

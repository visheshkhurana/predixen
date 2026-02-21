import React from 'react';
import { useLoadingState, LoadingStateConfig } from '@/hooks/useLoadingState';

/**
 * Component that handles conditional rendering of skeleton, empty, and content states
 * Reduces boilerplate for common loading patterns
 */

interface StateRendererProps extends LoadingStateConfig {
  skeleton: React.ReactNode;
  empty: React.ReactNode;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

/**
 * Renders different UI states based on loading and data conditions
 *
 * @example
 * <StateRenderer
 *   isLoading={isLoading}
 *   data={myData}
 *   error={error}
 *   skeleton={<TableSkeleton />}
 *   empty={<EmptyTable />}
 * >
 *   <ActualContent data={myData} />
 * </StateRenderer>
 */
export function StateRenderer({
  isLoading,
  data,
  error,
  isEmpty: customIsEmpty,
  skeleton,
  empty,
  children,
  fallback,
}: StateRendererProps) {
  const state = useLoadingState({
    isLoading,
    data,
    error,
    isEmpty: customIsEmpty,
  });

  if (state.shouldShowSkeleton) {
    return <>{skeleton}</>;
  }

  if (state.shouldShowEmpty) {
    return <>{empty}</>;
  }

  if (state.shouldShowContent) {
    return <>{children}</>;
  }

  // Error state or fallback
  if (state.hasError && fallback) {
    return <>{fallback}</>;
  }

  // Default fallback if error and no explicit fallback provided
  if (state.hasError) {
    return (
      <div className="p-4 rounded-lg border border-destructive/50 bg-destructive/10">
        <p className="text-sm text-destructive">
          An error occurred while loading data. Please try again.
        </p>
      </div>
    );
  }

  return null;
}

/**
 * Conditional wrapper for conditional rendering patterns
 * More flexible than StateRenderer for custom layouts
 *
 * @example
 * {renderState(state, {
 *   loading: <Skeleton />,
 *   empty: <Empty />,
 *   content: <Content />,
 *   error: <Error />,
 * })}
 */
export function renderState(
  state: ReturnType<typeof useLoadingState>,
  renderers: {
    loading?: React.ReactNode;
    empty?: React.ReactNode;
    content?: React.ReactNode;
    error?: React.ReactNode;
  }
) {
  if (state.shouldShowSkeleton) return renderers.loading ?? null;
  if (state.shouldShowEmpty) return renderers.empty ?? null;
  if (state.shouldShowContent) return renderers.content ?? null;
  if (state.hasError) return renderers.error ?? null;
  return null;
}

/**
 * Conditional rendering helper for multiple sections
 * Ensures all data is loaded before showing content
 *
 * @example
 * const section1 = useLoadingState({ isLoading: loading1, data: data1 });
 * const section2 = useLoadingState({ isLoading: loading2, data: data2 });
 *
 * <RenderWhenReady states={[section1, section2]}>
 *   <div>Both sections loaded!</div>
 * </RenderWhenReady>
 */
interface RenderWhenReadyProps {
  states: Array<ReturnType<typeof useLoadingState>>;
  loadingFallback?: React.ReactNode;
  errorFallback?: React.ReactNode;
  children: React.ReactNode;
}

export function RenderWhenReady({
  states,
  loadingFallback,
  errorFallback,
  children,
}: RenderWhenReadyProps) {
  const isAnyLoading = states.some(s => s.isLoading);
  const isAnyError = states.some(s => s.hasError);
  const isAnyEmpty = states.some(s => s.isEmpty);

  if (isAnyLoading) {
    return <>{loadingFallback}</>;
  }

  if (isAnyError) {
    return (
      <>
        {errorFallback ?? (
          <div className="p-4 rounded-lg border border-destructive/50 bg-destructive/10">
            <p className="text-sm text-destructive">
              An error occurred while loading data. Please try again.
            </p>
          </div>
        )}
      </>
    );
  }

  // Check if any section is empty (optional - some might intentionally be empty)
  // Uncomment the line below if you want to prevent rendering when any section is empty
  // if (isAnyEmpty) return <>{emptyFallback ?? null}</>;

  return <>{children}</>;
}

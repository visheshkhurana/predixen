import { useMemo } from 'react';

/**
 * Hook to manage common loading state patterns
 * Simplifies the conditional rendering of skeleton, empty, and loaded states
 */

export interface LoadingStateConfig {
  isLoading: boolean;
  data?: unknown[] | Record<string, unknown> | null;
  error?: Error | null;
  isEmpty?: boolean;
}

export interface LoadingState {
  isLoading: boolean;
  isEmpty: boolean;
  hasError: boolean;
  hasData: boolean;
  shouldShowSkeleton: boolean;
  shouldShowEmpty: boolean;
  shouldShowContent: boolean;
}

/**
 * Determines which state to display based on loading status and data availability
 *
 * @param config - Configuration object with loading state info
 * @returns LoadingState object with flags for each state
 *
 * @example
 * const { shouldShowSkeleton, shouldShowEmpty, shouldShowContent } = useLoadingState({
 *   isLoading: isDataLoading,
 *   data: myData,
 *   error: dataError,
 * });
 *
 * return (
 *   <>
 *     {shouldShowSkeleton && <TableSkeleton />}
 *     {shouldShowEmpty && <EmptyTable />}
 *     {shouldShowContent && <ActualContent />}
 *   </>
 * );
 */
export function useLoadingState({
  isLoading,
  data,
  error,
  isEmpty: customIsEmpty,
}: LoadingStateConfig): LoadingState {
  return useMemo(() => {
    // Determine if we have data
    const hasDataValue = hasData(data);
    const isEmpty = customIsEmpty ?? !hasDataValue;
    const hasDataForView = !isEmpty && data != null;
    const hasError = error != null;

    return {
      isLoading,
      isEmpty,
      hasError,
      hasData: hasDataForView,
      shouldShowSkeleton: isLoading,
      shouldShowEmpty: !isLoading && isEmpty && !hasError,
      shouldShowContent: !isLoading && hasDataForView && !hasError,
    };
  }, [isLoading, data, error, customIsEmpty]);
}

/**
 * Helper function to check if data exists
 */
function hasData(data: unknown): boolean {
  if (data == null) return false;
  if (Array.isArray(data)) return data.length > 0;
  if (typeof data === 'object') return Object.keys(data).length > 0;
  return Boolean(data);
}

/**
 * Hook for multiple loading states (useful for queries on same page)
 * Returns true if any of the loaders are loading
 */
export function useAnyLoading(...loaders: boolean[]): boolean {
  return useMemo(() => loaders.some(l => l), [loaders]);
}

/**
 * Hook for multiple loading states (useful for queries on same page)
 * Returns true only if all loaders are loaded
 */
export function useAllLoaded(...loaders: boolean[]): boolean {
  return useMemo(() => loaders.every(l => !l), [loaders]);
}

/**
 * Hook to create a combined loading state from multiple sources
 * Useful when a page has multiple independent data sources
 */
export function useCombinedLoadingState(
  states: Array<{
    isLoading: boolean;
    data?: unknown;
    error?: Error | null;
  }>
): LoadingState {
  return useMemo(() => {
    const isLoading = states.some(s => s.isLoading);
    const allData = states.map(s => s.data);
    const isEmpty = allData.every(d => !hasData(d));
    const hasError = states.some(s => s.error != null);
    const hasDataForView = !isEmpty;

    return {
      isLoading,
      isEmpty,
      hasError,
      hasData: hasDataForView,
      shouldShowSkeleton: isLoading,
      shouldShowEmpty: !isLoading && isEmpty && !hasError,
      shouldShowContent: !isLoading && hasDataForView && !hasError,
    };
  }, [states]);
}

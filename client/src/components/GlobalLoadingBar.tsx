import { useEffect, useState } from 'react';
import { useIsFetching } from '@tanstack/react-query';
import { cn } from '@/lib/utils';

/**
 * Global loading progress bar that appears at the top of the page
 * Shows when any React Query requests are in progress
 */

export function GlobalLoadingBar() {
  const isFetching = useIsFetching();
  const [isVisible, setIsVisible] = useState(false);
  const [progress, setProgress] = useState(0);

  // Show/hide bar based on fetching state
  useEffect(() => {
    if (isFetching > 0) {
      setIsVisible(true);
      setProgress(30); // Start at 30%

      // Simulate progress
      const interval = setInterval(() => {
        setProgress(prev => {
          const newProgress = prev + Math.random() * 25;
          return Math.min(newProgress, 90);
        });
      }, 300);

      return () => clearInterval(interval);
    } else {
      // Complete the progress bar
      setProgress(100);

      // Hide after animation completes
      const timeout = setTimeout(() => {
        setIsVisible(false);
        setProgress(0);
      }, 300);

      return () => clearTimeout(timeout);
    }
  }, [isFetching]);

  if (!isVisible && progress === 0) {
    return null;
  }

  return (
    <div
      className={cn(
        "fixed top-0 left-0 h-1 bg-gradient-to-r from-primary via-primary to-primary/60 shadow-lg z-[999] transition-all duration-300",
        isVisible || progress > 0 ? 'opacity-100' : 'opacity-0'
      )}
      style={{
        width: `${progress}%`,
        transitionProperty: 'width, opacity',
      }}
    />
  );
}

export default GlobalLoadingBar;

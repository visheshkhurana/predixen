import { useEffect, useRef } from "react";
import { trackFunnel } from "@/lib/funnel";
import { createCalculatorUsedController } from "@/lib/calculator-used";

/**
 * Fire `calculator_used` once per page view, after the first real result.
 * `signature` is anything that changes when an input changes (the inputs
 * themselves); each change restarts the debounce so typing a number counts once.
 */
export function useCalculatorUsed(
  calculator: string,
  touched: boolean,
  hasResult: boolean,
  signature: unknown,
): void {
  const controllerRef = useRef<ReturnType<typeof createCalculatorUsedController> | null>(null);
  if (controllerRef.current === null) {
    controllerRef.current = createCalculatorUsedController({ calculator, emit: trackFunnel });
  }
  const key = typeof signature === "string" ? signature : JSON.stringify(signature);

  useEffect(() => {
    controllerRef.current?.update(touched, hasResult);
  }, [touched, hasResult, key]);

  useEffect(() => () => controllerRef.current?.dispose(), []);
}

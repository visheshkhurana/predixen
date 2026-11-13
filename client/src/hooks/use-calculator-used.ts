import { useCallback, useEffect, useRef } from "react";
import { trackFunnel } from "@/lib/funnel";
import { createCalculatorUsedController } from "@/lib/calculator-used";

/**
 * Fire `calculator_used` once per page load, the first time an input changes.
 * `signature` changes with the inputs. A missing result does not block the event.
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

/**
 * Same event, wired to the input event itself.
 * Returns a stable handler for `onInput` / `onChange` / slider updates.
 * One fire per mount, which is one page load under wouter.
 */
export function useCalculatorUsedOnce(calculator: string): () => void {
  const controllerRef = useRef<ReturnType<typeof createCalculatorUsedController> | null>(null);
  if (controllerRef.current === null) {
    controllerRef.current = createCalculatorUsedController({ calculator, emit: trackFunnel });
  }
  return useCallback(() => {
    controllerRef.current?.onInputChange();
  }, []);
}

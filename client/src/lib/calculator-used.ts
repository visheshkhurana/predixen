/**
 * `calculator_used` once per page view, after the visitor has changed an
 * input AND the tool produced a result, and only once typing has paused.
 *
 * Same event name and shape the runway calculator and default-alive test
 * already send ({ calculator }), so every free tool lands in one funnel step.
 * Kept free of React so it can be tested under plain node.
 */
export const CALCULATOR_USED_DEBOUNCE_MS = 1200;

type TimerHandle = ReturnType<typeof setTimeout>;

export interface CalculatorUsedOptions {
  calculator: string;
  emit: (event: string, params: Record<string, unknown>) => void;
  delayMs?: number;
  setTimer?: (fn: () => void, ms: number) => TimerHandle;
  clearTimer?: (handle: TimerHandle) => void;
}

export function createCalculatorUsedController(opts: CalculatorUsedOptions) {
  const delay = opts.delayMs ?? CALCULATOR_USED_DEBOUNCE_MS;
  const setTimer = opts.setTimer ?? ((fn, ms) => setTimeout(fn, ms));
  const clearTimer = opts.clearTimer ?? ((h) => clearTimeout(h));
  let fired = false;
  let timer: TimerHandle | null = null;

  const cancel = () => {
    if (timer !== null) {
      clearTimer(timer);
      timer = null;
    }
  };

  return {
    /** Call on every input change. Restarts the pause timer. */
    update(touched: boolean, hasResult: boolean) {
      if (fired) return;
      cancel();
      if (!touched || !hasResult) return;
      timer = setTimer(() => {
        timer = null;
        if (fired) return;
        fired = true;
        opts.emit("calculator_used", { calculator: opts.calculator });
      }, delay);
    },
    dispose: cancel,
    get fired() {
      return fired;
    },
  };
}

/**
 * `calculator_used` once per page load, on the first input change.
 *
 * The property is the calculator name (`{ calculator }`), the same shape the
 * runway and default-alive tools already used. Kept free of React so node
 * tests can drive it. No email and no other PII: the only property is the name.
 */
export interface CalculatorUsedOptions {
  calculator: string;
  emit: (event: string, params: Record<string, unknown>) => void;
}

export function createCalculatorUsedController(opts: CalculatorUsedOptions) {
  let fired = false;

  const emitOnce = () => {
    if (fired) return;
    const calculator = opts.calculator.trim();
    if (!calculator || calculator.includes("@")) return;
    fired = true;
    opts.emit("calculator_used", { calculator });
  };

  return {
    /** Call from the first input/change event on this page load. */
    onInputChange() {
      emitOnce();
    },
    /**
     * Call when derived state shows the visitor edited a field.
     * Fires immediately. A missing result must not drop the event.
     */
    update(touched: boolean, _hasResult?: boolean) {
      if (!touched) return;
      emitOnce();
    },
    dispose() {},
    get fired() {
      return fired;
    },
  };
}

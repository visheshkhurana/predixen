export const FEATURE_FLAGS = {
  INVESTOR_MODE: import.meta.env.VITE_FEATURE_INVESTOR_MODE === 'true',
  // Product bet #4. Kill: set false (or revert the PR) if CTA-attributed
  // simulation_started is near-zero after 2 weeks at ≤25% rollout.
  TRUTH_SCAN_SUGGESTED_ACTIONS: true,
  // Kill switch for the single top Suggested Action on /overview.
  // Default on for every eligible company. Independent of
  // TRUTH_SCAN_SUGGESTED_ACTIONS — turning that flag off must not hide
  // this card or break the /simulate prefill it links to.
  OVERVIEW_SUGGESTED_ACTION: true,
  // Council item 3, 2026-10-15: the "Try with Sample Startup" client-side
  // preview on /tools/runway-calculator.
  //
  // Kill, without reverting this PR, either way:
  //   (a) set VITE_FEATURE_SAMPLE_STARTUP_PREVIEW=false and rebuild — the
  //       button and its panel vanish and the page is byte-for-byte what it
  //       was before, because the whole block is behind this one condition;
  //   (b) flip this literal to false in a one-line PR.
  // Default is ON, which is why this reads `!== 'false'` and not `=== 'true'`:
  // a kill switch that has to be switched on to be off is not a kill switch.
  // An unset variable must mean "ship it", which is the opposite of the
  // INVESTOR_MODE convention above — that one gates an unfinished feature,
  // this one gates a live one.
  SAMPLE_STARTUP_PREVIEW: import.meta.env.VITE_FEATURE_SAMPLE_STARTUP_PREVIEW !== 'false',
} as const;

export function isInvestorEnabled(): boolean {
  return FEATURE_FLAGS.INVESTOR_MODE;
}

export function isFounderEnabled(): boolean {
  return true;
}

export function isSampleStartupPreviewEnabled(): boolean {
  return FEATURE_FLAGS.SAMPLE_STARTUP_PREVIEW;
}

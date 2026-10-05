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
} as const;

export function isInvestorEnabled(): boolean {
  return FEATURE_FLAGS.INVESTOR_MODE;
}

export function isFounderEnabled(): boolean {
  return true;
}

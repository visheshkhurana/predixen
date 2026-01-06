export const FEATURE_FLAGS = {
  INVESTOR_MODE: import.meta.env.VITE_FEATURE_INVESTOR_MODE === 'true',
} as const;

export function isInvestorEnabled(): boolean {
  return FEATURE_FLAGS.INVESTOR_MODE;
}

export function isFounderEnabled(): boolean {
  return true;
}

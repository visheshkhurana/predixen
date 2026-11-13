/**
 * Parse a field's raw text into a number for the model.
 *
 * Same helper Conversion Eng shipped on the runway calculator. Fields hold
 * TEXT, not numbers. They used to use `onChange={e => setX(Number(e.target.value))}`,
 * and Number("") is 0 — so deleting the last digit snapped the field back to
 * "0" and it could never be emptied.
 */
export function toNumber(text: string): number {
  const n = parseFloat(text);
  return Number.isFinite(n) ? n : 0;
}

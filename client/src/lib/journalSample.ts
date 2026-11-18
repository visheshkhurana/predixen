/**
 * Decision Journal entries: real ones are kept per company in localStorage.
 * The illustrative entries below are shown only for sample/demo companies,
 * always labelled "Sample". A real company with nothing logged sees an empty
 * state, never these.
 */

export interface JournalEntry {
  id: number;
  title: string;
  decision: string;
  reasoning: string;
  outcome?: string;
  status: 'pending' | 'resolved' | 'revisit';
  date: string;
  impact: 'high' | 'medium' | 'low';
  /** Set on illustrative entries; rendered with a "Sample" badge. */
  sample?: boolean;
}

export const SAMPLE_JOURNAL_ENTRIES: JournalEntry[] = [
  {
    id: 1,
    title: 'Expand to Enterprise Tier',
    decision: 'Launch enterprise pricing tier at $499/mo with dedicated support',
    reasoning: 'Top 5 customers requested SLAs and priority support. Enterprise deal pipeline shows 8 qualified leads worth $47K ARR.',
    outcome: 'Closed 3 enterprise deals in first month, +$18K MRR',
    status: 'resolved',
    date: '2026-01-15',
    impact: 'high',
    sample: true,
  },
  {
    id: 2,
    title: 'Reduce CAC via Content Marketing',
    decision: 'Shift 30% of paid ad budget to SEO content and webinars',
    reasoning: 'CAC trending up to $1,800. Organic leads convert 2.3x better and have 40% lower churn. Content has 6-month compounding effect.',
    status: 'pending',
    date: '2026-02-01',
    impact: 'high',
    sample: true,
  },
  {
    id: 3,
    title: 'Hire Senior Backend Engineer',
    decision: 'Prioritize hiring a senior backend engineer over a second sales rep',
    reasoning: 'API reliability is at 99.2%, below target. Churn exit surveys cite performance issues. Engineering bottleneck blocks 3 feature releases.',
    outcome: 'Hired in Feb. API uptime improved to 99.8%, unblocked Q2 roadmap.',
    status: 'resolved',
    date: '2026-01-22',
    impact: 'medium',
    sample: true,
  },
  {
    id: 4,
    title: 'Extend Runway Decision',
    decision: 'Cut discretionary spend by 15% to extend runway from 18 to 21+ months',
    reasoning: 'Fundraising market tightening. Current burn gives 18mo runway. Need buffer to hit Series A metrics without pressure.',
    status: 'revisit',
    date: '2026-02-05',
    impact: 'high',
    sample: true,
  },
];

const SAMPLE_KEYS = new Set(SAMPLE_JOURNAL_ENTRIES.map((e) => `${e.id}|${e.title}`));

/** True for an illustrative entry, including copies saved by older builds without the flag. */
export function isSampleJournalEntry(e: Pick<JournalEntry, 'id' | 'title' | 'sample'>): boolean {
  return e.sample === true || SAMPLE_KEYS.has(`${e.id}|${e.title}`);
}

/**
 * Older builds seeded every company with the sample entries and, on the
 * first "New Entry", saved them to localStorage next to the founder's real
 * one. Strip them so only what the founder wrote is shown as theirs.
 */
export function stripSampleJournalEntries(entries: unknown): JournalEntry[] {
  if (!Array.isArray(entries)) return [];
  return entries.filter(
    (e): e is JournalEntry =>
      !!e && typeof e === 'object' && typeof (e as JournalEntry).title === 'string' && !isSampleJournalEntry(e as JournalEntry),
  );
}

/**
 * Entries to show: the founder's own, plus (sample companies only) the
 * labelled sample entries when nothing real has been logged yet.
 */
export function journalEntriesToShow(input: {
  stored: unknown;
  isSample: boolean;
}): JournalEntry[] {
  const own = stripSampleJournalEntries(input.stored);
  if (own.length === 0 && input.isSample) return SAMPLE_JOURNAL_ENTRIES;
  return own;
}

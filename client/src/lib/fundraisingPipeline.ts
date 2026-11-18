// Pipeline board for the Fundraising page. Everything here is derived from the
// company's own saved entries — the page used to show a canned list of real
// investor names and a made-up "$850K of $1.5M" round to every company.

export const BOARD_STAGES = [
  { key: 'sourced', label: 'Researching' },
  { key: 'contacted', label: 'Reached Out' },
  { key: 'meeting', label: 'Intro Meeting' },
  { key: 'partner_meeting', label: 'Partner Meeting' },
  { key: 'dd', label: 'Due Diligence' },
  { key: 'term_sheet', label: 'Term Sheet' },
  { key: 'committed', label: 'Committed' },
  { key: 'closed', label: 'Closed' },
  { key: 'passed', label: 'Passed' },
] as const;

export type BoardStage = typeof BOARD_STAGES[number]['key'];

export interface BoardEntry {
  id: string;
  firm: string;
  partner: string;
  check_size: string;
  warm_intro: boolean;
  stage: BoardStage;
  last_activity_at: string | null;
}

export function stageLabel(stage: string): string {
  return BOARD_STAGES.find(s => s.key === stage)?.label ?? 'Researching';
}

export function groupByStage(entries: BoardEntry[]): Record<BoardStage, BoardEntry[]> {
  const grouped = Object.fromEntries(BOARD_STAGES.map(s => [s.key, [] as BoardEntry[]])) as Record<BoardStage, BoardEntry[]>;
  for (const e of entries) (grouped[e.stage] ?? grouped.sourced).push(e);
  return grouped;
}

// The funnel in the banner counts exactly what the board columns show, so the
// two can never disagree.
export const FUNNEL_STEPS: { label: string; stages: BoardStage[] }[] = [
  { label: 'Research', stages: ['sourced'] },
  { label: 'Outreach', stages: ['contacted'] },
  { label: 'Meetings', stages: ['meeting', 'partner_meeting'] },
  { label: 'DD', stages: ['dd'] },
  { label: 'Term sheet+', stages: ['term_sheet', 'committed', 'closed'] },
];

export function pipelineSummary(entries: BoardEntry[]) {
  const count = (stages: BoardStage[]) => entries.filter(e => stages.includes(e.stage)).length;
  return {
    total: entries.length,
    active: entries.filter(e => e.stage !== 'passed').length,
    funnel: FUNNEL_STEPS.map(step => ({ label: step.label, count: count(step.stages) })),
    committed: count(['committed', 'closed']),
    warmIntros: entries.filter(e => e.warm_intro && e.stage !== 'passed').length,
    passed: count(['passed']),
  };
}

export interface RoundLike {
  name: string;
  status?: string | null;
  target_raise?: number | null;
}

export function currentRound<T extends RoundLike>(rounds: T[] | undefined | null): T | null {
  const list = rounds ?? [];
  return list.find(r => r.status === 'active') ?? list.find(r => r.status === 'planned') ?? null;
}

export function relativeActivity(iso: string | null, now: Date = new Date()): string {
  if (!iso) return '';
  const then = new Date(iso.endsWith('Z') || /[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);
  if (Number.isNaN(then.getTime())) return '';
  const days = Math.floor((now.getTime() - then.getTime()) / 86_400_000);
  if (days <= 0) return 'Today';
  if (days === 1) return '1 day ago';
  if (days < 14) return `${days} days ago`;
  return `${Math.floor(days / 7)} weeks ago`;
}

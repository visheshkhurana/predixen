import { SimGlassCard } from "@/components/ui/sim-glass-card";
import {
  fieldLabel,
  formatInputValue,
  formatSyncedAtLocal,
  groupInputProvenance,
  type InputProvenanceMap,
  type ProvenanceEntry,
} from "@/lib/simulation/inputProvenance";

interface SimulationInputsPanelProps {
  provenance: InputProvenanceMap | null | undefined;
  values?: Record<string, number | null | undefined>;
}

function FieldRow({
  name,
  entry,
  value,
}: {
  name: string;
  entry: ProvenanceEntry;
  value: number | null | undefined;
}) {
  const shown = typeof value === "number" && Number.isFinite(value) ? formatInputValue(name, value) : null;
  const source = typeof entry.source === "string" && entry.source.trim() ? entry.source.trim() : null;
  const syncedAt = typeof entry.synced_at === "string" && entry.synced_at.trim()
    ? formatSyncedAtLocal(entry.synced_at)
    : null;

  return (
    <li className="flex items-start justify-between gap-3 py-1.5" data-testid={`input-field-${name}`}>
      <div className="min-w-0">
        <div className="text-xs text-zinc-200">{fieldLabel(name)}</div>
        {entry.kind === "synced" && (
          <div className="text-[10px] text-sky-300/90 mt-0.5" data-testid={`input-sync-${name}`}>
            {[source, syncedAt ? `last sync ${syncedAt}` : null].filter(Boolean).join(" · ") || "Synced"}
          </div>
        )}
        {entry.kind === "assumed" && (
          <div className="text-[10px] text-amber-300/90 mt-0.5">Assumption — not entered or synced</div>
        )}
      </div>
      {shown && <div className="text-xs font-mono text-zinc-300 shrink-0">{shown}</div>}
    </li>
  );
}

function Group({
  title,
  testId,
  names,
  provenance,
  values,
  empty,
}: {
  title: string;
  testId: string;
  names: string[];
  provenance: InputProvenanceMap;
  values: Record<string, number | null | undefined>;
  empty?: string;
}) {
  return (
    <div data-testid={testId}>
      <h4 className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500 mb-1">{title}</h4>
      {names.length === 0 ? (
        <p className="text-[11px] text-zinc-500 leading-relaxed">{empty}</p>
      ) : (
        <ul className="divide-y divide-white/[0.04]">
          {names.map((name) => (
            <FieldRow key={name} name={name} entry={provenance[name]} value={values[name]} />
          ))}
        </ul>
      )}
    </div>
  );
}

export function SimulationInputsPanel({ provenance, values = {} }: SimulationInputsPanelProps) {
  const groups = groupInputProvenance(provenance);
  if (!groups || !provenance) return null;

  return (
    <SimGlassCard variant="elevated" className="p-4" hover={false}>
      <div data-testid="simulation-inputs-panel">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">Inputs</h3>
        <p className="text-[11px] text-zinc-500 mb-3">
          Where each number in this run came from.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Group
            title="Entered by you"
            testId="inputs-group-entered"
            names={groups.entered}
            provenance={provenance}
            values={values}
            empty="None of these inputs were entered."
          />
          <Group
            title="Synced"
            testId="inputs-group-synced"
            names={groups.synced}
            provenance={provenance}
            values={values}
            empty="No synced inputs yet."
          />
          <Group
            title="Assumed"
            testId="inputs-group-assumed"
            names={groups.assumed}
            provenance={provenance}
            values={values}
            empty="No assumptions on this run."
          />
        </div>
      </div>
    </SimGlassCard>
  );
}

export function downloadCSV(data: Record<string, any>[], filename: string) {
  if (data.length === 0) return;
  
  const headers = Object.keys(data[0]);
  const csvContent = [
    headers.join(','),
    ...data.map(row => 
      headers.map(header => {
        const value = row[header];
        if (value === null || value === undefined) return '';
        if (typeof value === 'string' && (value.includes(',') || value.includes('"') || value.includes('\n'))) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return String(value);
      }).join(',')
    )
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${filename}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

export function downloadJSON(data: any, filename: string) {
  const jsonContent = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonContent], { type: 'application/json' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${filename}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
}

export function formatTruthScanForExport(truthScan: any) {
  if (!truthScan) return [];
  
  const metrics = truthScan.metrics || truthScan.outputs_json?.metrics || {};
  const flags = truthScan.flags || truthScan.outputs_json?.flags || [];
  
  const metricsData = Object.entries(metrics).map(([key, value]) => ({
    metric: key,
    value: value,
    type: 'metric'
  }));
  
  const flagsData = flags.map((flag: any) => ({
    metric: flag.title,
    value: flag.description,
    type: `flag-${flag.severity}`
  }));
  
  return [...metricsData, ...flagsData];
}

export function formatSimulationForExport(simulation: any) {
  if (!simulation?.results_json) return [];
  
  const results = simulation.results_json;
  const rows = [];
  
  const numMonths = results.survival_curve?.length || results.cash_bands?.p50?.length || 24;
  
  for (let i = 0; i < numMonths; i++) {
    rows.push({
      month: i + 1,
      survival_rate: results.survival_curve?.[i]?.survival_rate || null,
      cash_p10: results.cash_bands?.p10?.[i] || null,
      cash_p50: results.cash_bands?.p50?.[i] || null,
      cash_p90: results.cash_bands?.p90?.[i] || null,
      revenue_p10: results.revenue_bands?.p10?.[i] || null,
      revenue_p50: results.revenue_bands?.p50?.[i] || null,
      revenue_p90: results.revenue_bands?.p90?.[i] || null,
    });
  }
  
  return rows;
}

export function formatDecisionsForExport(decisions: any) {
  if (!decisions?.recommended_actions_json) return [];
  
  return decisions.recommended_actions_json.map((action: any, index: number) => ({
    rank: index + 1,
    title: action.title,
    rationale: action.rationale,
    survival_impact_18m: action.expected_impact?.delta_survival_18m || 0,
    runway_impact_months: action.expected_impact?.delta_runway_p50 || 0,
    key_assumption: action.key_assumption || '',
    risks: action.risks?.join('; ') || '',
  }));
}

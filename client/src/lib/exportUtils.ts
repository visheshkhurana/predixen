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

export function downloadPDF(data: any, filename: string, title: string = 'Report') {
  const styles = `
    <style>
      body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; color: #1a1a1a; max-width: 800px; margin: 0 auto; }
      h1 { color: #0ea5e9; border-bottom: 2px solid #0ea5e9; padding-bottom: 10px; }
      h2 { color: #374151; margin-top: 30px; }
      .section { margin-bottom: 30px; page-break-inside: avoid; }
      .metric { display: flex; justify-content: space-between; padding: 10px; background: #f8fafc; margin: 5px 0; border-radius: 4px; }
      .metric-name { font-weight: 600; }
      .metric-value { font-family: monospace; color: #0ea5e9; }
      .flag { padding: 12px; margin: 8px 0; border-radius: 4px; border-left: 4px solid; }
      .flag-high { background: #fef2f2; border-color: #ef4444; }
      .flag-medium { background: #fffbeb; border-color: #f59e0b; }
      .flag-low { background: #f0f9ff; border-color: #3b82f6; }
      .flag-title { font-weight: 600; margin-bottom: 4px; }
      .score-card { background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); padding: 20px; border-radius: 8px; margin: 10px 0; }
      .score-value { font-size: 36px; font-weight: bold; color: #0369a1; }
      .benchmark { padding: 15px; background: #f8fafc; margin: 10px 0; border-radius: 8px; }
      .benchmark-bar { height: 20px; background: #e2e8f0; border-radius: 10px; margin: 10px 0; position: relative; }
      .benchmark-marker { position: absolute; top: 0; bottom: 0; width: 3px; background: #64748b; }
      .benchmark-value { position: absolute; top: -4px; width: 12px; height: 12px; background: #0ea5e9; border-radius: 50%; transform: translateX(-50%); }
      .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 12px; }
      @media print { body { padding: 20px; } }
    </style>
  `;
  
  const formatMetrics = (metrics: Record<string, any>) => {
    const items = Object.entries(metrics).filter(([_, v]) => v !== null && v !== undefined);
    return items.map(([key, value]) => {
      const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
      let formattedValue = value;
      if (typeof value === 'number') {
        if (key.includes('margin') || key.includes('growth') || key.includes('rate')) {
          formattedValue = `${(value * 100).toFixed(1)}%`;
        } else if (key.includes('revenue') || key.includes('burn') || key.includes('cash')) {
          formattedValue = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
        } else {
          formattedValue = value.toLocaleString();
        }
      }
      return `<div class="metric"><span class="metric-name">${formattedKey}</span><span class="metric-value">${formattedValue}</span></div>`;
    }).join('');
  };
  
  const formatFlags = (flags: any[]) => {
    if (!flags || flags.length === 0) return '<p>No flags detected.</p>';
    return flags.map((flag: any) => `
      <div class="flag flag-${flag.severity || 'low'}">
        <div class="flag-title">${flag.title}</div>
        <div>${flag.description}</div>
      </div>
    `).join('');
  };
  
  const formatBenchmarks = (benchmarks: any[]) => {
    if (!benchmarks || benchmarks.length === 0) return '<p>No benchmark comparisons available.</p>';
    return benchmarks.map((bench: any) => {
      const min = Math.min(bench.p25 * 0.5, bench.value * 0.8);
      const max = Math.max(bench.p75 * 1.5, bench.value * 1.2);
      const range = max - min;
      const p25Pos = ((bench.p25 - min) / range) * 100;
      const p50Pos = ((bench.p50 - min) / range) * 100;
      const p75Pos = ((bench.p75 - min) / range) * 100;
      const valuePos = Math.min(100, Math.max(0, ((bench.value - min) / range) * 100));
      
      return `
        <div class="benchmark">
          <strong>${bench.metric.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}</strong>
          <div class="benchmark-bar">
            <div class="benchmark-marker" style="left: ${p25Pos}%"></div>
            <div class="benchmark-marker" style="left: ${p50Pos}%"></div>
            <div class="benchmark-marker" style="left: ${p75Pos}%"></div>
            <div class="benchmark-value" style="left: ${valuePos}%"></div>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 12px; color: #6b7280;">
            <span>P25: ${bench.p25.toFixed(2)}</span>
            <span>P50: ${bench.p50.toFixed(2)}</span>
            <span>P75: ${bench.p75.toFixed(2)}</span>
          </div>
          <div style="margin-top: 8px;">Your Value: <strong>${bench.value.toFixed(2)}</strong></div>
        </div>
      `;
    }).join('');
  };
  
  const metrics = data.metrics || data.outputs_json?.metrics || {};
  const flags = data.flags || data.outputs_json?.flags || [];
  const benchmarks = data.benchmark_comparisons || data.outputs_json?.benchmark_comparisons || [];
  const qualityOfGrowth = data.quality_of_growth_index || data.outputs_json?.quality_of_growth_index || 0;
  const confidence = data.data_confidence_score || data.outputs_json?.data_confidence_score || 0;
  
  const htmlContent = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>${title}</title>
      ${styles}
    </head>
    <body>
      <h1>${title}</h1>
      <p>Generated on ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</p>
      
      <div class="section">
        <h2>Composite Scores</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
          <div class="score-card">
            <div>Quality of Growth Index</div>
            <div class="score-value">${qualityOfGrowth}/100</div>
          </div>
          <div class="score-card">
            <div>Data Confidence Score</div>
            <div class="score-value">${confidence}/100</div>
          </div>
        </div>
      </div>
      
      <div class="section">
        <h2>Key Metrics</h2>
        ${formatMetrics(metrics)}
      </div>
      
      <div class="section">
        <h2>Benchmark Comparisons</h2>
        ${formatBenchmarks(benchmarks)}
      </div>
      
      <div class="section">
        <h2>Flags & Insights</h2>
        ${formatFlags(flags)}
      </div>
      
      <div class="footer">
        <p>This report was generated by Predixen Intelligence OS. For questions about methodology, please contact support.</p>
      </div>
    </body>
    </html>
  `;
  
  const printWindow = window.open('', '_blank');
  if (printWindow) {
    printWindow.document.write(htmlContent);
    printWindow.document.close();
    setTimeout(() => {
      printWindow.print();
    }, 500);
  }
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

export function printSimulationResults(): void {
  window.print();
}

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
        <p>This report was generated by FounderConsole. For questions about methodology, please contact support.</p>
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

export interface SimulationPDFData {
  scenarioName: string;
  companyName?: string;
  p90: { runway: string; revenue18m: number; cash12m: number; breakeven: string; survival: string };
  p50: { runway: string; revenue18m: number; cash12m: number; breakeven: string; survival: string };
  p10: { runway: string; revenue18m: number; cash12m: number; breakeven: string; survival: string };
  decisionScore?: { risk: number; reward: number; capitalEfficiency: number; survivalImpact: number };
  sensitivityBars?: { label: string; impact: number; level: string }[];
  counterMoves?: { name: string; runwayDelta: number; survivalDelta: number }[];
  fundraising?: { fundraiseAmount: number; dilution: number; ownershipPost: number; runwayExtMonths: number; survivalLift: number };
  survivalCurve?: { month: number; survival_rate: number }[];
  cashBands?: { p10: number[]; p50: number[]; p90: number[] };
}

const PDF_COLORS = {
  primary: [14, 165, 233] as [number, number, number],
  dark: [15, 23, 42] as [number, number, number],
  muted: [100, 116, 139] as [number, number, number],
  white: [255, 255, 255] as [number, number, number],
  lightBg: [248, 250, 252] as [number, number, number],
  green: [16, 185, 129] as [number, number, number],
  amber: [245, 158, 11] as [number, number, number],
  red: [239, 68, 68] as [number, number, number],
  border: [226, 232, 240] as [number, number, number],
};

function fmtCurrency(v: number): string {
  if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (Math.abs(v) >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v.toFixed(0)}`;
}

export async function downloadSimulationPDF(data: SimulationPDFData) {
  const { default: jsPDF } = await import('jspdf');
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const pageW = 210;
  const pageH = 297;
  const margin = 18;
  const contentW = pageW - margin * 2;
  let y = 0;

  function checkPage(needed: number) {
    if (y + needed > pageH - 20) {
      doc.addPage();
      y = margin;
    }
  }

  function drawProgressBar(x: number, yPos: number, w: number, h: number, value: number, max: number, color: [number, number, number]) {
    doc.setFillColor(...PDF_COLORS.border);
    doc.roundedRect(x, yPos, w, h, h / 2, h / 2, 'F');
    const fillW = Math.min(w, (value / max) * w);
    if (fillW > 0) {
      doc.setFillColor(...color);
      doc.roundedRect(x, yPos, Math.max(fillW, h), h, h / 2, h / 2, 'F');
    }
  }

  // --- HEADER ---
  doc.setFillColor(...PDF_COLORS.dark);
  doc.rect(0, 0, pageW, 42, 'F');
  doc.setTextColor(...PDF_COLORS.white);
  doc.setFontSize(22);
  doc.setFont('helvetica', 'bold');
  doc.text('SIMULATION REPORT', margin, 18);
  doc.setFontSize(11);
  doc.setFont('helvetica', 'normal');
  doc.text(data.scenarioName, margin, 26);
  doc.setFontSize(8);
  doc.setTextColor(180, 190, 210);
  const dateStr = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  doc.text(`${data.companyName || 'FounderConsole'}  |  ${dateStr}  |  1,000 Monte Carlo Runs`, margin, 34);

  const tagW = 28;
  doc.setFillColor(...PDF_COLORS.primary);
  doc.roundedRect(pageW - margin - tagW, 12, tagW, 7, 2, 2, 'F');
  doc.setTextColor(...PDF_COLORS.white);
  doc.setFontSize(7);
  doc.setFont('helvetica', 'bold');
  doc.text('CONFIDENTIAL', pageW - margin - tagW + 3.5, 16.8);

  y = 52;

  // --- EXECUTIVE SUMMARY: P90 / P50 / P10 ---
  doc.setTextColor(...PDF_COLORS.dark);
  doc.setFontSize(13);
  doc.setFont('helvetica', 'bold');
  doc.text('EXECUTIVE SUMMARY', margin, y);
  y += 8;

  const colW = (contentW - 6) / 3;
  const scenarios = [
    { label: 'BEST CASE (P90)', data: data.p90, color: PDF_COLORS.green },
    { label: 'MOST LIKELY (P50)', data: data.p50, color: PDF_COLORS.primary },
    { label: 'WORST CASE (P10)', data: data.p10, color: PDF_COLORS.red },
  ];

  scenarios.forEach((sc, i) => {
    const x = margin + i * (colW + 3);
    doc.setFillColor(...PDF_COLORS.lightBg);
    doc.roundedRect(x, y, colW, 52, 2, 2, 'F');

    doc.setFillColor(...sc.color);
    doc.roundedRect(x, y, colW, 8, 2, 2, 'F');
    doc.rect(x, y + 4, colW, 4, 'F');
    doc.setTextColor(...PDF_COLORS.white);
    doc.setFontSize(7);
    doc.setFont('helvetica', 'bold');
    doc.text(sc.label, x + 3, y + 5.5);

    const metrics = [
      { label: 'Runway', value: `${sc.data.runway} mo` },
      { label: 'Revenue @18m', value: fmtCurrency(sc.data.revenue18m || 0) },
      { label: 'Cash @12m', value: fmtCurrency(sc.data.cash12m || 0) },
      { label: 'Break-even', value: sc.data.breakeven },
      { label: 'Survival', value: `${sc.data.survival}%` },
    ];

    let my = y + 14;
    doc.setFontSize(7.5);
    metrics.forEach((m) => {
      doc.setTextColor(...PDF_COLORS.muted);
      doc.setFont('helvetica', 'normal');
      doc.text(m.label, x + 3, my);
      doc.setTextColor(...PDF_COLORS.dark);
      doc.setFont('helvetica', 'bold');
      doc.text(m.value, x + colW - 3, my, { align: 'right' });
      my += 7;
    });

    const survivalVal = parseFloat(sc.data.survival) || 0;
    drawProgressBar(x + 3, my, colW - 6, 2.5, survivalVal, 100, sc.color);
  });

  y += 60;

  // --- DECISION SCORE CARD ---
  if (data.decisionScore) {
    checkPage(45);
    doc.setTextColor(...PDF_COLORS.dark);
    doc.setFontSize(13);
    doc.setFont('helvetica', 'bold');
    doc.text('DECISION SCORE', margin, y);
    y += 8;

    const ds = data.decisionScore;
    const scores = [
      { label: 'Risk Management', value: ds.risk, color: ds.risk >= 7 ? PDF_COLORS.green : ds.risk >= 4 ? PDF_COLORS.amber : PDF_COLORS.red },
      { label: 'Reward Potential', value: ds.reward, color: ds.reward >= 7 ? PDF_COLORS.green : ds.reward >= 4 ? PDF_COLORS.amber : PDF_COLORS.red },
      { label: 'Capital Efficiency', value: ds.capitalEfficiency, color: ds.capitalEfficiency >= 7 ? PDF_COLORS.green : ds.capitalEfficiency >= 4 ? PDF_COLORS.amber : PDF_COLORS.red },
    ];

    doc.setFillColor(...PDF_COLORS.lightBg);
    doc.roundedRect(margin, y, contentW, 32, 2, 2, 'F');

    scores.forEach((s, i) => {
      const sx = margin + 6;
      const sy = y + 6 + i * 9;
      doc.setTextColor(...PDF_COLORS.muted);
      doc.setFontSize(8);
      doc.setFont('helvetica', 'normal');
      doc.text(s.label, sx, sy + 1);
      doc.setTextColor(...PDF_COLORS.dark);
      doc.setFont('helvetica', 'bold');
      doc.text(`${s.value}/10`, sx + 42, sy + 1);
      drawProgressBar(sx + 55, sy - 1.5, contentW - 70, 3, s.value, 10, s.color);
    });

    const impactLabel = ds.survivalImpact >= 0 ? `+${ds.survivalImpact.toFixed(1)}%` : `${ds.survivalImpact.toFixed(1)}%`;
    const impactColor = ds.survivalImpact >= 0 ? PDF_COLORS.green : PDF_COLORS.red;
    doc.setFontSize(7);
    doc.setTextColor(...impactColor);
    doc.setFont('helvetica', 'bold');
    doc.text(`Survival Impact: ${impactLabel}`, margin + contentW - 4, y + 30, { align: 'right' });

    y += 38;
  }

  // --- SENSITIVITY LEVERS ---
  if (data.sensitivityBars && data.sensitivityBars.length > 0) {
    checkPage(35);
    doc.setTextColor(...PDF_COLORS.dark);
    doc.setFontSize(13);
    doc.setFont('helvetica', 'bold');
    doc.text('KEY SENSITIVITY LEVERS', margin, y);
    y += 8;

    data.sensitivityBars.forEach((bar) => {
      const barColor = bar.level === 'high' ? PDF_COLORS.red : bar.level === 'med' ? PDF_COLORS.amber : PDF_COLORS.green;
      doc.setTextColor(...PDF_COLORS.muted);
      doc.setFontSize(7.5);
      doc.setFont('helvetica', 'normal');
      doc.text(bar.label, margin + 2, y + 1);
      drawProgressBar(margin + 38, y - 1.5, contentW - 55, 3, bar.impact, 100, barColor);
      doc.setTextColor(...barColor);
      doc.setFontSize(6.5);
      doc.setFont('helvetica', 'bold');
      doc.text(bar.level.toUpperCase(), margin + contentW - 2, y + 1, { align: 'right' });
      y += 7;
    });
    y += 4;
  }

  // --- COUNTER-MOVES ---
  if (data.counterMoves && data.counterMoves.length > 0) {
    checkPage(35);
    doc.setTextColor(...PDF_COLORS.dark);
    doc.setFontSize(13);
    doc.setFont('helvetica', 'bold');
    doc.text('COUNTER-MOVE ANALYSIS', margin, y);
    y += 8;

    doc.setFillColor(...PDF_COLORS.lightBg);
    const tableH = 7 + data.counterMoves.length * 7;
    doc.roundedRect(margin, y, contentW, tableH, 2, 2, 'F');

    doc.setFillColor(...PDF_COLORS.dark);
    doc.roundedRect(margin, y, contentW, 7, 2, 2, 'F');
    doc.rect(margin, y + 4, contentW, 3, 'F');
    doc.setTextColor(...PDF_COLORS.white);
    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'bold');
    doc.text('STRATEGY', margin + 4, y + 4.8);
    doc.text('RUNWAY DELTA', margin + contentW * 0.55, y + 4.8);
    doc.text('SURVIVAL DELTA', margin + contentW * 0.78, y + 4.8);

    y += 7;
    data.counterMoves.forEach((cm) => {
      doc.setTextColor(...PDF_COLORS.dark);
      doc.setFontSize(7);
      doc.setFont('helvetica', 'normal');
      doc.text(cm.name, margin + 4, y + 4.8);
      const rwColor = cm.runwayDelta >= 0 ? PDF_COLORS.green : PDF_COLORS.red;
      const svColor = cm.survivalDelta >= 0 ? PDF_COLORS.green : PDF_COLORS.red;
      doc.setTextColor(...rwColor);
      doc.setFont('helvetica', 'bold');
      doc.text(`${cm.runwayDelta >= 0 ? '+' : ''}${cm.runwayDelta.toFixed(1)} mo`, margin + contentW * 0.55, y + 4.8);
      doc.setTextColor(...svColor);
      doc.text(`${cm.survivalDelta >= 0 ? '+' : ''}${cm.survivalDelta.toFixed(1)}%`, margin + contentW * 0.78, y + 4.8);
      y += 7;
    });
    y += 6;
  }

  // --- FUNDRAISING ---
  if (data.fundraising) {
    checkPage(35);
    doc.setTextColor(...PDF_COLORS.dark);
    doc.setFontSize(13);
    doc.setFont('helvetica', 'bold');
    doc.text('FUNDRAISING IMPACT', margin, y);
    y += 8;

    doc.setFillColor(...PDF_COLORS.lightBg);
    doc.roundedRect(margin, y, contentW, 22, 2, 2, 'F');

    const fr = data.fundraising;
    const frMetrics = [
      { label: 'Raise Amount', value: fmtCurrency(fr.fundraiseAmount) },
      { label: 'Dilution', value: `${fr.dilution.toFixed(1)}%` },
      { label: 'Ownership Post', value: `${fr.ownershipPost.toFixed(1)}%` },
      { label: 'Runway Ext.', value: `+${fr.runwayExtMonths.toFixed(0)} mo` },
      { label: 'Survival Lift', value: `+${fr.survivalLift.toFixed(1)}%` },
    ];

    const frColW = contentW / frMetrics.length;
    frMetrics.forEach((m, i) => {
      const fx = margin + i * frColW;
      doc.setTextColor(...PDF_COLORS.muted);
      doc.setFontSize(6.5);
      doc.setFont('helvetica', 'normal');
      doc.text(m.label, fx + frColW / 2, y + 7, { align: 'center' });
      doc.setTextColor(...PDF_COLORS.dark);
      doc.setFontSize(10);
      doc.setFont('helvetica', 'bold');
      doc.text(m.value, fx + frColW / 2, y + 15, { align: 'center' });
    });

    y += 28;
  }

  // --- SURVIVAL CURVE (mini chart) ---
  if (data.survivalCurve && data.survivalCurve.length > 0) {
    checkPage(55);
    doc.setTextColor(...PDF_COLORS.dark);
    doc.setFontSize(13);
    doc.setFont('helvetica', 'bold');
    doc.text('SURVIVAL PROBABILITY CURVE', margin, y);
    y += 6;

    const chartX = margin + 8;
    const chartW = contentW - 16;
    const chartH = 35;
    const chartY = y;

    doc.setDrawColor(...PDF_COLORS.border);
    doc.setLineWidth(0.2);
    for (let pct = 0; pct <= 100; pct += 25) {
      const ly = chartY + chartH - (pct / 100) * chartH;
      doc.line(chartX, ly, chartX + chartW, ly);
      doc.setTextColor(...PDF_COLORS.muted);
      doc.setFontSize(5.5);
      doc.setFont('helvetica', 'normal');
      doc.text(`${pct}%`, chartX - 2, ly + 1, { align: 'right' });
    }

    const curve = data.survivalCurve;
    const maxMonth = curve.length;
    doc.setDrawColor(...PDF_COLORS.primary);
    doc.setLineWidth(0.6);
    for (let i = 1; i < curve.length; i++) {
      const x1 = chartX + ((i - 1) / (maxMonth - 1)) * chartW;
      const x2 = chartX + (i / (maxMonth - 1)) * chartW;
      const y1 = chartY + chartH - (curve[i - 1].survival_rate) * chartH;
      const y2 = chartY + chartH - (curve[i].survival_rate) * chartH;
      doc.line(x1, y1, x2, y2);
    }

    for (let m = 0; m < maxMonth; m += 6) {
      const mx = chartX + (m / (maxMonth - 1)) * chartW;
      doc.setTextColor(...PDF_COLORS.muted);
      doc.setFontSize(5.5);
      doc.text(`M${m + 1}`, mx, chartY + chartH + 4, { align: 'center' });
    }

    y += chartH + 10;
  }

  // --- CASH PROJECTION BANDS (mini chart) ---
  if (data.cashBands && data.cashBands.p50.length > 0) {
    checkPage(55);
    doc.setTextColor(...PDF_COLORS.dark);
    doc.setFontSize(13);
    doc.setFont('helvetica', 'bold');
    doc.text('CASH PROJECTION BANDS', margin, y);
    y += 6;

    const chartX = margin + 12;
    const chartW = contentW - 20;
    const chartH = 35;
    const chartY = y;

    const allVals = [...data.cashBands.p10, ...data.cashBands.p50, ...data.cashBands.p90].filter(v => v != null);
    const maxVal = Math.max(...allVals, 1);
    const minVal = Math.min(...allVals, 0);
    const range = maxVal - minVal || 1;

    const toY = (v: number) => chartY + chartH - ((v - minVal) / range) * chartH;
    const months = data.cashBands.p50.length;

    doc.setDrawColor(...PDF_COLORS.border);
    doc.setLineWidth(0.15);
    for (let g = 0; g <= 4; g++) {
      const gv = minVal + (range * g) / 4;
      const gy = toY(gv);
      doc.line(chartX, gy, chartX + chartW, gy);
      doc.setTextColor(...PDF_COLORS.muted);
      doc.setFontSize(5);
      doc.setFont('helvetica', 'normal');
      doc.text(fmtCurrency(gv), chartX - 2, gy + 1, { align: 'right' });
    }

    const drawLine = (band: number[], color: [number, number, number], width: number) => {
      doc.setDrawColor(...color);
      doc.setLineWidth(width);
      for (let i = 1; i < band.length; i++) {
        const x1 = chartX + ((i - 1) / (months - 1)) * chartW;
        const x2 = chartX + (i / (months - 1)) * chartW;
        doc.line(x1, toY(band[i - 1]), x2, toY(band[i]));
      }
    };

    drawLine(data.cashBands.p10, PDF_COLORS.red, 0.3);
    drawLine(data.cashBands.p50, PDF_COLORS.primary, 0.6);
    drawLine(data.cashBands.p90, PDF_COLORS.green, 0.3);

    const legendY = chartY + chartH + 4;
    [[PDF_COLORS.green, 'P90'], [PDF_COLORS.primary, 'P50'], [PDF_COLORS.red, 'P10']].forEach(([c, l], i) => {
      const lx = chartX + i * 20;
      doc.setFillColor(...(c as [number, number, number]));
      doc.rect(lx, legendY - 1, 4, 1.5, 'F');
      doc.setTextColor(...PDF_COLORS.muted);
      doc.setFontSize(5.5);
      doc.text(l as string, lx + 5.5, legendY);
    });

    y += chartH + 12;
  }

  // --- FOOTER ---
  const addFooter = (pageNum: number, totalPages: number) => {
    doc.setPage(pageNum);
    doc.setDrawColor(...PDF_COLORS.border);
    doc.setLineWidth(0.3);
    doc.line(margin, pageH - 14, pageW - margin, pageH - 14);
    doc.setTextColor(...PDF_COLORS.muted);
    doc.setFontSize(6);
    doc.setFont('helvetica', 'normal');
    doc.text('Generated by FounderConsole  |  For authorized recipients only', margin, pageH - 9);
    doc.text(`Page ${pageNum} of ${totalPages}`, pageW - margin, pageH - 9, { align: 'right' });
  };

  const totalPages = doc.getNumberOfPages();
  for (let p = 1; p <= totalPages; p++) {
    addFooter(p, totalPages);
  }

  doc.save(`${data.scenarioName.toLowerCase().replace(/\s+/g, '-')}-report.pdf`);
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

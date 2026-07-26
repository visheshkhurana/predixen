export interface MetricItem {
  label: string;
  value: string;
  delta?: string;
  color?: string;
}

export interface ChartPoint {
  label: string;
  value: number;
}

export interface ScenarioItem {
  name: string;
  runwayP50?: number;
  survival18m?: number;
  description?: string;
}

export interface SlideData {
  title: string;
  type: 'metrics' | 'chart' | 'simulation' | 'narrative' | 'comparison';
  content: string;
  metrics?: MetricItem[];
  narrativeHtml?: string;
  modelUsed?: string;
  providerUsed?: string;
  imageBase64?: string;
  chartData?: {
    revenue?: ChartPoint[];
    burn?: ChartPoint[];
    cash?: ChartPoint[];
    mrr?: ChartPoint[];
  };
  scenarios?: ScenarioItem[];
  simulationData?: {
    runwayP10?: number;
    runwayP50?: number;
    runwayP90?: number;
    survival12m?: number;
    survival18m?: number;
  };
}

function escHtml(str: string): string {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const COLORS = {
  primary: '#6366f1',
  primaryLight: '#818cf8',
  primaryDark: '#4f46e5',
  accent: '#06b6d4',
  accentLight: '#22d3ee',
  success: '#10b981',
  successLight: '#34d399',
  warning: '#f59e0b',
  danger: '#ef4444',
  dangerLight: '#f87171',
  dark: '#0f172a',
  darkAlt: '#1e293b',
  medium: '#475569',
  muted: '#94a3b8',
  light: '#e2e8f0',
  lighter: '#f1f5f9',
  white: '#ffffff',
  gradient1Start: '#4f46e5',
  gradient1End: '#7c3aed',
  gradient2Start: '#0ea5e9',
  gradient2End: '#6366f1',
};

export function generatePDF(slides: SlideData[], companyName: string) {
  const html = buildPrintableHTML(slides, companyName);
  const printWindow = window.open('', '_blank');
  if (!printWindow) return;
  printWindow.document.write(html);
  printWindow.document.close();
  setTimeout(() => {
    printWindow.print();
  }, 600);
}

export function downloadAsHTML(slides: SlideData[], companyName: string) {
  const html = buildPrintableHTML(slides, companyName);
  const blob = new Blob([html], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const safeName = companyName.replace(/[^a-zA-Z0-9]/g, '_');
  a.download = `${safeName}_Board_Deck.html`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function fmtCurrency(n: number): string {
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

function buildSvgLineChart(
  series: { points: ChartPoint[]; color: string; label: string }[],
  width = 700,
  height = 260
): string {
  if (!series.length || !series[0].points.length) return '';

  const pad = { top: 30, right: 30, bottom: 50, left: 70 };
  const w = width - pad.left - pad.right;
  const h = height - pad.top - pad.bottom;

  const allValues = series.flatMap(s => s.points.map(p => p.value));
  const minVal = Math.min(...allValues, 0);
  const maxVal = Math.max(...allValues, 1);
  const range = maxVal - minVal || 1;

  const labels = series[0].points.map(p => p.label);
  const stepX = w / Math.max(labels.length - 1, 1);

  const scaleY = (v: number) => pad.top + h - ((v - minVal) / range) * h;
  const scaleX = (i: number) => pad.left + i * stepX;

  const gridLines = 5;
  let gridHtml = '';
  for (let i = 0; i <= gridLines; i++) {
    const y = pad.top + (h / gridLines) * i;
    const val = maxVal - (range / gridLines) * i;
    gridHtml += `<line x1="${pad.left}" y1="${y}" x2="${pad.left + w}" y2="${y}" stroke="${COLORS.light}" stroke-width="1" stroke-dasharray="4,4"/>`;
    gridHtml += `<text x="${pad.left - 8}" y="${y + 4}" text-anchor="end" fill="${COLORS.muted}" font-size="11" font-family="Inter,system-ui,sans-serif">${fmtCurrency(val)}</text>`;
  }

  let labelHtml = '';
  const labelStep = Math.max(1, Math.floor(labels.length / 6));
  labels.forEach((lbl, i) => {
    if (i % labelStep === 0 || i === labels.length - 1) {
      labelHtml += `<text x="${scaleX(i)}" y="${pad.top + h + 20}" text-anchor="middle" fill="${COLORS.muted}" font-size="10" font-family="Inter,system-ui,sans-serif">${lbl}</text>`;
    }
  });

  let seriesHtml = '';
  series.forEach((s, sIdx) => {
    const gradId = `grad-${sIdx}`;
    const pts = s.points;

    const pathD = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${scaleX(i).toFixed(1)},${scaleY(p.value).toFixed(1)}`).join(' ');
    const areaD = pathD + ` L${scaleX(pts.length - 1).toFixed(1)},${(pad.top + h).toFixed(1)} L${scaleX(0).toFixed(1)},${(pad.top + h).toFixed(1)} Z`;

    seriesHtml += `
      <defs>
        <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${s.color}" stop-opacity="0.25"/>
          <stop offset="100%" stop-color="${s.color}" stop-opacity="0.02"/>
        </linearGradient>
      </defs>
      <path d="${areaD}" fill="url(#${gradId})" />
      <path d="${pathD}" fill="none" stroke="${s.color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    `;

    const lastPt = pts[pts.length - 1];
    seriesHtml += `<circle cx="${scaleX(pts.length - 1).toFixed(1)}" cy="${scaleY(lastPt.value).toFixed(1)}" r="4" fill="${s.color}" stroke="${COLORS.white}" stroke-width="2"/>`;
  });

  let legendHtml = '';
  series.forEach((s, i) => {
    const x = pad.left + i * 140;
    legendHtml += `
      <rect x="${x}" y="${pad.top + h + 35}" width="12" height="12" rx="3" fill="${s.color}"/>
      <text x="${x + 18}" y="${pad.top + h + 45}" fill="${COLORS.medium}" font-size="11" font-family="Inter,system-ui,sans-serif">${s.label}</text>
    `;
  });

  return `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" style="max-width:100%;height:auto;">
      <rect width="${width}" height="${height}" rx="12" fill="${COLORS.white}" />
      ${gridHtml}
      ${labelHtml}
      ${seriesHtml}
      ${legendHtml}
    </svg>
  `;
}

function buildSvgBarChart(
  points: ChartPoint[],
  color: string,
  width = 700,
  height = 220,
  label = ''
): string {
  if (!points.length) return '';

  const pad = { top: 25, right: 20, bottom: 50, left: 70 };
  const w = width - pad.left - pad.right;
  const h = height - pad.top - pad.bottom;

  const maxVal = Math.max(...points.map(p => p.value), 1);
  const barW = Math.min(36, (w / points.length) * 0.6);
  const gap = w / points.length;

  let bars = '';
  const labelStep = Math.max(1, Math.floor(points.length / 8));
  points.forEach((p, i) => {
    const barH = (p.value / maxVal) * h;
    const x = pad.left + i * gap + (gap - barW) / 2;
    const y = pad.top + h - barH;
    bars += `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW}" height="${barH.toFixed(1)}" rx="4" fill="${color}" opacity="${0.6 + (i / points.length) * 0.4}"/>`;
    if (i % labelStep === 0 || i === points.length - 1) {
      bars += `<text x="${(x + barW / 2).toFixed(1)}" y="${pad.top + h + 18}" text-anchor="middle" fill="${COLORS.muted}" font-size="10" font-family="Inter,system-ui,sans-serif">${p.label}</text>`;
    }
  });

  const gridLines = 4;
  let gridHtml = '';
  for (let i = 0; i <= gridLines; i++) {
    const y = pad.top + (h / gridLines) * i;
    const val = maxVal - (maxVal / gridLines) * i;
    gridHtml += `<line x1="${pad.left}" y1="${y}" x2="${pad.left + w}" y2="${y}" stroke="${COLORS.light}" stroke-width="1" stroke-dasharray="4,4"/>`;
    gridHtml += `<text x="${pad.left - 8}" y="${y + 4}" text-anchor="end" fill="${COLORS.muted}" font-size="11" font-family="Inter,system-ui,sans-serif">${fmtCurrency(val)}</text>`;
  }

  return `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" style="max-width:100%;height:auto;">
      <rect width="${width}" height="${height}" rx="12" fill="${COLORS.white}"/>
      ${gridHtml}
      ${bars}
      ${label ? `<text x="${width / 2}" y="${height - 4}" text-anchor="middle" fill="${COLORS.muted}" font-size="11" font-family="Inter,system-ui,sans-serif">${label}</text>` : ''}
    </svg>
  `;
}

function buildGaugeChart(value: number, max: number, label: string, color: string, unit = '', width = 160, height = 130): string {
  const cx = width / 2;
  const cy = height - 20;
  const r = 55;
  const startAngle = Math.PI;
  const endAngle = 0;
  const pct = Math.min(value / max, 1);
  const sweepAngle = startAngle - pct * Math.PI;

  const bgArcStart = `${cx + r * Math.cos(startAngle)},${cy - r * Math.sin(startAngle)}`;
  const bgArcEnd = `${cx + r * Math.cos(endAngle)},${cy - r * Math.sin(endAngle)}`;
  const valArcEnd = `${cx + r * Math.cos(sweepAngle)},${cy - r * Math.sin(sweepAngle)}`;

  return `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
      <path d="M ${bgArcStart} A ${r} ${r} 0 0 1 ${bgArcEnd}" fill="none" stroke="${COLORS.lighter}" stroke-width="12" stroke-linecap="round"/>
      <path d="M ${bgArcStart} A ${r} ${r} 0 0 1 ${valArcEnd}" fill="none" stroke="${color}" stroke-width="12" stroke-linecap="round"/>
      <text x="${cx}" y="${cy - 16}" text-anchor="middle" fill="${COLORS.dark}" font-size="22" font-weight="700" font-family="Inter,system-ui,sans-serif">${value}${unit}</text>
      <text x="${cx}" y="${cy + 2}" text-anchor="middle" fill="${COLORS.muted}" font-size="11" font-family="Inter,system-ui,sans-serif">${label}</text>
    </svg>
  `;
}

function buildDonutChart(pct: number, label: string, color: string, width = 120, height = 140): string {
  const cx = width / 2;
  const cy = 55;
  const r = 40;
  const circ = 2 * Math.PI * r;
  const filled = (pct / 100) * circ;

  return `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${COLORS.lighter}" stroke-width="10"/>
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${color}" stroke-width="10"
        stroke-dasharray="${filled.toFixed(1)} ${(circ - filled).toFixed(1)}"
        stroke-dashoffset="${(circ * 0.25).toFixed(1)}" stroke-linecap="round" transform="rotate(-90,${cx},${cy})"/>
      <text x="${cx}" y="${cy + 5}" text-anchor="middle" fill="${COLORS.dark}" font-size="16" font-weight="700" font-family="Inter,system-ui,sans-serif">${pct}%</text>
      <text x="${cx}" y="${cy + r + 22}" text-anchor="middle" fill="${COLORS.muted}" font-size="10" font-family="Inter,system-ui,sans-serif">${label}</text>
    </svg>
  `;
}

function buildMetricCard(m: MetricItem, idx: number): string {
  const colors = [COLORS.primary, COLORS.accent, COLORS.success, COLORS.warning, COLORS.primaryDark, COLORS.accentLight];
  const borderColor = m.color || colors[idx % colors.length];
  const deltaHtml = m.delta
    ? `<div style="font-size:12px;margin-top:4px;color:${m.delta.startsWith('-') ? COLORS.danger : COLORS.success};font-weight:600;">${m.delta.startsWith('-') ? '↓' : '↑'} ${escHtml(m.delta)}</div>`
    : '';

  return `
    <div style="background:${COLORS.white};border-radius:12px;padding:20px 16px;text-align:center;border:1px solid ${COLORS.light};border-top:3px solid ${borderColor};box-shadow:0 1px 3px rgba(0,0,0,0.06);">
      <div style="font-size:11px;color:${COLORS.muted};text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;font-weight:500;">${escHtml(m.label)}</div>
      <div style="font-size:28px;font-weight:800;color:${COLORS.dark};line-height:1.1;">${escHtml(m.value)}</div>
      ${deltaHtml}
    </div>
  `;
}

function buildScenarioCard(s: ScenarioItem, idx: number): string {
  const colors = [COLORS.primary, COLORS.accent, COLORS.success, COLORS.warning];
  const c = colors[idx % colors.length];
  const runway = s.runwayP50 != null ? `${s.runwayP50.toFixed(1)} mo` : 'N/A';
  const survival = s.survival18m != null ? `${s.survival18m.toFixed(0)}%` : 'N/A';
  const barWidth = s.runwayP50 != null ? Math.min((s.runwayP50 / 36) * 100, 100) : 0;

  return `
    <div style="background:${COLORS.white};border-radius:12px;padding:20px;border:1px solid ${COLORS.light};border-left:4px solid ${c};">
      <div style="font-size:15px;font-weight:700;color:${COLORS.dark};margin-bottom:4px;">${escHtml(s.name)}</div>
      ${s.description ? `<div style="font-size:12px;color:${COLORS.muted};margin-bottom:12px;">${escHtml(s.description)}</div>` : ''}
      <div style="display:flex;gap:24px;margin-bottom:10px;">
        <div>
          <div style="font-size:10px;color:${COLORS.muted};text-transform:uppercase;letter-spacing:0.5px;">Runway P50</div>
          <div style="font-size:20px;font-weight:700;color:${COLORS.dark};">${runway}</div>
        </div>
        <div>
          <div style="font-size:10px;color:${COLORS.muted};text-transform:uppercase;letter-spacing:0.5px;">18m Survival</div>
          <div style="font-size:20px;font-weight:700;color:${COLORS.dark};">${survival}</div>
        </div>
      </div>
      <div style="height:6px;background:${COLORS.lighter};border-radius:3px;overflow:hidden;">
        <div style="height:100%;width:${barWidth}%;background:${c};border-radius:3px;"></div>
      </div>
    </div>
  `;
}

function buildSlideHeader(slideNum: number, totalSlides: number, companyName: string, modelUsed?: string): string {
  let modelBadge = '';
  if (modelUsed && modelUsed !== 'fallback' && modelUsed !== 'unknown') {
    const modelColors: Record<string, string> = {
      claude: '#d97706',
      gpt: '#10b981',
      gemini: '#6366f1',
    };
    const lower = modelUsed.toLowerCase();
    const badgeColor = Object.entries(modelColors).find(([k]) => lower.includes(k))?.[1] || COLORS.muted;
    const displayName = lower.includes('claude') ? 'Claude' : lower.includes('gpt-5.6-terra') ? 'GPT-4o' : lower.includes('gemini') ? 'Gemini' : escHtml(modelUsed);
    modelBadge = `<span style="font-size:9px;color:${badgeColor};background:${badgeColor}15;padding:3px 8px;border-radius:20px;font-weight:600;letter-spacing:0.3px;">${displayName}</span>`;
  }

  return `
    <div style="display:flex;justify-content:space-between;align-items:center;padding-bottom:10px;margin-bottom:24px;border-bottom:1px solid ${COLORS.light};">
      <div style="display:flex;align-items:center;gap:10px;">
        <span style="font-size:11px;color:${COLORS.primary};font-weight:700;letter-spacing:1px;">FC</span>
        <span style="font-size:11px;color:${COLORS.muted};">${escHtml(companyName)}</span>
      </div>
      <div style="display:flex;align-items:center;gap:10px;">
        ${modelBadge}
        <span style="font-size:11px;color:${COLORS.muted};">${slideNum} / ${totalSlides}</span>
      </div>
    </div>
  `;
}

function buildPrintableHTML(slides: SlideData[], companyName: string): string {
  const timestamp = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  const slideHtml = slides.map((slide, idx) => {
    const header = buildSlideHeader(idx + 1, slides.length, companyName, slide.modelUsed);
    let body = '';

    if (slide.type === 'metrics' && slide.metrics && slide.metrics.length > 0) {
      const cols = slide.metrics.length <= 4 ? slide.metrics.length : 3;
      const grid = slide.metrics.map((m, i) => buildMetricCard(m, i)).join('');
      body += `<div style="display:grid;grid-template-columns:repeat(${cols},1fr);gap:16px;margin-top:8px;">${grid}</div>`;
    }

    if (slide.type === 'chart' && slide.chartData) {
      const cd = slide.chartData;
      if (cd.revenue?.length || cd.mrr?.length) {
        const chartSeries: { points: ChartPoint[]; color: string; label: string }[] = [];
        if (cd.revenue?.length) chartSeries.push({ points: cd.revenue, color: COLORS.primary, label: 'Revenue' });
        if (cd.mrr?.length) chartSeries.push({ points: cd.mrr, color: COLORS.accent, label: 'MRR' });
        body += `<div style="margin-top:12px;background:${COLORS.white};border-radius:12px;padding:16px;border:1px solid ${COLORS.light};">${buildSvgLineChart(chartSeries)}</div>`;
      }
      if (cd.burn?.length) {
        body += `<div style="margin-top:16px;background:${COLORS.white};border-radius:12px;padding:16px;border:1px solid ${COLORS.light};">
          <div style="font-size:13px;font-weight:600;color:${COLORS.medium};margin-bottom:8px;">Monthly Burn Rate</div>
          ${buildSvgBarChart(cd.burn, COLORS.danger, 700, 180, 'Burn Rate')}
        </div>`;
      }
      if (cd.cash?.length) {
        body += `<div style="margin-top:16px;background:${COLORS.white};border-radius:12px;padding:16px;border:1px solid ${COLORS.light};">
          <div style="font-size:13px;font-weight:600;color:${COLORS.medium};margin-bottom:8px;">Cash Balance</div>
          ${buildSvgLineChart([{ points: cd.cash, color: COLORS.success, label: 'Cash' }], 700, 180)}
        </div>`;
      }
    }

    if (slide.type === 'simulation') {
      const sim = slide.simulationData;
      if (sim) {
        body += `<div style="display:flex;justify-content:center;gap:24px;margin-top:12px;flex-wrap:wrap;">`;

        if (sim.runwayP10 != null || sim.runwayP50 != null || sim.runwayP90 != null) {
          body += `<div style="background:${COLORS.white};border-radius:12px;padding:20px;border:1px solid ${COLORS.light};flex:1;min-width:280px;">
            <div style="font-size:13px;font-weight:600;color:${COLORS.medium};margin-bottom:16px;">Runway Distribution</div>
            <div style="display:flex;justify-content:center;gap:12px;">
              ${buildGaugeChart(sim.runwayP10 ?? 0, 36, 'P10 (Bear)', COLORS.danger, 'mo')}
              ${buildGaugeChart(sim.runwayP50 ?? 0, 36, 'P50 (Base)', COLORS.primary, 'mo')}
              ${buildGaugeChart(sim.runwayP90 ?? 0, 36, 'P90 (Bull)', COLORS.success, 'mo')}
            </div>
          </div>`;
        }

        if (sim.survival12m != null || sim.survival18m != null) {
          body += `<div style="background:${COLORS.white};border-radius:12px;padding:20px;border:1px solid ${COLORS.light};flex:0 0 280px;">
            <div style="font-size:13px;font-weight:600;color:${COLORS.medium};margin-bottom:16px;">Survival Probability</div>
            <div style="display:flex;justify-content:center;gap:16px;">
              ${sim.survival12m != null ? buildDonutChart(sim.survival12m, '12-Month', COLORS.primary) : ''}
              ${sim.survival18m != null ? buildDonutChart(sim.survival18m, '18-Month', COLORS.accent) : ''}
            </div>
          </div>`;
        }

        body += `</div>`;
      }

      if (slide.metrics && slide.metrics.length > 0 && !sim) {
        const grid = slide.metrics.map((m, i) => buildMetricCard(m, i)).join('');
        body += `<div style="display:grid;grid-template-columns:repeat(${Math.min(slide.metrics.length, 5)},1fr);gap:16px;margin-top:8px;">${grid}</div>`;
      }
    }

    if (slide.type === 'comparison' && slide.scenarios && slide.scenarios.length > 0) {
      const cards = slide.scenarios.map((s, i) => buildScenarioCard(s, i)).join('');
      body += `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-top:8px;">${cards}</div>`;
    }

    if (slide.narrativeHtml) {
      body += `
        <div style="margin-top:${slide.type === 'metrics' || slide.type === 'simulation' ? '24px' : '8px'};padding:20px 24px;background:${COLORS.lighter};border-radius:12px;border-left:4px solid ${COLORS.primary};">
          <div style="line-height:1.8;color:${COLORS.medium};font-size:14px;">${slide.narrativeHtml}</div>
        </div>
      `;
    }

    if (slide.content && !slide.narrativeHtml && slide.type !== 'chart' && slide.type !== 'simulation' && slide.type !== 'comparison') {
      body += `<div style="margin-top:8px;line-height:1.8;color:${COLORS.medium};font-size:14px;white-space:pre-wrap;">${slide.content}</div>`;
    }

    if (slide.imageBase64) {
      body += `<div style="margin-top:20px;text-align:center;">
        <img src="data:image/png;base64,${slide.imageBase64}" style="max-width:100%;max-height:340px;border-radius:12px;border:1px solid ${COLORS.light};box-shadow:0 2px 8px rgba(0,0,0,0.08);" />
      </div>`;
    }

    if (!body.trim()) {
      body = `<div style="padding:40px;text-align:center;color:${COLORS.muted};font-style:italic;">No data available for this section</div>`;
    }

    return `
      <div class="slide">
        ${header}
        <h2 style="font-size:24px;font-weight:800;color:${COLORS.dark};margin:0 0 20px 0;letter-spacing:-0.3px;">${escHtml(slide.title)}</h2>
        ${body}
      </div>
    `;
  }).join('');

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>${escHtml(companyName)} - Board Deck</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    @media print {
      body { margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      @page { size: letter landscape; margin: 0; }
      .slide { page-break-after: always; }
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      color: ${COLORS.dark};
      background: ${COLORS.lighter};
    }
    .slide {
      page-break-after: always;
      padding: 40px 48px;
      min-height: 100vh;
      background: ${COLORS.lighter};
    }
  </style>
</head>
<body>
  <div class="slide" style="background:linear-gradient(135deg,${COLORS.gradient1Start},${COLORS.gradient1End} 50%,${COLORS.gradient2Start});display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;position:relative;overflow:hidden;">
    <div style="position:absolute;top:0;left:0;right:0;bottom:0;opacity:0.08;">
      <svg width="100%" height="100%" viewBox="0 0 800 600">
        <circle cx="100" cy="100" r="200" fill="white"/>
        <circle cx="700" cy="500" r="250" fill="white"/>
        <circle cx="400" cy="300" r="150" fill="white"/>
      </svg>
    </div>
    <div style="position:relative;z-index:1;">
      <div style="display:inline-flex;align-items:center;gap:10px;background:rgba(255,255,255,0.15);backdrop-filter:blur(4px);padding:8px 20px;border-radius:40px;margin-bottom:32px;">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
        <span style="font-size:13px;color:white;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;">FounderConsole</span>
      </div>
      <h1 style="font-size:52px;font-weight:900;color:white;margin-bottom:12px;letter-spacing:-1px;line-height:1.1;">${escHtml(companyName)}</h1>
      <div style="width:60px;height:4px;background:rgba(255,255,255,0.4);border-radius:2px;margin:20px auto;"></div>
      <p style="font-size:18px;color:rgba(255,255,255,0.8);font-weight:500;">${timestamp}</p>
      <div style="margin-top:40px;display:inline-flex;gap:20px;">
        <div style="background:rgba(255,255,255,0.12);border-radius:12px;padding:12px 24px;backdrop-filter:blur(4px);">
          <div style="font-size:10px;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px;">Deck Type</div>
          <div style="font-size:14px;color:white;font-weight:600;">Board Presentation</div>
        </div>
        <div style="background:rgba(255,255,255,0.12);border-radius:12px;padding:12px 24px;backdrop-filter:blur(4px);">
          <div style="font-size:10px;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px;">Slides</div>
          <div style="font-size:14px;color:white;font-weight:600;">${slides.length} Pages</div>
        </div>
        <div style="background:rgba(255,255,255,0.12);border-radius:12px;padding:12px 24px;backdrop-filter:blur(4px);">
          <div style="font-size:10px;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px;">Powered By</div>
          <div style="font-size:14px;color:white;font-weight:600;">AI Intelligence</div>
        </div>
      </div>
    </div>
  </div>
  ${slideHtml}
</body>
</html>`;
}

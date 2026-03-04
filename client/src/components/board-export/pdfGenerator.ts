export interface SlideData {
  title: string;
  type: 'metrics' | 'chart' | 'simulation' | 'narrative' | 'comparison';
  content: string;
  metrics?: { label: string; value: string; delta?: string }[];
  narrativeHtml?: string;
  modelUsed?: string;
  providerUsed?: string;
  imageBase64?: string;
}

export function generatePDF(slides: SlideData[], companyName: string) {
  const html = buildPrintableHTML(slides, companyName);
  const printWindow = window.open('', '_blank');
  if (!printWindow) return;
  printWindow.document.write(html);
  printWindow.document.close();
  setTimeout(() => {
    printWindow.print();
  }, 500);
}

function buildPrintableHTML(slides: SlideData[], companyName: string): string {
  const timestamp = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  const slideHtml = slides.map((slide, idx) => {
    let body = '';

    if (slide.metrics && slide.metrics.length > 0) {
      const metricsGrid = slide.metrics
        .map(
          m => `
        <div style="background:#f8f9fa;border-radius:8px;padding:16px;text-align:center;">
          <div style="font-size:12px;color:#6b7280;margin-bottom:4px;">${m.label}</div>
          <div style="font-size:24px;font-weight:700;color:#111827;">${m.value}</div>
          ${m.delta ? `<div style="font-size:12px;color:${m.delta.startsWith('-') ? '#ef4444' : '#22c55e'};margin-top:2px;">${m.delta}</div>` : ''}
        </div>
      `
        )
        .join('');
      body += `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-top:12px;">${metricsGrid}</div>`;
    }

    if (slide.narrativeHtml) {
      body += `<div style="margin-top:16px;line-height:1.7;color:#374151;font-size:14px;">${slide.narrativeHtml}</div>`;
    }

    if (slide.content && !slide.narrativeHtml) {
      body += `<div style="margin-top:16px;line-height:1.7;color:#374151;font-size:14px;white-space:pre-wrap;">${slide.content}</div>`;
    }

    if (slide.imageBase64) {
      body += `<div style="margin-top:20px;text-align:center;">
        <img src="data:image/png;base64,${slide.imageBase64}" style="max-width:100%;max-height:400px;border-radius:8px;border:1px solid #e5e7eb;" />
      </div>`;
    }

    let modelBadge = '';
    if (slide.modelUsed && slide.modelUsed !== 'fallback') {
      modelBadge = `<span style="font-size:10px;color:#6366f1;background:#eef2ff;padding:2px 8px;border-radius:4px;font-weight:500;">${slide.modelUsed}</span>`;
    }

    return `
      <div style="page-break-after:always;padding:40px;min-height:90vh;box-sizing:border-box;">
        <div style="border-bottom:2px solid #e5e7eb;padding-bottom:12px;margin-bottom:24px;display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:12px;color:#9ca3af;">Slide ${idx + 1} of ${slides.length}</span>
          ${modelBadge}
        </div>
        <h2 style="font-size:22px;font-weight:700;color:#111827;margin-bottom:16px;">${slide.title}</h2>
        ${body}
      </div>
    `;
  }).join('');

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>${companyName} - Board Deck</title>
  <style>
    @media print {
      body { margin: 0; }
      @page { size: letter landscape; margin: 0; }
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      color: #111827;
      margin: 0;
      padding: 0;
    }
  </style>
</head>
<body>
  <div style="page-break-after:always;padding:60px;min-height:90vh;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;box-sizing:border-box;">
    <div style="font-size:14px;color:#6366f1;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:16px;">FounderConsole</div>
    <h1 style="font-size:36px;font-weight:800;margin-bottom:8px;">${companyName}</h1>
    <p style="font-size:16px;color:#6b7280;">${timestamp}</p>
  </div>
  ${slideHtml}
</body>
</html>`;
}

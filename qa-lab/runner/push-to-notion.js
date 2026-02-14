#!/usr/bin/env node
/**
 * Pushes QA Lab report to Notion as a page.
 * Uses Replit's Notion connection for authentication.
 * 
 * Usage: node qa-lab/runner/push-to-notion.js [path-to-report.md]
 */

import { Client } from '@notionhq/client';
import fs from 'fs';
import path from 'path';

let connectionSettings = null;

async function getAccessToken() {
  if (connectionSettings && connectionSettings.settings.expires_at && new Date(connectionSettings.settings.expires_at).getTime() > Date.now()) {
    return connectionSettings.settings.access_token;
  }

  const hostname = process.env.REPLIT_CONNECTORS_HOSTNAME;
  if (!hostname) {
    throw new Error('REPLIT_CONNECTORS_HOSTNAME not set. Ensure the Notion integration is configured in your Replit project.');
  }

  const xReplitToken = process.env.REPL_IDENTITY
    ? 'repl ' + process.env.REPL_IDENTITY
    : process.env.WEB_REPL_RENEWAL
    ? 'depl ' + process.env.WEB_REPL_RENEWAL
    : null;

  if (!xReplitToken) {
    throw new Error('Replit token not found - ensure Notion connection is configured');
  }

  connectionSettings = await fetch(
    'https://' + hostname + '/api/v2/connection?include_secrets=true&connector_names=notion',
    {
      headers: {
        'Accept': 'application/json',
        'X_REPLIT_TOKEN': xReplitToken
      }
    }
  ).then(res => res.json()).then(data => data.items?.[0]);

  const accessToken = connectionSettings?.settings?.access_token || connectionSettings?.settings?.oauth?.credentials?.access_token;

  if (!connectionSettings || !accessToken) {
    throw new Error('Notion not connected');
  }
  return accessToken;
}

async function getNotionClient() {
  const accessToken = await getAccessToken();
  return new Client({ auth: accessToken });
}

function parseReport(reportPath) {
  const content = fs.readFileSync(reportPath, 'utf-8');
  const lines = content.split('\n');

  let title = 'QA Lab Report';
  let summary = {};
  let sections = [];
  let currentSection = null;

  for (const line of lines) {
    if (line.startsWith('# ')) {
      title = line.replace('# ', '').trim();
    } else if (line.startsWith('**Generated**:')) {
      summary.generated = line.replace('**Generated**:', '').trim();
    } else if (line.startsWith('**Duration**:')) {
      summary.duration = line.replace('**Duration**:', '').trim();
    } else if (line.startsWith('**Monte Carlo**:')) {
      summary.monteCarlo = line.replace('**Monte Carlo**:', '').trim();
    } else if (line.startsWith('## ')) {
      if (currentSection) sections.push(currentSection);
      currentSection = { heading: line.replace('## ', '').trim(), lines: [] };
    } else if (line.startsWith('### ')) {
      if (currentSection) {
        currentSection.lines.push(line);
      }
    } else if (currentSection) {
      currentSection.lines.push(line);
    }
  }
  if (currentSection) sections.push(currentSection);

  let totalTests = 0, passed = 0, failed = 0, passRate = '0%';
  const summarySection = sections.find(s => s.heading === 'Summary');
  if (summarySection) {
    for (const l of summarySection.lines) {
      const m = l.match(/\|\s*Total Tests\s*\|\s*(\d+)/);
      if (m) totalTests = parseInt(m[1]);
      const mp = l.match(/\|\s*Passed\s*\|\s*(\d+)/);
      if (mp) passed = parseInt(mp[1]);
      const mf = l.match(/\|\s*Failed\s*\|\s*(\d+)/);
      if (mf) failed = parseInt(mf[1]);
      const mr = l.match(/\|\s*Pass Rate\s*\|\s*([^\|]+)/);
      if (mr) passRate = mr[1].trim();
    }
  }

  return { title, summary, sections, totalTests, passed, failed, passRate, rawContent: content };
}

function mdLineToRichText(line) {
  const result = [];
  const regex = /(\*\*(.+?)\*\*|`(.+?)`|([^*`]+))/g;
  let match;
  while ((match = regex.exec(line)) !== null) {
    if (match[2]) {
      result.push({ type: 'text', text: { content: match[2] }, annotations: { bold: true } });
    } else if (match[3]) {
      result.push({ type: 'text', text: { content: match[3] }, annotations: { code: true } });
    } else if (match[4]) {
      result.push({ type: 'text', text: { content: match[4] } });
    }
  }
  return result.length > 0 ? result : [{ type: 'text', text: { content: line } }];
}

function chunkArray(arr, size) {
  const chunks = [];
  for (let i = 0; i < arr.length; i += size) {
    chunks.push(arr.slice(i, i + size));
  }
  return chunks;
}

function buildBlocks(parsed) {
  const blocks = [];

  const statusEmoji = parsed.failed === 0 ? 'white_check_mark' : 'x';
  
  blocks.push({
    object: 'block',
    type: 'callout',
    callout: {
      icon: { type: 'emoji', emoji: parsed.failed === 0 ? '\u2705' : '\u274C' },
      rich_text: [{
        type: 'text',
        text: { content: `${parsed.passed}/${parsed.totalTests} tests passed (${parsed.passRate}) | ${parsed.summary.duration || 'N/A'} | ${parsed.summary.monteCarlo || ''}` }
      }],
      color: parsed.failed === 0 ? 'green_background' : 'red_background',
    }
  });

  blocks.push({
    object: 'block',
    type: 'divider',
    divider: {}
  });

  for (const section of parsed.sections) {
    blocks.push({
      object: 'block',
      type: 'heading_2',
      heading_2: {
        rich_text: [{ type: 'text', text: { content: section.heading } }]
      }
    });

    let tableLines = [];
    let inTable = false;

    for (const line of section.lines) {
      const trimmed = line.trim();
      if (!trimmed) {
        if (inTable && tableLines.length > 0) {
          blocks.push(...buildTableBlocks(tableLines));
          tableLines = [];
          inTable = false;
        }
        continue;
      }

      if (trimmed.startsWith('|')) {
        inTable = true;
        tableLines.push(trimmed);
        continue;
      }

      if (inTable && tableLines.length > 0) {
        blocks.push(...buildTableBlocks(tableLines));
        tableLines = [];
        inTable = false;
      }

      if (trimmed.startsWith('### ')) {
        blocks.push({
          object: 'block',
          type: 'heading_3',
          heading_3: {
            rich_text: [{ type: 'text', text: { content: trimmed.replace('### ', '') } }]
          }
        });
      } else if (trimmed.startsWith('- ')) {
        blocks.push({
          object: 'block',
          type: 'bulleted_list_item',
          bulleted_list_item: {
            rich_text: mdLineToRichText(trimmed.replace(/^- /, ''))
          }
        });
      } else if (trimmed.startsWith('---')) {
        blocks.push({ object: 'block', type: 'divider', divider: {} });
      } else if (trimmed.startsWith('*') && trimmed.endsWith('*')) {
        blocks.push({
          object: 'block',
          type: 'paragraph',
          paragraph: {
            rich_text: [{ type: 'text', text: { content: trimmed.replace(/^\*+|\*+$/g, '') }, annotations: { italic: true } }],
            color: 'gray'
          }
        });
      } else {
        blocks.push({
          object: 'block',
          type: 'paragraph',
          paragraph: { rich_text: mdLineToRichText(trimmed) }
        });
      }
    }

    if (inTable && tableLines.length > 0) {
      blocks.push(...buildTableBlocks(tableLines));
    }
  }

  return blocks;
}

function buildTableBlocks(tableLines) {
  const dataRows = tableLines.filter(l => !l.match(/^\|[\s\-:|]+\|$/));
  if (dataRows.length === 0) return [];

  const parseRow = (line) => line.split('|').filter((_, i, arr) => i > 0 && i < arr.length - 1).map(c => c.trim());

  const rows = dataRows.map(parseRow);
  const colCount = rows[0]?.length || 0;
  if (colCount === 0) return [];

  const headerRow = rows[0];
  const bodyRows = rows.slice(1);
  const MAX_ROWS = 98;
  const chunks = chunkArray(bodyRows, MAX_ROWS);
  const tables = [];

  for (const chunk of chunks) {
    const allRows = [headerRow, ...chunk];
    tables.push({
      object: 'block',
      type: 'table',
      table: {
        table_width: colCount,
        has_column_header: true,
        has_row_header: false,
        children: allRows.map(row => ({
          type: 'table_row',
          table_row: {
            cells: row.map(cell => [{ type: 'text', text: { content: cell.substring(0, 2000) } }])
          }
        }))
      }
    });
  }

  return tables;
}

async function findOrCreateQADatabase(notion) {
  const searchRes = await notion.search({
    query: 'Predixen QA Reports',
    filter: { property: 'object', value: 'database' }
  });

  const existing = searchRes.results.find(r =>
    r.object === 'database' && r.title?.some(t => t.plain_text?.includes('Predixen QA Reports'))
  );

  if (existing) {
    console.log(`Found existing QA Reports database: ${existing.id}`);
    return existing.id;
  }

  const pagesRes = await notion.search({
    filter: { property: 'object', value: 'page' }
  });

  let parentPageId = null;
  for (const page of pagesRes.results) {
    const titleProp = page.properties?.title?.title || page.properties?.Name?.title;
    if (titleProp) {
      parentPageId = page.id;
      break;
    }
  }

  if (!parentPageId && pagesRes.results.length > 0) {
    parentPageId = pagesRes.results[0].id;
  }

  if (!parentPageId) {
    throw new Error('No accessible Notion pages found. Please share at least one page with the Predixen integration.');
  }

  console.log(`Creating QA Reports database under page ${parentPageId}...`);

  const db = await notion.databases.create({
    parent: { type: 'page_id', page_id: parentPageId },
    title: [{ type: 'text', text: { content: 'Predixen QA Reports' } }],
    properties: {
      'Report': { title: {} },
      'Status': {
        select: {
          options: [
            { name: 'All Passed', color: 'green' },
            { name: 'Has Failures', color: 'red' },
          ]
        }
      },
      'Pass Rate': { rich_text: {} },
      'Tests': { number: {} },
      'Passed': { number: { format: 'number' } },
      'Failed': { number: { format: 'number' } },
      'Duration': { rich_text: {} },
      'Run Date': { date: {} },
    }
  });

  console.log(`Created QA Reports database: ${db.id}`);
  return db.id;
}

async function pushReport(reportPath) {
  console.log(`\nPushing QA report to Notion...`);
  console.log(`Report: ${reportPath}`);

  if (!fs.existsSync(reportPath)) {
    console.error(`Report file not found: ${reportPath}`);
    process.exit(1);
  }

  const parsed = parseReport(reportPath);
  const notion = await getNotionClient();
  const databaseId = await findOrCreateQADatabase(notion);

  const runDate = parsed.summary.generated
    ? new Date(parsed.summary.generated).toISOString().split('T')[0]
    : new Date().toISOString().split('T')[0];

  const pageTitle = `QA Run — ${parsed.summary.generated || new Date().toISOString()} — ${parsed.passRate}`;

  console.log(`Creating page: ${pageTitle}`);

  const page = await notion.pages.create({
    parent: { database_id: databaseId },
    icon: { type: 'emoji', emoji: parsed.failed === 0 ? '\u2705' : '\u274C' },
    properties: {
      'Report': { title: [{ text: { content: pageTitle } }] },
      'Status': { select: { name: parsed.failed === 0 ? 'All Passed' : 'Has Failures' } },
      'Pass Rate': { rich_text: [{ text: { content: parsed.passRate } }] },
      'Tests': { number: parsed.totalTests },
      'Passed': { number: parsed.passed },
      'Failed': { number: parsed.failed },
      'Duration': { rich_text: [{ text: { content: parsed.summary.duration || 'N/A' } }] },
      'Run Date': { date: { start: runDate } },
    }
  });

  console.log(`Page created: ${page.id}`);

  const allBlocks = buildBlocks(parsed);
  const chunks = chunkArray(allBlocks, 100);

  for (let i = 0; i < chunks.length; i++) {
    await notion.blocks.children.append({
      block_id: page.id,
      children: chunks[i],
    });
    if (i < chunks.length - 1) {
      await new Promise(r => setTimeout(r, 350));
    }
  }

  console.log(`\nDone! ${allBlocks.length} blocks pushed to Notion.`);
  console.log(`View: https://notion.so/${page.id.replace(/-/g, '')}`);
}

const reportPath = process.argv[2] || path.resolve('qa-lab/latest-report.md');
pushReport(reportPath).catch(err => {
  console.error('Failed to push to Notion:', err.message);
  process.exit(1);
});

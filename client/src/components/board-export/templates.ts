export interface TemplateSection {
  type: 'metrics' | 'chart' | 'simulation' | 'narrative' | 'comparison';
  title: string;
  dataSource: string;
  aiNarrative: boolean;
}

export interface BoardTemplate {
  id: string;
  name: string;
  description: string;
  sections: TemplateSection[];
}

export const monthlyUpdate: BoardTemplate = {
  id: 'monthly-update',
  name: 'Monthly Update',
  description: 'Standard monthly board update with key metrics and narrative',
  sections: [
    { type: 'narrative', title: 'Executive Summary', dataSource: 'truth_scan', aiNarrative: true },
    { type: 'metrics', title: 'Key Financial Metrics', dataSource: 'metrics', aiNarrative: false },
    { type: 'chart', title: 'Revenue & Burn Trend', dataSource: 'financials', aiNarrative: false },
    { type: 'metrics', title: 'Unit Economics', dataSource: 'unit_economics', aiNarrative: false },
    { type: 'narrative', title: 'Operational Highlights', dataSource: 'decisions', aiNarrative: true },
    { type: 'narrative', title: 'Risks & Mitigations', dataSource: 'risks', aiNarrative: true },
  ],
};

export const fundraisingPrep: BoardTemplate = {
  id: 'fundraising-prep',
  name: 'Fundraising Prep',
  description: 'Investor-ready deck with traction data and growth narrative',
  sections: [
    { type: 'narrative', title: 'Company Overview', dataSource: 'truth_scan', aiNarrative: true },
    { type: 'metrics', title: 'Traction Metrics', dataSource: 'metrics', aiNarrative: false },
    { type: 'chart', title: 'Growth Trajectory', dataSource: 'financials', aiNarrative: false },
    { type: 'metrics', title: 'Unit Economics & Efficiency', dataSource: 'unit_economics', aiNarrative: false },
    { type: 'simulation', title: 'Forward Projections', dataSource: 'simulations', aiNarrative: false },
    { type: 'narrative', title: 'Market Opportunity', dataSource: 'market', aiNarrative: true },
    { type: 'narrative', title: 'Use of Funds', dataSource: 'fundraising', aiNarrative: true },
  ],
};

export const scenarioAnalysis: BoardTemplate = {
  id: 'scenario-analysis',
  name: 'Scenario Analysis',
  description: 'Multi-scenario comparison with simulation results',
  sections: [
    { type: 'narrative', title: 'Scenario Overview', dataSource: 'scenarios', aiNarrative: true },
    { type: 'comparison', title: 'Scenario Comparison', dataSource: 'scenarios', aiNarrative: false },
    { type: 'simulation', title: 'Monte Carlo Results', dataSource: 'simulations', aiNarrative: false },
    { type: 'metrics', title: 'Key Metrics by Scenario', dataSource: 'metrics', aiNarrative: false },
    { type: 'narrative', title: 'Risk Assessment', dataSource: 'risks', aiNarrative: true },
    { type: 'narrative', title: 'Recommended Path Forward', dataSource: 'decisions', aiNarrative: true },
  ],
};

export const BOARD_TEMPLATES: BoardTemplate[] = [monthlyUpdate, fundraisingPrep, scenarioAnalysis];

export function getTemplateById(id: string): BoardTemplate | undefined {
  return BOARD_TEMPLATES.find(t => t.id === id);
}

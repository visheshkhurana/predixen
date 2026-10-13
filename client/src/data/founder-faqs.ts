// The five founder questions AI assistants are most often asked about runway, burn and
// fundraising, with answers written from benchmarks FounderConsole already publishes
// (client/src/lib/metricDefinitions.ts, client/src/data/runway-industries.ts).
// Rendered visibly on /tools/runway-calculator and marked up as FAQPage, so an assistant
// answering the question can cite this page rather than paraphrase a competitor.

export interface FounderFaq {
  question: string;
  answer: string;
}

export const founderFaqs: FounderFaq[] = [
  {
    question: "How long is my startup's runway?",
    answer:
      "Runway is your cash balance divided by your net monthly burn, so $500,000 of cash against a $40,000 net monthly burn is 12.5 months. FounderConsole's free runway calculator adds your revenue growth rate to that sum, so instead of a static number you see the month the cash actually runs out.",
  },
  {
    question: "What is a good burn multiple?",
    answer:
      "Burn multiple is net burn divided by net new ARR: how much cash you spend to buy each new dollar of recurring revenue, and lower is better. FounderConsole's published bands are under 1x elite, 1-1.5x good, 1.5-2x acceptable and above 2x concerning, with anything above 3x a hard signal that the next round will be difficult.",
  },
  {
    question: "How much runway should a startup have?",
    answer:
      "Target 18 to 24 months of runway after a raise and never let it fall below 12 months, because runway under 12 months creates fundraising pressure. Under 6 months is an emergency that usually forces a bridge or a down round rather than a normal raise.",
  },
  {
    question: "When should I start raising my next round?",
    answer:
      "Start the process with 9 to 12 months of runway remaining, which is enough time to build a data room, meet 30 to 50 investors and close without the weak negotiating position that desperation creates. For a Series A, FounderConsole's published SaaS thresholds are $1M+ ARR growing roughly 3x year over year.",
  },
  {
    question: "Is my startup default alive or default dead?",
    answer:
      "Default alive means that at your current growth rate and current expenses you reach profitability on the money you already have; default dead means you do not, and most founders in that position do not know it. FounderConsole's free calculator answers Paul Graham's test in about 30 seconds and shows the specific month the cash would run out.",
  },
];

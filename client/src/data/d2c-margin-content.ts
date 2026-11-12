/**
 * Copy for /tools/d2c-contribution-margin that both the React page and the
 * server prerender (server/seo-prerender.ts) render, so the answer a crawler or
 * an AI assistant reads and the one a visitor reads are the same text.
 * No "@/" imports: the server imports this file by relative path.
 */

export const D2C_MARGIN_DEFINITIONS: ReadonlyArray<{ term: string; definition: string }> = [
  {
    term: "Net revenue",
    definition:
      "The value of orders that were delivered and kept, excluding GST, after discounts. RTO'd orders and customer returns are not revenue.",
  },
  {
    term: "CM1 (contribution margin 1)",
    definition: "Net revenue minus cost of goods sold (COGS): the gross margin on what customers actually kept.",
  },
  {
    term: "CM2 (contribution margin 2)",
    definition:
      "CM1 minus fulfilment (forward shipping, packaging, reverse shipping on RTO and returns) and payment costs (gateway fees on prepaid orders, COD fees).",
  },
  {
    term: "CM3 (contribution margin 3)",
    definition:
      "CM2 minus marketing spend. CM3 is what each order contributes towards fixed costs (team, rent, software) and profit.",
  },
  {
    term: "MER (marketing efficiency ratio)",
    definition:
      "Net revenue divided by total marketing spend, across every channel. Unlike platform ROAS, it cannot be inflated by attribution.",
  },
  {
    term: "Break-even MER",
    definition: "1 divided by the CM2 margin. Below this MER, every rupee of marketing loses money at CM3.",
  },
];

export const D2C_MARGIN_FAQS: ReadonlyArray<{ question: string; answer: string }> = [
  {
    question: "What is the difference between CM1, CM2 and CM3?",
    answer:
      "CM1 is net revenue minus COGS. CM2 subtracts the variable cost of getting an order to the customer and getting paid for it: shipping, packaging, RTO and return logistics, payment gateway and COD fees. CM3 subtracts marketing. Each layer answers a different question: CM1 is product pricing, CM2 is operations, CM3 is whether growth pays for itself.",
  },
  {
    question: "What is a good CM3 for a D2C brand?",
    answer:
      "There is no published, sourced benchmark for Indian D2C CM3 that we can point to, so this page does not quote one. The test that matters is arithmetic: CM3 has to cover your monthly fixed costs before the business stops burning cash. If CM3 is negative, more orders make the loss bigger.",
  },
  {
    question: "How does RTO affect contribution margin?",
    answer:
      "An RTO (return to origin) order pays forward shipping, packaging and reverse shipping, and earns no revenue. The marketing that acquired it is also wasted. In the worked example on this page, raising RTO from 18% to 30% with everything else unchanged cuts monthly CM3 from ₹3.27 lakh to ₹1.38 lakh.",
  },
  {
    question: "Should contribution margin be calculated including GST?",
    answer:
      "No. GST collected on a sale is owed to the government, so revenue for margin purposes should be ex-GST. Shopify order totals often include GST when prices are tax-inclusive, which overstates revenue if used directly.",
  },
  {
    question: "What is the difference between MER and ROAS?",
    answer:
      "ROAS is the revenue an ad platform attributes to its own ads divided by spend on that platform. MER is total net revenue divided by total marketing spend. Platforms can double-count the same order, so the sum of platform ROAS often exceeds what the bank account shows; MER cannot.",
  },
];

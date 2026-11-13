// India is the primary market: amounts for an INR company read in lakhs and
// crores (₹12.5L, ₹3.2Cr) with Indian grouping (₹12,50,000), and formatters
// that are not handed a currency follow the selected company instead of USD.
import assert from "assert";
import {
  formatBaseToDisplay,
  formatInrCompact,
  formatInrFull,
  getDisplayCurrency,
  setDisplayCurrency,
} from "../../client/src/lib/money";
import { formatCurrencyAbbrev, formatCurrencyFull } from "../../client/src/lib/utils";
import { formatCurrency } from "../../client/src/lib/formatters";

assert.equal(formatInrCompact(32_000_000), "₹3.2Cr");
assert.equal(formatInrCompact(1_250_000), "₹12.5L");
assert.equal(formatInrCompact(500_000), "₹5L");
assert.equal(formatInrCompact(45_000), "₹45K");
assert.equal(formatInrCompact(850), "₹850");
assert.equal(formatInrCompact(-2_000_000), "-₹20L");
assert.equal(formatInrCompact(null), "N/A");
assert.equal(formatInrFull(1_250_000), "₹12,50,000");

// USD default: dollar output unchanged.
assert.equal(getDisplayCurrency(), "USD");
assert.equal(formatCurrencyAbbrev(1_500_000), "$1.5M");
assert.equal(formatCurrency(1_500_000), "$1.5M");
assert.equal(formatCurrencyFull(1500), "$1,500");

// INR company.
setDisplayCurrency("inr");
assert.equal(formatCurrencyAbbrev(1_250_000), "₹12.5L");
assert.equal(formatCurrency(32_000_000), "₹3.2Cr");
assert.equal(formatCurrencyFull(1_250_000), "₹12,50,000");
assert.equal(formatBaseToDisplay(32_000_000), "₹3.2Cr");

// Explicit currency or prefix still wins.
assert.equal(formatCurrencyAbbrev(1_500_000, "USD"), "$1.5M");
assert.equal(formatCurrency(1_500_000, "$"), "$1.5M");

setDisplayCurrency("<script>");
assert.equal(getDisplayCurrency(), "USD", "junk codes fall back to USD");

console.log("PASS  inr-format");

// 402 plan_limit_reached must open the upgrade dialog with the server's message;
// any other error must not.
import assert from "assert";
import { planLimitFromError, planLimitNoun, planLimitTitle } from "../../client/src/lib/planLimit";

const detail = {
  error: "plan_limit_reached",
  limit: "max_simulations_per_month",
  used: 3,
  max: 3,
  current_plan: "free",
  message: "You've used all 3 simulations for this month on the Free plan. Upgrade your plan for more, or wait for the month to reset at 00:00 UTC on the 1st.",
};
const info = planLimitFromError(402, detail)!;
assert.ok(info);
assert.equal(info.limit, "max_simulations_per_month");
assert.equal(info.used, 3);
assert.equal(info.max, 3);
assert.equal(info.currentPlan, "free");
assert.equal(info.message, detail.message);
assert.equal(planLimitNoun(info.limit), "simulations");
assert.equal(planLimitNoun("max_copilot_messages_per_month"), "Copilot messages");
assert.equal(planLimitTitle("max_copilot_messages_per_month"), "You've used this month's Copilot messages");
assert.equal(planLimitTitle("max_connectors"), "You've reached your plan's data connectors");

assert.equal(planLimitFromError(403, detail), null, "403 feature_locked is not a quota");
assert.equal(planLimitFromError(402, { error: "payment_required" }), null);
assert.equal(planLimitFromError(402, "Payment required"), null);
assert.equal(planLimitFromError(402, null), null);
assert.match(planLimitFromError(402, { error: "plan_limit_reached" })!.message, /Upgrade/);
console.log("plan-limit-dialog: ok");

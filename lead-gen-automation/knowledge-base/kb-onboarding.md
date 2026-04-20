# FounderConsole — Onboarding Help

> Paste into a Google Doc titled **"KB — Onboarding"**. The AI agent uses this when users reply with stuck / bug / help messages after signing up.

## The three numbers you need for a first simulation

Before you can run the Survival Simulator you need:

1. **Current cash balance** — total in all bank accounts, including any uncalled-but-committed funding you're certain of
2. **Monthly burn rate** — expenses minus revenue, averaged over the last 3 months (use last month if you're pre-revenue)
3. **MRR** — monthly recurring revenue (put `0` if pre-revenue)

That's it. Takes 90 seconds if you have access to your bank + Stripe/Chargebee dashboards.

## Step-by-step first simulation

1. Go to founderconsole.ai/simulator
2. Click "Start a simulation"
3. Enter the 3 numbers above
4. Click "Run simulation" — takes 2–3 seconds
5. You'll see: runway in months, P50 survival, P90 survival, and a sensitivity chart

First-run average: 4 minutes end-to-end.

## Common first-run mistakes

### "My P50 looks way lower than my naive runway"

That's correct and that's the point. Naive runway = cash / burn. P50 = probability-weighted survival given growth variance. The gap is usually 20–40% because spreadsheets assume growth continues at a constant rate; reality has dips.

### "Growth variance seems high"

Default variance is calibrated on YC-stage SaaS data (~30% standard deviation on monthly growth rate month-over-month). If your business is more stable (enterprise with long contracts), bring it down to 10–15% in the advanced settings.

### "I don't know my monthly burn, I just have annual"

Divide annual by 12. Good enough for a first sim.

### "Hiring a new engineer — how do I model that?"

Two ways:
- **Quick:** add their monthly cost (salary × 1.3 for burden) to your burn, re-run
- **Proper (Pro):** go to the Scenarios tab, create a "With new hire" scenario alongside your baseline, compare survival curves

### "The Survival Simulator shows my runway in years, not months"

Congrats — you have >24 months runway. Happens to well-funded seed/Series A companies. The simulator auto-switches units. You can toggle back in the display settings.

## Where to find the main tabs

After running your first simulation:

- **Runway tab** — your P50/P90 survival + sensitivity analysis (where to cut / where growth matters most)
- **Scenarios tab** (Pro only) — saved what-ifs, side-by-side comparison
- **Cap Table tab** (Pro only) — model founder/employee/investor ownership
- **Dilution tab** (Pro only) — post-round preview

If you don't see Scenarios / Cap Table / Dilution, you're on the Free tier. They unlock on Pro.

## Common bugs (known issues)

### "Simulation ran but shows NaN for survival"

Usually means your burn is negative (i.e., you're profitable). The simulator needs a burn > 0. Workaround: set burn to $1 to get a very-high runway result. Real fix is in the Feb 2026 update.

### "Cap table won't let me add a second round"

You need to fill in the first round completely (valuation, amount raised, investor name) before the "+ Add round" button activates. UX bug, will be fixed.

### "PDF export cuts off the last page"

Known Safari issue. Use Chrome for PDF export as a workaround.

### "I invited a teammate but they can't see my scenarios"

Check that you're on Team ($99/mo) plan — Pro is single-user. On Team, make sure they accepted the invite email and joined your workspace (not created their own).

## When to reach out to us

- Any time a simulation returns obviously wrong numbers
- Any time a feature in Pro/Team isn't working
- Any time you have a feature request (we read all of them)

Email: vishesh@founderconsole.ai
Response time: <24h on weekdays

## When NOT to reach out (we can't help)

- Tax / legal / regulatory advice on your fundraising — get a real CFO or lawyer
- "Is this valuation reasonable?" — that's not what we do, try Carta Benchmarks
- "What should my burn be?" — depends entirely on your stage and strategy

## Escalation wording for bugs

If the AI agent can't resolve an onboarding issue, reply with:
> "This looks like a bug I want to look at personally. Can you send me a screenshot and the email you signed up with? I'll look into it this afternoon."
> — Vishesh

Then tag the thread for human review.

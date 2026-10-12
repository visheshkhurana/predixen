# RUN_MIGRATIONS=true prod audit

Date: 2026-10-12. Read-only. `server/core/migrations.py` is 1,811 lines. This audit does not change what that file does.

Scope: what `settings.should_run_migrations` runs. In production that property is true only when `RUN_MIGRATIONS=true` (`server/core/config.py` 92–97). The Dockerfile sets `ENVIRONMENT=production`, so the default is off. The call site is `server/main.py` 237–240, which calls `run_migrations(engine)` (`server/core/migrations.py` 1000–1053).

`run_migrations` calls the helpers below in this order, each on its own connection. There is no wrapper transaction and no advisory lock. A raised exception stops the rest of the list. Helpers that already committed stay committed.

The file contains no `INSERT`, `UPDATE`, `DELETE FROM`, `DROP TABLE`, `DROP COLUMN`, or `TRUNCATE`.

## Verdict

**STOP.** Do not flip `RUN_MIGRATIONS=true` as the one-time prod deploy for the three provenance columns.

The three columns themselves are a safe, idempotent, metadata-only add. The flag does not run only those columns. On a populated Postgres the later helper `ensure_simulation_accuracy_tables` is expected to error, raise out of `run_migrations`, and leave deferred startup not ready, after every earlier helper has already committed.

## Flags

1. **Transaction abort that stops the boot** (`server/core/migrations.py` 1716–1727). The same function creates `simulation_accuracy.variance_pct_json` as `JSONB` (1689), then runs:

```sql
ALTER TABLE simulation_accuracy
ALTER COLUMN variance_pct_json TYPE JSONB USING variance_pct_json::jsonb
```

On PostgreSQL, altering a column to the type it already has fails with `column "variance_pct_json" of relation "simulation_accuracy" is already of type jsonb`. That aborts the open transaction. The `except: pass` does not roll back to a savepoint. `conn.commit()` at 1727 then runs on the aborted transaction and raises. `run_migrations` has no per-call guard, so it stops before:

- `ensure_copilot_feedback_table` (1731)
- `ensure_agent_simulation_runs_table` (1762)
- `ensure_subscription_trial_columns` (1795)

`server/main.py` 354–358 records the exception and does not set `ready`. `/health` then reports `degraded` (`server/main.py` 515) and still returns HTTP 200, so Railway's `/health` check can stay green.

If an older `simulation_accuracy.variance_pct_json` is `text` or `json` rather than `jsonb`, this statement is a full-table rewrite under `ACCESS EXCLUSIVE`, for as long as the rewrite takes. Invalid casts fail the statement. They do not delete rows.

2. **Unguarded statements stop the chain.** These creates are not inside `try`. A missing parent table, or any other error, raises and skips every helper after them:

- `ensure_cap_table_enhancements` creates `convertible_securities`, `cap_table_scenarios`, and `cap_table_audit_log` with `REFERENCES companies` and `REFERENCES shareholders` (938–986). The `shareholders` / `equity_holdings` adds just above (914–936) swallow errors, so a missing `shareholders` table still reaches this create.
- `ensure_auth_tokens_tables` creates `password_reset_tokens`, `email_verification_tokens`, and `refresh_tokens` with `REFERENCES users` (1152–1184).
- From `ensure_rate_limits_table` (1201) through `ensure_autopilot_tables` (1546), `ensure_survival_simulations_table` (1611), `ensure_cross_company_patterns_table` (1643), `ensure_copilot_feedback_table` (1733, also `REFERENCES users` and `companies`), and `ensure_agent_simulation_runs_table` (1764), the `CREATE TABLE` is unguarded.

3. **Locks on tables that can already hold data.** `ALTER TABLE` takes `ACCESS EXCLUSIVE`. `CREATE INDEX` is not `CONCURRENTLY`, so it takes `SHARE` and blocks writes for the build. Targets that this file alters or indexes in place, rather than only creating new:

- `financial_records` (8–68 and 1094–1104)
- `companies` (103, 116, 596–597, 904, 1633)
- `users` (1122–1136, 1147)
- `import_sessions` (591–594)
- `simulation_runs` (640–646)
- `scenarios` (657–658)
- `email_events` (710–716)
- `metric_definitions` (835–846)
- `metric_values` (858–862)
- `shareholders` and `equity_holdings` (914–936)
- `company_decisions` (1578–1603)
- `subscriptions` (1805)

Nullable adds and constant defaults (`'{}'`, `'UNITS'`, `FALSE`, `1`, `60`, `'USD'`, `'completed'`) are metadata-only on PostgreSQL 11 and newer. They still take the exclusive lock. This file does not use a volatile default on an `ADD COLUMN`, so those adds should not rewrite the heap. `railway.json` sets `numReplicas` to 1. A second process booting during the run can deadlock on the same DDL. `run_migrations` does not take a lock of its own (TD-001).

4. **Constraint changes, not value changes.**

- `metric_definitions.formula` and `source_connector` `DROP NOT NULL` (845–846). Stored values stay. Brief exclusive lock. Already-nullable is a no-op. The whole function is inside one `try`; a missing table is logged at debug and skipped.
- `users.password_hash` `DROP NOT NULL` (1128–1130). Same. Drizzle's `users` definition already treats `password_hash` as nullable (`shared/schema.ts` 9).
- `company_decisions` check constraints (1584–1603) validate existing rows. `duplicate_object` is swallowed inside the `DO` block. Any other failure aborts the transaction, and `conn.commit()` at 1605 can raise. New nullable `outcome_rating` and constant default `followup_days` of 60 pass the checks. Pre-existing out-of-range `followup_days` would fail the add.

5. **Drizzle is not on this path.** `run_migrations` does not read `migrations/0001_lead_gen.sql` or `shared/schema.ts`. Drizzle's schema file defines only `users`. The lead-gen script alters `leads` and is a separate manual apply. This runner assumes the SQLAlchemy base tables it alters already exist (`financial_records`, `companies`, `users`, `import_sessions`, `datasets`, `simulation_runs`, `scenarios`, `metric_definitions`, `metric_values`, `shareholders`, `equity_holdings`, `subscriptions`). It does not create those tables. `CREATE TABLE IF NOT EXISTS` does not repair an existing table whose columns differ.

6. **Swallowed failures look like success.** Many helpers log at `debug` and then log "migration complete" at info. A missing `financial_records` table skips every provenance column (`43–67`) and still logs complete at line 70.

## What the flag does not run

Turning the flag on does not enable `CREATE_SCHEMA`, `SEED_BENCHMARKS`, or `SEED_DEMO_DATA` (`server/main.py` 207–276). Those stay off in production unless their own variables are set.

These startup steps already run with the flag off, and stay outside this inventory: competitor `create_all` and two `ADD COLUMN IF NOT EXISTS` statements (`server/main.py` 218–232), `ensure_graph_indexes` (246–250), `ensure_default_flags` (282), `ensure_agent_permissions` (289), and `ensure_table` for the onboarding scheduler (296).

## Inventory

Call order from `run_migrations` (1000–1052). "Idempotent" means a second run on a Postgres that already has the object is a no-op or a swallowed duplicate, and does not change stored rows.

| # | Function | Lines | Tables | What it does | Idempotent |
| --- | --- | --- | --- | --- | --- |
| 1 | `ensure_financial_record_columns` | 8–70 | `financial_records` | Add nullable metric columns plus `source`, `synced_at`, `synced_fields`. Catalog check, then `ADD COLUMN IF NOT EXISTS` inside a savepoint. No index. | Yes |
| 2 | `ensure_invites_table` | 73–95 | `invites` | `CREATE TABLE IF NOT EXISTS` (FK `users`), two indexes. Error swallowed. | Yes, if `users` exists |
| 3 | `ensure_company_metadata_column` | 98–107 | `companies` | Add `metadata_json JSONB DEFAULT '{}'`. | Yes |
| 4 | `ensure_company_description_column` | 111–121 | `companies` | Add `description TEXT`. | Yes |
| 5 | `ensure_company_decisions_table` | 124–151 | `company_decisions` | Create (FK `companies`, `gen_random_uuid()`), two indexes. | Yes, if `companies` exists |
| 6 | `ensure_company_scenarios_table` | 154–175 | `company_scenarios` | Create (FK `companies`, self-FK), two indexes. | Yes, if `companies` exists |
| 7 | `ensure_company_sources_table` | 178–203 | `company_sources` | Create (FK `companies`), two indexes. | Yes, if `companies` exists |
| 8 | `ensure_company_workstreams_table` | 206–227 | `company_workstreams` | Create (FK `companies`), one index. | Yes, if `companies` exists |
| 9 | `ensure_company_alerts_table` | 230–252 | `company_alerts` | Create (FK `companies`), two indexes. | Yes, if `companies` exists |
| 10 | `ensure_company_driver_models_table` | 255–277 | `company_driver_models` | Create (FK `companies`), one index. | Yes, if `companies` exists |
| 11 | `ensure_llm_audit_logs_table` | 279–310 | `llm_audit_logs` | Create (FK `companies`, `users`), four indexes. | Yes, if parents exist |
| 12 | `ensure_eval_runs_table` | 313–337 | `eval_runs` | Create, three indexes. No FK. | Yes |
| 13 | `ensure_fundraising_tables` | 340–424 | `company_cap_tables`, `fundraising_rounds`, `round_terms`, `investors`, `investor_pipeline` | Create five tables (FK chain back to `companies`), indexes. | Yes, if `companies` exists |
| 14 | `ensure_conversations_tables` | 427–486 | `conversations`, `conversation_messages`, `conversation_recommendations` | Create three tables. Messages and recommendations use `ON DELETE CASCADE` as the FK rule for later deletes. This run does not delete rows. Indexes. FK to `companies`, `users`, `scenarios`. | Yes, if parents exist |
| 15 | `ensure_truth_scan_tables` | 488–584 | `truth_scan_uploads`, `truth_datasets`, `validation_reports`, `validation_issues`, `truth_decision_logs` | Create five tables. FK to `companies`, `import_sessions`, `datasets`, and to each other in that order. Indexes. | Yes, if `companies`, `import_sessions`, and `datasets` exist |
| 16 | `ensure_truth_scan_columns` | 587–603 | `import_sessions`, `companies` | Add two columns and two indexes on `import_sessions`. Add `latest_truth_dataset_id` and one index on `companies`. | Yes. Index build locks the existing tables |
| 17 | `ensure_company_states_table` | 605–633 | `company_states` | Create (unique FK `companies`), three indexes, then add `fundraising_rounds_json TEXT DEFAULT '[]'`. | Yes, if `companies` exists |
| 18 | `ensure_simulation_runs_provenance` | 636–650 | `simulation_runs` | Add `data_snapshot_id`, `inputs_json`, `status` default `'completed'`, `error_message`, `completed_at`. Two indexes. | Yes. Index build locks `simulation_runs` |
| 19 | `ensure_scenarios_overrides` | 653–662 | `scenarios` | Add `overrides_json JSONB DEFAULT '{}'` and `outputs_json JSONB`. | Yes |
| 20 | `ensure_email_events_table` | 665–767 | `email_events`, `email_link_clicks`, `email_feedback` | Create `email_events`, then add 16 columns (`IF NOT EXISTS`, constant defaults), indexes. Create the other two tables and their indexes. | Yes. Later column adds and indexes lock `email_events` if it already has rows |
| 21 | `ensure_metric_suggestions_tables` | 771–828 | `connector_capabilities`, `metric_suggestions`, `suggestion_events` | Create three tables (FK `companies`, `users`, `metric_definitions`). Unique index on `(company_id, suggestion_key)`. | Create is idempotent. The unique index fails if duplicate keys already exist; the function swallows that and rolls the open transaction back on close |
| 22 | `ensure_metric_definitions_columns` | 831–850 | `metric_definitions` | Add seven columns in one `ALTER`. Then `DROP NOT NULL` on `formula` and `source_connector`. | Adds are idempotent. `DROP NOT NULL` is a no-op when already nullable. Missing table is swallowed |
| 23 | `ensure_metric_values_columns` | 853–866 | `metric_values` | Add `metric_version`, `source_versions`, `compiled_sql`. | Yes |
| 24 | `ensure_team_members_table` | 869–896 | `team_members` | Create. No FK. | Yes |
| 25 | `ensure_currency_tables` | 1056–1108 | `exchange_rates`, `financial_records` | Create `exchange_rates` (Postgres `SERIAL` path), two indexes. Add `original_currency` default `'USD'`, `fx_rate_to_base` default `1.0`, `base_currency` default `'USD'`. | Yes. The three adds lock `financial_records` |
| 26 | `ensure_company_amount_scale` | 899–909 | `companies` | Add `amount_scale VARCHAR DEFAULT 'UNITS'`. | Yes |
| 27 | `ensure_user_oauth_columns` | 1111–1140 | `users` | Add `oauth_provider`, `oauth_id`, `avatar_url`, `display_name`. `DROP NOT NULL` on `password_hash`. Index `oauth_id`. | Yes. Locks `users` |
| 28 | `ensure_auth_tokens_tables` | 1143–1195 | `users`, `password_reset_tokens`, `email_verification_tokens`, `refresh_tokens` | Add `is_email_verified BOOLEAN DEFAULT FALSE` (swallowed). Create three token tables (FK `users`) **without** a try. Indexes are swallowed. | Creates are idempotent only when `users` exists. A failure raises and stops `run_migrations` |
| 29 | `ensure_beta_feedback_table` | 1220–1235 | `beta_feedback` | Create (FK `users`). Unguarded. | Yes, if `users` exists. Otherwise raises |
| 30 | `ensure_rate_limits_table` | 1198–1217 | `rate_limits` | Create, unique `(key, endpoint)`, two indexes. Unguarded create. | Yes |
| 31 | `ensure_cap_table_enhancements` | 912–997 | `shareholders`, `equity_holdings`, `convertible_securities`, `cap_table_scenarios`, `cap_table_audit_log` | `ADD COLUMN` **without** `IF NOT EXISTS` on `shareholders` (2) and `equity_holdings` (4). Duplicate-column errors are swallowed per column. Then three `CREATE TABLE`s with `gen_random_uuid()` and FKs, **unguarded**. Indexes swallowed. | Column adds are idempotent only because the error is ignored. The creates raise if `companies` or `shareholders` is missing, and stop the runner |
| 32 | `ensure_twin_events_table` | 1238–1259 | `twin_events` | Create (FK `companies`), four indexes. Unguarded create. | Yes, if `companies` exists |
| 33 | `ensure_simulation_outputs_table` | 1262–1284 | `simulation_outputs` | Create (`run_id` is not an FK), two indexes. Unguarded create. | Yes |
| 34 | `ensure_scenario_inputs_table` | 1287–1306 | `scenario_inputs` | Create (`scenario_id` is not an FK), one index. Unguarded create. | Yes |
| 35 | `ensure_scenario_events_table` | 1310–1329 | `scenario_events` | Create, one index. Unguarded create. | Yes |
| 36 | `ensure_decision_options_table` | 1333–1353 | `decision_options` | Create (`decision_id` is not an FK), one index. Unguarded create. | Yes |
| 37 | `ensure_event_ledger_tables` | 1357–1399 | `events`, `event_payloads`, `event_consumers`, `event_projections` | Create four tables. `event_payloads.event_id` is `ON DELETE CASCADE` (FK rule only). Unguarded creates. | Yes |
| 38 | `ensure_feature_flags_tables` | 1402–1435 | `feature_flags`, `company_flags`, `user_flags` | Create three tables. Child tables FK `feature_flags.key`. No seed inserts. Unguarded creates. | Yes |
| 39 | `ensure_ai_governance_tables` | 1438–1478 | `ai_agent_permissions`, `ai_agent_logs`, `ai_agent_budgets` | Create three tables. No seed inserts. Unguarded creates. | Yes |
| 40 | `ensure_data_confidence_table` | 1481–1502 | `data_confidence_scores` | Create, unique `(company_id, metric_name)`, two indexes. Unguarded create. | Yes |
| 41 | `ensure_graph_adjacency_tables` | 1505–1541 | `graph_nodes`, `graph_edges` | Create. Edges FK `graph_nodes`. Unguarded creates. | Yes |
| 42 | `ensure_autopilot_tables` | 1544–1561 | `autopilot_runs` | Create, two indexes. Unguarded create. | Yes |
| 43 | `ensure_survival_simulations_table` | 1609–1626 | `survival_simulations` | Create, unique `sim_id`, two indexes. Unguarded create. | Yes |
| 44 | `ensure_decision_outcome_columns` | 1564–1606 | `company_decisions` | Add seven columns (`IF NOT EXISTS`), including `followup_days INTEGER DEFAULT 60`. Add two `CHECK` constraints. | Adds are idempotent. A check failure aborts the transaction and can raise at `commit` (1605), which stops the runner |
| 45 | `ensure_company_data_sharing_column` | 1629–1638 | `companies` | Add `data_sharing_enabled BOOLEAN DEFAULT FALSE`. | Yes |
| 46 | `ensure_cross_company_patterns_table` | 1641–1669 | `cross_company_patterns` | Create, unique on four columns, four indexes. Unguarded create. | Yes |
| 47 | `ensure_simulation_accuracy_tables` | 1672–1728 | `simulation_accuracy`, `calibration_biases` | Create both (accuracy.`variance_pct_json` is `JSONB`; churn columns are in the create). Indexes. Then `ALTER COLUMN variance_pct_json TYPE JSONB USING ...`. Then `ADD COLUMN IF NOT EXISTS` for the two churn columns. | **No.** The type change errors when the column is already `jsonb`, aborts the transaction, and the `commit` raises. See flag 1. The `USING` cast rewrites the table when the column is a different type |
| 48 | `ensure_copilot_feedback_table` | 1731–1759 | `copilot_feedback` | Create (FK `companies`, `users`), six indexes. Unguarded create. Reached only if 47 does not raise. | Yes, if parents exist |
| 49 | `ensure_agent_simulation_runs_table` | 1762–1792 | `agent_simulation_runs` | Create, three indexes. `company_id` is not an FK. Unguarded create. | Yes |
| 50 | `ensure_subscription_trial_columns` | 1795–1811 | `subscriptions` | `ADD COLUMN` `trial_start` and `trial_end` **without** `IF NOT EXISTS`. Duplicate-column errors are swallowed. | Effectively, on a table that already exists. A missing `subscriptions` table is swallowed, and the function still logs complete |

## Provenance columns inside this run

`source VARCHAR(64)`, `synced_at VARCHAR(40)`, and `synced_fields JSON` are items in the first helper (36–40), applied at 56–68. They are nullable, have no default, and add no index. A second run skips them when the catalog already lists them. Postgres uses `IF NOT EXISTS`. That step does not depend on Drizzle and does not rewrite `financial_records` on PostgreSQL 11+.

Shipping those three columns by setting `RUN_MIGRATIONS=true` also runs the other 49 helpers.

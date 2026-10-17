// Company-level access checks for Express-handled features (the WebSocket
// subscription today). Mirrors FastAPI's require_company_access: the master
// session may read any company; everyone else needs to own the company or be
// an active workspace member of it. Fails closed when the DB is unavailable.
import { isMasterPayload } from "./requireAuth";

export type CompanyAccessCheck = (payload: Record<string, any>, companyId: number) => Promise<boolean>;

export const userCanAccessCompany: CompanyAccessCheck = async (payload, companyId) => {
  if (!Number.isInteger(companyId) || companyId <= 0) return false;
  if (isMasterPayload(payload)) return true;
  const userId = Number(payload.sub);
  if (!Number.isInteger(userId) || userId <= 0) return false;
  if (!process.env.DATABASE_URL) return false;
  try {
    const { sql } = await import("drizzle-orm");
    const { db } = await import("../db");
    const result: any = await db.execute(sql`
      SELECT 1 FROM companies WHERE id = ${companyId} AND user_id = ${userId}
      UNION ALL
      SELECT 1 FROM workspace_members
        WHERE company_id = ${companyId} AND user_id = ${userId}
          AND COALESCE(status, 'active') = 'active'
      LIMIT 1`);
    const rows = Array.isArray(result) ? result : result?.rows;
    return Array.isArray(rows) && rows.length > 0;
  } catch (err) {
    console.error("[companyAccess] lookup failed:", err instanceof Error ? err.message : err);
    return false;
  }
};

/** company_id of a scenario, or null when it cannot be resolved. */
export async function companyIdForScenario(scenarioId: number): Promise<number | null> {
  if (!Number.isInteger(scenarioId) || scenarioId <= 0 || !process.env.DATABASE_URL) return null;
  try {
    const { sql } = await import("drizzle-orm");
    const { db } = await import("../db");
    const result: any = await db.execute(sql`SELECT company_id FROM scenarios WHERE id = ${scenarioId} LIMIT 1`);
    const rows = Array.isArray(result) ? result : result?.rows;
    const id = Number(rows?.[0]?.company_id);
    return Number.isInteger(id) && id > 0 ? id : null;
  } catch (err) {
    console.error("[companyAccess] scenario lookup failed:", err instanceof Error ? err.message : err);
    return null;
  }
}

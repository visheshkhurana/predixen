// Express-side read of the revocation tables #134 writes on logout, password
// reset, and suspension. FastAPI's get_current_user already consults them.
// Express routes (/api/ai/*, Notion, messaging) verify the JWT themselves, so
// a copied access token stayed valid there until it expired.
import pg from "pg";

export interface RevocationQuery {
  (sql: string, params: unknown[]): Promise<{ rows: Array<Record<string, unknown>> }>;
}

const REVOKED_JTI_SQL =
  "SELECT 1 AS revoked FROM revoked_access_tokens WHERE jti = $1 LIMIT 1";

// revoked_before is timestamp without time zone, stored as UTC. AT TIME ZONE
// 'UTC' makes EXTRACT return an absolute epoch rather than the session zone.
const CUTOFF_SQL =
  "SELECT EXTRACT(EPOCH FROM (revoked_before AT TIME ZONE 'UTC')) AS cutoff " +
  "FROM user_session_cutoffs WHERE user_id = $1";

let pool: pg.Pool | undefined;

/** Database lookup, or null when this process has no DATABASE_URL. */
export function databaseRevocationQuery(): RevocationQuery | null {
  const url = process.env.DATABASE_URL;
  if (!url) return null;
  if (!pool) {
    pool = new pg.Pool({ connectionString: url, max: 2 });
  }
  const active = pool;
  return async (sql, params) => {
    const result = await active.query(sql, params);
    return { rows: result.rows };
  };
}

function cutoffSeconds(raw: unknown): number | null {
  if (raw === null || raw === undefined || raw === "") return null;
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
}

/**
 * True when this access token was logged out (jti) or was issued before the
 * user's session cutoff (password reset / suspension). A token with no iat
 * predates the cutoff check and is treated as already ended.
 */
export async function isAccessTokenRevoked(
  payload: Record<string, unknown>,
  query: RevocationQuery,
): Promise<boolean> {
  const jti = typeof payload.jti === "string" ? payload.jti.trim() : "";
  if (jti) {
    const hit = await query(REVOKED_JTI_SQL, [jti]);
    if (hit.rows.length > 0) return true;
  }

  const userId = Number(payload.sub);
  if (!Number.isFinite(userId) || userId <= 0) return false;

  const cutoff = await query(CUTOFF_SQL, [userId]);
  if (cutoff.rows.length === 0) return false;
  const seconds = cutoffSeconds(cutoff.rows[0]?.cutoff);
  if (seconds === null) return false;

  const iat = payload.iat;
  if (iat === undefined || iat === null || iat === "") return true;
  const issued = Number(iat);
  if (!Number.isFinite(issued)) return true;
  return issued < seconds;
}

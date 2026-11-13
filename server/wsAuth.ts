// Session and tenant checks for the /ws upgrade and its subscriptions.
import type { IncomingMessage } from "http";
import { verifyJwtHS256 } from "./middleware/requireAuth";
import {
  databaseRevocationQuery,
  isAccessTokenRevoked,
  type RevocationQuery,
} from "./middleware/sessionRevocation";

export interface WsUser {
  sub: string;
  isMaster: boolean;
}

let queryForTests: RevocationQuery | null | undefined;

/** Tests inject a query so no Postgres is needed. `undefined` restores the default. */
export function setWsQueryForTests(query: RevocationQuery | null | undefined): void {
  queryForTests = query;
}

function activeQuery(): RevocationQuery | null {
  return queryForTests !== undefined ? queryForTests : databaseRevocationQuery();
}

function cookieValue(header: string | undefined, name: string): string | null {
  if (typeof header !== "string") return null;
  for (const part of header.split(";")) {
    const idx = part.indexOf("=");
    if (idx === -1) continue;
    if (part.slice(0, idx).trim() === name) {
      try {
        return decodeURIComponent(part.slice(idx + 1).trim());
      } catch {
        return null;
      }
    }
  }
  return null;
}

function upgradeToken(req: IncomingMessage): string | null {
  const fromCookie = cookieValue(req.headers["cookie"], "auth_token");
  if (fromCookie) return fromCookie;
  try {
    const url = new URL(req.url || "", "http://localhost");
    const fromQuery = url.searchParams.get("token");
    if (fromQuery) return fromQuery;
  } catch {
    // fall through
  }
  return null;
}

/**
 * A browser always sends Origin on a WebSocket upgrade. When it does, it must
 * name this host, so another site cannot open a socket with the visitor's
 * cookie. Non-browser clients that omit it still need a valid session.
 */
export function isAllowedUpgradeOrigin(req: IncomingMessage): boolean {
  const origin = req.headers["origin"];
  if (origin === undefined || origin === "") return true;
  if (typeof origin !== "string") return false;
  const host = (req.headers["host"] || "").toString().toLowerCase();
  try {
    return new URL(origin).host.toLowerCase() === host && host !== "";
  } catch {
    return false;
  }
}

/** The session behind an upgrade request, or null when it is missing, forged, expired or ended. */
export async function authenticateUpgrade(req: IncomingMessage): Promise<WsUser | null> {
  const secret = process.env.SECRET_KEY || process.env.SESSION_SECRET;
  if (!secret) return null;
  const token = upgradeToken(req);
  if (!token) return null;
  const payload = verifyJwtHS256(token, secret);
  if (!payload || payload.sub === undefined || payload.sub === null || payload.sub === "") {
    return null;
  }
  const query = activeQuery();
  if (query) {
    try {
      if (await isAccessTokenRevoked(payload, query)) return null;
    } catch {
      return null;
    }
  }
  const isMaster = payload.sub === "master" && payload.is_master === true;
  return { sub: String(payload.sub), isMaster };
}

const COMPANY_ACCESS_SQL =
  "SELECT 1 AS ok FROM companies WHERE id = $1 AND user_id = $2 " +
  "UNION ALL " +
  "SELECT 1 AS ok FROM workspace_members WHERE company_id = $1 AND user_id = $2 AND status = 'active' " +
  "LIMIT 1";

/** True when this user owns the company or is an active member of it. */
export async function canAccessCompany(user: WsUser, companyId: unknown): Promise<boolean> {
  const id = Number(companyId);
  if (!Number.isInteger(id) || id <= 0) return false;
  if (user.isMaster) return true;
  const userId = Number(user.sub);
  if (!Number.isInteger(userId) || userId <= 0) return false;
  const query = activeQuery();
  if (!query) return false;
  try {
    const result = await query(COMPANY_ACCESS_SQL, [id, userId]);
    return result.rows.length > 0;
  } catch {
    return false;
  }
}

/** The company a scenario belongs to, or null when unknown. */
export async function scenarioCompanyId(scenarioId: unknown): Promise<number | null> {
  const id = Number(scenarioId);
  if (!Number.isInteger(id) || id <= 0) return null;
  const query = activeQuery();
  if (!query) return null;
  try {
    const result = await query("SELECT company_id FROM scenarios WHERE id = $1", [id]);
    const value = Number(result.rows[0]?.company_id);
    return Number.isInteger(value) && value > 0 ? value : null;
  } catch {
    return null;
  }
}

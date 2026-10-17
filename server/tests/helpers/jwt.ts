// Mints HS256 tokens shaped like the ones FastAPI issues, for Express tests.
import crypto from "crypto";

const b64url = (b: Buffer | string) =>
  Buffer.from(b).toString("base64").replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");

export function signJwt(payload: Record<string, any>, secret: string, alg = "HS256"): string {
  const h = b64url(JSON.stringify({ alg, typ: "JWT" }));
  const p = b64url(JSON.stringify(payload));
  const sig = b64url(crypto.createHmac("sha256", secret).update(`${h}.${p}`).digest());
  return `${h}.${p}.${sig}`;
}

export const inOneHour = () => Math.floor(Date.now() / 1000) + 3600;

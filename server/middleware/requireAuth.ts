// Dependency-free auth gate for Express-handled routes (Twilio messaging, Notion).
// Verifies the same HS256 JWT the FastAPI backend issues (signed with SECRET_KEY,
// carried in the `auth_token` cookie or an Authorization: Bearer header).
import crypto from 'crypto';
import type { Request, Response, NextFunction } from 'express';

function b64urlDecode(s: string): Buffer {
  s = s.replace(/-/g, '+').replace(/_/g, '/');
  while (s.length % 4) s += '=';
  return Buffer.from(s, 'base64');
}

function verifyJwtHS256(token: string, secret: string): Record<string, any> | null {
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  const [h, p, sig] = parts;
  const expected = crypto.createHmac('sha256', secret).update(`${h}.${p}`).digest();
  const given = b64urlDecode(sig);
  if (expected.length !== given.length || !crypto.timingSafeEqual(expected, given)) return null;
  let payload: Record<string, any>;
  try {
    payload = JSON.parse(b64urlDecode(p).toString('utf8'));
  } catch {
    return null;
  }
  if (payload.exp && Math.floor(Date.now() / 1000) > Number(payload.exp)) return null;
  return payload;
}

function getToken(req: Request): string | null {
  const auth = req.headers['authorization'];
  if (typeof auth === 'string' && auth.startsWith('Bearer ')) return auth.slice(7).trim();
  const cookie = req.headers['cookie'];
  if (typeof cookie === 'string') {
    for (const part of cookie.split(';')) {
      const idx = part.indexOf('=');
      if (idx === -1) continue;
      const k = part.slice(0, idx).trim();
      if (k === 'auth_token') return decodeURIComponent(part.slice(idx + 1).trim());
    }
  }
  return null;
}

// Requires a valid, unexpired, backend-signed session. Blocks unauthenticated access.
export function requireAuth(req: Request, res: Response, next: NextFunction): void {
  const secret = process.env.SECRET_KEY || process.env.SESSION_SECRET;
  if (!secret) {
    res.status(500).json({ error: 'Server auth not configured' });
    return;
  }
  const token = getToken(req);
  if (!token) {
    res.status(401).json({ error: 'Authentication required' });
    return;
  }
  const payload = verifyJwtHS256(token, secret);
  if (!payload || !payload.sub) {
    res.status(401).json({ error: 'Invalid or expired session' });
    return;
  }
  (req as any).authUser = payload;
  next();
}

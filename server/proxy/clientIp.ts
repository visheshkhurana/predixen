/**
 * Express is the only hop that may name the client for FastAPI.
 *
 * Railway's edge appends the address it saw. `trust proxy` is 1, so req.ip
 * is that appended hop and a leftmost X-Forwarded-For value the caller wrote
 * is ignored. FastAPI used to trust whatever X-Real-IP arrived, and this
 * proxy forwarded the caller's header unchanged, so a new X-Real-IP opened a
 * new lead bucket and the 9th POST in a minute stayed a consent 400.
 */
export function setProxyClientIp(
  proxyReq: { setHeader(name: string, value: string): void; removeHeader(name: string): void },
  req: { ip?: string; socket?: { remoteAddress?: string | null } },
): void {
  const ip = req.ip || req.socket?.remoteAddress || "";
  if (ip) proxyReq.setHeader("X-Real-IP", ip);
  else proxyReq.removeHeader("X-Real-IP");
}

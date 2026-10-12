import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { FCLogo } from "@/components/FCLogo";

type Status = "loading" | "ready" | "working" | "done" | "error";

/**
 * Public lifecycle unsubscribe. The token in the query string is the
 * credential — there is no login. POST matches the RFC 8058 one-click body
 * so the page and the mail-client header hit the same endpoint.
 */
export default function UnsubscribePage() {
  const [status, setStatus] = useState<Status>("loading");
  const [message, setMessage] = useState("");
  const [masked, setMasked] = useState("");
  const token = new URLSearchParams(window.location.search).get("token") || "";

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("This unsubscribe link is missing its token. Open the link from a product email.");
      return;
    }

    let cancelled = false;
    fetch(`/api/email/unsubscribe?token=${encodeURIComponent(token)}`)
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (cancelled) return;
        if (!res.ok) {
          setStatus("error");
          setMessage(data.detail || "This unsubscribe link is not valid.");
          return;
        }
        setMasked(data.masked_email || "");
        if (data.unsubscribed) {
          setStatus("done");
          setMessage("Product emails are already off for this account.");
          return;
        }
        setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) {
          setStatus("error");
          setMessage("Something went wrong. Please try the link again.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function confirm() {
    setStatus("working");
    try {
      const res = await fetch(`/api/email/unsubscribe?token=${encodeURIComponent(token)}`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: "List-Unsubscribe=One-Click",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setStatus("error");
        setMessage(data.detail || "Could not unsubscribe.");
        return;
      }
      setMasked(data.masked_email || masked);
      setStatus("done");
      setMessage("You will no longer get onboarding, activity, or digest emails.");
    } catch {
      setStatus("error");
      setMessage("Something went wrong. Please try again.");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardContent className="p-6 text-center space-y-4">
          <div className="flex justify-center mb-2">
            <FCLogo size="lg" />
          </div>

          {status === "loading" || status === "working" ? (
            <>
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
              <h1 className="text-xl font-semibold">
                {status === "working" ? "Unsubscribing…" : "Checking this link…"}
              </h1>
            </>
          ) : null}

          {status === "ready" && (
            <>
              <h1 className="text-xl font-semibold">Unsubscribe from product emails</h1>
              <p className="text-sm text-muted-foreground">
                {masked ? <>This stops product emails for {masked}. </> : null}
                Onboarding, activity reports, and digests stop. Password resets and
                verification emails still send.
              </p>
              <Button className="w-full" onClick={confirm} data-testid="button-unsubscribe">
                Unsubscribe
              </Button>
            </>
          )}

          {status === "done" && (
            <>
              <div className="w-12 h-12 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto">
                <CheckCircle className="h-6 w-6 text-emerald-500" />
              </div>
              <h1 className="text-xl font-semibold" data-testid="text-unsubscribed">Unsubscribed</h1>
              <p className="text-sm text-muted-foreground">
                {masked ? <>{masked}. </> : null}
                {message} You can turn them back on from Settings after you sign in.
              </p>
            </>
          )}

          {status === "error" && (
            <>
              <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mx-auto">
                <AlertCircle className="h-6 w-6 text-red-500" />
              </div>
              <h1 className="text-xl font-semibold" data-testid="text-unsubscribe-error">Unsubscribe link invalid</h1>
              <p className="text-sm text-muted-foreground">{message}</p>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

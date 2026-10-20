import { useState, type FormEvent } from "react";
import { Link } from "wouter";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useViewedOnce } from "@/hooks/use-viewed-once";
import { trackFunnel } from "@/lib/funnel";
import { getBrowserDistinctId } from "@/lib/posthog";
import { cn } from "@/lib/utils";
import { Check, Loader2, Mail } from "lucide-react";

/** The offer, verbatim. The checkbox starts unchecked. */
export const CALCULATOR_OPT_IN_LABEL =
  "Email me this result + monthly founder finance tips";

export type CalculatorEmailOptInProps = {
  /** Short lead source. Reported as lead_form_submitted location. */
  source: string;
  /** Public path the result was shown on. Stored as source_page. */
  sourcePage: string;
  plan?: string;
  notes: string;
  runwayMonths?: string;
  runwayDate?: string;
  monthlyBurn?: string;
  /** False until the calculator is showing a result. */
  visible?: boolean;
  /**
   * True when this page queues a result email. Burn multiple, dilution,
   * LTV/CAC, and default-alive do not, so their success line must not
   * promise an inbox.
   */
  resultByEmail?: boolean;
  className?: string;
  inputClassName?: string;
};

/**
 * Public calculator email capture.
 *
 * Consent-true POST /api/leads saves succeed, so the box is shown. Set this
 * to false to hide it again. Calculator results do not read this flag and
 * stay on screen either way.
 */
export const CALCULATOR_EMAIL_CAPTURE_ENABLED: boolean = true;

/**
 * Consent capture for a public calculator result.
 *
 * The box starts unchecked. Submit stays disabled until it is checked, and
 * the POST sends consent=true with a timestamp and this page. Monthly tips
 * are stored pending: there is no Resend double opt-in for leads, so this
 * form does not tell the visitor they are subscribed.
 */
export function CalculatorEmailOptIn(props: CalculatorEmailOptInProps) {
  if (!CALCULATOR_EMAIL_CAPTURE_ENABLED) return null;
  return <CalculatorEmailOptInForm {...props} />;
}

function CalculatorEmailOptInForm({
  source,
  sourcePage,
  plan,
  notes,
  runwayMonths,
  runwayDate,
  monthlyBurn,
  visible = true,
  resultByEmail = true,
  className,
  inputClassName,
}: CalculatorEmailOptInProps) {
  const [email, setEmail] = useState("");
  const [consented, setConsented] = useState(false);
  const [sendState, setSendState] = useState<"idle" | "sending" | "done" | "error">("idle");
  const leadFormRef = useViewedOnce("lead_form_viewed", { location: source });
  const consentId = `lead-consent-${source}`;

  async function handleEmailResult(e: FormEvent) {
    e.preventDefault();
    if (sendState === "sending" || !email.trim() || !consented) return;
    setSendState("sending");
    let saved = false;
    try {
      const distinctId = await getBrowserDistinctId();
      const res = await fetch("/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          source,
          source_page: sourcePage,
          plan: plan ?? source,
          notes,
          consent: true,
          consent_at: new Date().toISOString(),
          ...(runwayMonths ? { runway_months: runwayMonths } : {}),
          ...(runwayDate ? { runway_date: runwayDate } : {}),
          ...(monthlyBurn ? { monthly_burn: monthlyBurn } : {}),
          ...(distinctId ? { distinct_id: distinctId } : {}),
        }),
      });
      if (!res.ok) throw new Error(String(res.status));
      saved = true;
    } catch {
      // The result is still on screen. Ask them to try again, nothing else.
      setSendState("error");
    }
    if (!saved) return;
    setSendState("done");
    // After the save, not inside its try: a telemetry throw must not flip a
    // saved lead back to the error state. The conversion event stays on the
    // server. This form event is location and host only.
    trackFunnel("lead_form_submitted", {
      location: source,
      host: window.location.host,
    });
  }

  if (!visible) return null;

  return (
    <div
      className={cn("rounded-xl border bg-card/50 p-6", className)}
      data-testid="email-result-panel"
    >
      {sendState === "done" ? (
        <div className="flex items-start gap-3 py-2" data-testid="text-email-sent">
          <Check className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
          <p className="text-sm text-foreground">
            {resultByEmail
              ? "Check your inbox for this result. Monthly founder finance tips are pending and are not sent until you confirm. Unsubscribe any time."
              : "We'll keep you posted. Monthly founder finance tips are pending and are not sent until you confirm. Unsubscribe any time."}
          </p>
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2">
            <Mail className="h-4 w-4 text-primary shrink-0" />
            <h3 className="text-base font-semibold text-foreground" data-testid="text-email-heading">
              {CALCULATOR_OPT_IN_LABEL}
            </h3>
          </div>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Your result, emailed so you can forward it, plus a short monthly
            note on founder finance. No account needed.
          </p>
          <form ref={leadFormRef} onSubmit={handleEmailResult} className="mt-4 space-y-3">
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                type="email"
                required
                autoComplete="email"
                inputMode="email"
                placeholder="you@yourstartup.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={cn("sm:flex-1", inputClassName)}
                aria-label="Your email address"
                data-testid="input-lead-email"
              />
              <Button
                type="submit"
                disabled={sendState === "sending" || !consented}
                data-testid="button-email-result"
              >
                {sendState === "sending" ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Sending
                  </>
                ) : (
                  "Send it to me"
                )}
              </Button>
            </div>
            <div className="flex items-start gap-2">
              <Checkbox
                id={consentId}
                checked={consented}
                onCheckedChange={(value) => setConsented(value === true)}
                data-testid="checkbox-lead-consent"
                className="mt-0.5"
              />
              <Label htmlFor={consentId} className="text-sm font-normal leading-snug">
                {CALCULATOR_OPT_IN_LABEL}
              </Label>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed" data-testid="text-lead-privacy">
              We store your email only because you check this box. See the{" "}
              <Link href="/privacy" className="text-primary underline underline-offset-2" data-testid="link-lead-privacy">
                Privacy Policy
              </Link>
              .
            </p>
            <p className="text-xs text-muted-foreground leading-relaxed" data-testid="text-lead-unsubscribe">
              Unsubscribe any time from the link in those emails, or by writing
              to hello@founderconsole.ai. Monthly tips stay off until you confirm.
            </p>
          </form>
          {sendState === "error" && (
            <p className="mt-2 text-sm text-destructive" data-testid="text-email-error">
              That did not go through. Try again in a moment.
            </p>
          )}
        </>
      )}
    </div>
  );
}

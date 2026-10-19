/**
 * Post-login routing and forgot-password result handling.
 *
 * A failed companies.list() used to look the same as an empty list, so a
 * non-admin was sent to /onboarding after a 500 or a network error. Onboarding
 * is only for a list that actually came back empty. Forgot-password used to
 * show "check your email" even when the request failed.
 */

export type CompanyListOutcome =
  | { status: "ok"; companies: readonly unknown[] }
  | { status: "error" };

export type PostLoginDestination = "/" | "/onboarding" | "retry";

export function postLoginDestination(
  isPlatformAdmin: boolean,
  companies: CompanyListOutcome,
): PostLoginDestination {
  if (companies.status === "error") return "retry";
  if (!isPlatformAdmin && companies.companies.length === 0) return "/onboarding";
  return "/";
}

/** The reset form may show "check your email" only after a 2xx. */
export function forgotPasswordAccepted(responseOk: boolean): boolean {
  return responseOk === true;
}

export function forgotPasswordFailureCopy(status: number | null): {
  title: string;
  description: string;
} {
  if (status === null) {
    return {
      title: "Couldn't send reset email",
      description: "Unable to reach the server. Please check your connection and try again.",
    };
  }
  if (status === 429) {
    return {
      title: "Couldn't send reset email",
      description: "Too many reset attempts. Wait a minute and try again.",
    };
  }
  return {
    title: "Couldn't send reset email",
    description: "We couldn't send the reset email. Please try again.",
  };
}

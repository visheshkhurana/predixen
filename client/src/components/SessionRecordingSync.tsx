import React, { useEffect, type ReactNode } from "react";
import { useLocation } from "wouter";
import { syncSessionRecording } from "../lib/sessionRecording";

/**
 * Sits above the route switch so every path updates session replay, including
 * routes that render outside the authenticated shell (signup, auth, onboarding).
 */
export function SessionRecordingSync({ children }: { children?: ReactNode }) {
  const [location] = useLocation();
  useEffect(() => {
    syncSessionRecording(location);
  }, [location]);
  return <>{children}</>;
}

// Keeps the copilot question the user just sent until an answer arrives, so a
// session expiry (401 -> /auth?expired=1) does not lose it. sessionStorage can
// be missing or throw (private mode, blocked storage); every access is guarded.

export const COPILOT_DRAFT_KEY = "founderconsole-copilot-draft";

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function defaultStorage(): StorageLike | null {
  try {
    return typeof window !== "undefined" ? window.sessionStorage : null;
  } catch {
    return null;
  }
}

export function saveCopilotDraft(text: string, storage: StorageLike | null = defaultStorage()): void {
  if (!storage) return;
  try {
    if (text.trim()) storage.setItem(COPILOT_DRAFT_KEY, text);
    else storage.removeItem(COPILOT_DRAFT_KEY);
  } catch {
    // storage full or blocked: nothing to do
  }
}

export function loadCopilotDraft(storage: StorageLike | null = defaultStorage()): string | null {
  if (!storage) return null;
  try {
    const v = storage.getItem(COPILOT_DRAFT_KEY);
    return v && v.trim() ? v : null;
  } catch {
    return null;
  }
}

export function clearCopilotDraft(storage: StorageLike | null = defaultStorage()): void {
  if (!storage) return;
  try {
    storage.removeItem(COPILOT_DRAFT_KEY);
  } catch {
    // ignore
  }
}

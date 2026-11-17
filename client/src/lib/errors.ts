export class ApiError extends Error {
  status: number;
  code?: string;
  detail?: any;
  upload_id?: string;

  constructor(status: number, message: string, detail?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    if (detail && typeof detail === 'object') {
      this.code = detail.code;
      this.upload_id = detail.upload_id;
    }
  }
}

export function getErrorMessage(error: unknown, fallback: string = 'An unexpected error occurred'): string {
  if (error === null || error === undefined) {
    return fallback;
  }
  if (typeof error === 'string') {
    return error || fallback;
  }
  if (error instanceof ApiError) {
    return error.message || fallback;
  }
  if (error instanceof Error) {
    return error.message || fallback;
  }
  if (typeof error === 'object') {
    const obj = error as Record<string, any>;
    if (typeof obj.message === 'string') return obj.message || fallback;
    if (typeof obj.detail === 'string') return obj.detail || fallback;
    if (typeof obj.error === 'string') return obj.error || fallback;
    if (typeof obj.statusText === 'string') return obj.statusText || fallback;
    try {
      const str = JSON.stringify(error);
      if (str && str !== '{}') return str;
    } catch {
      // ignore
    }
    return fallback;
  }
  return String(error) || fallback;
}

/**
 * Safely parse JSON from a Response object with proper error handling
 * @param response The Response object to parse
 * @param fallbackMessage Message to use if parsing fails
 * @returns The parsed JSON object or null if parsing fails
 */
export async function safeParseJSON(
  response: Response,
  fallbackMessage: string = 'Failed to parse response'
): Promise<any> {
  try {
    const text = await response.text();
    if (!text) {
      return null;
    }
    return JSON.parse(text);
  } catch (error) {
    const parseError = error instanceof Error ? error.message : String(error);
    console.error(
      `JSON parse error from ${response.status} response: ${parseError}`,
      error
    );
    throw new ApiError(
      response.status,
      `${fallbackMessage} (${response.status}) - JSON parsing failed: ${parseError}`
    );
  }
}

export function isTruthScanRequired(err: any): boolean {
  return (
    err?.code === 'TRUTH_SCAN_REQUIRED' || 
    err?.detail?.code === 'TRUTH_SCAN_REQUIRED' ||
    err?.status === 409 ||
    err?.message?.includes('TRUTH_SCAN_REQUIRED')
  );
}

export function getTruthScanUploadId(err: any): string | undefined {
  return err?.upload_id || err?.detail?.upload_id;
}

const FIELD_LABELS: Record<string, string> = {
  email: 'Email',
  password: 'Password',
  name: 'Name',
  company_name: 'Company name',
};

/**
 * FastAPI validation errors arrive as `detail: [{loc, msg}, ...]`. Shown as-is
 * the founder only saw "Request failed (422)". Turn the first entry into a
 * sentence they can act on.
 */
export function validationDetailMessage(detail: unknown): string | null {
  if (!Array.isArray(detail) || detail.length === 0) return null;
  const first = detail[0] as { loc?: unknown[]; msg?: unknown };
  const msg = typeof first?.msg === 'string' ? first.msg : '';
  if (!msg) return null;
  const loc = Array.isArray(first.loc) ? first.loc : [];
  const field = String(loc[loc.length - 1] ?? '');
  if (field === 'email' || /email address/i.test(msg)) {
    return 'Please use a real email address you can receive mail at.';
  }
  const label = FIELD_LABELS[field] ?? (field ? field.replace(/_/g, ' ') : '');
  const clean = msg.replace(/^Value error,\s*/i, '');
  const sentence = clean.charAt(0).toUpperCase() + clean.slice(1);
  return label ? `${label.charAt(0).toUpperCase() + label.slice(1)}: ${sentence}` : sentence;
}

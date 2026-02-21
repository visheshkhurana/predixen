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

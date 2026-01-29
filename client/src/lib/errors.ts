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

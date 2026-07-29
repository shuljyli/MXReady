import type { ApiErrorBody, ScanJob, ScanReport } from "./types";

export class MxReadyApiError extends Error {
  readonly code: string;
  readonly details: Record<string, string>;
  readonly status: number;

  constructor(
    code: string,
    message: string,
    details: Record<string, string> = {},
    status = 0,
  ) {
    super(message);
    this.name = "MxReadyApiError";
    this.code = code;
    this.details = details;
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: {
        Accept: "application/json",
        ...init?.headers,
      },
    });
  } catch {
    throw new MxReadyApiError(
      "NETWORK_ERROR",
      "无法连接 MXReady 服务，请确认后端已经启动。",
    );
  }

  if (!response.ok) {
    let error: ApiErrorBody["error"] | undefined;
    try {
      const body = (await response.json()) as Partial<ApiErrorBody>;
      error = body.error;
    } catch {
      // A proxy or web server may return a non-JSON error page.
    }
    throw new MxReadyApiError(
      error?.code ?? "HTTP_ERROR",
      error?.message ?? `请求失败（HTTP ${response.status}）。`,
      error?.details ?? {},
      response.status,
    );
  }

  return (await response.json()) as T;
}

export function createScan(input: {
  repo_url: string;
  ref: string | null;
}): Promise<ScanJob> {
  return request<ScanJob>("/api/scans", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function getScan(id: string): Promise<ScanJob> {
  return request<ScanJob>(`/api/scans/${encodeURIComponent(id)}`);
}

export function getReport(id: string): Promise<ScanReport> {
  return request<ScanReport>(
    `/api/scans/${encodeURIComponent(id)}/report`,
  );
}

export function uploadVerification(
  scanId: string,
  file: File,
): Promise<ScanReport> {
  return request<ScanReport>(
    `/api/scans/${encodeURIComponent(scanId)}/verification-runs`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: file,
    },
  );
}

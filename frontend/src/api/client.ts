import type { ApiErrorBody, RuleCatalog, ScanJob, ScanReport } from "./types";

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
  const controller = new AbortController();
  let timedOut = false;
  const cancel = () => controller.abort();
  init?.signal?.addEventListener("abort", cancel, { once: true });
  if (init?.signal?.aborted) controller.abort();
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, 15_000);

  try {
    const response = await fetch(path, {
      ...init,
      signal: controller.signal,
      headers: { Accept: "application/json", ...init?.headers },
    });
    if (!response.ok) {
      let error: ApiErrorBody["error"] | undefined;
      try {
        const body = (await response.json()) as Partial<ApiErrorBody>;
        error = body.error;
      } catch {
        // Proxies may return non-JSON error pages.
      }
      throw new MxReadyApiError(
        error?.code ?? "HTTP_ERROR",
        error?.message ?? `请求失败（HTTP ${response.status}）。`,
        error?.details ?? {},
        response.status,
      );
    }
    return (await response.json()) as T;
  } catch (error) {
    if (timedOut) {
      throw new MxReadyApiError("REQUEST_TIMEOUT", "请求超时，请稍后继续查看扫描。");
    }
    if (init?.signal?.aborted) {
      throw new MxReadyApiError("REQUEST_CANCELLED", "请求已取消。");
    }
    if (error instanceof MxReadyApiError) throw error;
    throw new MxReadyApiError(
      "NETWORK_ERROR", "无法连接 MXReady 服务，请确认后端已经启动。",
    );
  } finally {
    clearTimeout(timer);
    init?.signal?.removeEventListener("abort", cancel);
  }
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

export function getScan(id: string, signal?: AbortSignal): Promise<ScanJob> {
  return request<ScanJob>(`/api/scans/${encodeURIComponent(id)}`, { signal });
}

export function getRules(): Promise<RuleCatalog> {
  return request<RuleCatalog>("/api/rules");
}

export function getReport(id: string, signal?: AbortSignal): Promise<ScanReport> {
  return request<ScanReport>(
    `/api/scans/${encodeURIComponent(id)}/report`,
    { signal },
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

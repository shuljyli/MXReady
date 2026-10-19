import { afterEach, expect, it, vi } from "vitest";

import {
  createScan,
  getReport,
  getRules,
  getScan,
  MxReadyApiError,
  uploadVerification,
} from "./client";
import type { ScanJob } from "./types";

const sleepJob: ScanJob = {
  id: "00000000-0000-0000-0000-000000000001",
  repo_url: "https://github.com/example/project",
  requested_ref: null,
  resolved_commit: null,
  status: "queued",
  stage_message: "等待开始",
  created_at: "2026-07-29T00:00:00Z",
  updated_at: "2026-07-29T00:00:00Z",
  failure_code: null,
  failure_message: null,
};

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

function stubFetch(
  response: Response | Error | (() => Response),
): ReturnType<typeof vi.fn> {
  const mock = vi.fn();
  if (response instanceof Error) {
    mock.mockRejectedValue(response);
  } else if (typeof response === "function") {
    mock.mockImplementation(() => Promise.resolve(response()));
  } else {
    mock.mockResolvedValue(response);
  }
  vi.stubGlobal("fetch", mock);
  return mock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

it("bounds stalled API requests with a timeout", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("fetch", vi.fn((_url: string, init: RequestInit) =>
    new Promise((_resolve, reject) => {
      init.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    }),
  ));
  const pending = expect(getScan(sleepJob.id)).rejects.toMatchObject({ code: "REQUEST_TIMEOUT" });
  await vi.advanceTimersByTimeAsync(15_000);
  await pending;
});

it("posts a scan request as JSON to /api/scans", async () => {
  const mock = stubFetch(jsonResponse(sleepJob));

  await createScan({ repo_url: "https://github.com/example/project", ref: "main" });

  const [url, init] = mock.mock.calls[0] as [string, RequestInit];
  expect(url).toBe("/api/scans");
  expect(init.method).toBe("POST");
  expect(init.headers).toMatchObject({
    Accept: "application/json",
    "Content-Type": "application/json",
  });
  expect(JSON.parse(init.body as string)).toEqual({
    repo_url: "https://github.com/example/project",
    ref: "main",
  });
});

it("encodes the scan id in every scan URL", async () => {
  const mock = stubFetch(() => jsonResponse(sleepJob));

  await getScan("scan/id");
  await getReport("scan/id");

  expect(mock.mock.calls[0][0]).toBe("/api/scans/scan%2Fid");
  expect(mock.mock.calls[1][0]).toBe("/api/scans/scan%2Fid/report");
});

it("returns the parsed rules catalog", async () => {
  stubFetch(jsonResponse({ version: "1", rules: [{ id: "MXR-TEST-001" }] }));

  await expect(getRules()).resolves.toEqual({
    version: "1",
    rules: [{ id: "MXR-TEST-001" }],
  });
});

it("uploads the verification file as the raw request body", async () => {
  const mock = stubFetch(jsonResponse(sleepJob));
  const file = new File(['{"schema_version":"1.0"}'], "result.json", {
    type: "application/json",
  });

  await uploadVerification(sleepJob.id, file);

  const [url, init] = mock.mock.calls[0] as [string, RequestInit];
  expect(url).toBe(`/api/scans/${sleepJob.id}/verification-runs`);
  expect(init.method).toBe("POST");
  expect(init.body).toBe(file);
});

it("maps a rejected fetch to a NETWORK_ERROR", async () => {
  stubFetch(new TypeError("Failed to fetch"));

  await expect(getScan(sleepJob.id)).rejects.toMatchObject({
    name: "MxReadyApiError",
    code: "NETWORK_ERROR",
  });
});

it("preserves the structured API error from a JSON error body", async () => {
  stubFetch(
    jsonResponse(
      {
        error: {
          code: "INVALID_REPOSITORY_URL",
          message: "请输入完整的公开仓库地址。",
          details: { field: "repo_url" },
        },
      },
      { status: 400 },
    ),
  );

  const error = await getScan(sleepJob.id).catch((reason: unknown) => reason);
  expect(error).toBeInstanceOf(MxReadyApiError);
  expect(error).toMatchObject({
    code: "INVALID_REPOSITORY_URL",
    message: "请输入完整的公开仓库地址。",
    details: { field: "repo_url" },
    status: 400,
  });
});

it("falls back to HTTP_ERROR when the error body is not JSON", async () => {
  stubFetch(
    new Response("<html>bad gateway</html>", {
      status: 502,
      headers: { "Content-Type": "text/html" },
    }),
  );

  const error = await getScan(sleepJob.id).catch((reason: unknown) => reason);
  expect(error).toBeInstanceOf(MxReadyApiError);
  expect(error).toMatchObject({
    code: "HTTP_ERROR",
    status: 502,
  });
  expect((error as MxReadyApiError).message).toContain("502");
});

import { useEffect, useState } from "react";

import { getReport, getScan, MxReadyApiError } from "../api/client";
import type { ScanJob, ScanReport } from "../api/types";

type ViewState =
  | { kind: "idle" }
  | { kind: "restoring"; scanId: string }
  | { kind: "scanning"; job: ScanJob }
  | { kind: "report-loading"; job: ScanJob }
  | { kind: "report"; report: ScanReport }
  | { kind: "error"; code: string; message: string; scanId?: string };

function fromJob(job: ScanJob): ViewState {
  if (job.status === "completed") return { kind: "report-loading", job };
  if (job.status === "failed") {
    return {
      kind: "error", code: job.failure_code ?? "SCAN_FAILED",
      message: job.failure_message ?? "扫描未能完成。",
    };
  }
  return { kind: "scanning", job };
}

function fromUrl(): ViewState {
  const scanId = new URL(window.location.href).searchParams.get("scan");
  return scanId && /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(scanId)
    ? { kind: "restoring", scanId }
    : { kind: "idle" };
}

function failure(error: unknown, scanId: string): ViewState {
  return {
    kind: "error", scanId,
    code: error instanceof MxReadyApiError ? error.code : "POLLING_FAILED",
    message: error instanceof Error ? error.message : "读取扫描失败，请稍后继续查看。",
  };
}

export function useScan(initialJob: ScanJob | undefined, pollIntervalMs: number) {
  const [view, setView] = useState<ViewState>(() => initialJob ? fromJob(initialJob) : fromUrl());

  useEffect(() => {
    const restore = () => setView(fromUrl());
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);

  useEffect(() => {
    const scanId = view.kind === "scanning" || view.kind === "report-loading"
      ? view.job.id
      : view.kind === "report" ? view.report.scan_id
      : view.kind === "restoring" || view.kind === "error" ? view.scanId : undefined;
    const url = new URL(window.location.href);
    if (scanId) url.searchParams.set("scan", scanId);
    else if (view.kind === "idle") url.searchParams.delete("scan");
    window.history.replaceState(null, "", url);
  }, [view]);

  useEffect(() => {
    if (view.kind !== "scanning" && view.kind !== "restoring") return;
    const controller = new AbortController();
    const scanId = view.kind === "restoring" ? view.scanId : view.job.id;
    let timer: ReturnType<typeof setTimeout>;
    let retries = 0;

    const poll = async () => {
      try {
        const job = await getScan(scanId, controller.signal);
        if (!controller.signal.aborted) setView(fromJob(job));
      } catch (error) {
        if (controller.signal.aborted) return;
        const retryable = !(error instanceof MxReadyApiError)
          || error.status === 0 || error.status === 429 || error.status >= 500;
        if (retryable && retries < 3) {
          retries += 1;
          timer = setTimeout(poll, Math.max(250, pollIntervalMs) * 2 ** retries);
        } else {
          setView(failure(error, scanId));
        }
      }
    };
    timer = setTimeout(poll, view.kind === "restoring" ? 0 : pollIntervalMs);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [view, pollIntervalMs]);

  useEffect(() => {
    if (view.kind !== "report-loading") return;
    const controller = new AbortController();
    getReport(view.job.id, controller.signal)
      .then((report) => {
        if (!controller.signal.aborted) setView({ kind: "report", report });
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setView(failure(error, view.job.id));
      });
    return () => controller.abort();
  }, [view]);

  return {
    view,
    reset: () => setView({ kind: "idle" }),
    onCreated: (job: ScanJob) => setView(fromJob(job)),
    onUpdated: (report: ScanReport) => setView({ kind: "report", report }),
    retry: () => {
      if (view.kind === "error" && view.scanId) {
        setView({ kind: "restoring", scanId: view.scanId });
      }
    },
  };
}

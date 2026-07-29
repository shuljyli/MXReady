import { type FormEvent, useState } from "react";

import { createScan } from "../api/client";
import type { ScanJob } from "../api/types";

type ScanFormProps = {
  onCreated: (job: ScanJob) => void;
};

type VisibleError = {
  code: string;
  message: string;
};

function normalizeError(error: unknown): VisibleError {
  if (
    typeof error === "object" &&
    error !== null &&
    "message" in error &&
    "code" in error
  ) {
    return {
      code: String(error.code),
      message: String(error.message),
    };
  }
  return {
    code: "UNEXPECTED_ERROR",
    message: "提交没有成功，请稍后重试。",
  };
}

export function ScanForm({ onCreated }: ScanFormProps) {
  const [repoUrl, setRepoUrl] = useState("");
  const [requestedRef, setRequestedRef] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<VisibleError | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) {
      return;
    }

    const normalizedUrl = repoUrl.trim();
    const normalizedRef = requestedRef.trim();
    setError(null);
    setSubmitting(true);
    try {
      const job = await createScan({
        repo_url: normalizedUrl,
        ref: normalizedRef || null,
      });
      onCreated(job);
    } catch (caught) {
      setError(normalizeError(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="scan-form" onSubmit={handleSubmit}>
      <div className="form-heading">
        <p className="eyebrow">开始一次源码体检</p>
        <h2>输入公开仓库</h2>
        <p>
          首版聚焦 Python、PyTorch 与 CUDA 扩展项目，不会执行仓库中的任何代码。
        </p>
      </div>

      <div className="field">
        <label htmlFor="repo-url">公开仓库地址</label>
        <input
          aria-describedby="repo-url-help"
          autoComplete="url"
          id="repo-url"
          inputMode="url"
          name="repo_url"
          onChange={(event) => setRepoUrl(event.target.value)}
          placeholder="https://github.com/owner/repository"
          required
          type="url"
          value={repoUrl}
        />
        <small id="repo-url-help">支持 GitHub 与 Gitee 的公开 HTTPS 仓库</small>
      </div>

      <div className="field">
        <label htmlFor="requested-ref">分支、标签或提交（可选）</label>
        <input
          autoComplete="off"
          id="requested-ref"
          maxLength={200}
          name="ref"
          onChange={(event) => setRequestedRef(event.target.value)}
          placeholder="默认扫描仓库主分支"
          value={requestedRef}
        />
      </div>

      {error ? (
        <div className="form-error">
          <span>{error.code}</span>
          <p role="alert">{error.message}</p>
        </div>
      ) : null}

      <button className="primary-button" disabled={submitting} type="submit">
        <span>{submitting ? "正在创建任务" : "开始体检"}</span>
        <span aria-hidden="true">{submitting ? "…" : "↗"}</span>
      </button>
    </form>
  );
}

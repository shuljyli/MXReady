import { type FormEvent, useState } from "react";

import { MxReadyApiError, uploadVerification } from "../api/client";
import type { ScanReport, VerificationStatus } from "../api/types";

type VerificationPanelProps = {
  report: ScanReport;
  onUpdated: (report: ScanReport) => void;
};

const MAX_UPLOAD_BYTES = 1_048_576;

const statusCopy: Record<
  VerificationStatus,
  { label: string; detail: string; tone: string }
> = {
  "not-run": {
    label: "尚未在沐曦 GPU 上验证",
    detail: "下载验证包，在可控的远程沐曦服务器上运行后上传 result.json。",
    tone: "pending",
  },
  verified: {
    label: "沐曦 GPU 环境验证已通过",
    detail: "验证结果来自相同提交，且仍在 30 天有效期内。",
    tone: "verified",
  },
  failed: {
    label: "沐曦 GPU 环境验证未通过",
    detail: "查看 result.json 的失败命令，修复后可以重新上传结果。",
    tone: "failed",
  },
  stale: {
    label: "硬件验证结果已经过期",
    detail: "结果超过 30 天，请在相同提交上重新运行验证包。",
    tone: "stale",
  },
};

function uploadError(error: unknown) {
  if (error instanceof MxReadyApiError) {
    return `${error.code}：${error.message}`;
  }
  if (
    typeof error === "object" &&
    error !== null &&
    "message" in error
  ) {
    return String(error.message);
  }
  return "验证结果上传失败，请检查文件后重试。";
}

export function VerificationPanel({
  report,
  onUpdated,
}: VerificationPanelProps) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const status = statusCopy[report.verification_status];
  const bundleUrl = `/api/scans/${report.scan_id}/verification-bundle`;

  function chooseFile(selected: File | undefined) {
    setFile(selected ?? null);
    setError(null);
    if (selected && selected.size > MAX_UPLOAD_BYTES) {
      setError("验证结果不能超过 1 MiB。");
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || uploading) {
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setError("验证结果不能超过 1 MiB。");
      return;
    }
    if (!file.name.toLowerCase().endsWith(".json")) {
      setError("请选择 .json 格式的验证结果。");
      return;
    }

    setError(null);
    setUploading(true);
    try {
      onUpdated(await uploadVerification(report.scan_id, file));
      setFile(null);
    } catch (caught) {
      setError(uploadError(caught));
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="verification-panel" aria-labelledby="verification-title">
      <div className="verification-heading">
        <div>
          <p className="eyebrow">REMOTE VERIFICATION</p>
          <h2 id="verification-title">沐曦真机验证</h2>
        </div>
        <span className={`verification-state state-${status.tone}`}>
          {status.label}
        </span>
      </div>
      <p className="verification-detail">{status.detail}</p>

      <div className="verification-truth">
        <strong>结论边界</strong>
        <p>
          静态检查只会发现已编码的迁移风险，不代表项目已经兼容
          MXMACA。只有相同提交在沐曦 GPU
          上完成验证后，状态才会变为“已验证”。
        </p>
      </div>

      <ol className="verification-steps">
        <li>
          <span>01</span>
          <div>
            <strong>下载并审阅</strong>
            <p>先阅读 SECURITY.md 与 mxready.yml 中的全部命令。</p>
          </div>
        </li>
        <li>
          <span>02</span>
          <div>
            <strong>在远程服务器运行</strong>
            <code>
              python -m mxready_runner inspect --manifest mxready.yml --output
              result.json
            </code>
          </div>
        </li>
        <li>
          <span>03</span>
          <div>
            <strong>人工检查并上传</strong>
            <p>确认输出已脱敏，再把 result.json 上传到这里。</p>
          </div>
        </li>
      </ol>

      <div className="verification-actions">
        <a
          aria-label="下载远程验证包"
          className="bundle-link"
          href={bundleUrl}
        >
          <span>
            <small>ZIP · 标准库 runner</small>
            下载远程验证包
          </span>
          <span aria-hidden="true">↓</span>
        </a>

        <form className="upload-form" onSubmit={submit}>
          <label htmlFor="verification-file">选择验证结果 JSON</label>
          <div className="file-control">
            <input
              accept=".json,application/json"
              id="verification-file"
              onChange={(event) => chooseFile(event.target.files?.[0])}
              type="file"
            />
            <span>{file ? file.name : "尚未选择文件"}</span>
          </div>
          {error ? <p role="alert">{error}</p> : null}
          <button
            className="upload-button"
            disabled={!file || uploading}
            type="submit"
          >
            {uploading ? "正在校验…" : "上传验证结果"}
          </button>
        </form>
      </div>
    </section>
  );
}

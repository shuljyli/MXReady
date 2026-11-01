import { useState, type FormEvent } from "react";

export function OpenScanForm({ onOpen }: { onOpen: (scanId: string) => void }) {
  const [scanId, setScanId] = useState("");
  const [error, setError] = useState(false);
  function submit(event: FormEvent) {
    event.preventDefault();
    const id = scanId.trim();
    if (!/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(id)) {
      setError(true); return;
    }
    setError(false); onOpen(id);
  }
  return <details className="report-section open-scan">
    <summary>打开已有扫描</summary>
    <form onSubmit={submit}>
      <label className="field">扫描 ID<input value={scanId} onChange={(event) => {
        setScanId(event.target.value); setError(false);
      }} placeholder="扫描任务 UUID" aria-invalid={error} aria-describedby={error ? "scan-id-error" : undefined} required /></label>
      {error ? <p id="scan-id-error" role="alert">请输入完整的扫描 UUID。</p> : null}
      <button className="secondary-button" type="submit">打开扫描</button>
    </form>
  </details>;
}

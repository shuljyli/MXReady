import { useEffect, useRef, useState } from "react";

export function CopyButton({ text, label }: { text: string; label: string }) {
  const [state, setState] = useState<"idle" | "copied" | "manual">("idle");
  const fallback = useRef<HTMLTextAreaElement>(null);
  useEffect(() => { setState("idle"); }, [text]);
  useEffect(() => {
    if (state === "manual") {
      fallback.current?.focus();
      fallback.current?.select();
    }
  }, [state]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setState("copied");
    } catch {
      setState("manual");
    }
  }

  return (
    <span className="copy-control">
      <button className="secondary-button compact-button" type="button" onClick={copy}>{label}</button>
      <span className="copy-feedback" role="status">
        {state === "copied" ? "已复制" : state === "manual" ? "无法访问剪贴板，请手动复制。" : ""}
      </span>
      {state === "manual" ? <textarea ref={fallback} aria-label={"复制内容：" + label}
        readOnly value={text} rows={4} /> : null}
    </span>
  );
}

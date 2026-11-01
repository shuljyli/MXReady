import { CopyButton } from "./CopyButton";

export function CodeSnippet({ text, label }: { text: string; label: string }) {
  return <div className="code-snippet">
    <pre><code>{text}</code></pre>
    <CopyButton label={label} text={text} />
  </div>;
}

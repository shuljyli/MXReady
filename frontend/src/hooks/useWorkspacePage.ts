import { useEffect, useState } from "react";

export type WorkspacePage = "scan" | "history" | "rules" | "mcp" | "cli";
type Location = { page: WorkspacePage; ruleId?: string; ruleVersion?: number };

function readLocation(): Location {
  const params = new URL(window.location.href).searchParams;
  const page = params.get("page");
  const version = Number(params.get("ruleVersion"));
  return {
    page: page === "rules" || page === "mcp" || page === "cli" || page === "history" ? page : "scan",
    ruleId: params.get("rule") ?? undefined,
    ruleVersion: version >= 1 && Number.isInteger(version) ? version : undefined,
  };
}

export function workspaceHref(page: WorkspacePage) {
  const url = new URL(window.location.href);
  if (page === "scan") url.searchParams.delete("page");
  else url.searchParams.set("page", page);
  url.searchParams.delete("rule");
  url.searchParams.delete("ruleVersion");
  return url.pathname + url.search;
}

export function useWorkspacePage() {
  const [location, setLocation] = useState(readLocation);
  useEffect(() => {
    const restore = () => setLocation(readLocation());
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);
  function navigate(page: WorkspacePage, ruleId?: string, ruleVersion?: number) {
    const url = new URL(workspaceHref(page), window.location.origin);
    if (ruleId) url.searchParams.set("rule", ruleId);
    if (ruleVersion !== undefined) url.searchParams.set("ruleVersion", String(ruleVersion));
    window.history.pushState(null, "", url);
    setLocation({ page, ruleId, ruleVersion });
  }
  return { ...location, navigate };
}
